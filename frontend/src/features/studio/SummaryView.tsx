import { useState } from 'react'
import type { SummaryResponse } from '../../types/api'
import { CitationList } from '../../components/CitationList'
import { ExportButton } from '../../components/ExportButton'
import { ResultViewerModal } from '../../components/ResultViewerModal'

export function SummaryView({ result, title, open, onClose }: { result: SummaryResponse; title: string; open: boolean; onClose: () => void }) {
  const [page, setPage] = useState(0)
  return <ResultViewerModal open={open} title="Tóm tắt" artifactTitle={title} onClose={onClose} pageKey={page} footer={<>
    <nav className="item-navigation" aria-label="Điều hướng tóm tắt">
      <button className="button subtle" type="button" disabled={page === 0} onClick={() => setPage(page - 1)}>‹ Trước</button>
      <span className="page-indicator" aria-live="polite">{page + 1} / 3</span>
      <button className="button subtle" type="button" disabled={page === 2} onClick={() => setPage(page + 1)}>Tiếp ›</button>
    </nav>
    <ExportButton feature="summary" result={result} />
  </>}>
    <article className="viewer-result" aria-label="Kết quả tóm tắt">
      {page === 0 && <><h3>Tóm tắt</h3><p className="prose">{result.summary}</p></>}
      {page === 1 && <><h3>Ý chính</h3>{result.key_points.length
        ? <ul className="key-points">{result.key_points.map((point, index) => <li key={index}>{point}</li>)}</ul>
        : <p className="muted">Không có ý chính.</p>}</>}
      {page === 2 && <>{result.citations.length
        ? <CitationList citations={result.citations} label={`Nguồn đã sử dụng (${result.citations.length})`} collapsed={false} />
        : <p className="muted">Không có nguồn tham chiếu.</p>}</>}
    </article>
  </ResultViewerModal>
}
