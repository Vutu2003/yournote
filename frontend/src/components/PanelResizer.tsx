import { useEffect, useRef, useState } from 'react'

export function PanelResizer({ side, hidden, value, min, max, onChange, onReset, label: customLabel, controls }: {
  side: 'sources' | 'studio'; hidden: boolean; value: number; min: number; max: number
  onChange: (value: number) => void; onReset: () => void
  label?: string; controls?: string
}) {
  const drag = useRef<{ pointer: number; startX: number; startWidth: number } | null>(null)
  const cleanup = useRef<(() => void) | null>(null)
  const change = useRef(onChange)
  change.current = onChange
  const [dragging, setDragging] = useState(false)
  const direction = side === 'sources' ? 1 : -1
  const label = customLabel || (side === 'sources' ? 'Độ rộng bảng nguồn' : 'Độ rộng Studio')
  useEffect(() => () => cleanup.current?.(), [])

  return <div className={`panel-resizer resizer-${side}`} hidden={hidden} role="separator" tabIndex={0}
    aria-label={label} aria-orientation="vertical" aria-controls={controls || `notebook-${side}-panel`}
    aria-valuemin={min} aria-valuemax={Math.round(max)} aria-valuenow={Math.round(value)} aria-valuetext={`${Math.round(value)} pixel`}
    title={`${label}: kéo để thay đổi, nhấp đúp để đặt lại`} data-dragging={dragging}
    onDoubleClick={onReset}
    onKeyDown={event => {
      const step = event.shiftKey ? 40 : 16
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        event.preventDefault()
        onChange(value + direction * (event.key === 'ArrowRight' ? step : -step))
      } else if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault(); onChange(event.key === 'Home' ? min : max)
      } else if (event.key === 'Enter') { event.preventDefault(); onReset() }
    }}
    onPointerDown={event => {
      if (event.button !== 0 || !event.isPrimary) return
      event.preventDefault()
      cleanup.current?.()
      event.currentTarget.focus({ preventScroll: true })
      const handle = event.currentTarget
      const pointer = event.pointerId
      drag.current = { pointer: event.pointerId, startX: event.clientX, startWidth: value }
      // Window listeners keep dragging reliable even if pointer capture is lost
      // while the grid moves or the pointer leaves the handle.
      function move(event: PointerEvent) {
        const current = drag.current
        if (current?.pointer === event.pointerId) change.current(current.startWidth + direction * (event.clientX - current.startX))
      }
      function finish(event: PointerEvent | FocusEvent) {
        if ('pointerId' in event && event.pointerId !== pointer) return
        drag.current = null
        cleanup.current?.()
        cleanup.current = null
        setDragging(false)
      }
      window.addEventListener('pointermove', move)
      window.addEventListener('pointerup', finish)
      window.addEventListener('pointercancel', finish)
      window.addEventListener('blur', finish)
      cleanup.current = () => {
        window.removeEventListener('pointermove', move)
        window.removeEventListener('pointerup', finish)
        window.removeEventListener('pointercancel', finish)
        window.removeEventListener('blur', finish)
        if (handle.hasPointerCapture(pointer)) handle.releasePointerCapture(pointer)
      }
      handle.setPointerCapture(pointer)
      setDragging(true)
    }}
  />
}
