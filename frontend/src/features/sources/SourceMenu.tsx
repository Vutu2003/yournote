import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Icon } from '../../components/Icon'

export function SourceMenu({ filename, onRead, onDownload, onRename, onReplace, onRemove, removeDisabled, replaceDisabled }: {
  filename: string; onRead: () => void; onDownload: () => void; onRename: () => void; onReplace: () => void; onRemove: () => void; removeDisabled: boolean; replaceDisabled?: boolean
}) {
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const open = position !== null
  useLayoutEffect(() => {
    if (!open || !trigger.current || !menu.current) return
    const anchor = trigger.current.getBoundingClientRect()
    const bounds = menu.current.getBoundingClientRect()
    const top = anchor.bottom + 4 + bounds.height <= window.innerHeight - 12
      ? anchor.bottom + 4 : Math.max(12, anchor.top - bounds.height - 4)
    const left = Math.max(12, Math.min(anchor.right - bounds.width, window.innerWidth - bounds.width - 12))
    setPosition(previous => previous && (previous.top !== top || previous.left !== left) ? { top, left } : previous)
  }, [open])
  useEffect(() => {
    if (!position) return
    menu.current?.querySelector('button')?.focus()
    function outside(event: PointerEvent) { if (!menu.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) setPosition(null) }
    function dismiss() { setPosition(null) }
    window.addEventListener('pointerdown', outside)
    window.addEventListener('resize', dismiss)
    window.addEventListener('scroll', dismiss, true)
    return () => { window.removeEventListener('pointerdown', outside); window.removeEventListener('resize', dismiss); window.removeEventListener('scroll', dismiss, true) }
  }, [position])
  function act(action: () => void) { setPosition(null); trigger.current?.focus(); action() }
  return <>
    <button ref={trigger} type="button" className="icon-button source-menu-trigger" aria-label={`Tùy chọn tài liệu ${filename}`} aria-haspopup="menu" aria-expanded={!!position} onClick={() => {
      if (position) { setPosition(null); return }
      const rect = trigger.current!.getBoundingClientRect()
      setPosition({ top: rect.bottom + 4, left: rect.left })
    }}><Icon name="more" size={16} /></button>
    {position && createPortal(<div ref={menu} role="menu" className="source-menu-popup" style={position} onKeyDown={event => {
      if (event.key === 'Escape') { event.preventDefault(); setPosition(null); trigger.current?.focus() }
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault()
        const buttons = [...menu.current!.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')]
        const index = buttons.indexOf(document.activeElement as HTMLButtonElement)
        buttons[(index + (event.key === 'ArrowDown' ? 1 : buttons.length - 1)) % buttons.length]?.focus()
      }
    }}>
      <button type="button" role="menuitem" onClick={() => act(onRead)}><Icon name="book" size={17} />Đọc chuyên sâu</button>
      <button type="button" role="menuitem" onClick={() => act(onRename)}><Icon name="edit" size={17} />Đổi tên nguồn</button>
      <button type="button" role="menuitem" onClick={() => act(onDownload)}><Icon name="download" size={17} />Tải tệp gốc</button>
      <button type="button" role="menuitem" disabled={removeDisabled || replaceDisabled} onClick={() => act(onReplace)}><Icon name="refresh" size={17} />Cập nhật nội dung</button>
      <button type="button" role="menuitem" className="delete-action" disabled={removeDisabled} onClick={() => act(onRemove)}><Icon name="close" size={17} />Gỡ khỏi sổ</button>
    </div>, document.body)}
  </>
}
