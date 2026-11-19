"""Bounded, notebook-owned completed history. Previous answers are never evidence."""
import re

FOLLOWUP=re.compile(r'\b(nó|đó|vậy|thế|còn|trên|ấy|này|chúng|it|that|those|they|this)\b',re.I)


def contextual_query(question,history):
    if not history or not FOLLOWUP.search(question): return question
    questions=[turn['question'][:2000] for turn in history[-2:]]
    return '\n'.join([*questions,question])[:6000]


def scoped_history(workspace,sources,current_versions):
    allowed=set(sources.filenames);result=[]
    for turn in workspace.state.chat[-8:]:
        meta=turn.generation
        if meta and meta.status!='completed': continue
        citations=turn.citations
        names=set(meta.source_filenames if meta else [c.filename for c in citations])
        if not names or not names<=allowed: continue
        if sources.pages and (not citations or any(c.page not in sources.pages for c in citations)): continue
        known=dict(getattr(meta,'source_versions',{}) or {}) if meta else {}
        for citation in citations:
            if citation.document_version: known[citation.filename]=citation.document_version
        # A prior unknown version cannot become trusted context after a replacement.
        if any(current_versions.get(name) and known.get(name)!=current_versions[name] for name in names): continue
        if any(c.filename not in allowed for c in citations): continue
        result.append({'question':turn.question[:2000],'answer':turn.answer[:1500],'filenames':sorted(names)})
    return result[-3:]
