import { useCallback, useEffect, useState } from 'react'
import * as api from './api/client'
import { useToast } from './hooks/useToast'
import { NotebooksHome } from './features/notebooks/NotebooksHome'
import { NotebookWorkspace } from './features/notebooks/NotebookWorkspace'
import { NotebookDialog } from './features/notebooks/NotebookDialog'
import { SettingsDialog } from './features/notebooks/SettingsDialog'
import type { Notebook, NotebookInfo } from './types/notebooks'
import { APP_NAME } from './brand'

function App() {
  const notify = useToast()
  const [notebooks, setNotebooks] = useState<NotebookInfo[]>([])
  const [active, setActive] = useState<Notebook | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [opening, setOpening] = useState<string | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [workspaceVersion, setWorkspaceVersion] = useState(0)
  const openSettings = useCallback(() => setSettingsOpen(true), [])
  const closeSettings = useCallback(() => setSettingsOpen(false), [])
  const [dialog, setDialog] = useState<{ mode: 'create' | 'rename' | 'delete'; notebook?: NotebookInfo } | null>(null)
  const closeDialog = useCallback(() => setDialog(null), [])
  const updateList = useCallback((notebook: NotebookInfo) => {
    setNotebooks(old => [notebook, ...old.filter(item => item.id !== notebook.id)])
  }, [])
  const refresh = useCallback(async (signal?: AbortSignal) => {
    setLoading(true); setError('')
    try { const result = await api.getNotebooks(signal); if (!signal?.aborted) setNotebooks(result.notebooks) }
    catch (reason) { if (!signal?.aborted) setError(reason instanceof Error ? reason.message : 'Không thể tải sổ ghi chú.') }
    finally { if (!signal?.aborted) setLoading(false) }
  }, [])
  useEffect(() => {
    const controller = new AbortController()
    void refresh(controller.signal)
    return () => controller.abort()
  }, [refresh])
  useEffect(() => {
    document.title = active ? `${active.title} · ${APP_NAME}` : `Sổ ghi chú của tôi · ${APP_NAME}`
  }, [active?.title])

  async function open(id: string) {
    if (opening) return
    setOpening(id); setError('')
    try { setActive(await api.getNotebook(id)); window.scrollTo({ top: 0 }) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Không thể mở sổ ghi chú.') }
    finally { setOpening(null) }
  }

  return (
    <>
      {active ? <NotebookWorkspace key={`${active.id}:${workspaceVersion}`} notebook={active} onSettings={openSettings} onSaved={updateList} onHome={() => setActive(null)} onRename={() => setDialog({ mode: 'rename', notebook: active })} onCreate={() => setDialog({ mode: 'create' })} /> :
        <NotebooksHome notebooks={notebooks} loading={loading} error={error} opening={opening} onOpen={id => { void open(id) }} onCreate={() => setDialog({ mode: 'create' })}
          onEdit={notebook => setDialog({ mode: 'rename', notebook })} onDelete={notebook => setDialog({ mode: 'delete', notebook })} onRefresh={() => { void refresh() }} onSettings={openSettings} />}
      {settingsOpen && <SettingsDialog notebooks={notebooks} notebookId={active?.id} onClose={closeSettings} onReset={async (id, confirmation) => {
        const result = await api.resetNotebook(id, confirmation)
        updateList(result)
        if (active?.id === id) { setActive(result); setWorkspaceVersion(version => version + 1) }
        closeSettings()
        notify('Đã đặt lại dữ liệu sổ tay.', 'success')
      }} />}
      {dialog && <NotebookDialog mode={dialog.mode} notebook={dialog.notebook} onClose={closeDialog} onSubmit={async (title, icon) => {
        if (dialog.mode === 'create') {
          const result = await api.createNotebook(title, icon)
          updateList(result); setActive(result)
          notify('Đã tạo sổ ghi chú mới.', 'success')
        } else if (dialog.mode === 'rename' && dialog.notebook) {
          if (active?.id === dialog.notebook.id) {
            // The workspace autosaves metadata together with its latest state.
            setActive(previous => previous ? { ...previous, title, icon } : previous)
          } else {
            const current = await api.getNotebook(dialog.notebook.id)
            updateList(await api.saveNotebook(current.id, { title, icon, state: current.state }))
          }
          notify('Đã cập nhật sổ ghi chú.', 'success')
        } else if (dialog.mode === 'delete' && dialog.notebook) {
          await api.deleteNotebook(dialog.notebook.id)
          setNotebooks(old => old.filter(item => item.id !== dialog.notebook?.id))
          notify('Đã xóa sổ ghi chú.', 'success')
        }
        setDialog(null)
      }} />}
    </>
  )
}

export default App
