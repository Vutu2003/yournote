import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import * as api from '../../api/client'
import { Brand, Icon } from '../../components/Icon'
import { SourcesPanel } from '../sources/SourcesPanel'
import { ChatPanel } from '../chat/ChatPanel'
import { StudioPanel } from '../studio/StudioPanel'
import { useNotebook } from '../../useNotebook'
import type { Notebook, NotebookUpdate } from '../../types/notebooks'
import { usePanelWidths } from '../../hooks/usePanelWidths'
import { PanelResizer } from '../../components/PanelResizer'
import { useReaderWidth } from '../reading/useReaderWidth'
import { useToast } from '../../hooks/useToast'
import type { Citation, DocumentInfo } from '../../types/api'
import type { PdfTarget } from '../../types/reading'
import '../reading/reading.css'

const PdfReader = lazy(() => import('../reading/PdfReader'))

export function NotebookWorkspace({ notebook, onHome, onSaved, onRename, onCreate, onSettings }: {
  notebook: Notebook; onHome: () => void; onSaved: (notebook: Notebook) => void; onRename: () => void; onCreate: () => void; onSettings: () => void
}) {
  const n = useNotebook(notebook.state)
  const notify = useToast()
  const [readingDocument, setReadingDocument] = useState<DocumentInfo | null>(null)
  const [readingScope, setReadingScope] = useState<'document' | 'notebook'>('document')
  const [readingTarget, setReadingTarget] = useState<PdfTarget>({ page: 1, token: 0 })
  const busy = Object.entries(n.loading).some(([operation, value]) => operation !== 'documents' && value)
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'error'>('saved')
  const [leaving, setLeaving] = useState(false)
  const [sourcesCollapsed, setSourcesCollapsed] = useState(false)
  const [studioCollapsed, setStudioCollapsed] = useState(false)
  const panelWidths = usePanelWidths(sourcesCollapsed, studioCollapsed)
  const readerWidth = useReaderWidth(panelWidths.workspaceRef, !!readingDocument)
  const [mobilePanel, setMobilePanel] = useState('chat')
  function openDocument(document: DocumentInfo, page = 1, text?: string | null) {
    n.selectSource(document.filename)
    n.markRead(document.filename)
    setReadingDocument(document); setReadingScope('document')
    setReadingTarget(old => ({ page, text, token: old.token + 1 })); setMobilePanel('pdf')
  }
  function openCitation(citation: Citation) {
    const document = n.documents.find(doc => doc.filename === citation.filename)
    if (document) openDocument(document, citation.page, citation.source_text)
    else notify('Nguồn trích dẫn không còn trong sổ này.', 'error')
  }
  function closeReading() { setReadingDocument(null); setMobilePanel('chat') }
  async function download(document: DocumentInfo) {
    try { await api.downloadOriginalPdf(notebook.id, document.document_id, document.filename) }
    catch (reason) { notify(reason instanceof Error ? reason.message : 'Không thể tải PDF gốc.', 'error') }
  }
  const body: NotebookUpdate = { title: notebook.title, icon: notebook.icon, state: n.snapshot }
  const latest = useRef(body)
  const saved = useRef(JSON.stringify(body))
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const mounted = useRef(true)
  const onSavedRef = useRef(onSaved)
  latest.current = body
  onSavedRef.current = onSaved
  useEffect(() => { window.scrollTo({ top: 0 }) }, [])

  const flush = useCallback(async () => {
    const snapshot = latest.current
    const serialized = JSON.stringify(snapshot)
    if (serialized === saved.current) return
    if (mounted.current) setSaveStatus('saving')
    try {
      const result = await api.saveNotebook(notebook.id, snapshot)
      saved.current = serialized
      onSavedRef.current(result)
      if (mounted.current && JSON.stringify(latest.current) === serialized) setSaveStatus('saved')
    } catch (reason) {
      if (mounted.current) setSaveStatus('error')
      throw reason
    }
  }, [notebook.id])

  useEffect(() => {
    if (JSON.stringify(latest.current) === saved.current) return
    setSaveStatus('saving')
    timer.current = setTimeout(() => { void flush().catch(() => undefined) }, 500)
    return () => clearTimeout(timer.current)
  }, [n.snapshot, notebook.title, notebook.icon, flush])

  useEffect(() => {
    mounted.current = true
    function beforeUnload(event: BeforeUnloadEvent) {
      if (JSON.stringify(latest.current) !== saved.current) event.preventDefault()
    }
    window.addEventListener('beforeunload', beforeUnload)
    return () => {
      mounted.current = false
      window.removeEventListener('beforeunload', beforeUnload)
      clearTimeout(timer.current)
      void flush().catch(() => undefined)
    }
  }, [flush])

  useEffect(() => {
    if (!busy) return
    function beforeUnload(event: BeforeUnloadEvent) { event.preventDefault() }
    window.addEventListener('beforeunload', beforeUnload)
    return () => window.removeEventListener('beforeunload', beforeUnload)
  }, [busy])

  return <div className="app-shell">
    <header className="workspace-header">
      <button type="button" className="icon-button back-home" aria-label="Về trang chủ" title={busy ? 'Đợi tác vụ hoàn tất để trở về trang chủ' : 'Về trang chủ'} disabled={busy || leaving} onClick={async () => {
        setLeaving(true)
        clearTimeout(timer.current)
        try { await flush(); onHome() } catch { setLeaving(false) }
      }}><Icon name="back" /></button>
      <Brand /><span className="header-divider" aria-hidden="true" />
      <button type="button" className="workspace-name" onClick={onRename} disabled={busy || leaving}><span className="workspace-notebook-icon" aria-hidden="true">{notebook.icon}</span><span><h1>{notebook.title}</h1></span><Icon name="edit" size={14} /></button>
      <div className={`save-status ${saveStatus}`} role="status">
        {saveStatus === 'saved' ? <><Icon name="check" size={15} />Đã lưu</> : saveStatus === 'error' ? <button className="text-button" onClick={() => { void flush().catch(() => undefined) }}>Lưu chưa thành công · Thử lại</button> : 'Đang lưu…'}
      </div>
      <div className="workspace-header-actions">{readingDocument ? <button type="button" className="button subtle" onClick={closeReading}><Icon name="back" size={15} /><span>Về sổ</span></button> : <><button type="button" className={`icon-button panel-toggle ${!sourcesCollapsed ? 'active' : ''}`} aria-label={sourcesCollapsed ? 'Hiện bảng nguồn' : 'Ẩn bảng nguồn'} aria-pressed={!sourcesCollapsed} onClick={() => setSourcesCollapsed(old => !old)}><Icon name="panelLeft" /></button>
        <button type="button" className={`icon-button panel-toggle ${!studioCollapsed ? 'active' : ''}`} aria-label={studioCollapsed ? 'Hiện Studio' : 'Ẩn Studio'} aria-pressed={!studioCollapsed} onClick={() => setStudioCollapsed(old => !old)}><Icon name="panelRight" /></button></>}
        <button type="button" className="button subtle workspace-create" disabled={busy || leaving} onClick={async () => {
          setLeaving(true); clearTimeout(timer.current)
          try { await flush(); onCreate() } catch { /* Save status exposes retry. */ } finally { setLeaving(false) }
        }}><Icon name="plus" size={16} /><span>Sổ mới</span></button>
        <button type="button" className="icon-button" aria-label="Cài đặt" title={busy ? 'Đợi tác vụ hoàn tất để mở cài đặt' : 'Cài đặt'} disabled={busy || leaving} onClick={async () => {
          setLeaving(true); clearTimeout(timer.current)
          try { await flush(); onSettings() } catch { /* Save status exposes retry. */ } finally { setLeaving(false) }
        }}><Icon name="settings" /></button>
      </div>
    </header>
    <nav className="mobile-workspace-nav" aria-label="Khu vực làm việc">{(readingDocument ? [
      { id: 'pdf', title: 'PDF gốc', icon: 'book' as const }, { id: 'chat', title: 'Trò chuyện', icon: 'chat' as const },
    ] : [
      { id: 'sources', title: 'Nguồn', icon: 'source' as const }, { id: 'chat', title: 'Trò chuyện', icon: 'chat' as const }, { id: 'studio', title: 'Studio', icon: 'cards' as const },
    ]).map(item => <button type="button" key={item.id} aria-pressed={mobilePanel === item.id} className={mobilePanel === item.id ? 'active' : ''} onClick={() => {
      setMobilePanel(item.id)
      if (item.id === 'sources') setSourcesCollapsed(false)
      if (item.id === 'studio') setStudioCollapsed(false)
    }}><Icon name={item.icon} size={17} />{item.title}{item.id === 'sources' && <span>{n.documents.length}</span>}</button>)}</nav>
    <main ref={panelWidths.workspaceRef} style={{ ...panelWidths.style, ...(readingDocument ? { '--pdf-width': `${readerWidth.value}px` } : {}) } as CSSProperties} className={`workspace ${readingDocument ? 'reading-workspace' : ''}`} data-sources-collapsed={sourcesCollapsed} data-studio-collapsed={studioCollapsed} data-mobile-panel={mobilePanel}>
      {readingDocument && <Suspense fallback={<section className="panel pdf-reader"><p className="pdf-message">Đang mở PDF…</p></section>}><PdfReader key={readingDocument.document_id} notebookId={notebook.id} document={readingDocument} documents={n.documents} target={readingTarget} onClose={closeReading} onDocumentChange={document => openDocument(document)} sourceName={n.sourceName} /></Suspense>}
      <SourcesPanel key="sources" notebook={n} collapsed={sourcesCollapsed || !!readingDocument} onCollapse={() => setSourcesCollapsed(true)} onRead={document => openDocument(document)} onDownload={document => { void download(document) }} />
      <PanelResizer key="source-resizer" side="sources" hidden={!readingDocument && sourcesCollapsed} {...(readingDocument ? readerWidth : panelWidths.sources)} label={readingDocument ? 'Độ rộng PDF' : undefined} controls={readingDocument ? 'notebook-pdf-panel' : undefined} />
      <ChatPanel key="notebook-chat" notebook={n} title={notebook.title} icon={notebook.icon} createdAt={notebook.created_at} onOpenCitation={openCitation} reading={readingDocument ? { notebookId: notebook.id, document_id: readingDocument.document_id, scope: readingScope, onScopeChange: setReadingScope } : undefined} />
      <PanelResizer key="studio-resizer" side="studio" hidden={studioCollapsed || !!readingDocument} {...panelWidths.studio} />
      <StudioPanel key="studio" notebook={n} collapsed={studioCollapsed || !!readingDocument} onCollapse={() => setStudioCollapsed(true)} onOpenCitation={openCitation} onShowChat={() => setMobilePanel('chat')} />
    </main>
  </div>
}
