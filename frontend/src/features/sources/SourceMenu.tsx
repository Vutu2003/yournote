import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Icon } from '../../components/Icon'

export function SourceMenu({ filename, onRead, onDownload, onRename, onRemove, removeDisabled }: {
  filename: string; onRead: () => void; onDownload: () => void; onRename: () => void; onRemove: () => void; removeDisabled: boolean
}) {
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
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
      setPosition({ top: rect.bottom + 190 > window.innerHeight ? Math.max(8, rect.top - 180) : rect.bottom + 4, left: Math.max(8, Math.min(rect.right - 215, window.innerWidth - 223)) })
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
      <button type="button" role="menuitem" onClick={() => act(onDownload)}><Icon name="download" size={17} />Tải PDF gốc</button>
      <button type="button" role="menuitem" className="delete-action" disabled={removeDisabled} onClick={() => act(onRemove)}><Icon name="close" size={17} />Gỡ khỏi sổ</button>
    </div>, document.body)}
  </>
}
