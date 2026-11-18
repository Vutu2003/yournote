import { useCallback, useId, useState } from 'react'
import type { NotebookState } from '../../useNotebook'
import type { UserNote } from '../../types/notebooks'
import { Icon } from '../../components/Icon'
import { ResultViewerModal } from '../../components/ResultViewerModal'
import './notes.css'

const noteTitle = (note: UserNote) => note.title.trim() || 'Ghi chú chưa đặt tên'
const updated = (note: UserNote) => new Intl.DateTimeFormat('vi-VN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(note.updatedAt)

function NoteEditor({ note, onChange }: { note: UserNote; onChange: (id: string, patch: Pick<Partial<UserNote>, 'title' | 'content'>) => void }) {
  const id = useId()
  return <div className="user-note-editor">
    <label htmlFor={`${id}-title`}>Tiêu đề</label>
    <input id={`${id}-title`} className="user-note-title" maxLength={160} placeholder="Ghi chú chưa đặt tên" value={note.title} onChange={event => onChange(note.id, { title: event.target.value })} />
    <label htmlFor={`${id}-content`}>Nội dung</label>
    <textarea id={`${id}-content`} className="user-note-content" maxLength={100000} placeholder="Viết ghi chú của bạn…" value={note.content} onChange={event => onChange(note.id, { content: event.target.value })} />
  </div>
}

export function NotesPanel({ notebook: n }: { notebook: NotebookState }) {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const closeEditor = useCallback(() => setExpanded(false), [])
  const active = n.notes.find(note => note.id === activeId) || n.notes[0]
  const deleting = n.notes.find(note => note.id === deletingId)
  return <section className="user-notes" aria-label="Ghi chú của bạn">
    <div className="notes-heading"><h3>Ghi chú của bạn</h3><button type="button" className="button" disabled={n.notes.length >= 100} onClick={() => { const id = n.createNote(); if (id) { setActiveId(id); setDeletingId(null) } }}><Icon name="plus" size={15} />Tạo ghi chú</button></div>
    {!!n.notes.length && <ul className="user-note-list" aria-label="Danh sách ghi chú">{n.notes.map(note => <li key={note.id}>
      <button type="button" className={`user-note-open ${active?.id === note.id ? 'active' : ''}`} aria-pressed={active?.id === note.id} onClick={() => { setActiveId(note.id); setDeletingId(null) }}>
        <Icon name="notebook" size={17} /><span><strong>{noteTitle(note)}</strong><small>{note.content.trim() || 'Chưa có nội dung'}</small></span><time dateTime={new Date(note.updatedAt).toISOString()}>{updated(note)}</time>
      </button>
    </li>)}</ul>}
    {active ? <>
      <div className="note-editor-actions"><button type="button" className="text-button" onClick={() => setExpanded(true)}><Icon name="expand" size={14} />Mở rộng</button><button type="button" className="icon-button delete-note" aria-label={`Xóa ghi chú ${noteTitle(active)}`} title="Xóa ghi chú" onClick={() => setDeletingId(active.id)}><Icon name="trash" size={16} /></button></div>
      <NoteEditor key={active.id} note={active} onChange={n.updateNote} />
    </> : <p className="notes-empty">Chưa có ghi chú.</p>}
    {deleting && <div className="note-delete-confirm" role="alert"><p>Xóa ghi chú “{noteTitle(deleting)}”?</p><div><button type="button" className="button" onClick={() => setDeletingId(null)}>Hủy</button><button type="button" className="button danger" onClick={() => { n.deleteNote(deleting.id); setDeletingId(null) }}>Xóa ghi chú</button></div></div>}
    {expanded && active && <ResultViewerModal open title="Ghi chú" artifactTitle="" onClose={closeEditor} footer={<button type="button" className="button" onClick={closeEditor}>Đóng</button>}>
      <div className="expanded-note"><NoteEditor note={active} onChange={n.updateNote} /></div>
    </ResultViewerModal>}
  </section>
}
