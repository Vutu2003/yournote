"""Only scoped completed notebook history can clarify a follow-up query."""
from types import SimpleNamespace
import unittest
from backend.schemas.api import SourceSelection,ChatResponse
from backend.schemas.notebooks import WorkspaceState
from src.conversation import contextual_query,scoped_history


class HistoryTests(unittest.TestCase):
    def turn(self,filename='a.md',version='a'*64,page=None):
        return ChatResponse(question='Explain assignment QZ-417',answer='Earlier draft claim is not evidence [S1]',citations=[{
            'source_index':1,'source_marker':'S1','filename':filename,'page':page,'document_version':version}])

    def history(self,turns,filenames=None,pages=None,versions=None):
        workspace=SimpleNamespace(state=WorkspaceState(chat=turns))
        sources=SourceSelection(filenames=filenames or ['a.md'],pages=pages or [])
        return scoped_history(workspace,sources,versions or {'a.md':'a'*64})

    def test_scope_and_versions_are_checked_and_history_is_bounded(self):
        turns=[self.turn() for _ in range(10)]+[self.turn('outside.md'),self.turn(version='b'*64)]
        history=self.history(turns)
        self.assertEqual(len(history),3)
        self.assertTrue(all(turn['filenames']==['a.md'] for turn in history))
        query=contextual_query('Vậy nó nộp khi nào?',history)
        self.assertIn('QZ-417',query)
        self.assertNotIn('Earlier draft',query)

    def test_unknown_legacy_version_is_not_reused_after_migration(self):
        self.assertEqual(self.history([self.turn(version=None)]),[])

    def test_page_scope_and_unrelated_new_questions(self):
        history=self.history([self.turn(filename='a.pdf',page=2)],filenames=['a.pdf'],pages=[1],versions={'a.pdf':'a'*64})
        self.assertEqual(history,[])
        self.assertEqual(contextual_query('Define eigenvector',[{'question':'Unrelated assignment'}]),'Define eigenvector')
