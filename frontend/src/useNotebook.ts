import { useCallback, useEffect, useMemo, useState } from 'react'
import * as api from './api/client'
import { useToast } from './hooks/useToast'
import type { ChatResponse, DocumentInfo, StudioTool } from './types/api'
import { createArtifact } from './types/artifacts'
import type { FlashcardArtifact, QuizArtifact, SummaryArtifact } from './types/artifacts'

const selectionMessage = 'Vui lòng chọn ít nhất một tài liệu.'
const errorMessage = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback
type Operation = 'documents' | 'upload' | 'chat' | StudioTool
type Messages = Partial<Record<Operation, string>>

export function useNotebook() {
  const notify = useToast()
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [page, setPage] = useState('')
  const [activeTool, setActiveTool] = useState<StudioTool>('summary')
  const [chat, setChat] = useState<ChatResponse[]>([])
  const [pendingQuestion, setPendingQuestion] = useState('')
  const [summaryArtifacts, setSummaryArtifacts] = useState<SummaryArtifact[]>([])
  const [quizArtifacts, setQuizArtifacts] = useState<QuizArtifact[]>([])
  const [flashcardArtifacts, setFlashcardArtifacts] = useState<FlashcardArtifact[]>([])
  const [loading, setLoading] = useState<Partial<Record<Operation, boolean>>>({ documents: true })
  const [errors, setErrors] = useState<Messages>({})
  const [uploadStatus, setUploadStatus] = useState('')
  const selectedDocument = useMemo(() => selected.length === 1
    ? documents.find(doc => doc.filename === selected[0]) : undefined, [documents, selected])

  const applyDocuments = useCallback((docs: DocumentInfo[]) => {
    setDocuments(docs)
    setSelected(previous => previous.filter(name => docs.some(doc => doc.filename === name)))
    setPage('')
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    api.getDocuments(controller.signal).then(result => applyDocuments(result.documents)).catch(error => {
      if (!controller.signal.aborted) setErrors(old => ({ ...old, documents: errorMessage(error, 'Không thể tải danh sách tài liệu.') }))
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(old => ({ ...old, documents: false }))
    })
    return () => controller.abort()
  }, [applyDocuments])

  async function run<T>(operation: Operation, work: () => Promise<T>): Promise<T | undefined> {
    setLoading(old => ({ ...old, [operation]: true }))
    setErrors(old => ({ ...old, [operation]: '' }))
    try { return await work() }
    catch (error) {
      setErrors(old => ({ ...old, [operation]: errorMessage(error, 'Không thể hoàn tất thao tác.') }))
      if (operation === 'upload') notify('Không thể thêm nguồn tài liệu.', 'error')
      else if (operation === 'summary' || operation === 'quiz' || operation === 'flashcards') notify('Không thể tạo nội dung.', 'error')
    }
    finally { setLoading(old => ({ ...old, [operation]: false })) }
  }

  function choose(names: string[]) { setSelected(names); setPage('') }
  function toggle(name: string) {
    setSelected(old => old.includes(name) ? old.filter(value => value !== name) : [...old, name])
    setPage('')
  }
  async function refresh() {
    const result = await run('documents', () => api.getDocuments())
    if (result) applyDocuments(result.documents)
  }
  async function upload(file: File): Promise<boolean> {
    setUploadStatus('')
    if (!/\.pdf$/i.test(file.name) || file.size === 0 || file.size > 25 * 1024 * 1024) {
      setErrors(old => ({ ...old, upload: 'Vui lòng chọn một tệp PDF không rỗng, tối đa 25 MB.' }))
      notify('Không thể thêm nguồn tài liệu. Vui lòng kiểm tra tệp PDF.', 'error')
      return false
    }
    const result = await run('upload', () => api.uploadDocument(file))
    if (!result) return false
    setUploadStatus(`Đã thêm ${result.filename} (${result.chunks_indexed} đoạn).`)
    notify('Đã thêm nguồn tài liệu.', 'success')
    await refresh()
    return true
  }
  function selection(operation: Operation) {
    if (!selected.length) {
      setErrors(old => ({ ...old, [operation]: selectionMessage }))
      return null
    }
    return { filenames: [...selected], pages: selectedDocument && page ? [Number(page)] : [] }
  }
  async function send(question: string): Promise<boolean> {
    if (loading.chat) return false
    if (!question.trim()) {
      setErrors(old => ({ ...old, chat: 'Vui lòng nhập câu hỏi.' }))
      return false
    }
    const sources = selection('chat')
    if (!sources) return false
    setPendingQuestion(question.trim())
    const result = await run('chat', () => api.askQuestion({ ...sources, question: question.trim(), k: 6 }))
    setPendingQuestion('')
    if (result) setChat(old => [...old, result])
    return !!result
  }
  async function generate(tool: StudioTool, topic: string, count: number) {
    if (loading[tool]) return
    const sources = selection(tool)
    if (!sources) return
    const body = { ...sources, topic: topic.trim() || null }
    if (tool === 'summary') {
      const result = await run(tool, () => api.generateSummary(body))
      if (result) {
        const artifact = createArtifact(result, body)
        setSummaryArtifacts(old => [artifact, ...old])
        notify('Tóm tắt đã sẵn sàng.', 'success')
      }
    } else if (tool === 'quiz') {
      const result = await run(tool, () => api.generateQuiz({ ...body, count }))
      if (result) {
        const artifact = createArtifact(result, body)
        setQuizArtifacts(old => [artifact, ...old])
        notify('Quiz đã sẵn sàng.', 'success')
      }
    } else {
      const result = await run(tool, () => api.generateFlashcards({ ...body, count }))
      if (result) {
        const artifact = createArtifact(result, body)
        setFlashcardArtifacts(old => [artifact, ...old])
        notify('Flashcards đã sẵn sàng.', 'success')
      }
    }
  }
  return {
    documents, selected, page, setPage, selectedDocument, activeTool, setActiveTool,
    chat, pendingQuestion, summaryArtifacts, quizArtifacts, flashcardArtifacts, loading, errors, uploadStatus,
    choose, toggle, refresh, upload, send, generate,
  }
}
export type NotebookState = ReturnType<typeof useNotebook>
