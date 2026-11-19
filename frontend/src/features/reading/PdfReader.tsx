import { useEffect, useRef, useState } from 'react'
import { getDocument, GlobalWorkerOptions, TextLayer } from 'pdfjs-dist'
import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import * as api from '../../api/client'
import { Icon } from '../../components/Icon'
import { ErrorMessage, LoadingIndicator } from '../../components/Status'
import { useToast } from '../../hooks/useToast'
import type { DocumentInfo } from '../../types/api'
import type { PdfTarget, ReadingDocument } from '../../types/reading'

GlobalWorkerOptions.workerSrc = workerUrl
const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

export default function PdfReader({ notebookId, document: source, documents, target, onClose, onDocumentChange, sourceName }: {
  notebookId: string; document: DocumentInfo; documents: DocumentInfo[]; target: PdfTarget
  onClose: () => void; onDocumentChange: (document: DocumentInfo) => void
  sourceName: (filename: string) => string
}) {
  const notify = useToast()
  const [info, setInfo] = useState<ReadingDocument | null>(null)
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null)
  const [page, setPage] = useState(target.page || 1)
  const [zoom, setZoom] = useState(1)
  const [{ width: availableWidth, height: availableHeight }, setAvailableSize] = useState({ width: 0, height: 0 })
  const [size, setSize] = useState({ width: 0, height: 0 })
  const [rendering, setRendering] = useState(true)
  const [hasText, setHasText] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const [selection, setSelection] = useState('')
  const scroll = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const layer = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false
    let task: ReturnType<typeof getDocument> | undefined
    setLoading(true); setError(''); setPdf(null); setInfo(null); setSelection('')
    async function load() {
      try {
        const metadata = await api.getReadingDocument(notebookId, source.document_id, controller.signal,target.version)
        if (cancelled) return
        setInfo(metadata)
        task = getDocument({ url: `${api.originalPdfUrl(notebookId, source.document_id)}?version=${metadata.document_version}`, useSystemFonts: true, enableXfa: false })
        const loaded = await task.promise
        if (cancelled) return
        setPdf(loaded)
        setPage(current => Math.min(loaded.numPages, Math.max(1, current)))
      } catch (reason) { if (!cancelled) setError(failure(reason, 'Không thể đọc PDF gốc.')) }
      finally { if (!cancelled) setLoading(false) }
    }
    void load()
    return () => { cancelled = true; controller.abort(); void task?.destroy() }
  }, [notebookId, source.document_id, target.version, retry])

  useEffect(() => {
    const element = scroll.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      const styles = getComputedStyle(element)
      const width = Math.floor(entry.contentRect.width)
      // Keep the fit scale stable when zooming adds a horizontal scrollbar.
      const height = Math.floor(entry.borderBoxSize[0].blockSize - parseFloat(styles.paddingTop) - parseFloat(styles.paddingBottom))
      if (width <= 0 || height <= 0) return
      setAvailableSize(current => current.width === width && current.height === height ? current : { width, height })
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  useEffect(() => { setPage(Math.max(1, Math.min(info?.page_count || target.page, target.page))) }, [target.token, target.page, info?.page_count])
  useEffect(() => {
    if (!pdf || !availableWidth || !availableHeight || !canvas.current || !layer.current) return
    let cancelled = false
    let renderTask: RenderTask | undefined
    let textLayer: TextLayer | undefined
    const textContainer = layer.current
    const canvasElement = canvas.current
    setRendering(true); setSelection('')
    const selected = window.getSelection()
    if (selected?.anchorNode && textContainer.contains(selected.anchorNode)) selected.removeAllRanges()
    async function render() {
      try {
        const original = await pdf!.getPage(page)
        if (cancelled) return
        const base = original.getViewport({ scale: 1 })
        const fitScale = Math.min(availableWidth / base.width, availableHeight / base.height)
        const viewport = original.getViewport({ scale: fitScale * zoom })
        const density = Math.min(window.devicePixelRatio || 1, 2)
        canvasElement.width = Math.ceil(viewport.width * density)
        canvasElement.height = Math.ceil(viewport.height * density)
        setSize({ width: viewport.width, height: viewport.height })
        textContainer.replaceChildren()
        textContainer.style.setProperty('--total-scale-factor', String(viewport.scale * viewport.userUnit))
        const text = await original.getTextContent()
        if (cancelled) return
        setHasText(text.items.some(item => 'str' in item && item.str.trim()))
        renderTask = original.render({ canvas: canvasElement, viewport, transform: density === 1 ? undefined : [density, 0, 0, density, 0, 0] })
        textLayer = new TextLayer({ textContentSource: text, container: textContainer, viewport })
        await Promise.all([renderTask.promise, textLayer.render()])
        if (!cancelled) setRendering(false)
      } catch (reason) { if (!cancelled) { setError(failure(reason, 'Không thể hiển thị trang PDF.')); setRendering(false) } }
    }
    scroll.current?.scrollTo({ top: 0, left: 0 })
    void render()
    return () => { cancelled = true; renderTask?.cancel(); textLayer?.cancel() }
  }, [pdf, page, availableWidth, availableHeight, zoom])

  useEffect(() => {
    function captureSelection() {
      const current = window.getSelection()
      if (loading || rendering || !current?.rangeCount || current.isCollapsed) { setSelection(''); return }
      const range = current.getRangeAt(0)
      if (!layer.current?.contains(range.startContainer) || !layer.current.contains(range.endContainer)) { setSelection(''); return }
      const text = current.toString()
      setSelection(text.trim() ? text : '')
    }
    document.addEventListener('selectionchange', captureSelection)
    return () => document.removeEventListener('selectionchange', captureSelection)
  }, [loading, rendering])

  function clearSelection() {
    setSelection('')
    const current = window.getSelection()
    if (current?.anchorNode && layer.current?.contains(current.anchorNode)) current.removeAllRanges()
  }
  async function copySelection() {
    if (!selection) return
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(selection)
      else if (!document.execCommand('copy')) throw new Error('Copy unavailable')
      notify('Đã sao chép đoạn chọn.', 'success')
    } catch { notify('Không thể sao chép. Bạn có thể dùng Ctrl+C hoặc menu Sao chép của trình duyệt.', 'error') }
  }

  return <section className="panel pdf-reader" id="notebook-pdf-panel" aria-label="PDF gốc">
    <header className="pdf-reader-header"><Icon name="book" size={18} /><select aria-label="Tài liệu đang đọc" title={source.filename} value={source.document_id} onChange={event => { const chosen = documents.find(doc => doc.document_id === event.target.value); if (chosen) onDocumentChange(chosen) }}>{documents.map(doc => <option key={doc.document_id} value={doc.document_id}>{sourceName(doc.filename)}</option>)}</select>
      {selection && <button type="button" className="icon-button" aria-label="Sao chép đoạn chọn" title="Sao chép đoạn chọn" onPointerDown={event => event.preventDefault()} onClick={() => { void copySelection() }}><Icon name="copy" size={18} /></button>}
      <button type="button" className="icon-button" aria-label="Tải PDF gốc" title="Tải PDF gốc" disabled={!info} onClick={async () => { try { await api.downloadOriginalPdf(notebookId, source.document_id, source.original_filename || source.filename, info?.document_version) } catch (reason) { notify(failure(reason, 'Không thể tải PDF.'), 'error') } }}><Icon name="download" size={18} /></button>
      <button type="button" className="icon-button" aria-label="Đóng chế độ đọc chuyên sâu" title="Đóng chế độ đọc chuyên sâu" onClick={onClose}><Icon name="close" size={19} /></button>
    </header>
    {info?.historical && <p className="source-version-banner">Đang xem phiên bản của trích dẫn cũ. <button type="button" className="text-button" onClick={() => { const current = documents.find(doc => doc.document_id === source.document_id); if (current) onDocumentChange(current) }}>Mở bản hiện tại</button></p>}
    <div className="pdf-toolbar">
      <div className="pdf-page-controls"><button type="button" className="icon-button" aria-label="Trang trước" disabled={!pdf || page <= 1} onClick={() => { clearSelection(); setPage(old => old - 1) }}><Icon name="back" size={16} /></button>
        <label><span className="sr-only">Trang PDF</span><input aria-label="Trang PDF" type="number" min={1} max={info?.page_count || 1} value={page} disabled={!pdf} onChange={event => { const value = Number(event.target.value); if (value >= 1 && value <= (info?.page_count || 1)) { clearSelection(); setPage(value) } }} /></label><span>/ {info?.page_count || '…'}</span>
        <button type="button" className="icon-button" aria-label="Trang tiếp theo" disabled={!pdf || page >= (info?.page_count || 1)} onClick={() => { clearSelection(); setPage(old => old + 1) }}><Icon name="arrow" size={16} /></button></div>
      <div className="pdf-zoom-controls">
        <button type="button" className="icon-button" aria-label="Thu nhỏ PDF" disabled={zoom <= .5} onClick={() => setZoom(old => Math.max(.5, old - .25))}><Icon name="minus" size={16} /></button>
        <button type="button" className="text-button pdf-fit-button" title="Vừa trang" aria-label={zoom === 1 ? 'Vừa trang' : `${Math.round(zoom * 100)}%, trở về vừa trang`} onClick={() => setZoom(1)}>{zoom === 1 ? 'Vừa trang' : `${Math.round(zoom * 100)}%`}</button>
        <button type="button" className="icon-button" aria-label="Phóng to PDF" disabled={zoom >= 3} onClick={() => setZoom(old => Math.min(3, old + .25))}><Icon name="plus" size={16} /></button>
      </div>
    </div>
    {target.text && target.page === page && <details className="pdf-evidence"><summary>Trích dẫn · trang {page}</summary><p>{target.text}</p></details>}
    {error && <div className="pdf-message"><ErrorMessage message={error} /><button type="button" className="button" onClick={() => { setPdf(null); setRetry(old => old + 1) }}>Thử lại</button></div>}
    {loading && <div className="pdf-message"><LoadingIndicator text="Đang mở PDF gốc…" /></div>}
    {!loading && !hasText && !error && <p className="pdf-text-warning">Trang này không có lớp văn bản để bôi chọn. PDF scan cần OCR.</p>}
    <div className="pdf-scroll" ref={scroll} aria-busy={loading || rendering}>
      {pdf && !error && <div className="pdf-page" key={`${source.document_id}-${page}-${zoom}-${availableWidth}-${availableHeight}`} style={size}>
        <canvas ref={canvas} aria-label={`PDF nguyên bản, trang ${page}`} />
        <div ref={layer} className="textLayer pdf-text-layer" />
      </div>}
    </div>
  </section>
}
