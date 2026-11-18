import { useCallback, useState } from 'react'
import { ResultViewerModal } from '../../components/ResultViewerModal'
import { ErrorMessage } from '../../components/Status'
import type { NotebookInfo } from '../../types/notebooks'

const icons = ['📓', '📚', '🔬', '📈', '🧠', '🌐', '💡', '🧬', '🎯', '🌱', '💻', '🎨']

export function NotebookDialog({ notebook, mode, onClose, onSubmit }: {
  notebook?: NotebookInfo; mode: 'create' | 'rename' | 'delete'; onClose: () => void
  onSubmit: (title: string, icon: string) => Promise<void>
}) {
  const [title, setTitle] = useState(notebook?.title || '')
  const [icon, setIcon] = useState(notebook?.icon || '📓')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const close = useCallback(() => { if (!pending) onClose() }, [pending, onClose])
  const heading = mode === 'create' ? 'Tạo sổ ghi chú mới' : mode === 'rename' ? 'Chỉnh sửa sổ ghi chú' : 'Xóa sổ ghi chú?'
  return <ResultViewerModal open title={heading} artifactTitle="" onClose={close} footer={null}>
    <form className="notebook-form" onSubmit={async event => {
      event.preventDefault()
      if (pending) return
      setPending(true); setError('')
      try { await onSubmit(title.trim(), icon) }
      catch (reason) { setError(reason instanceof Error ? reason.message : 'Không thể hoàn tất thao tác.'); setPending(false) }
    }}>
      {mode === 'delete' ? <p>Sổ <strong>{notebook?.title}</strong> cùng lịch sử trò chuyện và nội dung Studio sẽ bị xóa. Các PDF vẫn được giữ trong thư viện tài liệu.</p> : <>
        <label htmlFor="notebook-title">Tên sổ ghi chú</label>
        <input id="notebook-title" autoFocus required maxLength={160} placeholder="Ví dụ: Nghiên cứu biến thiên nhịp tim" value={title} onChange={event => setTitle(event.target.value)} disabled={pending} />
        <span className="field-label">Biểu tượng</span>
        <div className="notebook-icons" role="group" aria-label="Chọn biểu tượng">
          {icons.map(value => <button type="button" key={value} aria-label={`Biểu tượng ${value}`} aria-pressed={icon === value} className={icon === value ? 'chosen' : ''} disabled={pending} onClick={() => setIcon(value)}>{value}</button>)}
        </div>
      </>}
      <ErrorMessage message={error} />
      <div className="dialog-actions"><button type="button" className="button" disabled={pending} onClick={close}>Hủy</button>
        <button type="submit" className={`button ${mode === 'delete' ? 'danger' : 'primary'}`} disabled={pending || (mode !== 'delete' && !title.trim())}>
          {pending ? 'Đang xử lý…' : mode === 'create' ? 'Tạo sổ ghi chú' : mode === 'rename' ? 'Lưu thay đổi' : 'Xóa sổ ghi chú'}
        </button>
      </div>
    </form>
  </ResultViewerModal>
}
