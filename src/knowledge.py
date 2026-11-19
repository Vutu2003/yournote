"""Conservative, artifact-local knowledge networks with source-supported edges."""
import unicodedata
from pydantic import ValidationError
from src.errors import LLMServiceError
from src.llm import llm_operation,check_workload
from src.research import _call,_emit,_fail,_limits,_used_citations,prepare_sources,validate_statement
from src.research_schemas import (ExtractEdge,GraphEdge,GraphNode,GroundedStatement,KnowledgeGraph,SourceGraph,SourceNote)


def _name(value):
    return ' '.join(unicodedata.normalize('NFKC',value).casefold().split())


def _combine_evidence(a,b,citations):
    unique=[];seen=set()
    for ref in [*a,*b]:
        key=(ref.source_marker,ref.quote)
        if key not in seen: seen.add(key);unique.append(ref)
    by_marker={c.source_marker:c.filename for c in citations}
    first=[];rest=[];sources=set()
    for ref in unique:
        filename=by_marker[ref.source_marker]
        if filename not in sources: first.append(ref);sources.add(filename)
        else: rest.append(ref)
    return (first+rest)[:8]


def build_network(sources,citations,extractions,goal,progress=None):
    nodes=[];edges=[];dropped=0;notes=[]
    for source,extraction in zip(sources,extractions):
        check_workload(0);mapping={}
        if len({node.id for node in extraction.nodes})!=len(extraction.nodes): _fail()
        for node in extraction.nodes:
            validate_statement(node.definition,citations,allowed_filename=source.filename)
            quoted=' '.join(_name(ref.quote) for ref in node.definition.evidence)
            documented=[name for name in [node.label,*node.aliases] if _name(name) in quoted]
            if not documented: _fail('Graph concept has no named evidence in its quoted source.')
            names={_name(name) for name in [node.label,*documented]}
            existing=next((candidate for candidate in nodes if _name(candidate.meaning_key)==_name(node.meaning_key) and names.intersection({_name(candidate.label),*map(_name,candidate.aliases)})),None)
            if existing:
                existing.aliases=list(dict.fromkeys([*existing.aliases,node.label,*documented]))
                existing.definition=GroundedStatement(text=existing.definition.text,evidence=_combine_evidence(existing.definition.evidence,node.definition.evidence,citations))
            else:
                existing=GraphNode(id=f'n{len(nodes)+1}',label=node.label,meaning_key=node.meaning_key,
                    aliases=list(dict.fromkeys(documented)),definition=node.definition)
                nodes.append(existing)
            mapping[node.id]=existing.id
        accepted=0
        for raw in extraction.edges:
            try:
                edge=ExtractEdge.model_validate(raw)
                if edge.source not in mapping or edge.target not in mapping or mapping[edge.source]==mapping[edge.target]: raise ValueError('Unknown/self endpoint')
                validate_statement(edge.statement,citations,allowed_filename=source.filename)
                start,end=mapping[edge.source],mapping[edge.target]
                existing=next((candidate for candidate in edges if (candidate.source,candidate.target,candidate.relation,_name(candidate.statement.text))==(start,end,edge.relation,_name(edge.statement.text))),None)
                if existing:
                    existing.statement=GroundedStatement(text=existing.statement.text,evidence=_combine_evidence(existing.statement.evidence,edge.statement.evidence,citations))
                else: edges.append(GraphEdge(id=f'e{len(edges)+1}',source=start,target=end,relation=edge.relation,statement=edge.statement))
                accepted+=1
            except (ValidationError,ValueError,LLMServiceError): dropped+=1
        notes.append(SourceNote(filename=source.filename,status='evidence' if accepted else 'not_found',
            detail=f'Có {accepted} quan hệ đủ trích đoạn kiểm chứng.' if accepted else 'Chưa tìm thấy quan hệ đủ bằng chứng trong các đoạn đã xét.'))
    if len(nodes)>50 or len(edges)>100: _fail('Graph exceeds 50 concepts or 100 relations. Choose a narrower goal or fewer sources.')
    if len(nodes)<2 or not edges: _fail('No supported graph relations were found in the selected sources.')
    statements=[node.definition for node in nodes]+[edge.statement for edge in edges]
    limits=_limits(sources)+['Chỉ gộp khái niệm khi cùng khóa nghĩa và trùng tên/alias có trong nguồn; khái niệm có thể còn trùng nếu chưa chắc đồng nghĩa.']
    if dropped: limits.append(f'Đã loại {dropped} quan hệ thiếu bằng chứng, sai marker hoặc endpoint; không coi các quan hệ đó là đã xác nhận.')
    result=KnowledgeGraph(goal=goal,target=goal,sources=sources,nodes=nodes,edges=edges,citations=_used_citations(citations,statements),
        source_notes=notes,limits=limits,discarded_relations=dropped)
    _emit(progress,'validating',len(sources)+1,len(sources)+1)
    return result


@llm_operation
def create_knowledge_graph(goal,filenames,filters=None,progress=None):
    sources,citations,passages=prepare_sources(goal,filenames,filters,progress,synthesis=False)
    extracted=[]
    for index,(source,items) in enumerate(zip(sources,passages)):
        _emit(progress,'examining',index,len(sources)+1)
        graph=_call('''RESEARCH_STEP=graph_source
Extract a SMALL network useful for the study goal: at most 20 nodes and 30 candidate relations from THIS source.
Nodes are concepts/entities; a definition states only what these passages support, not outside textbook knowledge.
Use distinct meaning_key values for homonyms (e.g. a programming language and an animal). For equivalent meanings use
short stable English snake_case meaning keys. Aliases should be verbatim documented names (not guessed abbreviations).
At least the label or a documented alias must appear in the quoted evidence. A translated canonical label is allowed
when an original name appears in aliases/evidence. Each node definition and relation needs literal source evidence.
Do not infer relationships merely because concepts co-occur; quotes must actually support the asserted typed relation.
Types: is_a, part_of, requires, causes, contrasts_with, related_to, example_of, equivalent_to, optimizes, measures, predicts, uses.
Direction matters: "A requires B" means source=A,target=B. No self edges. Prefer 5–10 useful concepts to a cluttered network.
Use plain prose without inline [S] tags; structured evidence carries the marker. Never reset global markers.
Shape: {"nodes":[{"id":"a","label":"...","meaning_key":"...","aliases":["..."],"definition":{"text":"...","evidence":[{"source_marker":"S1","quote":"literal excerpt"}]}}],
"edges":[{"source":"a","target":"b","relation":"requires","statement":{"text":"...","evidence":[{"source_marker":"S1","quote":"literal excerpt"}]}}],"limitations":[]}.
If the source does not support a relationship, omit it; never manufacture one to satisfy the schema.''',{'goal':goal,'passages':items},SourceGraph)
        extracted.append(graph);_emit(progress,'examining',index+1,len(sources)+1)
    _emit(progress,'building_graph',len(sources),len(sources)+1)
    return build_network(sources,citations,extracted,goal,progress)
