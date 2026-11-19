import type { ComparisonResponse, ReportResponse, GraphResponse, ResearchTool, ReportMode, TaskProgress } from './types/research'
import type { StudioArtifact } from './types/artifacts'
import type { LegacyGenerationTool } from './types/api'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as api from './api/client'
import { useToast } from './hooks/useToast'
import type { ChatContext, ChatResponse, DocumentInfo, StudioTool, GenerationTool, LearningResponse, SummaryResponse, QuizResponse, FlashcardsResponse, MindMapResponse } from './types/api'
import { runTask, cancelTask } from './features/ai/tasks'
import type { TaskInput } from './features/ai/tasks'
import { useModelChoice } from './features/ai/useModelChoice'
import type { ReadingChatInput } from './types/reading'
import { createArtifact } from './types/artifacts'
import type { FlashcardArtifact, QuizArtifact, SummaryArtifact, MindMapArtifact } from './types/artifacts'
import type { UserNote, WorkspaceSnapshot } from './types/notebooks'

const selectionMessage = 'Vui lòng chọn ít nhất một tài liệu.'
const errorMessage = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback
type Operation = 'documents' | 'upload' | 'chat' | GenerationTool
type Messages = Partial<Record<Operation, string>>

export function useNotebook(initial: WorkspaceSnapshot, notebookId: string, prepare?: () => Promise<void>) {
  const modelControls = useModelChoice()
  const operations = useRef<Partial<Record<'chat' | GenerationTool, { id: string; controller: AbortController }>>>({})
  const alive = useRef(true)
  const [operationStatus, setOperationStatus] = useState<Partial<Record<'chat' | GenerationTool, 'running' | 'completed' | 'cancelled' | 'failed'>>>({})
  const [taskProgress, setTaskProgress] = useState<Partial<Record<GenerationTool, TaskProgress>>>({})
  const [pendingAnswer, setPendingAnswer] = useState('')
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
      for (const operation of Object.values(operations.current)) if (operation) {
        operation.controller.abort(); void cancelTask(operation.id)
      }
      operations.current = {}
    }
  }, [])
  const notify = useToast()
  const [library, setLibrary] = useState<DocumentInfo[]>([])
  const [members, setMembers] = useState<string[]>(initial.document_filenames)
  const [sourceNames, setSourceNames] = useState<Record<string, string>>(initial.source_names || {})
  const sourceName = useCallback((filename: string) => sourceNames[filename] || library.find(doc => doc.filename === filename)?.original_filename || filename, [sourceNames, library])
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
  const [comparisonArtifacts, setComparisonArtifacts] = useState<StudioArtifact<ComparisonResponse>[]>(initial.comparison_artifacts || [])
  const [reportArtifacts, setReportArtifacts] = useState<StudioArtifact<ReportResponse>[]>(initial.report_artifacts || [])
  const [graphArtifacts, setGraphArtifacts] = useState<StudioArtifact<GraphResponse>[]>(initial.graph_artifacts || [])
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
  async function upload(file: File, replacing?: DocumentInfo): Promise<boolean> {
    setUploadStatus('')
    if (!/\.(pdf|docx|md|txt)$/i.test(file.name) || file.size === 0 || file.size > 25 * 1024 * 1024) {
      setErrors(old => ({ ...old, upload: 'Chọn tệp PDF, DOCX, Markdown hoặc TXT không rỗng, tối đa 25 MB.' }))
      notify('Không thể thêm nguồn tài liệu. Vui lòng kiểm tra định dạng và dung lượng tệp.', 'error')
      return false
    }
    if (!replacing && members.length >= 64) {
      setErrors(old => ({ ...old, upload: 'Mỗi sổ hỗ trợ tối đa 64 nguồn tài liệu.' }))
      return false
    }
    const result = await run('upload', () => api.uploadDocument(file,replacing))
    if (!result) return false
    if (!result.chunks_indexed) {
      setErrors(old => ({ ...old, upload: 'Không đọc được nội dung PDF. Hãy dùng tệp có văn bản hoặc thực hiện OCR trước.' }))
      return false
    }
    setMembers(old => [...new Set([...old, result.filename])])
    setSelected(old => [...new Set([...old, result.filename])])
    setPage('')
    setUploadStatus(`${result.deduplicated ? 'Nguồn đã có' : replacing ? 'Đã cập nhật' : 'Đã thêm'} ${result.original_filename || file.name} (${result.chunks_indexed} đoạn).${result.warnings?.length ? ' ' + result.warnings.join(' ') : ''}`)
    notify('Đã thêm nguồn tài liệu.', 'success')
    await refresh()
    return true
  }
  function selection(operation: Operation) {
    if (!selected.length) {
      setErrors(old => ({ ...old, [operation]: selectionMessage }))
      return null
    }
    return { filenames: [...selected], pages: selectedDocument && (!selectedDocument.kind || selectedDocument.kind === 'pdf') && page ? [Number(page)] : [],
      document_versions: Object.fromEntries(documents.filter(doc => selected.includes(doc.filename) && doc.document_version).map(doc => [doc.filename, doc.document_version!])) }
  }
  function cancel(operation: 'chat' | GenerationTool) {
    const active = operations.current[operation]
    if (!active) return
    delete operations.current[operation]
    active.controller.abort(); void cancelTask(active.id)
    setLoading(old => ({ ...old, [operation]: false }))
    setOperationStatus(old => ({ ...old, [operation]: 'cancelled' }))
    if (operation === 'chat') { setPendingQuestion(''); setPendingContext(null); setPendingAnswer('') }
  }
  function cancelAll() {
    for (const operation of Object.keys(operations.current)) cancel(operation as 'chat' | GenerationTool)
  }
  async function perform<T extends ChatResponse | LearningResponse>(
    operation: 'chat' | GenerationTool, body: Omit<TaskInput, 'id' | 'notebook_id' | 'model'>,
    commit: (result: T) => void,
  ): Promise<boolean> {
    if (operations.current[operation] || !modelControls.ready || !modelControls.choice) {
      if (!modelControls.ready) setErrors(old => ({ ...old, [operation]: 'Hãy chọn kết nối và model khả dụng trước khi tạo nội dung.' }))
      return false
    }
    const active = { id: crypto.randomUUID(), controller: new AbortController() }
    operations.current[operation] = active
    // Freeze choice and scope before the first await. No result reads the live controls.
    const request: TaskInput = { ...body, id: active.id, notebook_id: notebookId, model: { ...modelControls.choice } }
    const current = () => alive.current && operations.current[operation] === active && !active.controller.signal.aborted
    setLoading(old => ({ ...old, [operation]: true }))
    setErrors(old => ({ ...old, [operation]: '' }))
    setOperationStatus(old => ({ ...old, [operation]: 'running' }))
    if (operation !== 'chat') setTaskProgress(old => ({ ...old, [operation]: { stage: 'preparing', completed_steps: 0 } }))
    try {
      await prepare?.()
      active.controller.signal.throwIfAborted()
      const result = await runTask<T>(request, active.controller.signal, text => {
        if (current() && operation === 'chat') setPendingAnswer(old => old + text)
      }, progress => {
        if (current() && operation !== 'chat') setTaskProgress(old => ({ ...old, [operation]: { ...old[operation], ...progress } }))
      })
      if (!current()) return false
      commit(result)
      setOperationStatus(old => ({ ...old, [operation]: 'completed' }))
      return true
    } catch (reason) {
      if (current()) {
        const aborted = reason instanceof DOMException && reason.name === 'AbortError'
        setOperationStatus(old => ({ ...old, [operation]: aborted ? 'cancelled' : 'failed' }))
        if (!aborted) {
          setErrors(old => ({ ...old, [operation]: errorMessage(reason, 'Không thể hoàn tất tác vụ AI.') }))
          if (operation !== 'chat') notify('Không thể tạo nội dung.', 'error')
        }
      }
      return false
    } finally {
      if (alive.current && operations.current[operation] === active) {
        delete operations.current[operation]
        setLoading(old => ({ ...old, [operation]: false }))
        if (operation === 'chat') { setPendingQuestion(''); setPendingContext(null); setPendingAnswer('') }
      }
    }
  }
  async function send(question: string, reading?: ReadingChatInput): Promise<boolean> {
    if (operations.current.chat) return false
    const text = question.trim()
    if (!text) { setErrors(old => ({ ...old, chat: 'Vui lòng nhập câu hỏi.' })); return false }
    if (!modelControls.ready) { setErrors(old => ({ ...old, chat: 'Hãy chọn kết nối và model khả dụng trước khi gửi.' })); return false }
    if (reading?.document_version && documents.find(doc => doc.document_id === reading.document_id)?.document_version !== reading.document_version) {
      setErrors(old => ({ ...old, chat: 'Đang xem phiên bản cũ. Mở bản hiện tại để hỏi đáp về nguồn đang chọn.' })); return false
    }
    const names = reading ? (reading.scope === 'document'
      ? documents.filter(doc => doc.document_id === reading.document_id).map(doc => doc.filename) : [...members]) : [...selected]
    const sources = reading ? { filenames: names, pages: [], document_versions: Object.fromEntries(documents.filter(doc => names.includes(doc.filename) && doc.document_version).map(doc => [doc.filename,doc.document_version!])) } : selection('chat')
    if (!sources || !sources.filenames.length) return false
    setPendingQuestion(text); setPendingAnswer('')
    setPendingContext(reading ? { mode: 'reading', scope: reading.scope, filenames: [...names], selection: reading.selection || null } : null)
    const task = reading ? {
      feature: 'reading', sources,
      input: { document_version: reading.document_version || null, document_id: reading.document_id, scope: reading.scope, selection: reading.selection || null, question: text, k: 6 },
    } : { feature: 'chat', input: { ...sources, question: text, k: 6 } }
    return perform<ChatResponse>('chat', task, result => setChat(old => [...old, result]))
  }
  async function generate(tool: LegacyGenerationTool, topic: string, count: number) {
    if (operations.current[tool]) return
    const sources = selection(tool)
    if (!sources) return
    const body = { ...sources, topic: topic.trim() || null }
    const input = tool === 'quiz' || tool === 'flashcards' ? { ...body, count } : body
    await perform<SummaryResponse | QuizResponse | FlashcardsResponse | MindMapResponse>(tool, { feature: tool, input }, result => {
      if (tool === 'summary') setSummaryArtifacts(old => [createArtifact(result as SummaryResponse, body), ...old])
      else if (tool === 'quiz') setQuizArtifacts(old => [createArtifact(result as QuizResponse, body), ...old])
      else if (tool === 'flashcards') setFlashcardArtifacts(old => [createArtifact(result as FlashcardsResponse, body), ...old])
      else {
        const value = result as MindMapResponse
        setMindmapArtifacts(old => [{ ...createArtifact(value, body), title: value.root.label }, ...old])
      }
      notify('Nội dung đã sẵn sàng.', 'success')
    })
  }
  async function generateResearch(tool: ResearchTool, goal: string, criteria: string[], mode: ReportMode) {
    const sources = selection(tool)
    if (!sources) return
    if (!goal.trim()) { setErrors(old => ({ ...old, [tool]: 'Hãy nhập mục tiêu học tập.' })); return }
    if (sources.filenames.length > 6 || tool === 'comparison' && sources.filenames.length < 2) {
      setErrors(old => ({ ...old, [tool]: tool === 'comparison' ? 'Chọn từ 2 đến 6 nguồn để so sánh.' : 'Chọn tối đa 6 nguồn.' })); return
    }
    const input = { ...sources, goal: goal.trim(), ...(tool === 'comparison' ? { criteria } : tool === 'report' ? { mode } : {}) }
    await perform<ComparisonResponse | ReportResponse | GraphResponse>(tool, { feature: tool, input }, result => {
      const context = { ...sources, topic: goal.trim() }
      if (tool === 'comparison') setComparisonArtifacts(old => [{ ...createArtifact(result as ComparisonResponse, context), title: goal.trim().slice(0, 160) }, ...old])
      else if (tool === 'report') setReportArtifacts(old => [{ ...createArtifact(result as ReportResponse, context), title: (result as ReportResponse).title }, ...old])
      else setGraphArtifacts(old => [{ ...createArtifact(result as GraphResponse, context), title: goal.trim().slice(0, 160) }, ...old])
      notify('Nội dung đã sẵn sàng.', 'success')
    })
  }
  function saveResearchNote(title: string, content: string) {
    if (notes.length >= 100) { notify('Mỗi sổ hỗ trợ tối đa 100 ghi chú.', 'error'); return false }
    if (content.length > 100000) { notify('Phần nội dung này quá dài để lưu thành một ghi chú.', 'error'); return false }
    const timestamp = Date.now()
    setNotes(old => [{ id: crypto.randomUUID(), title: title.trim().slice(0, 160) || 'Ghi chú từ Studio', content, createdAt: timestamp, updatedAt: timestamp }, ...old])
    setActiveTool('notes'); notify('Đã chuyển nội dung và trích dẫn thành ghi chú.', 'success'); return true
  }
  function deleteArtifact(tool: GenerationTool, id: string) {
    if (tool === 'summary') setSummaryArtifacts(old => old.filter(artifact => artifact.id !== id))
    else if (tool === 'quiz') setQuizArtifacts(old => old.filter(artifact => artifact.id !== id))
    else if (tool === 'flashcards') setFlashcardArtifacts(old => old.filter(artifact => artifact.id !== id))
    else if (tool === 'mindmap') setMindmapArtifacts(old => old.filter(artifact => artifact.id !== id))
    else if (tool === 'comparison') setComparisonArtifacts(old => old.filter(artifact => artifact.id !== id))
    else if (tool === 'report') setReportArtifacts(old => old.filter(artifact => artifact.id !== id))
    else if (tool === 'graph') setGraphArtifacts(old => old.filter(artifact => artifact.id !== id))
    notify('Đã xóa nội dung Studio.', 'success')
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
    schema_version: 3, document_filenames: members, source_names: sourceNames, selected, read_documents: readDocuments,
    notes: notes.map(note => ({ ...note, title: note.title.trim() || 'Ghi chú chưa đặt tên' })), page, active_tool: activeTool, chat,
    comparison_artifacts: comparisonArtifacts, report_artifacts: reportArtifacts, graph_artifacts: graphArtifacts,
    summary_artifacts: summaryArtifacts, quiz_artifacts: quizArtifacts, flashcard_artifacts: flashcardArtifacts, mindmap_artifacts: mindmapArtifacts,
  }), [members, sourceNames, selected, readDocuments, notes, page, activeTool, chat, summaryArtifacts, quizArtifacts, flashcardArtifacts, mindmapArtifacts, comparisonArtifacts, reportArtifacts, graphArtifacts])
  return {
    documents, selected, readDocuments, toggleRead, notes, createNote, updateNote, deleteNote, page, setPage, selectedDocument, activeTool, setActiveTool,
    clearChatError: () => setErrors(old => ({ ...old, chat: '' })),
    comparisonArtifacts, reportArtifacts, graphArtifacts, generateResearch, saveResearchNote, taskProgress,
    modelControls, cancel, cancelAll, operationStatus, pendingAnswer,
    chat, pendingQuestion, pendingContext, summaryArtifacts, quizArtifacts, flashcardArtifacts, mindmapArtifacts, questionDraft, prepareMindMapQuestion, loading, errors, uploadStatus,
    choose, selectSource, toggle, refresh, upload, send, generate, deleteArtifact, library, attach, detach, snapshot, sourceName, renameSource,
  }
}
export type NotebookState = ReturnType<typeof useNotebook>
