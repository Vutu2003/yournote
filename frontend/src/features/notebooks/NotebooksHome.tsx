import { useEffect, useMemo, useRef, useState } from 'react'
import { Brand, Icon } from '../../components/Icon'
import { ErrorMessage, LoadingIndicator } from '../../components/Status'
import type { NotebookInfo } from '../../types/notebooks'
import { useTheme } from '../../hooks/useTheme'

function initialView(): 'list' | 'grid' {
  try { return localStorage.getItem('notebooks-view') === 'grid' ? 'grid' : 'list' } catch { return 'list' }
}
const date = (value: string) => new Intl.DateTimeFormat('vi-VN', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value))

export function NotebooksHome({ notebooks, loading, error, opening, onOpen, onCreate, onEdit, onDelete, onRefresh, onSettings }: {
  notebooks: NotebookInfo[]; loading: boolean; error: string; opening: string | null
  onOpen: (id: string) => void; onCreate: () => void; onEdit: (notebook: NotebookInfo) => void
  onDelete: (notebook: NotebookInfo) => void; onRefresh: () => void; onSettings: () => void
}) {
  const { theme, toggleTheme } = useTheme()
  const [query, setQuery] = useState('')
  const [view, setView] = useState(initialView)
  const [filter, setFilter] = useState('all')
  const [sort, setSort] = useState('updated')
  const [menu, setMenu] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const menuTrigger = useRef<HTMLButtonElement | null>(null)
  useEffect(() => { try { localStorage.setItem('notebooks-view', view) } catch { /* Preference is optional. */ } }, [view])
  useEffect(() => {
    if (!menu) return
    function dismiss(event: MouseEvent) { if (!menuRef.current?.contains(event.target as Node)) setMenu(null) }
    function escape(event: KeyboardEvent) { if (event.key === 'Escape') { setMenu(null); menuTrigger.current?.focus() } }
    document.addEventListener('click', dismiss); document.addEventListener('keydown', escape)
    return () => { document.removeEventListener('click', dismiss); document.removeEventListener('keydown', escape) }
  }, [menu])
  const shown = useMemo(() => notebooks.filter(notebook => {
    if (filter === 'recent' && Date.now() - new Date(notebook.updated_at).getTime() > 7 * 86400000) return false
    if (filter === 'chats' && !notebook.chat_count) return false
    return notebook.title.toLocaleLowerCase('vi').includes(query.trim().toLocaleLowerCase('vi'))
  }).sort((a, b) => sort === 'title' ? a.title.localeCompare(b.title, 'vi') :
    new Date(sort === 'created' ? b.created_at : b.updated_at).getTime() - new Date(sort === 'created' ? a.created_at : a.updated_at).getTime()), [notebooks, filter, query, sort])

  function actions(notebook: NotebookInfo) {
    return <div className="notebook-actions" ref={menu === notebook.id ? menuRef : undefined}>
      <button type="button" className="icon-button more-button" aria-label={`Tùy chọn cho ${notebook.title}`} aria-expanded={menu === notebook.id} onClick={event => {
        event.stopPropagation(); menuTrigger.current = event.currentTarget; setMenu(menu === notebook.id ? null : notebook.id)
      }}><Icon name="more" size={18} /></button>
      {menu === notebook.id && <div className="notebook-menu">
        <button type="button" onClick={() => { setMenu(null); onEdit(notebook) }}><Icon name="edit" size={17} />Chỉnh sửa</button>
        <button type="button" className="delete-action" onClick={() => { setMenu(null); onDelete(notebook) }}><Icon name="trash" size={17} />Xóa sổ ghi chú</button>
      </div>}
    </div>
  }

  return <div className="home-shell">
    <header className="home-header">
      <Brand />
      <nav className="home-nav" aria-label="Lọc sổ ghi chú">
        {[['all', 'Tất cả'], ['recent', 'Gần đây'], ['chats', 'Đã trò chuyện']].map(([id, label]) => <button type="button" key={id} className={filter === id ? 'active' : ''} aria-pressed={filter === id} onClick={() => setFilter(id)}>{label}</button>)}
      </nav>
      <div className="home-header-tools">
        <label className="notebook-search"><Icon name="search" size={18} /><span className="sr-only">Tìm kiếm sổ ghi chú</span><input type="search" placeholder="Tìm kiếm trong sổ ghi chú" value={query} onChange={event => setQuery(event.target.value)} /></label>
        <div className="view-switch" role="group" aria-label="Kiểu hiển thị">
          <button type="button" className={view === 'grid' ? 'active' : ''} aria-label="Dạng lưới" aria-pressed={view === 'grid'} onClick={() => setView('grid')}><Icon name="grid" size={18} /></button>
          <button type="button" className={view === 'list' ? 'active' : ''} aria-label="Dạng danh sách" aria-pressed={view === 'list'} onClick={() => setView('list')}><Icon name="list" size={19} /></button>
        </div>
        <button type="button" className="icon-button theme-toggle" aria-label={theme === 'dark' ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'} title={theme === 'dark' ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'} onClick={toggleTheme}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button>
        <button type="button" className="icon-button" aria-label="Cài đặt" title="Cài đặt" disabled={loading || !!opening} onClick={onSettings}><Icon name="settings" /></button>
      </div>
    </header>
    <main className="notebooks-main">
      <div className="home-title-row"><h1>Sổ ghi chú của tôi <span className="count-badge">{notebooks.length}</span></h1>
        <button type="button" className="new-notebook button primary" onClick={onCreate} disabled={loading}><Icon name="plus" size={21} />Sổ ghi chú mới</button>
      </div>
      <div className="home-toolbar"><span className="library-label"><Icon name="notebook" size={16} />{query ? `${shown.length} kết quả` : filter === 'recent' ? 'Cập nhật trong 7 ngày qua' : filter === 'chats' ? 'Sổ có lịch sử trò chuyện' : 'Tất cả sổ ghi chú'}</span>
        <label className="sort-control"><span>Sắp xếp:</span><select aria-label="Sắp xếp sổ ghi chú" value={sort} onChange={event => setSort(event.target.value)}><option value="updated">Cập nhật gần đây</option><option value="created">Ngày tạo mới nhất</option><option value="title">Tên A–Z</option></select></label>
      </div>
      {error && <div className="home-error"><ErrorMessage message={error} /><button type="button" className="text-button" onClick={onRefresh}>Thử lại</button></div>}
      {loading ? <div className="home-loading"><LoadingIndicator text="Đang tải sổ ghi chú…" /></div> : shown.length ? <>
        {view === 'list' ? <div className="notebook-table-wrap"><table className="notebook-table"><thead><tr><th scope="col">Tiêu đề</th><th scope="col">Nguồn</th><th scope="col">Ngày tạo</th><th scope="col">Vai trò</th><th scope="col"><span className="sr-only">Tùy chọn</span></th></tr></thead>
          <tbody>{shown.map(notebook => <tr key={notebook.id} className={opening === notebook.id ? 'opening' : ''}>
            <td><button type="button" className="notebook-open" disabled={!!opening} onClick={() => onOpen(notebook.id)}><span className="notebook-emoji" aria-hidden="true">{notebook.icon}</span><span className="notebook-row-title">{notebook.title}</span>{opening === notebook.id && <span className="muted">Đang mở…</span>}</button></td>
            <td>{notebook.source_count} nguồn</td><td>{date(notebook.created_at)}</td><td>Chủ sở hữu</td><td>{actions(notebook)}</td>
          </tr>)}</tbody></table></div> : <div className="notebook-grid">{shown.map((notebook, index) => <article className={`notebook-card tone-${index % 4}`} key={notebook.id}>
          {actions(notebook)}<button type="button" className="notebook-card-open" disabled={!!opening} onClick={() => onOpen(notebook.id)}>
            <span className="card-emoji" aria-hidden="true">{notebook.icon}</span><h2>{notebook.title}</h2>
            <span className="card-date">{date(notebook.created_at)}</span><span className="card-metadata"><span>{notebook.source_count} nguồn</span><span>{notebook.chat_count} lượt trò chuyện</span></span>
            {opening === notebook.id && <span>Đang mở…</span>}
          </button></article>)}</div>}
      </> : !error && <div className="home-empty"><span className="empty-notebooks-icon"><Icon name="notebook" size={38} /></span>
        <h2>{query || filter !== 'all' ? 'Không tìm thấy sổ ghi chú' : 'Chưa có sổ ghi chú'}</h2>
        {query || filter !== 'all' ? <button type="button" className="button" onClick={() => { setQuery(''); setFilter('all') }}>Xem tất cả</button> : <button type="button" className="button primary" onClick={onCreate}><Icon name="plus" size={18} />Tạo sổ ghi chú đầu tiên</button>}
      </div>}
    </main>
  </div>
}
