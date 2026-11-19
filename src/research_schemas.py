"""Small, evidence-bearing study artifacts; distinct from the Mind Map tree."""
from typing import Annotated,Literal
from pydantic import BaseModel,ConfigDict,Field,StringConstraints,model_validator
from src.schemas import Citation

Text=Annotated[str,StringConstraints(strip_whitespace=True,min_length=1,max_length=1200)]
Label=Annotated[str,StringConstraints(strip_whitespace=True,min_length=1,max_length=160)]
Marker=Annotated[str,Field(pattern=r'^S[1-9][0-9]*$')]

class StrictModel(BaseModel):
    model_config=ConfigDict(extra='forbid',validate_assignment=True)

class EvidenceRef(StrictModel):
    source_marker:Marker
    quote:Annotated[str,StringConstraints(strip_whitespace=True,min_length=8,max_length=700)]

class GroundedStatement(StrictModel):
    text:Text
    evidence:list[EvidenceRef]=Field(min_length=1,max_length=8)

class SourceCoverage(StrictModel):
    filename:str
    document_id:str
    document_version:Annotated[str,Field(pattern=r'^[a-f0-9]{64}$')]
    total_chunks:int=Field(ge=1)
    examined_chunk_ids:list[str]=Field(min_length=1,max_length=6)
    coverage:Literal['complete','selected_excerpt']

class SourceNote(StrictModel):
    filename:str
    status:Literal['evidence','not_found']
    detail:Text

class ResearchResult(StrictModel):
    schema_version:Literal[1]=1
    scope:Literal['filter']='filter'
    target:str|None=None
    goal:Annotated[str,StringConstraints(strip_whitespace=True,min_length=1,max_length=2000)]
    sources:list[SourceCoverage]=Field(min_length=1,max_length=6)
    citations:list[Citation]=Field(default_factory=list,max_length=36)
    limits:list[Text]=Field(min_length=1,max_length=30)
    source_notes:list[SourceNote]=Field(default_factory=list,max_length=6)

    @model_validator(mode='after')
    def check_evidence_integrity(self):
        from src.grounding import normalized
        sources={source.filename:source for source in self.sources}
        if len(sources)!=len(self.sources): raise ValueError('Source coverage must be unique')
        for source in self.sources:
            count=len(source.examined_chunk_ids)
            if len(set(source.examined_chunk_ids))!=count or count>source.total_chunks or (source.coverage=='complete')!=(count==source.total_chunks):
                raise ValueError('Invalid source coverage')
        citations={c.source_marker:c for c in self.citations}
        if len(citations)!=len(self.citations): raise ValueError('Duplicate citation marker')
        for citation in self.citations:
            source=sources.get(citation.filename)
            if not source or citation.document_id!=source.document_id or citation.document_version!=source.document_version or citation.chunk_id not in source.examined_chunk_ids:
                raise ValueError('Citation is outside the examined source/version')
        def walk(value):
            if isinstance(value,dict):
                if 'text' in value and 'evidence' in value:
                    statement=GroundedStatement.model_validate(value)
                    for ref in statement.evidence:
                        citation=citations.get(ref.source_marker)
                        if not citation or normalized(ref.quote) not in normalized(citation.source_text or ''):
                            raise ValueError('Evidence quote is not in its source chunk')
                    import re
                    if not set(re.findall(r'\[(S[1-9][0-9]*)\]',statement.text)) <= {r.source_marker for r in statement.evidence}:
                        raise ValueError('Statement marker disagrees with structured evidence')
                else:
                    for key,item in value.items():
                        if key not in ('citations','generation'): walk(item)
            elif isinstance(value,list):
                for item in value: walk(item)
        walk(self.model_dump())
        if any(note.filename not in sources for note in self.source_notes): raise ValueError('Unknown source note')
        return self

class CriterionReview(StrictModel):
    criterion_id:Annotated[str,Field(pattern=r'^c[1-6]$')]
    status:Literal['supported','not_found']
    statement:GroundedStatement|None=None
    limitation:str=Field(default='',max_length=600)
    @model_validator(mode='after')
    def has_evidence_or_limit(self):
        if self.status=='supported' and self.statement is None: raise ValueError('Supported criteria need evidence')
        if self.status=='not_found' and (self.statement is not None or not self.limitation.strip()):
            raise ValueError('Missing criteria need a limitation and no invented statement')
        return self

class SourceCriterion(CriterionReview):
    filename:str

class ComparisonCriterion(StrictModel):
    id:Annotated[str,Field(pattern=r'^c[1-6]$')]
    label:Label
    sources:list[SourceCriterion]=Field(min_length=2,max_length=6)

class ComparisonFinding(StrictModel):
    criterion_id:Annotated[str,Field(pattern=r'^c[1-6]$')]
    kind:Literal['agreement','direct_conflict','different_conditions','different_wording','difference']
    statement:GroundedStatement

