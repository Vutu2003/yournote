"""Synthetic formats, immutable identity, source scope and version-aware citations."""
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from pypdf import PdfWriter

from backend.main import app
from backend.services import notebooks
from backend.schemas.notebooks import NotebookCreate, NotebookUpdate
from src.config import settings
from src.document_parser import extract, DocumentParseError
from src.indexing import save_and_ingest_document
from src import documents, rag
from src.store import close_client, get_client, list_documents
from backend.tests.test_reading import write_pdf


def docx(text='Lecture notes', heading='Vectors'):
    from xml.sax.saxutils import escape
    result=BytesIO()
    with ZipFile(result,'w',ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>'+escape(heading)+'</w:t></w:r></w:p><w:p><w:r><w:t>'+escape(text)+'</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table evidence 42</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
    return result.getvalue()


class TinyEmbeddings(Embeddings):
    def embed_query(self,text): return [float(text.casefold().count(c)+1) for c in 'abcdefgh']
    def embed_documents(self,texts): return [self.embed_query(text) for text in texts]


class ParserTests(unittest.TestCase):
    def test_docx_preserves_heading_and_table_order_without_pages(self):
        result=extract(docx(),'.docx')
        self.assertEqual(result['page_count'],0)
        self.assertEqual([b['locator']['anchor'] for b in result['blocks']],['b000001','b000002','b000003'])
        self.assertEqual(result['blocks'][1]['locator']['heading'],['Vectors'])
        self.assertIn('42',result['blocks'][2]['text'])
        self.assertTrue(all('page' not in b['locator'] for b in result['blocks']))

    def test_markdown_headings_and_html_are_text_only(self):
        result=extract(b'# Course\n\n<script>window.pwned=1</script>\n\n## Topic\n\nFact 42.','.md')
        self.assertEqual(result['blocks'][-1]['locator']['heading'],['Course','Topic'])
        self.assertIn('<script>',result['blocks'][1]['text'])
        self.assertEqual(result,extract(b'# Course\n\n<script>window.pwned=1</script>\n\n## Topic\n\nFact 42.','.md'))

    def test_bad_empty_binary_and_wrong_formats_are_rejected(self):
        for content,extension in [(b'', '.txt'),(b'\xff\x00','.txt'),(b'PK\x03\x04','.md'),(b'%PDF-fake','.pdf'),(b'not a zip','.docx'),(b'text','.exe')]:
            with self.subTest(extension=extension),self.assertRaises(DocumentParseError): extract(content,extension)

    def test_scanned_pdf_reports_ocr(self):
        pdf=BytesIO();writer=PdfWriter();writer.add_blank_page(100,100);writer.write(pdf)
        with self.assertRaisesRegex(DocumentParseError,'OCR'): extract(pdf.getvalue(),'.pdf')

    def test_zip_bomb_and_entity_declarations_are_rejected(self):
        archive=BytesIO()
        with ZipFile(archive,'w',ZIP_DEFLATED) as writer:
            writer.writestr('[Content_Types].xml','x');writer.writestr('word/document.xml','x'*1_000_000)
        with self.assertRaisesRegex(DocumentParseError,'compression'): extract(archive.getvalue(),'.docx')
        archive=BytesIO()
        with ZipFile(archive,'w') as writer:
            writer.writestr('[Content_Types].xml','x');writer.writestr('word/document.xml','<!DOCTYPE a [<!ENTITY e "boom">]><a>&e;</a>')
        with self.assertRaisesRegex(DocumentParseError,'XML'): extract(archive.getvalue(),'.docx')


class DocumentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory(prefix='phase04-doc-test-')))
        self.enterContext(patch.object(settings,'storage_dir',self.root/'qdrant'))
        self.enterContext(patch.object(settings,'data_dir',self.root/'data'))
        self.enterContext(patch('src.store.get_embeddings',return_value=TinyEmbeddings()))
        self.enterContext(patch('backend.services.notebooks._database_path',return_value=self.root/'notebooks.sqlite'))
        self.addCleanup(close_client)
        self.client=self.enterContext(TestClient(app))

    def upload(self,filename,content):
        response=self.client.post('/api/documents/upload',files={'file':(filename,content,'application/octet-stream')})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def notebook(self,*sources):
        notebook=notebooks.create_notebook(NotebookCreate(title='Synthetic'))
        notebook.state.document_filenames=list(sources);notebook.state.selected=list(sources)
        return notebooks.update_notebook(notebook.id,NotebookUpdate(title=notebook.title,icon=notebook.icon,state=notebook.state))

    def citation(self,source):
        chunks=rag.fetch_all_chunks(filters={'filename':source['filename']})
        return rag.format_citations(chunks)[-1].model_dump()

    def test_all_four_formats_and_downloads_preserve_original(self):
        pdf=self.root/'slides.pdf';write_pdf(pdf,'Synthetic lecture slide about vectors.')
        for filename,content in [('slides.pdf',pdf.read_bytes()),('textbook.docx',docx()),('notes.md',b'# Notes\n\nFact 42.'),('notes.txt',b'Fact 42.\n\nA second paragraph.')]:
            with self.subTest(format=filename):
                source=self.upload(filename,content);book=self.notebook(source['filename'])
                info=self.client.get(f'/api/notebooks/{book.id}/documents/{source["document_id"]}').json()
                self.assertEqual(info['document_version'],source['document_version'])
                original=self.client.get(f'/api/notebooks/{book.id}/documents/{source["document_id"]}/original')
                self.assertEqual(original.content,content)
                if not filename.endswith('.pdf'):
                    self.assertEqual(info['page_count'],0)
                    chunks=rag.fetch_all_chunks(filters={'filename':source['filename']})
                    self.assertTrue(all(c.metadata.page is None and c.metadata.locator.kind=='paragraph' for c in chunks))
                    text=self.client.get(f'/api/notebooks/{book.id}/documents/{source["document_id"]}/text').json()
                    self.assertTrue(text['blocks'])

    def test_same_name_same_size_different_content_and_repeat_upload(self):
        a=self.upload('notes.md',b'# Topic\n\nValue 11.')
        b=self.upload('notes.md',b'# Topic\n\nValue 22.')
        self.assertNotEqual(a['filename'],b['filename']);self.assertNotEqual(a['document_id'],b['document_id'])
        again=self.upload('another.md',b'# Topic\n\nValue 11.')
        self.assertTrue(again['deduplicated']);self.assertEqual(a['document_id'],again['document_id'])
        self.assertEqual(len(list_documents()),2)

    def test_explicit_replacement_removes_stale_chunks_and_old_citation_opens_old_version(self):
        source=self.upload('notes.md',b'# Original\n\nOld evidence 11.\n\nOld extra paragraph.')
        book=self.notebook(source['filename']);citation=self.citation(source)
        response=self.client.post(f'/api/documents/{source["document_id"]}/versions?expected_version={source["document_version"]}',files={'file':('notes.md',b'# Updated\n\nNew evidence 22.','text/markdown')})
        self.assertEqual(response.status_code,200,response.text);updated=response.json()
        self.assertEqual(updated['filename'],source['filename']);self.assertEqual(updated['document_id'],source['document_id'])
        chunks=rag.fetch_all_chunks(filters={'filename':source['filename']})
        self.assertTrue(all('Old' not in c.text for c in chunks))
        self.assertTrue(all(c.metadata.document_version==updated['document_version'] for c in chunks))
        resolved=self.client.post(f'/api/notebooks/{book.id}/citations/resolve',json=citation)
        self.assertEqual(resolved.status_code,200,resolved.text)
        self.assertEqual(resolved.json()['document']['document_version'],source['document_version'])
        self.assertTrue(resolved.json()['document']['historical'])
        old=self.client.get(f'/api/notebooks/{book.id}/documents/{source["document_id"]}/text?version={source["document_version"]}').json()
        self.assertTrue(any('Old' in b['text'] for b in old['blocks']))
        stale=self.client.post(f'/api/documents/{source["document_id"]}/versions?expected_version={source["document_version"]}',files={'file':('notes.md',b'Newer','text/markdown')})
        self.assertEqual(stale.status_code,400)

    def test_forged_version_locator_excerpt_and_other_notebook_are_rejected(self):
        source=self.upload('notes.txt',b'Genuine evidence 42.')
        book=self.notebook(source['filename']);other=self.notebook();citation=self.citation(source)
        for patch_value in [{'document_version':'f'*64},{'source_text':'Invented evidence'},{'locator':{'kind':'paragraph','anchor':'b000099','paragraph':99}}]:
            with self.subTest(patch_value=patch_value):
                response=self.client.post(f'/api/notebooks/{book.id}/citations/resolve',json={**citation,**patch_value})
                self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(self.client.post(f'/api/notebooks/{other.id}/citations/resolve',json=citation).status_code,404)

    def test_page_filter_is_not_accepted_for_text_and_versions_are_checked(self):
        source=self.upload('notes.txt',b'Scoped evidence 42.')
        response=self.client.post('/api/chat',json={'question':'What?','filenames':[source['filename']],'pages':[1]})
        self.assertEqual(response.status_code,422)
        from backend.schemas.api import SourceSelection
        from backend.services.core_adapter import _filters,AdapterError
        with self.assertRaises(AdapterError): _filters(SourceSelection(filenames=[source['filename']],document_versions={source['filename']:'f'*64}))

    def test_lexical_vector_and_all_chunk_branches_keep_exact_source_scope(self):
        chosen=self.upload('a.md',b'# Assignment\n\nCode ZX-417 deadline 18 April.')
        outside=self.upload('b.md',b'# Assignment\n\nCode ZX-417 deadline 25 May. PRIVATE_OUTSIDE_SELECTION')
        for query in ['ZX-417 deadline','nonsense secret']:
            for function in [rag.retrieve,rag.retrieve_vector]:
                hits=function(query,k=8,filters={'filename':chosen['filename']})
                self.assertTrue(all(h.metadata.filename==chosen['filename'] and 'PRIVATE_OUTSIDE' not in h.text for h in hits))
        self.assertNotEqual(chosen['filename'],outside['filename'])

    def test_archive_tampering_is_detected(self):
        source=self.upload('notes.txt',b'Original evidence.')
        version=documents.get_version(source['document_id'])
        path=documents.original_path(version);path.write_bytes(b'Changed evidence!')
        with self.assertRaisesRegex(ValueError,'checksum'): documents.original_path(version)

    def test_embedding_model_change_cannot_mix_same_dimension_vectors(self):
        self.upload('notes.txt',b'Original evidence.')
        with patch.object(settings,'embedding_model','different-model'):
            with self.assertRaisesRegex(ValueError,'Embedding model'): rag.retrieve('query',filters={'filename':list_documents()[0]['filename']})

    def test_unreferenced_marker_rejected_and_no_context_does_not_call_model(self):
        source=self.upload('notes.txt',b'Fact 42.')
        chunks=rag.fetch_all_chunks(filters={'filename':source['filename']})
        from src.errors import LLMServiceError
        with patch('src.rag.invoke_llm',return_value='Invented [S999]'):
            with self.assertRaises(LLMServiceError): rag.answer_from_chunks('Question',chunks)
        with patch('src.rag.invoke_llm') as inference:
            result=rag.answer_from_chunks('Question',[])
        inference.assert_not_called();self.assertEqual(result.citations,[])
        self.assertIn('không có đủ',result.answer)

    def test_failed_new_ingestion_leaves_no_visible_staged_source(self):
        from src.indexing import index_chunks
        def partial(chunks,collection_name=None):
            index_chunks(chunks[:1],collection_name=collection_name)
            raise RuntimeError('simulated write failure')
        with patch('src.indexing.index_chunks',side_effect=partial):
            with self.assertRaises(RuntimeError): save_and_ingest_document(b'# Stage\n\nUncommitted text.','stage.md')
        self.assertEqual(list_documents(),[])
        self.assertEqual(documents.all_documents(),[])
        self.assertEqual(rag.fetch_all_chunks(),[])
        self.assertEqual(rag.retrieve('Uncommitted',k=3),[])

    def test_failed_update_keeps_old_active_version_and_retry_cleans_staging(self):
        from src.indexing import index_chunks
        source=self.upload('notes.md',b'# Old\n\nOld evidence.')
        def partial(chunks,collection_name=None):
            index_chunks(chunks[:1],collection_name=collection_name)
            raise RuntimeError('simulated write failure')
        with patch('src.indexing.index_chunks',side_effect=partial):
            with self.assertRaises(RuntimeError):
                save_and_ingest_document(b'# New\n\nNew evidence.','notes.md',replace_document_id=source['document_id'],expected_version=source['document_version'])
        active=rag.fetch_all_chunks(filters={'filename':source['filename']})
        self.assertTrue(active);self.assertTrue(all(c.metadata.document_version==source['document_version'] for c in active))
        updated=save_and_ingest_document(b'# New\n\nNew evidence.','notes.md',replace_document_id=source['document_id'],expected_version=source['document_version'])
        points=get_client().scroll(settings.qdrant_collection)[0]
        self.assertTrue(all(p.payload['metadata']['document_version']==updated['document_version'] for p in points))

    def test_non_pdf_export_has_anchor_and_version_without_fake_page(self):
        from src.export import export
        from src.schemas import RagAnswer
        source=self.upload('notes.md',b'# Heading\n\nFact 42.')
        citation=rag.format_citations(rag.fetch_all_chunks(filters={'filename':source['filename']}))[-1]
        markdown=export(RagAnswer(question='What?',answer='Fact [S2]',citations=[citation]),fmt='md')
        self.assertIn('anchor: b000002',markdown);self.assertIn('đoạn 2',markdown)
        self.assertIn(source['document_version'],markdown);self.assertNotIn('p.None',markdown)

    def test_same_content_reupload_repairs_missing_index(self):
        source=self.upload('notes.txt',b'Repairable evidence 42.')
        get_client().delete_collection(settings.qdrant_collection)
        repaired=self.upload('notes.txt',b'Repairable evidence 42.')
        self.assertEqual(repaired['document_id'],source['document_id'])
        self.assertEqual(len(list_documents()),1)

    def test_studio_fetch_vector_lexical_and_map_reduce_stay_inside_new_source(self):
        import re
        from backend.services import core_adapter
        from backend.schemas.api import SummaryRequest,QuizRequest,FlashcardsRequest,MindMapRequest
        chosen=self.upload('study.md',b'# Topic\n\nSelected evidence 42.')
        self.upload('other.txt',b'PRIVATE_OUTSIDE_SELECTION must never be included.')
        prompts=[]
        def output(prompt,feature):
            prompts.append(prompt)
            markers=re.findall(r'\[source=(S\d+)\]',prompt) or re.findall(r'\[(S\d+)\]',prompt) or ['S1']
            marker=markers[0]
            if feature=='summary': return json.dumps({'summary':'Selected evidence 42 ['+marker+']','key_points':[]})
            if feature=='quiz': return json.dumps({'items':[{'question':'Which?','options':['42','0','1','2'],'correct_index':0,'explanation':'42','source_markers':[marker]}]})
            if feature=='flashcards': return json.dumps({'cards':[{'front':'Evidence?','back':'42','source_markers':[marker]}]})
            return json.dumps({'root':{'label':'Topic','children':[{'label':'42','source_markers':[marker]}]}})
        for topic in (None,'Selected evidence'):
            for feature,model in [('summary',SummaryRequest),('quiz',QuizRequest),('flashcards',FlashcardsRequest),('mindmap',MindMapRequest)]:
                with self.subTest(feature=feature,topic=topic),patch('src.learning.invoke_llm',side_effect=lambda prompt:output(prompt,feature)),patch('src.mindmap.invoke_llm',side_effect=lambda prompt:output(prompt,feature)),patch.object(settings,'summarize_batch_size',1),patch.object(settings,'mindmap_batch_size',1):
                    result=getattr(core_adapter,feature)(model(filenames=[chosen['filename']],topic=topic))
                    self.assertTrue(result.citations)
                    self.assertTrue(all(c.filename==chosen['filename'] and c.document_version==chosen['document_version'] and c.locator.kind=='paragraph' for c in result.citations))
        self.assertTrue(prompts);self.assertTrue(all('PRIVATE_OUTSIDE_SELECTION' not in prompt for prompt in prompts))

    def test_cli_rebuild_includes_archive_only_uploads(self):
        from src.indexing import ingest
        source=self.upload('notes.md',b'# Rebuild\n\nEvidence 42.')
        self.assertFalse((settings.data_dir/'notes.md').exists())
        self.assertGreater(ingest(recreate=True),0)
        self.assertEqual(list_documents()[0]['document_id'],source['document_id'])
        again=self.upload('notes.md',b'# Rebuild\n\nEvidence 42.')
        self.assertTrue(again['deduplicated'])

    def test_pdf_hyphen_at_chunk_boundary_keeps_exact_facts(self):
        from src.grounding import normalized
        self.assertIn(normalized('a line-'),normalized('a line-\nbreak'))
        self.assertNotEqual(normalized('value -2'),normalized('value 2'))
        self.assertNotEqual(normalized('deadline 18'),normalized('deadline 19'))
