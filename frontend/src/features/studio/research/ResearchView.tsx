import { ResultViewerModal } from '../../../components/ResultViewerModal'
import { FormattedText } from '../../../components/FormattedText'
import { GenerationInfo } from '../../../components/GenerationInfo'
import { ExportButton } from '../../../components/ExportButton'
import { statementNote } from './researchData'
import { citationLocation } from '../../../types/citations'
import type { Citation, DocumentInfo } from '../../../types/api'
import type { ComparisonResponse, GroundedStatement, ReportResponse, ResearchResult } from '../../../types/research'
import { findingLabels } from '../../../types/research'

export function EvidenceStatement({ value, result, sourceName, onOpenCitation }: {
  value: GroundedStatement; result: ResearchResult; sourceName: (filename: string) => string; onOpenCitation?: (citation: Citation) => void
}) {
  return <div className="research-statement">
    <FormattedText text={value.text} onSource={marker => { const c = result.citations.find(item => item.source_marker === marker); if (c) onOpenCitation?.(c) }} />
    <details className="research-evidence"><summary>Bằng chứng ({value.evidence.length})</summary>
      {value.evidence.map((ref, index) => {
        const citation = result.citations.find(item => item.source_marker === ref.source_marker)
        return <div className="research-quote" key={index}><blockquote>{ref.quote}</blockquote>{citation && <button type="button" className="text-button" onClick={() => onOpenCitation?.(citation)}>[{ref.source_marker}] {sourceName(citation.filename)} · {citationLocation(citation)}</button>}</div>
      })}
    </details>
  </div>
}
export function ResearchScope({ result, documents, sourceName }: { result: ResearchResult; documents: DocumentInfo[]; sourceName: (filename: string) => string }) {
  const changed = result.sources.filter(source => !documents.some(doc => doc.filename === source.filename && doc.document_version === source.document_version))
  return <>
    {!!changed.length && <p className="research-stale" role="status">{changed.length} nguồn đã thay đổi phiên bản hoặc không còn trong sổ. Kết quả này giữ bằng chứng ở phiên bản đã tạo; mở trích dẫn để đối chiếu bản cũ.</p>}
    <details className="research-scope"><summary>Phạm vi đã xét · {result.sources.length} nguồn</summary><ul>{result.sources.map(source => <li key={source.filename}><strong>{sourceName(source.filename)}</strong><span>{source.examined_chunk_ids.length}/{source.total_chunks} đoạn · {source.coverage === 'complete' ? 'Đã xét đủ đoạn trong phạm vi' : 'Một số đoạn liên quan'}</span></li>)}</ul></details>
  </>
}

export function ResearchView({ result, title, onClose, onOpenCitation, onNote, sourceName, documents }: {
  result: ComparisonResponse | ReportResponse; title: string; onClose: () => void; onOpenCitation?: (citation: Citation) => void
  onNote: (title: string, content: string) => boolean; sourceName: (filename: string) => string; documents: DocumentInfo[]
}) {
  function note(label: string, statements: GroundedStatement[]) { if (onNote(label, statementNote(label, statements, result, sourceName))) onClose() }
  const render = (statement: GroundedStatement, index: number) => <EvidenceStatement key={index} value={statement} result={result} sourceName={sourceName} onOpenCitation={onOpenCitation} />
  return <ResultViewerModal open title={result.kind === 'comparison' ? 'So sánh tài liệu' : 'Tổng hợp / Báo cáo'} artifactTitle={title} onClose={onClose} footer={<ExportButton feature={result.kind} result={result} />}>
    <div className="research-view"><p className="research-goal">{result.goal}</p><GenerationInfo value={result.generation} /><ResearchScope result={result} documents={documents} sourceName={sourceName} />
      {result.kind === 'comparison' ? <>
        {result.criteria.map(criterion => <section className="research-section" key={criterion.id}><h3>{criterion.label}</h3>
          <div className="comparison-sources">{criterion.sources.map(source => <article className="comparison-source" key={source.filename}><h4>{sourceName(source.filename)}</h4>
            {source.statement ? <><EvidenceStatement value={source.statement} result={result} sourceName={sourceName} onOpenCitation={onOpenCitation} /><button type="button" className="text-button" onClick={() => note(criterion.label, [source.statement!])}>Lưu ý này vào ghi chú</button></>
              : <p className="research-missing">Chưa tìm thấy trong các đoạn đã xét. {source.limitation}</p>}</article>)}</div>
          {result.findings.filter(f => f.criterion_id === criterion.id).map((finding, index) => <div className={`comparison-finding finding-${finding.kind}`} key={index}><span className="research-label">{findingLabels[finding.kind]}</span><EvidenceStatement value={finding.statement} result={result} sourceName={sourceName} onOpenCitation={onOpenCitation} /><button type="button" className="text-button" onClick={() => note(criterion.label, [finding.statement])}>Lưu nhận định vào ghi chú</button></div>)}
        </section>)}
      </> : result.sections.map((section, index) => <section key={index} className="research-section"><div className="research-section-heading"><h3>{section.title}</h3><button type="button" className="text-button" onClick={() => note(section.title, section.statements)}>Lưu mục này vào ghi chú</button></div>{section.statements.map(render)}</section>)}
      <section className="research-section"><div className="research-section-heading"><h3>Kết luận</h3>{!!result.conclusion.length && <button type="button" className="text-button" onClick={() => note('Kết luận · ' + title, result.conclusion)}>Lưu kết luận vào ghi chú</button>}</div>{result.conclusion.length ? result.conclusion.map(render) : <p className="research-missing">Chưa đủ bằng chứng để kết luận.</p>}</section>
      <section className="research-section"><h3>Giới hạn</h3><ul className="research-limits">{result.limits.map((limit, index) => <li key={index}>{limit}</li>)}</ul>{result.source_notes.map(item => <p className="research-missing" key={item.filename}>{sourceName(item.filename)}: {item.detail}</p>)}</section>
    </div>
  </ResultViewerModal>
}
