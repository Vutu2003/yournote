import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'

type Side = 'sources' | 'studio'
type Widths = Record<Side, number>
const STORAGE_KEY = 'research-notebook-panel-widths'
const MIN: Widths = { sources: 220, studio: 240 }
const MAX = 720
const CHAT_MIN = 320
const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(value, max))

function readWidths(): Partial<Widths> {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
    const result: Partial<Widths> = {}
    for (const side of ['sources', 'studio'] as const) {
      if (typeof stored?.[side] === 'number' && Number.isFinite(stored[side])) result[side] = clamp(stored[side], MIN[side], MAX)
    }
    return result
  } catch { return {} }
}

export function usePanelWidths(sourcesCollapsed: boolean, studioCollapsed: boolean) {
  const workspaceRef = useRef<HTMLElement>(null)
  const [preferred, setPreferred] = useState(readWidths)
  const [layout, setLayout] = useState({ available: 0, gutter: 18, defaults: { sources: 280, studio: 326 } })

  useLayoutEffect(() => {
    const element = workspaceRef.current
    if (!element) return
    function measure() {
      if (!element) return
      const style = getComputedStyle(element)
      setLayout({
        available: element.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight),
        gutter: parseFloat(style.getPropertyValue('--panel-gutter')) || 18,
        defaults: {
          sources: parseFloat(style.getPropertyValue('--default-sources-width')) || 280,
          studio: parseFloat(style.getPropertyValue('--default-studio-width')) || 326,
        },
      })
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(preferred)) } catch { /* Resizing still works without stored preferences. */ }
  }, [preferred])

  const open: Side[] = (['sources', 'studio'] as const).filter(side => side === 'sources' ? !sourcesCollapsed : !studioCollapsed)
  const budget = Math.max(0, layout.available - open.length * layout.gutter - CHAT_MIN)
  const widths: Widths = {
    sources: clamp(preferred.sources ?? layout.defaults.sources, MIN.sources, MAX),
    studio: clamp(preferred.studio ?? layout.defaults.studio, MIN.studio, MAX),
  }
  const total = open.reduce((sum, side) => sum + widths[side], 0)
  const minimum = open.reduce((sum, side) => sum + MIN[side], 0)
  if (layout.available && total > budget && total > minimum) {
    // Fit the viewport without discarding the user's preferred desktop widths.
    const ratio = clamp((budget - minimum) / (total - minimum), 0, 1)
    for (const side of open) widths[side] = MIN[side] + (widths[side] - MIN[side]) * ratio
  }

  function maximum(side: Side) {
    const other = side === 'sources' ? 'studio' : 'sources'
    return Math.max(MIN[side], Math.min(MAX, budget - (open.includes(other) ? widths[other] : 0)))
  }

  function resize(side: Side, value: number) {
    // Start from the current fitted widths so the opposite panel stays still.
    const next = { ...widths, [side]: clamp(value, MIN[side], maximum(side)) }
    setPreferred(next)
  }

  function reset(side: Side) {
    setPreferred(old => { const next = { ...old }; delete next[side]; return next })
  }

  return {
    workspaceRef,
    style: { '--sources-width': `${widths.sources}px`, '--studio-width': `${widths.studio}px` } as CSSProperties,
    sources: { value: widths.sources, min: MIN.sources, max: maximum('sources'), onChange: (value: number) => resize('sources', value), onReset: () => reset('sources') },
    studio: { value: widths.studio, min: MIN.studio, max: maximum('studio'), onChange: (value: number) => resize('studio', value), onReset: () => reset('studio') },
  }
}
