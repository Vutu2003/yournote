import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import type { ReactNode } from 'react'

export function ResultViewerModal({ open, title, artifactTitle, onClose, children, footer, pageKey = 0 }: {
  open: boolean; title: string; artifactTitle: string; onClose: () => void; children: ReactNode; footer: ReactNode; pageKey?: number
}) {
  const titleId = useId()
  const panel = useRef<HTMLDivElement>(null)
  const closeButton = useRef<HTMLButtonElement>(null)
  const content = useRef<HTMLDivElement>(null)
  useEffect(() => { content.current?.scrollTo({ top: 0 }) }, [pageKey])
  useEffect(() => {
    if (!open) return
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    const appRoot = document.getElementById('root')
    const previousInert = appRoot?.inert ?? false
    document.body.style.overflow = 'hidden'
    if (appRoot) appRoot.inert = true
    closeButton.current?.focus({ preventScroll: true })
    function keyboard(event: KeyboardEvent) {
      if (event.key === 'Escape') { event.preventDefault(); onClose(); return }
      if (event.key !== 'Tab') return
      const controls = [...(panel.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), summary, a[href], [tabindex="0"]',
      ) || [])].filter(element => element.getClientRects().length && element.tabIndex >= 0)
      const first = controls[0]
      const last = controls.at(-1)
      const active = document.activeElement
      if (!panel.current?.contains(active) || (event.shiftKey && active === first) || (!event.shiftKey && active === last)) {
        event.preventDefault()
        ;(event.shiftKey ? last : first)?.focus()
      }
    }
    document.addEventListener('keydown', keyboard)
    return () => {
      document.removeEventListener('keydown', keyboard)
      document.body.style.overflow = previousOverflow
      if (appRoot) appRoot.inert = previousInert
      previousFocus?.focus({ preventScroll: true })
    }
  }, [open, onClose])

  // Keep content mounted while hidden so pagination and local learning state survive.
  return createPortal(<div className="viewer-overlay" hidden={!open} role="presentation"
    onClick={event => { if (event.target === event.currentTarget) onClose() }}>
    <div className="result-viewer" ref={panel} role="dialog" aria-modal="true" aria-labelledby={titleId}>
      <header className="viewer-header"><div className="viewer-heading"><h2 id={titleId}>{title}</h2>
        <p className="viewer-artifact-title" title={artifactTitle}>{artifactTitle}</p></div>
        <button ref={closeButton} type="button" className="viewer-close" aria-label="Đóng trình xem" onClick={onClose}>×</button>
      </header>
      <div className="viewer-content" ref={content}>{children}</div>
      <footer className="viewer-footer">{footer}</footer>
    </div>
  </div>, document.body)
}
