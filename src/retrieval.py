"""Small BM25 + rank-fusion helpers; no model download or paid reranker."""
from collections import Counter
import math
import re
import unicodedata


def tokens(text):
    normalized=unicodedata.normalize('NFKD',text.casefold()).replace('đ','d')
    normalized=''.join(c for c in normalized if not unicodedata.combining(c))
    return re.findall(r'\w+(?:[-.]\w+)*',normalized)


def lexical_rank(query,chunks,limit):
    terms=set(tokens(query))
    if not terms or not chunks: return []
    counts=[Counter(tokens(chunk.text+' '+(chunk.metadata.section or ''))) for chunk in chunks]
    sizes=[sum(count.values()) for count in counts];average=sum(sizes)/max(1,len(sizes))
    frequency={term:sum(term in count for count in counts) for term in terms}
    scored=[]
    for chunk,count,size in zip(chunks,counts,sizes):
        score=0
        for term in terms:
            tf=count[term]
            if tf:
                idf=math.log(1+(len(chunks)-frequency[term]+.5)/(frequency[term]+.5))
                score+=idf*(tf*2.2)/(tf+1.2*(.25+.75*size/max(1,average)))
        if score>0: scored.append((score,chunk))
    scored.sort(key=lambda item:(-item[0],item[1].metadata.chunk_id))
    return [item[1] for item in scored[:limit]]


def reciprocal_rank_fusion(rankings,limit):
    values={};scores={}
    for ranking in rankings:
        for rank,chunk in enumerate(ranking,1):
            key=chunk.metadata.chunk_id
            values[key]=chunk;scores[key]=scores.get(key,0)+1/(60+rank)
    ordered=sorted(scores,key=lambda key:(-scores[key],key))[:limit]
    return [values[key].model_copy(update={'score':scores[key]}) for key in ordered]
