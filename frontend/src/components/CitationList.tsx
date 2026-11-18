import type { Citation } from '../types/api'

export function CitationList({ citations, label = 'Nguồn đã sử dụng', collapsed = true, onOpenCitation, sourceName }: {
  citations: Citation[]; label?: string; collapsed?: boolean; onOpenCitation?: (citation: Citation) => void; sourceName?: (filename: string) => string
}) {
  if (!citations.length) return null
  const rows = <ul className="citation-list">
    {citations.map((citation, index) => <li key={`${citation.source_marker}-${index}`}>
      <details className="citation-detail">
        <summary title={citation.filename} onClick={() => onOpenCitation?.(citation)}>
          <span className="source-marker">[{citation.source_marker}]</span>
          <span className="citation-filename">{sourceName?.(citation.filename) || citation.filename}</span>
          <span className="citation-page">tr. {citation.page}</span>
        </summary>
        <div className="citation-content">
          {citation.section && <p>{citation.section}</p>}
          <p className="prose">{citation.source_text || 'Không có trích đoạn.'}</p>
          {citation.chunk_id && <small>Mã đoạn: {citation.chunk_id}</small>}
          {onOpenCitation && <button type="button" className="button subtle citation-open-pdf" onClick={() => onOpenCitation(citation)}>Mở PDF · trang {citation.page}</button>}
        </div>
      </details>
    </li>)}
  </ul>
  return collapsed ? <details className="citations-group">
    <summary>{label} ({citations.length})</summary>{rows}
  </details> : <section className="citations-group" aria-label={label}>
    <h3>{label}</h3>{rows}
  </section>
}
