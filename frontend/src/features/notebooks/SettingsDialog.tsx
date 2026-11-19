import { useCallback, useState } from 'react'
import { Icon } from '../../components/Icon'
import { ResultViewerModal } from '../../components/ResultViewerModal'
import { ErrorMessage } from '../../components/Status'
import type { NotebookInfo } from '../../types/notebooks'
import { AIConnections } from '../ai/AIConnections'

const confirmationText = 'ĐẶT LẠI'

export function SettingsDialog({ notebooks, notebookId, onClose, onReset }: {
  notebooks: NotebookInfo[]; notebookId?: string; onClose: () => void
  onReset: (id: string, confirmation: string) => Promise<void>
}) {
  const [selectedId, setSelectedId] = useState(notebookId || '')
  const [confirming, setConfirming] = useState(false)
  const [confirmation, setConfirmation] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const selected = notebooks.find(notebook => notebook.id === selectedId)
  const close = useCallback(() => { if (!pending) onClose() }, [pending, onClose])

  return <ResultViewerModal open title={confirming ? 'Đặt lại sổ tay?' : 'Cài đặt'} artifactTitle="" onClose={close} footer={null}>
    {!confirming && <AIConnections />}
    <form className="notebook-form settings-form" aria-busy={pending} onSubmit={async event => {
      event.preventDefault()
      if (!selected || pending) return
      if (!confirming) { setConfirming(true); return }
      if (confirmation !== confirmationText) return
      setPending(true); setError('')
      try { await onReset(selected.id, confirmation) }
      catch (reason) { setError(reason instanceof Error ? reason.message : 'Không thể đặt lại sổ tay.'); setPending(false) }
    }}>
      {!confirming && <h3 className="settings-section-title"><Icon name="notebook" size={18} />Dữ liệu sổ tay</h3>}
      {notebookId || confirming ? <div className="settings-notebook"><span aria-hidden="true">{selected?.icon}</span><strong>{selected?.title}</strong></div> : <>
        <label htmlFor="settings-notebook">Chọn sổ tay cần đặt lại</label>
        <select id="settings-notebook" value={selectedId} onChange={event => setSelectedId(event.target.value)}>
          <option value="">Chọn sổ tay…</option>
          {notebooks.map(notebook => <option key={notebook.id} value={notebook.id}>{notebook.title}</option>)}
        </select>
      </>}
      <p>Xóa nguồn trong sổ, lịch sử trò chuyện và nội dung Studio. Sổ tay vẫn ở trang chủ; PDF gốc được giữ trong thư viện.</p>
      {confirming ? <>
        <p className="settings-warning">Không thể hoàn tác. Chỉ dữ liệu của sổ tay này bị xóa.</p>
        <label htmlFor="reset-confirmation">Nhập <strong>{confirmationText}</strong> để xác nhận</label>
        <input id="reset-confirmation" autoComplete="off" spellCheck={false} value={confirmation} onChange={event => setConfirmation(event.target.value)} disabled={pending} />
      </> : <p>Dữ liệu được lưu tự động cho đến khi bạn chủ động xóa.</p>}
      <ErrorMessage message={error} />
      <div className="dialog-actions">
        <button type="button" className="button" disabled={pending} onClick={confirming ? () => { setConfirming(false); setConfirmation(''); setError('') } : close}>{confirming ? 'Quay lại' : 'Đóng'}</button>
        <button type="submit" className="button danger" disabled={!selected || pending || (confirming && confirmation !== confirmationText)}>
          <Icon name="refresh" size={16} />{pending ? 'Đang đặt lại…' : confirming ? 'Xác nhận đặt lại' : 'Đặt lại sổ tay'}
        </button>
      </div>
    </form>
  </ResultViewerModal>
}
