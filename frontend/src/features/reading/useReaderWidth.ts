import { useEffect, useLayoutEffect, useState } from 'react'
import type { RefObject } from 'react'

export function useReaderWidth(ref: RefObject<HTMLElement | null>, enabled: boolean) {
  const [ratio, setRatio] = useState(() => {
    try { const value = Number(localStorage.getItem('research-notebook-reading-split')); return value >= .2 && value <= .8 ? value : .58 } catch { return .58 }
  })
  const [available, setAvailable] = useState(1000)
  useLayoutEffect(() => {
    if (!enabled || !ref.current) return
    const element = ref.current
    function measure() {
      const style = getComputedStyle(element)
      setAvailable(element.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight) - (parseFloat(style.getPropertyValue('--panel-gutter')) || 18))
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    return () => observer.disconnect()
  }, [ref, enabled])
  useEffect(() => { try { localStorage.setItem('research-notebook-reading-split', String(ratio)) } catch { /* Reading still supports resizing. */ } }, [ratio])
  const max = Math.max(320, available - 320)
  const value = Math.max(320, Math.min(max, available * ratio))
  return { value, min: 320, max, onChange: (width: number) => setRatio(Math.max(.2, Math.min(.8, width / Math.max(1, available)))), onReset: () => setRatio(.58) }
}
