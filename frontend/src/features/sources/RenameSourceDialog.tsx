import { useEffect, useRef, useState } from 'react'
import { ResultViewerModal } from '../../components/ResultViewerModal'

export function RenameSourceDialog({ filename, name, onSave, onClose }: {
  filename: string; name: string; onSave: (name: string) => boolean; onClose: () => void
}) {
  const [value, setValue] = useState(name)
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => { input.current?.focus(); input.current?.select() }, [])
  return <ResultViewerModal open title="Đổi tên nguồn" artifactTitle="" onClose={onClose} footer={null}>
    <form className="notebook-form" onSubmit={event => { event.preventDefault(); if (onSave(value)) onClose() }}>
      <label htmlFor="source-name">Tên nguồn</label>
      <input ref={input} id="source-name" required maxLength={160} value={value} onChange={event => setValue(event.target.value)} />
      <p className="field-hint">Tệp gốc: {filename}</p>
      <div className="dialog-actions"><button type="button" className="button" onClick={onClose}>Hủy</button>
        <button type="submit" className="button primary" disabled={!value.trim() || /[\u0000-\u001f\u007f]/.test(value)}>Lưu thay đổi</button>
      </div>
    </form>
  </ResultViewerModal>
}
