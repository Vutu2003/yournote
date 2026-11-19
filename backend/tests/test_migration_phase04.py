"""Offline backup, legacy migration, idempotency and rollback in private temp stores."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from qdrant_client import models

from src.config import settings
from src.data_guard import data_guard
from src.migration import migrate,rollback,verify_backup
from src import documents
from src.store import close_client,get_client
from backend.tests.test_reading import write_pdf
from backend.main import app
from fastapi.testclient import TestClient


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory(prefix='phase04-migration-')))
        self.enterContext(patch.object(settings,'storage_dir',self.root/'storage/qdrant'))
        self.enterContext(patch.object(settings,'data_dir',self.root/'data'))
        self.enterContext(patch('backend.services.notebooks._database_path',return_value=self.root/'storage/notebooks.sqlite'))
        settings.data_dir.mkdir();write_pdf(settings.data_dir/'legacy.pdf','Legacy study evidence unchanged.')
        self.bytes=(settings.data_dir/'legacy.pdf').read_bytes()
        client=get_client();client.create_collection(settings.qdrant_collection,vectors_config=models.VectorParams(size=8,distance=models.Distance.COSINE))
        client.upsert(settings.qdrant_collection,[models.PointStruct(id=1,vector=[1.]*8,payload={'page_content':'Legacy study evidence unchanged.','metadata':{
            'document_id':'old-id-16','filename':'legacy.pdf','source':str(settings.data_dir/'legacy.pdf'),'page':1,'chunk_id':'old-id-16:1:0'}})])
        close_client();self.addCleanup(close_client)
        self.state={'document_filenames':['legacy.pdf'],'selected':['legacy.pdf'],'source_names':{'legacy.pdf':'My old alias'},'read_documents':['legacy.pdf'],
            'chat':[{'question':'Old question','answer':'Old answer [S1]','citations':[{'source_index':1,'source_marker':'S1','filename':'legacy.pdf','page':1,'source_text':'Legacy study evidence unchanged.','chunk_id':'old-id-16:1:0'}]}],
            'summary_artifacts':[{'id':'old-summary','title':'Existing summary','createdAt':1,'sourceFilenames':['legacy.pdf'],'pages':[],'topic':None,
                'result':{'scope':'document','summary':'Legacy summary','key_points':[],'citations':[]}}]}
        with sqlite3.connect(self.root/'storage/notebooks.sqlite') as connection:
            connection.execute('CREATE TABLE notebooks (id TEXT PRIMARY KEY,title TEXT,icon TEXT,created_at TEXT,updated_at TEXT,state TEXT)')
            connection.execute('INSERT INTO notebooks VALUES (?,?,?,?,?,?)',('old-book','Legacy','📓','2026-01-01','2026-01-01',json.dumps(self.state)))
            connection.execute('CREATE TABLE migrations(name TEXT PRIMARY KEY)');connection.execute("INSERT INTO migrations VALUES ('legacy_sources')")

    def test_legacy_roundtrip_idempotency_and_original_citations(self):
        first=migrate(backup_directory=self.root/'backup-1');self.assertEqual(first['registered'],1)
        second=migrate(backup_directory=self.root/'backup-2');self.assertEqual(second['registered'],0)
        self.assertEqual(documents.get_document(filename='legacy.pdf')['id'],'old-id-16')
        with TestClient(app) as client:
            book=client.get('/api/notebooks/old-book').json()
            self.assertEqual(book['state']['source_names'],self.state['source_names'])
            self.assertEqual(book['state']['read_documents'],['legacy.pdf'])
            self.assertEqual(book['state']['summary_artifacts'][0]['id'],'old-summary')
            citation=self.state['chat'][0]['citations'][0]
            resolved=client.post('/api/notebooks/old-book/citations/resolve',json=citation)
            self.assertEqual(resolved.status_code,200,resolved.text)
            self.assertEqual(resolved.json()['locator']['page'],1)
            original=client.get('/api/notebooks/old-book/documents/old-id-16/pdf')
            self.assertEqual(original.content,self.bytes)
        restored=rollback(self.root/'backup-1');self.assertTrue(restored['restored'])
        self.assertFalse(documents.database_path().exists())
        self.assertEqual((settings.data_dir/'legacy.pdf').read_bytes(),self.bytes)
        with sqlite3.connect(self.root/'storage/notebooks.sqlite') as connection:
            self.assertEqual(json.loads(connection.execute('SELECT state FROM notebooks').fetchone()[0]),self.state)
        payload=get_client().scroll(settings.qdrant_collection)[0][0].payload
        self.assertEqual(payload['metadata']['document_id'],'old-id-16');self.assertNotIn('document_version',payload['metadata'])

    def test_live_backend_guard_and_open_qdrant_refuse_migration(self):
        with data_guard():
            with self.assertRaisesRegex(RuntimeError,'Stop the backend'): migrate(backup_directory=self.root/'refused')
        get_client()
        with self.assertRaisesRegex(RuntimeError,'Close the index'): migrate(backup_directory=self.root/'refused')
        self.assertFalse((self.root/'refused').exists())

    def test_corrupt_backup_is_rejected_before_restore_changes_data(self):
        migrate(backup_directory=self.root/'backup')
        original=next((self.root/'backup/data').glob('*.pdf'));original.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'checksum'): rollback(self.root/'backup')
        self.assertEqual((settings.data_dir/'legacy.pdf').read_bytes(),self.bytes)

    def test_legacy_excerpt_mismatch_cannot_be_retargeted(self):
        migrate(backup_directory=self.root/'backup')
        with TestClient(app) as client:
            citation={**self.state['chat'][0]['citations'][0],'source_text':'An old revision whose content is no longer here.'}
            response=client.post('/api/notebooks/old-book/citations/resolve',json=citation)
            self.assertEqual(response.status_code,409)

    def test_backup_manifest_contains_no_credentials(self):
        migrate(backup_directory=self.root/'backup')
        manifest=verify_backup(self.root/'backup')
        self.assertEqual(set(manifest['present']),{'qdrant','data','notebooks.sqlite','documents.sqlite'})
        self.assertTrue(all(not any(part in name.lower() for part in ['.env','chatgpt','credential']) for name in manifest['sha256']))

    def test_legacy_citation_without_version_stays_on_migration_snapshot_after_update(self):
        from src.indexing import save_and_ingest_document
        from backend.tests.test_documents_phase04 import TinyEmbeddings
        self.enterContext(patch('src.store.get_embeddings',return_value=TinyEmbeddings()))
        migrate(backup_directory=self.root/'backup')
        previous=documents.get_document(filename='legacy.pdf')['active_version']
        revised=self.root/'revision.pdf';write_pdf(revised,'Replacement content with a different fact.')
        save_and_ingest_document(revised.read_bytes(),'legacy.pdf',replace_document_id='old-id-16',expected_version=previous)
        close_client()
        with TestClient(app) as client:
            resolved=client.post('/api/notebooks/old-book/citations/resolve',json=self.state['chat'][0]['citations'][0])
            self.assertEqual(resolved.status_code,200,resolved.text)
            self.assertEqual(resolved.json()['document']['document_version'],previous)
            self.assertTrue(resolved.json()['document']['historical'])
            old=client.get(f'/api/notebooks/old-book/documents/old-id-16/pdf?version={previous}')
            self.assertEqual(old.content,self.bytes)

    def test_failed_migration_blocks_startup_until_retry_finishes(self):
        with patch('src.documents.commit_document',side_effect=RuntimeError('simulated failure')):
            with self.assertRaises(RuntimeError): migrate(backup_directory=self.root/'backup')
        with self.assertRaisesRegex(RuntimeError,'incomplete'):
            with data_guard(): pass
        result=migrate(backup_directory=self.root/'retry-backup')
        self.assertEqual(result['registered'],1)
        with data_guard(): pass

    def test_rebuild_does_not_revert_updated_legacy_source_from_original_file(self):
        from src.indexing import save_and_ingest_document,ingest
        from src.rag import fetch_all_chunks
        from backend.tests.test_documents_phase04 import TinyEmbeddings
        self.enterContext(patch('src.store.get_embeddings',return_value=TinyEmbeddings()))
        migrate(backup_directory=self.root/'backup')
        previous=documents.get_document(filename='legacy.pdf')['active_version']
        revised=self.root/'revision.pdf';write_pdf(revised,'Replacement content with a different fact.')
        updated=save_and_ingest_document(revised.read_bytes(),'legacy.pdf',replace_document_id='old-id-16',expected_version=previous)
        ingest(recreate=True)
        self.assertEqual(documents.get_document(filename='legacy.pdf')['active_version'],updated['document_version'])
        chunks=fetch_all_chunks(filters={'filename':'legacy.pdf'})
        self.assertTrue(chunks);self.assertTrue(all(c.metadata.document_version==updated['document_version'] for c in chunks))
