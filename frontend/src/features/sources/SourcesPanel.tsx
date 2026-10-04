import { useRef, useState } from 'react'
import type { NotebookState } from '../../useNotebook'
import { ErrorMessage, LoadingIndicator } from '../../components/Status'

export function SourcesPanel({ notebook: n }: { notebook: NotebookState }) {
  const [file, setFile] = useState<File | null>(null)
  const input = useRef<HTMLInputElement>(null)
  async function upload() {
    if (file && await n.upload(file)) {
      setFile(null)
      if (input.current) input.current.value = ''
    }
  }
  return <section className="panel sources-panel" aria-labelledby="sources-title">
    <div className="panel-header"><h2 id="sources-title">Nguồn tài liệu</h2>
      <span className="count-badge" aria-label={`${n.documents.length} tài liệu đã lập chỉ mục`}>{n.documents.length}</span>
    </div>
    <div className="panel-body sources-body">
      <div className="source-actions">
        <button type="button" className="text-button" disabled={!n.documents.length || n.loading.documents}
          onClick={() => n.choose(n.documents.map(doc => doc.filename))}>Chọn tất cả</button>
        <button type="button" className="text-button" disabled={!n.selected.length} onClick={() => n.choose([])}>Bỏ chọn</button>
        <button type="button" className="text-button" disabled={n.loading.documents || n.loading.upload} onClick={n.refresh}>Làm mới</button>
      </div>
      {n.loading.documents && <LoadingIndicator text="Đang tải tài liệu..." />}
      <ErrorMessage message={n.errors.documents} />
      {!n.loading.documents && !n.errors.documents && !n.documents.length && <p className="muted">Chưa có tài liệu. Thêm PDF để bắt đầu.</p>}
      <ul className="document-list">
        {n.documents.map(doc => <li key={doc.filename}>
          <label className={`source-row ${n.selected.includes(doc.filename) ? 'selected' : ''}`}>
            <input type="checkbox" checked={n.selected.includes(doc.filename)} onChange={() => n.toggle(doc.filename)} />
            <span className="source-info"><span className="source-name" title={doc.filename}>{doc.filename}</span>
              <small>{doc.page_count} trang · {doc.chunk_count} đoạn</small>
            </span>
          </label>
        </li>)}
      </ul>
      <div className="source-filter">
        <p className="selection-count" role="status">Đã chọn {n.selected.length} tài liệu</p>
        <label htmlFor="page-filter">Trang</label>
        <select id="page-filter" value={n.page} disabled={!n.selectedDocument} onChange={event => n.setPage(event.target.value)}>
          <option value="">Tất cả các trang</option>
          {n.selectedDocument?.pages.map(page => <option key={page} value={page}>Trang {page}</option>)}
        </select>
        <p className="field-hint">Chỉ lọc trang khi chọn một tài liệu.</p>
      </div>
      <div className="upload-area">
        <label htmlFor="pdf-upload">Thêm tài liệu PDF</label>
        <input ref={input} id="pdf-upload" type="file" accept=".pdf,application/pdf" disabled={n.loading.upload}
          onChange={event => setFile(event.target.files?.[0] || null)} />
        {file && <p className="selected-file" title={file.name}>{file.name}</p>}
        <p className="field-hint">Một tệp PDF, tối đa 25 MB.</p>
        <button type="button" className="button" disabled={!file || n.loading.upload || n.loading.documents} onClick={upload}>Thêm nguồn</button>
        {n.loading.upload && <LoadingIndicator text="Đang thêm và lập chỉ mục tài liệu..." />}
        <ErrorMessage message={n.errors.upload} />
        {n.uploadStatus && <p className="success-message" role="status">{n.uploadStatus}</p>}
      </div>
    </div>
  </section>
}