class Comparison(ResearchResult):
    kind:Literal['comparison']='comparison'
    criteria:list[ComparisonCriterion]=Field(min_length=1,max_length=6)
    findings:list[ComparisonFinding]=Field(default_factory=list,max_length=24)
    conclusion:list[GroundedStatement]=Field(default_factory=list,max_length=8)

    @model_validator(mode='after')
    def all_sources_and_sides(self):
        names=[s.filename for s in self.sources]
        if len(names)<2 or len({c.id for c in self.criteria})!=len(self.criteria): raise ValueError('Comparison requires unique criteria and >=2 sources')
        by_marker={c.source_marker:c for c in self.citations}
        by_criterion={c.id:c for c in self.criteria}
        for criterion in self.criteria:
            if [s.filename for s in criterion.sources]!=names: raise ValueError('Every criterion must examine every source')
            for row in criterion.sources:
                if row.criterion_id!=criterion.id: raise ValueError('Source review criterion disagrees with its row')
                if row.statement and any(by_marker[r.source_marker].filename!=row.filename for r in row.statement.evidence): raise ValueError('Source review cites another source')
        for finding in self.findings:
            criterion=by_criterion.get(finding.criterion_id)
            if not criterion: raise ValueError('Unknown finding criterion')
            sides={by_marker[r.source_marker].filename for r in finding.statement.evidence}
            eligible={r.filename for r in criterion.sources if r.status=='supported'}
            if len(sides)<2 or not sides<=eligible: raise ValueError('Comparison findings need supported evidence from both sides')
        return self

class ReportSection(StrictModel):
    title:Label
    statements:list[GroundedStatement]=Field(min_length=1,max_length=8)

class StudyReport(ResearchResult):
    kind:Literal['report']='report'
    mode:Literal['study_guide','explanation','synthesis']
    title:Label
    sections:list[ReportSection]=Field(min_length=1,max_length=8)
    conclusion:list[GroundedStatement]=Field(min_length=1,max_length=6)

class SourceComparison(StrictModel):
    criteria:list[CriterionReview]=Field(min_length=1,max_length=6)

class SourceFacts(StrictModel):
    facts:list[GroundedStatement]=Field(default_factory=list,max_length=8)
    limitations:list[Text]=Field(default_factory=list,max_length=4)

class ComparisonSynthesis(StrictModel):
    findings:list[ComparisonFinding]=Field(default_factory=list,max_length=24)
    conclusion:list[GroundedStatement]=Field(default_factory=list,max_length=8)

class ReportSynthesis(StrictModel):
    title:Label
    sections:list[ReportSection]=Field(min_length=1,max_length=8)
    conclusion:list[GroundedStatement]=Field(min_length=1,max_length=6)

Relation=Literal['is_a','part_of','requires','causes','contrasts_with','related_to','example_of','equivalent_to','optimizes','measures','predicts','uses']

class ExtractNode(StrictModel):
    id:Annotated[str,Field(pattern=r'^[A-Za-z0-9_-]{1,32}$')]
    label:Label
    meaning_key:Label
    aliases:list[Label]=Field(default_factory=list,max_length=6)
    definition:GroundedStatement

class ExtractEdge(StrictModel):
    source:str
    target:str
    relation:Relation
    statement:GroundedStatement

class SourceGraph(StrictModel):
    nodes:list[ExtractNode]=Field(default_factory=list,max_length=20)
    # Validate edges separately so unsupported candidates can be explicitly discarded.
    edges:list[dict]=Field(default_factory=list,max_length=30)
    limitations:list[Text]=Field(default_factory=list,max_length=4)

class GraphNode(StrictModel):
    id:Annotated[str,Field(pattern=r'^n[1-9][0-9]*$')]
    label:Label
    meaning_key:Label
    aliases:list[Label]=Field(default_factory=list,max_length=48)
    definition:GroundedStatement

class GraphEdge(StrictModel):
    id:Annotated[str,Field(pattern=r'^e[1-9][0-9]*$')]
    source:str
    target:str
    relation:Relation
    statement:GroundedStatement

class KnowledgeGraph(ResearchResult):
    kind:Literal['graph']='graph'
    nodes:list[GraphNode]=Field(min_length=2,max_length=50)
    edges:list[GraphEdge]=Field(min_length=1,max_length=100)
    discarded_relations:int=Field(default=0,ge=0)
    merge_policy:Literal['same_meaning_and_documented_name']='same_meaning_and_documented_name'

    @model_validator(mode='after')
    def valid_network(self):
        ids={node.id for node in self.nodes}
        if len(ids)!=len(self.nodes) or len({edge.id for edge in self.edges})!=len(self.edges): raise ValueError('Graph IDs must be unique')
        for edge in self.edges:
            if edge.source not in ids or edge.target not in ids or edge.source==edge.target: raise ValueError('Graph relation has invalid endpoints')
        return self
