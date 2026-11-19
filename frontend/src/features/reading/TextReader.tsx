import { useEffect, useRef, useState } from 'react'
import * as api from '../../api/client'
import { Icon } from '../../components/Icon'
import { ErrorMessage, LoadingIndicator } from '../../components/Status'
import { useToast } from '../../hooks/useToast'
import type { DocumentInfo } from '../../types/api'
import type { PdfTarget, TextDocument } from '../../types/reading'

const perPage = 100
export default function TextReader({ notebookId, document: source, documents, target, onClose, onDocumentChange, sourceName }: {
  notebookId: string; document: DocumentInfo; documents: DocumentInfo[]; target: PdfTarget
  onClose: () => void; onDocumentChange: (document: DocumentInfo) => void; sourceName: (filename: string) => string
}) {
  const [info, setInfo] = useState<TextDocument | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const [jump, setJump] = useState('1')
  const [jumpAnchor, setJumpAnchor] = useState<string | null>(null)
  const [retry, setRetry] = useState(0)
  const body = useRef<HTMLDivElement>(null)
  const notify = useToast()
  useEffect(() => {
    const controller = new AbortController()
    void Promise.resolve().then(() => {
      if (controller.signal.aborted) return
      setLoading(true); setError(''); setInfo(null)
      return api.getTextDocument(notebookId, source.document_id, target.version, controller.signal)
    }).then(value => {
      if (!value || controller.signal.aborted) return
      setInfo(value)
      const index = value.blocks.findIndex(block => block.locator.anchor === target.anchor)
      setPage(index < 0 ? 0 : Math.floor(index / perPage)); setJump(String(index < 0 ? 1 : index + 1)); setJumpAnchor(target.anchor || null)
    }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Không thể mở văn bản nguồn.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [notebookId, source.document_id, target.version, target.anchor, retry])
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const cited = jumpAnchor ? body.current?.querySelector<HTMLElement>(`[data-anchor="${jumpAnchor}"]`) : null
      if (cited) { cited.scrollIntoView({ block: 'center' }); cited.focus({ preventScroll: true }) }
      else body.current?.scrollTo({ top: 0 })
    })
    return () => cancelAnimationFrame(frame)
  }, [info, page, jumpAnchor, target.token])
  const blocks = info?.blocks || []
  function changePage(value: number) { setPage(value); setJump(String(value * perPage + 1)); setJumpAnchor(null) }
  function goToParagraph() {
    const value = Math.max(1, Math.min(blocks.length || 1, Math.floor(Number(jump) || 1)))
    setJump(String(value)); setPage(Math.floor((value - 1) / perPage)); setJumpAnchor(blocks[value - 1]?.locator.anchor || null)
  }
  const lastPage = Math.max(0, Math.ceil(blocks.length / perPage) - 1)
  return <section className="panel pdf-reader text-reader" id="notebook-pdf-panel" aria-label="Văn bản nguồn">
    <header className="pdf-reader-header"><Icon name="book" size={18} />
      <select aria-label="Tài liệu đang đọc" value={source.document_id} onChange={event => { const chosen = documents.find(doc => doc.document_id === event.target.value); if (chosen) onDocumentChange(chosen) }}>
        {documents.map(doc => <option key={doc.document_id} value={doc.document_id}>{sourceName(doc.filename)}</option>)}
      </select>
      <button type="button" className="icon-button" aria-label="Tải tệp gốc" disabled={!info} onClick={() => { void api.downloadOriginalPdf(notebookId, source.document_id, info?.original_filename || source.filename, info?.document_version).catch(reason => notify(reason.message, 'error')) }}><Icon name="download" size={18} /></button>
      <button type="button" className="icon-button" aria-label="Đóng chế độ đọc chuyên sâu" onClick={onClose}><Icon name="close" size={19} /></button>
    </header>
    {info?.historical && <p className="source-version-banner">Đang xem phiên bản của trích dẫn cũ. <button type="button" className="text-button" onClick={() => { const current = documents.find(doc => doc.document_id === source.document_id); if (current) onDocumentChange(current) }}>Mở bản hiện tại</button></p>}
    <div className="text-reader-toolbar">
      <span>{source.kind === 'docx' ? 'DOCX' : source.kind === 'markdown' ? 'Markdown' : 'TXT'} · Văn bản trích xuất</span>
      <label>Đoạn <input type="number" aria-label="Đến đoạn văn" min={1} max={blocks.length || 1} value={jump} disabled={!info} onChange={event => setJump(event.target.value)} onBlur={goToParagraph} onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); goToParagraph() } }} /></label>
      <span>/ {blocks.length || '…'}</span>
      <button type="button" className="icon-button" aria-label="Nhóm đoạn trước" disabled={page <= 0} onClick={() => changePage(page - 1)}><Icon name="back" size={16} /></button>
      <button type="button" className="icon-button" aria-label="Nhóm đoạn tiếp" disabled={page >= lastPage} onClick={() => changePage(page + 1)}><Icon name="arrow" size={16} /></button>
    </div>
    <p className="text-reader-note">Vị trí theo tiêu đề/đoạn trong phiên bản nội dung, không quy đổi thành số trang.</p>
    {loading && <LoadingIndicator text="Đang mở văn bản nguồn…" />}
    {error && <div className="pdf-message"><ErrorMessage message={error} /><button type="button" className="button" onClick={() => setRetry(value => value + 1)}>Thử lại</button></div>}
    <div className="text-reader-body" ref={body} aria-busy={loading}>
      {blocks.slice(page * perPage, (page + 1) * perPage).map(block => <article key={block.locator.anchor} data-anchor={block.locator.anchor}
        tabIndex={-1} className={`text-source-block ${target.anchor === block.locator.anchor ? 'is-cited' : ''}`}>
        <div className="text-block-location"><span>Đoạn {block.locator.paragraph}</span>{!!block.locator.heading?.length && <span>{block.locator.heading.join(' / ')}</span>}</div>
        <p>{block.text}</p>
      </article>)}
    </div>
  </section>
}
