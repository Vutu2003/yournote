import { useCallback, useRef, useState } from 'react'
import type { NotebookState } from '../../useNotebook'
import { ErrorMessage, LoadingIndicator } from '../../components/Status'
import { Icon } from '../../components/Icon'
import { ResultViewerModal } from '../../components/ResultViewerModal'
import { SourceMenu } from './SourceMenu'
import type { DocumentInfo } from '../../types/api'
import { RenameSourceDialog } from './RenameSourceDialog'

export function SourcesPanel({ notebook: n, collapsed = false, onCollapse, onRead, onDownload }: {
  notebook: NotebookState; collapsed?: boolean; onCollapse?: () => void
  onRead: (document: DocumentInfo) => void; onDownload: (document: DocumentInfo) => void
}) {
  const [replacing, setReplacing] = useState<DocumentInfo | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [libraryOpen, setLibraryOpen] = useState(false)
  const [chosen, setChosen] = useState<string[]>([])
  const [search, setSearch] = useState('')
  const [readFilter, setReadFilter] = useState('all')
  const [renaming, setRenaming] = useState<DocumentInfo | null>(null)
  const closeRename = useCallback(() => setRenaming(null), [])
  const matchesSearch = (doc: DocumentInfo) => `${n.sourceName(doc.filename)} ${doc.filename}`.toLocaleLowerCase('vi').includes(search.toLocaleLowerCase('vi'))
  const shown = n.documents.filter(doc => matchesSearch(doc) && (readFilter === 'all' || n.readDocuments.includes(doc.filename) === (readFilter === 'read')))
  const readCount = n.documents.filter(doc => n.readDocuments.includes(doc.filename)).length
  const closeLibrary = useCallback(() => { setLibraryOpen(false); setChosen([]) }, [])
  const input = useRef<HTMLInputElement>(null)
  async function upload() {
    if (file && await n.upload(file,replacing || undefined)) {
      setFile(null); setReplacing(null)
      if (input.current) input.current.value = ''
    }
  }
  return <section id="notebook-sources-panel" className="panel sources-panel" hidden={collapsed} aria-labelledby="sources-title">
    <div className="panel-header"><span className="panel-heading"><Icon name="source" size={17} /><h2 id="sources-title">Nguồn tài liệu</h2><span className="count-badge" aria-label={`${n.documents.length} tài liệu đã lập chỉ mục`}>{n.documents.length}</span></span>
      {onCollapse && <button type="button" className="icon-button collapse-panel" aria-label="Thu gọn bảng nguồn" onClick={onCollapse}><Icon name="panelLeft" size={18} /></button>}
    </div>
    <div className="panel-body sources-body">
      <div className="source-add-actions"><button type="button" className="button library-source-button" disabled={n.loading.documents || n.snapshot.document_filenames.length >= 64} onClick={() => setLibraryOpen(true)}><Icon name="plus" size={17} />Thêm từ thư viện</button>
        <button type="button" className="button subtle upload-shortcut" disabled={n.loading.upload || n.snapshot.document_filenames.length >= 64} onClick={() => input.current?.click()}><Icon name="upload" size={16} />Tải tài liệu</button></div>
      {(n.documents.length > 3 || search) && <label className="source-search"><Icon name="search" size={15} /><span className="sr-only">Tìm nguồn tài liệu</span><input type="search" placeholder="Tìm trong nguồn…" value={search} onChange={event => setSearch(event.target.value)} /></label>}
      {!!n.documents.length && <div className="source-reading-toolbar">
        <span className="source-reading-count" role="status"><Icon name="book" size={14} />Đã đọc {readCount}/{n.documents.length}</span>
        <select aria-label="Lọc theo trạng thái đọc" value={readFilter} onChange={event => setReadFilter(event.target.value)}>
          <option value="all">Tất cả</option><option value="unread">Chưa đọc</option><option value="read">Đã đọc</option>
        </select>
      </div>}
      <div className="source-actions">
        <button type="button" className="text-button" disabled={!n.documents.length || n.loading.documents}
          onClick={() => n.choose(n.documents.map(doc => doc.filename))}>Chọn tất cả</button>
        <button type="button" className="text-button" disabled={!n.selected.length} onClick={() => n.choose([])}>Bỏ chọn</button>
        <button type="button" className="icon-button refresh-sources" aria-label="Làm mới nguồn" title="Làm mới" disabled={n.loading.documents || n.loading.upload} onClick={n.refresh}><Icon name="refresh" size={14} /></button>
      </div>
      {n.loading.documents && <LoadingIndicator text="Đang tải tài liệu..." />}
      <ErrorMessage message={n.errors.documents} />
      {!n.loading.documents && !n.errors.documents && !n.documents.length && <p className="muted">Chưa có tài liệu. Thêm tài liệu để bắt đầu.</p>}
      <ul className="document-list">
        {shown.map(doc => <li className={`source-item ${n.readDocuments.includes(doc.filename) ? 'source-read' : ''}`} key={doc.filename}>
          <div className="source-entry">
          <label className={`source-row ${n.selected.includes(doc.filename) ? 'selected' : ''}`}>
            <span className="pdf-symbol"><Icon name="source" size={19} /><span>{(doc.kind === 'markdown' ? 'MD' : doc.kind === 'text' ? 'TXT' : doc.kind || 'PDF').toUpperCase()}</span></span>
            <span className="source-info"><span className="source-name" title={doc.filename}>{n.sourceName(doc.filename)}</span>
              <small>{!doc.kind || doc.kind === 'pdf' ? `${doc.page_count} trang · ${doc.chunk_count} đoạn` : `${doc.anchor_count || 0} đoạn văn`}</small>
              {!!doc.document_version && n.documents.filter(item => (item.original_filename || item.filename) === (doc.original_filename || doc.filename)).length > 1 && <small>Bản {doc.document_version.slice(0, 8)} · Có nguồn trùng tên</small>}
              {!!doc.warnings?.length && <small className="source-warning">Có trang chưa đọc được văn bản; có thể cần OCR.</small>}
            </span>
            <input type="checkbox" aria-label={`Dùng nguồn ${n.sourceName(doc.filename)} cho chat và Studio`} title="Dùng cho chat và Studio" checked={n.selected.includes(doc.filename)} onChange={() => n.toggle(doc.filename)} />
          </label>
          <label className="source-read-status"><input type="checkbox" aria-label={`Đã đọc: ${n.sourceName(doc.filename)}`} checked={n.readDocuments.includes(doc.filename)} onChange={() => n.toggleRead(doc.filename)} /><span>Đã đọc</span></label>
          </div>
          <SourceMenu filename={n.sourceName(doc.filename)} onRead={() => onRead(doc)} onDownload={() => onDownload(doc)} onRename={() => setRenaming(doc)} onReplace={() => { setReplacing(doc); setFile(null); requestAnimationFrame(() => input.current?.click()) }} onRemove={() => n.detach(doc.filename)} replaceDisabled={!doc.document_version} removeDisabled={!!n.loading.graph || !!n.loading.comparison || !!n.loading.report || !!n.loading.upload || !!n.loading.chat || !!n.loading.summary || !!n.loading.quiz || !!n.loading.flashcards || !!n.loading.mindmap} />
        </li>)}
      </ul>
      {!!n.documents.length && !shown.length && <p className="field-hint">Không có tài liệu phù hợp.</p>}
      <div className="source-filter">
        <p className="selection-count" role="status">Đã chọn {n.selected.length} tài liệu</p>
        <label htmlFor="page-filter">Trang</label>
        <select id="page-filter" value={n.page} disabled={!n.selectedDocument || !!n.selectedDocument.kind && n.selectedDocument.kind !== 'pdf'} onChange={event => n.setPage(event.target.value)}>
          <option value="">Tất cả các trang</option>
          {n.selectedDocument?.pages.map(page => <option key={page} value={page}>Trang {page}</option>)}
        </select>
        <p className="field-hint">Chỉ lọc trang khi chọn một PDF. Nguồn văn bản dùng tiêu đề và đoạn.</p>
      </div>
      <div className={`upload-area ${file ? 'has-file' : ''}`} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); if (!n.loading.upload && (replacing || n.snapshot.document_filenames.length < 64)) setFile(event.dataTransfer.files[0] || null) }}>
        <span className="upload-drop-icon"><Icon name="upload" size={20} /></span><label htmlFor="pdf-upload">Tải tài liệu lên</label>
        <p className="field-hint">Kéo thả tài liệu vào đây hoặc <button type="button" className="text-button" disabled={n.loading.upload || n.snapshot.document_filenames.length >= 64} onClick={() => input.current?.click()}>chọn tệp</button></p>
        <input className="sr-only" ref={input} id="pdf-upload" type="file" accept=".pdf,.docx,.md,.txt,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document" disabled={n.loading.upload || (!replacing && n.snapshot.document_filenames.length >= 64)}
          onChange={event => setFile(event.target.files?.[0] || null)} />
        {replacing && <p className="field-hint">Cập nhật nội dung: {n.sourceName(replacing.filename)}. Thay đổi áp dụng cho thư viện và các sổ đang dùng nguồn này; trích dẫn cũ vẫn mở bản đã lưu. <button type="button" className="text-button" disabled={n.loading.upload} onClick={() => { setReplacing(null); setFile(null); if (input.current) input.current.value = '' }}>Hủy cập nhật</button></p>}
        {file && <p className="selected-file" title={file.name}>{file.name}</p>}
        <p className="upload-limit">PDF / DOCX / MD / TXT · Tối đa 25 MB</p>
        {file && <button type="button" className="button primary" disabled={n.loading.upload || n.loading.documents} onClick={upload}><Icon name="plus" size={15} />{replacing ? 'Cập nhật nguồn' : 'Thêm nguồn'}</button>}
        {n.loading.upload && <LoadingIndicator text="Đang thêm và lập chỉ mục tài liệu..." />}
        <ErrorMessage message={n.errors.upload} />
        {n.uploadStatus && <p className="success-message" role="status">{n.uploadStatus}</p>}
      </div>
    </div>
    <ResultViewerModal open={libraryOpen} title="Thêm nguồn từ thư viện" artifactTitle="" onClose={closeLibrary} footer={<>
      <span className="muted">Đã chọn {chosen.length} nguồn · Tối đa 64 nguồn mỗi sổ</span>
      <button type="button" className="button primary" disabled={!chosen.length || chosen.length + n.snapshot.document_filenames.length > 64} onClick={() => { n.attach(chosen); closeLibrary() }}>Thêm vào sổ</button>
    </>}>
      <ul className="document-list library-documents">{n.library.filter(doc => !n.snapshot.document_filenames.includes(doc.filename)).map(doc => <li key={doc.filename}>
        <label className={`source-row ${chosen.includes(doc.filename) ? 'selected' : ''}`}><input type="checkbox" checked={chosen.includes(doc.filename)} onChange={() => setChosen(old => old.includes(doc.filename) ? old.filter(name => name !== doc.filename) : [...old, doc.filename])} />
          <Icon name="source" size={20} /><span className="source-info"><span className="source-name" title={doc.filename}>{n.sourceName(doc.filename)}</span><small>{!doc.kind || doc.kind === 'pdf' ? `${doc.page_count} trang` : `${doc.kind.toUpperCase()} · ${doc.anchor_count || 0} đoạn văn`}</small></span></label>
      </li>)}</ul>
      {!n.library.some(doc => !n.snapshot.document_filenames.includes(doc.filename)) && <p className="muted">Không có nguồn mới trong thư viện. Bạn có thể tải PDF lên từ bảng Nguồn tài liệu.</p>}
    </ResultViewerModal>
    {renaming && <RenameSourceDialog filename={renaming.filename} name={n.sourceName(renaming.filename)} onSave={name => n.renameSource(renaming.filename, name)} onClose={closeRename} />}
  </section>
}
