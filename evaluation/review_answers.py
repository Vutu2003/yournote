"""Recorded manual assessment against the frozen synthetic source excerpts.

No LLM judge. This rubric checks question relevance and each material claim's
support, separately from whether a marker merely exists.
"""
import json
from pathlib import Path
import statistics

import hashlib
reviews=json.loads(Path('evaluation/manual_review.json').read_text())['rows']
path=Path('reports/phase04/answers.json');data=json.loads(path.read_text())
for row in data['rows']:
 key=row['id']+':'+row['mode'];review=reviews[key]
 reviewed={k:row.get(k) for k in ('answer','context_chunk_ids','citations')}
 digest=hashlib.sha256(json.dumps(reviewed,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 if digest!=review['reviewed_sha256']: raise ValueError('Answer/context changed: new manual assessment required for '+key)
 row['manual_review']={k:v for k,v in review.items() if k!='reviewed_sha256'}
 data.setdefault('assessment',{})[row['mode']]={}
for mode in ('baseline','hybrid'):
 rows=[row for row in data['rows'] if row['mode']==mode]
 data['assessment'][mode]={'cases':len(rows),'correct_and_supported':sum(row['manual_review']['correct_and_supported_for_intended_question'] for row in rows),
  'completed':sum(row['status']=='completed' for row in rows),'calls':sum(row['calls'] for row in rows),'median_seconds':statistics.median(row['duration_seconds'] for row in rows),
  'reported_tokens':{key:sum(usage[key] for row in rows for usage in row['usage'] if usage and usage.get(key) is not None) for key in ('input_tokens','output_tokens','total_tokens')}}
data['assessment']['method']='Agent manual review of all 16 outputs against the synthetic fixture and marker-to-chunk mapping; small developer test, not independent human annotation or a general quality guarantee.'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(data['assessment'],ensure_ascii=False,indent=2))
