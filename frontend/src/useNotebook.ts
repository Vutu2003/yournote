import { useCallback, useEffect, useMemo, useState } from 'react'
import * as api from './api/client'
import { useToast } from './hooks/useToast'
import type { ChatContext, ChatResponse, DocumentInfo, StudioTool, GenerationTool } from './types/api'
import type { ReadingChatInput } from './types/reading'
import { createArtifact } from './types/artifacts'
import type { FlashcardArtifact, QuizArtifact, SummaryArtifact, MindMapArtifact } from './types/artifacts'
import type { UserNote, WorkspaceSnapshot } from './types/notebooks'

const selectionMessage = 'Vui lòng chọn ít nhất một tài liệu.'
const errorMessage = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback
type Operation = 'documents' | 'upload' | 'chat' | GenerationTool
type Messages = Partial<Record<Operation, string>>

export function useNotebook(initial: WorkspaceSnapshot) {
  const notify = useToast()
  const [library, setLibrary] = useState<DocumentInfo[]>([])
  const [members, setMembers] = useState<string[]>(initial.document_filenames)
  const [sourceNames, setSourceNames] = useState<Record<string, string>>(initial.source_names || {})
  const sourceName = useCallback((filename: string) => sourceNames[filename] || filename, [sourceNames])
  function renameSource(filename: string, value: string) {
    const title = value.trim()
    if (!members.includes(filename) || !title || title.length > 160 || /[\u0000-\u001f\u007f]/.test(title)) return false
    setSourceNames(old => {
      const next = { ...old }
      if (title === filename) delete next[filename]
      else next[filename] = title
      return next
    })
    return true
  }
  const documents = useMemo(() => library.filter(doc => members.includes(doc.filename)), [library, members])
  const [selected, setSelected] = useState<string[]>(initial.selected)
  const [readDocuments, setReadDocuments] = useState<string[]>(initial.read_documents || [])
  const [notes, setNotes] = useState<UserNote[]>(initial.notes || [])
  const [page, setPage] = useState(initial.page)
  const [activeTool, setActiveTool] = useState<StudioTool>(initial.active_tool)
  const [chat, setChat] = useState<ChatResponse[]>(initial.chat)
  const [pendingQuestion, setPendingQuestion] = useState('')
  const [pendingContext, setPendingContext] = useState<ChatContext | null>(null)
  const [summaryArtifacts, setSummaryArtifacts] = useState<SummaryArtifact[]>(initial.summary_artifacts)
  const [quizArtifacts, setQuizArtifacts] = useState<QuizArtifact[]>(initial.quiz_artifacts)
  const [flashcardArtifacts, setFlashcardArtifacts] = useState<FlashcardArtifact[]>(initial.flashcard_artifacts)
  const [mindmapArtifacts, setMindmapArtifacts] = useState<MindMapArtifact[]>(initial.mindmap_artifacts || [])
  const [questionDraft, setQuestionDraft] = useState<{ text: string; token: string } | null>(null)
  const [loading, setLoading] = useState<Partial<Record<Operation, boolean>>>({ documents: true })
  const [errors, setErrors] = useState<Messages>({})
  const [uploadStatus, setUploadStatus] = useState('')
  const selectedDocument = useMemo(() => selected.length === 1
    ? documents.find(doc => doc.filename === selected[0]) : undefined, [documents, selected])

  const applyDocuments = useCallback((docs: DocumentInfo[]) => {
    setLibrary(docs)
    setSelected(previous => previous.filter(name => docs.some(doc => doc.filename === name)))
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
      else if (operation !== 'documents' && operation !== 'chat') notify('Không thể tạo nội dung.', 'error')
    }
    finally { setLoading(old => ({ ...old, [operation]: false })) }
  }

  function choose(names: string[]) { setSelected(names); setPage('') }
  function markRead(name: string) {
    if (members.includes(name)) setReadDocuments(old => old.includes(name) ? old : [...old, name])
  }
  function toggleRead(name: string) {
    if (members.includes(name)) setReadDocuments(old => old.includes(name) ? old.filter(value => value !== name) : [...old, name])
  }
  function createNote() {
    if (notes.length >= 100) { notify('Mỗi sổ hỗ trợ tối đa 100 ghi chú.', 'error'); return null }
    const timestamp = Date.now()
    const note = { id: crypto.randomUUID(), title: '', content: '', createdAt: timestamp, updatedAt: timestamp }
    setNotes(old => [note, ...old]); setActiveTool('notes')
    return note.id
  }
  function updateNote(id: string, patch: Pick<Partial<UserNote>, 'title' | 'content'>) {
    setNotes(old => old.map(note => note.id === id && ((patch.title !== undefined && patch.title !== note.title) || (patch.content !== undefined && patch.content !== note.content))
      ? { ...note, ...patch, updatedAt: Math.max(Date.now(), note.createdAt) } : note))
  }
  function deleteNote(id: string) { setNotes(old => old.filter(note => note.id !== id)) }
  function selectSource(name: string) {
    if (!members.includes(name)) return
    setSelected(old => old.includes(name) ? old : [...old, name])
    if (!selected.includes(name)) setPage('')
  }
  function toggle(name: string) {
    setSelected(old => old.includes(name) ? old.filter(value => value !== name) : [...old, name])
    setPage('')
  }
  function attach(names: string[]) {
    const valid = names.filter(name => library.some(doc => doc.filename === name))
    setMembers(old => [...new Set([...old, ...valid])].slice(0, 64))
    setSelected(old => [...new Set([...old, ...valid])].slice(0, 64))
    setPage('')
  }
  function detach(name: string) {
    setMembers(old => old.filter(value => value !== name))
    setSelected(old => old.filter(value => value !== name))
    setReadDocuments(old => old.filter(value => value !== name))
    setPage('')
    setSourceNames(old => { const next = { ...old }; delete next[name]; return next })
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
    if (library.some(doc => doc.filename === file.name)) {
      setErrors(old => ({ ...old, upload: 'Tên PDF này đã có trong thư viện. Chọn “Thêm từ thư viện” hoặc đổi tên tệp mới trước khi tải lên.' }))
      return false
    }
    if (members.length >= 64) {
      setErrors(old => ({ ...old, upload: 'Mỗi sổ hỗ trợ tối đa 64 nguồn tài liệu.' }))
      return false
    }
    const result = await run('upload', () => api.uploadDocument(file))
    if (!result) return false
    if (!result.chunks_indexed) {
      setErrors(old => ({ ...old, upload: 'Không đọc được nội dung PDF. Hãy dùng tệp có văn bản hoặc thực hiện OCR trước.' }))
      return false
    }
    setMembers(old => [...new Set([...old, result.filename])])
    setSelected(old => [...new Set([...old, result.filename])])
    setPage('')
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
  async function send(question: string, reading?: ReadingChatInput): Promise<boolean> {
    if (loading.chat) return false
    if (!question.trim()) {
      setErrors(old => ({ ...old, chat: 'Vui lòng nhập câu hỏi.' }))
      return false
    }
    const sources = reading ? null : selection('chat')
    if (!reading && !sources) return false
    setPendingQuestion(question.trim())
    setPendingContext(reading ? { mode: 'reading', scope: reading.scope, filenames: reading.scope === 'document' ? documents.filter(doc => doc.document_id === reading.document_id).map(doc => doc.filename) : [...members], selection: reading.selection || null } : null)
    const result = await run('chat', () => reading ? api.askReadingQuestion(reading, question.trim()) : api.askQuestion({ ...sources!, question: question.trim(), k: 6 }))
    setPendingQuestion('')
    setPendingContext(null)
    if (result) setChat(old => [...old, result])
    return !!result
  }
  async function generate(tool: GenerationTool, topic: string, count: number) {
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
    } else if (tool === 'mindmap') {
      const result = await run(tool, () => api.generateMindMap(body))
      if (result) {
        const artifact = createArtifact(result, body)
        setMindmapArtifacts(old => [{ ...artifact, title: result.root.label }, ...old])
        notify('Sơ đồ tư duy đã sẵn sàng.', 'success')
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
  function prepareMindMapQuestion(label: string, filenames: string[]) {
    if (loading.chat) return false
    const valid = filenames.filter(name => documents.some(doc => doc.filename === name))
    if (!valid.length) { notify('Hãy thêm lại nguồn của sơ đồ vào sổ để hỏi tiếp.', 'error'); return false }
    choose(valid)
    setQuestionDraft({ text: `Giải thích chi tiết về “${label}” dựa trên các nguồn đã chọn và dẫn chứng từ tài liệu.`, token: crypto.randomUUID() })
    return true
  }
  const snapshot = useMemo<WorkspaceSnapshot>(() => ({
    document_filenames: members, source_names: sourceNames, selected, read_documents: readDocuments,
    notes: notes.map(note => ({ ...note, title: note.title.trim() || 'Ghi chú chưa đặt tên' })), page, active_tool: activeTool, chat,
    summary_artifacts: summaryArtifacts, quiz_artifacts: quizArtifacts, flashcard_artifacts: flashcardArtifacts, mindmap_artifacts: mindmapArtifacts,
  }), [members, sourceNames, selected, readDocuments, notes, page, activeTool, chat, summaryArtifacts, quizArtifacts, flashcardArtifacts, mindmapArtifacts])
  return {
    documents, selected, readDocuments, markRead, toggleRead, notes, createNote, updateNote, deleteNote, page, setPage, selectedDocument, activeTool, setActiveTool,
    chat, pendingQuestion, pendingContext, summaryArtifacts, quizArtifacts, flashcardArtifacts, mindmapArtifacts, questionDraft, prepareMindMapQuestion, loading, errors, uploadStatus,
    choose, selectSource, toggle, refresh, upload, send, generate, library, attach, detach, snapshot, sourceName, renameSource,
  }
}
export type NotebookState = ReturnType<typeof useNotebook>
