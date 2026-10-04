import { useEffect, useRef, useState } from 'react'
import type { ChatResponse } from '../../types/api'
import { CitationList } from '../../components/CitationList'
import { ExportButton } from '../../components/ExportButton'
import { useToast } from '../../hooks/useToast'

export function ChatAnswer({ result }: { result: ChatResponse }) {
  const [copied, setCopied] = useState(false)
  const [fresh, setFresh] = useState(true)
  const copyTimer = useRef<number | undefined>(undefined)
  const notify = useToast()
  useEffect(() => {
    const timer = window.setTimeout(() => setFresh(false), 800)
    return () => { window.clearTimeout(timer); window.clearTimeout(copyTimer.current) }
  }, [])
  async function copy() {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(result.answer)
      setCopied(true)
      window.clearTimeout(copyTimer.current)
      copyTimer.current = window.setTimeout(() => setCopied(false), 1800)
      notify('Đã sao chép câu trả lời.', 'success')
    } catch { notify('Không thể sao chép.', 'error') }
  }
  return <div className={`assistant-message${fresh ? ' answer-complete' : ''}`}>
    <h3>Research Notebook</h3><p className="prose">{result.answer}</p>
    <CitationList citations={result.citations} label="Nguồn tham chiếu" collapsed={false} />
    <div className="answer-actions">
      <button className="button subtle copy-answer" type="button" aria-label="Sao chép câu trả lời" onClick={copy}>
        {copied ? 'Đã sao chép ✓' : 'Sao chép'}
      </button>
      <ExportButton feature="chat" result={result} />
    </div>
  </div>
}
