"""Conservative aliases/homonyms and unsupported relation contracts."""
import unittest
from pydantic import ValidationError
from src.research_schemas import SourceCoverage,SourceGraph,KnowledgeGraph
from src.schemas import Citation
from src.knowledge import build_network
from src.errors import LLMServiceError


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.quote='Python programming language uses code. Python animal eats prey. MSE means mean squared error.'
        self.sources=[SourceCoverage(filename=f'{i}.md',document_id=str(i),document_version='a'*64,total_chunks=1,examined_chunk_ids=[str(i)],coverage='complete') for i in range(3)]
        self.citations=[Citation(source_index=i+1,source_marker=f'S{i+1}',filename=f'{i}.md',document_id=str(i),document_version='a'*64,chunk_id=str(i),source_text=self.quote) for i in range(3)]
    def statement(self,marker='S1',quote=None):return {'text':'Supported concept.','evidence':[{'source_marker':marker,'quote':quote or self.quote}]}
    def node(self,id,label,key,marker='S1',aliases=None):return {'id':id,'label':label,'meaning_key':key,'aliases':aliases or [],'definition':self.statement(marker)}
    def edge(self,a,b,marker='S1'):return {'source':a,'target':b,'relation':'uses','statement':self.statement(marker)}
    def test_documented_synonyms_merge_and_homonyms_stay_separate(self):
        first=SourceGraph(nodes=[self.node('a','Python','programming'),self.node('b','code','code'),self.node('m','MSE','mean_squared_error')],edges=[self.edge('a','b')])
        second=SourceGraph(nodes=[self.node('a','Python','animal','S2'),self.node('b','prey','prey','S2'),self.node('m','mean squared error','mean_squared_error','S2',['MSE'])],edges=[self.edge('a','b','S2')])
        result=build_network(self.sources[:2],self.citations[:2],[first,second],'Learn')
        self.assertEqual(len(result.nodes),5)
        self.assertEqual(len([n for n in result.nodes if n.label=='Python']),2)
        mse=next(n for n in result.nodes if n.meaning_key=='mean_squared_error')
        self.assertIn('mean squared error',mse.aliases)
        self.assertEqual({r.source_marker for r in mse.definition.evidence},{'S1','S2'})
    def test_missing_quote_wrong_marker_unknown_endpoint_and_type_are_discarded(self):
        valid=self.edge('a','b')
        bad=[{**valid,'statement':{'text':'Unsupported','evidence':[]}},self.edge('a','b','S999'),self.edge('a','absent'),{**valid,'relation':'invented'},{**valid,'statement':self.statement(quote='An invented quotation.')}]
        extracted=SourceGraph(nodes=[self.node('a','Python','language'),self.node('b','code','code')],edges=[valid,*bad])
        result=build_network(self.sources[:1],self.citations[:1],[extracted],'Study')
        self.assertEqual(result.discarded_relations,5);self.assertEqual(len(result.edges),1)
        extracted.edges=bad
        with self.assertRaises(LLMServiceError):build_network(self.sources[:1],self.citations[:1],[extracted],'Study')
    def test_unknown_named_node_and_duplicate_local_id_rejected(self):
        for nodes in [[self.node('a','Invented','missing'),self.node('b','code','code')],[self.node('a','Python','language'),self.node('a','code','code')]]:
            with self.assertRaises(LLMServiceError):build_network(self.sources[:1],self.citations[:1],[SourceGraph(nodes=nodes,edges=[self.edge('a','b')])],'Study')
    def test_network_bounds_and_persisted_endpoint_validation(self):
        extracted=[]
        for i in range(3):
            extracted.append(SourceGraph(nodes=[self.node(f'x{j}','Python',f'unique_{i}_{j}',f'S{i+1}') for j in range(20)],edges=[self.edge('x0','x1',f'S{i+1}')]))
        with self.assertRaises(LLMServiceError):build_network(self.sources,self.citations,extracted,'Too large')
        graph=build_network(self.sources[:1],self.citations[:1],[SourceGraph(nodes=[self.node('a','Python','programming'),self.node('b','code','code')],edges=[self.edge('a','b')])],'Study').model_dump()
        graph['edges'][0]['target']='n999'
        with self.assertRaises(ValidationError):KnowledgeGraph.model_validate(graph)
        graph['nodes']*=26
        with self.assertRaises(ValidationError):KnowledgeGraph.model_validate(graph)
        graph['nodes']=graph['nodes'][:2];graph['edges']*=101
        with self.assertRaises(ValidationError):KnowledgeGraph.model_validate(graph)
