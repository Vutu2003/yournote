import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ReactNode } from 'react'
import { ToastContext } from '../hooks/useToast'
import type { ToastKind } from '../hooks/useToast'

interface ToastMessage { id: number; message: string; kind: ToastKind }

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  const sequence = useRef(0)
  const timers = useRef(new Map<number, number>())
  const dismiss = useCallback((id: number) => {
    window.clearTimeout(timers.current.get(id))
    timers.current.delete(id)
    setToasts(old => old.filter(toast => toast.id !== id))
  }, [])
  const notify = useCallback((message: string, kind: ToastKind = 'info') => {
    const id = ++sequence.current
    setToasts(old => [...old, { id, message, kind }].slice(-3))
    timers.current.set(id, window.setTimeout(() => dismiss(id), 3200))
  }, [dismiss])
  useEffect(() => {
    const pending = timers.current
    return () => { pending.forEach(timer => window.clearTimeout(timer)); pending.clear() }
  }, [])

  return <ToastContext.Provider value={notify}>
    {children}
    {createPortal(<div className="toast-viewport" aria-label="Thông báo">
      {toasts.map(toast => <div key={toast.id} className={`toast toast-${toast.kind}`} role={toast.kind === 'error' ? 'alert' : 'status'}>
        <span className="toast-symbol" aria-hidden="true">{toast.kind === 'success' ? '✓' : toast.kind === 'error' ? '!' : 'i'}</span>
        <span>{toast.message}</span>
        <button type="button" aria-label="Đóng thông báo" onClick={() => dismiss(toast.id)}>×</button>
      </div>)}
    </div>, document.body)}
  </ToastContext.Provider>
}
