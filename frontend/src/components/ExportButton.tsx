import { useState } from 'react'
import { downloadExport } from '../api/client'
import type { ExportFeature, ExportResults } from '../types/api'
import { ErrorMessage } from './Status'
import { useToast } from '../hooks/useToast'

export function ExportButton<F extends ExportFeature>({ feature, result }: { feature: F; result: ExportResults[F] }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const notify = useToast()
  async function download() {
    setBusy(true)
    setError('')
    try { await downloadExport(feature, result); notify('Đã tải Markdown.', 'success') }
    catch (error) {
      setError(error instanceof Error ? error.message : 'Không thể tải tệp xuống.')
      notify('Không thể tải tệp.', 'error')
    }
    finally { setBusy(false) }
  }
  return <div className="export-control">
    <button className="button subtle" type="button" disabled={busy} onClick={download}>
      {busy ? 'Đang tải tệp...' : 'Tải Markdown'}
    </button>
    <ErrorMessage message={error} />
  </div>
}
