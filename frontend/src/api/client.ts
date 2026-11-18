import type {
  APIErrorResponse, ChatRequest, ChatResponse, DocumentsResponse, ExportFeature,
  ExportResults, FlashcardsRequest, FlashcardsResponse, HealthResponse,
  QuizRequest, QuizResponse, SummaryRequest, SummaryResponse, UploadResponse, MindMapResponse,
} from '../types/api'
import type { Notebook, NotebookInfo, NotebookUpdate } from '../types/notebooks'
import type { ReadingChatInput, ReadingDocument } from '../types/reading'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

async function request(path: string, fallback: string, init?: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/api/${path}`, init)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new Error(`${fallback} Vui lòng kiểm tra kết nối và thử lại.`)
  }
  if (response.ok) return response
  // Never show arbitrary backend text, validation input, or provider exceptions.
  const data: APIErrorResponse | null = await response.json().catch(() => null)
  const safeDetails: Record<string, string> = {
    'A page filter requires exactly one selected PDF': 'Chỉ lọc trang khi chọn một tài liệu.',
    'Selected text could not be matched to the original PDF.': 'Không khớp đoạn chọn với văn bản PDF. Hãy thử bôi chọn một đoạn ngắn hơn.',
    'Original PDF is unavailable.': 'Không tìm thấy PDF gốc trên máy chủ.',
    'Original PDF has changed. Reopen the document.': 'PDF gốc đã thay đổi. Hãy đóng và mở lại tài liệu.',
    'AI service is temporarily unavailable.': 'Gemini đang quá tải. Hệ thống đã tự thử lại nhưng chưa thành công. Vui lòng thử lại sau ít phút.',
    'AI service rate limit exceeded.': 'Gemini đã đạt giới hạn lượt gọi hoặc hạn mức API. Vui lòng kiểm tra hạn mức rồi thử lại.',
    'AI service timed out.': 'Gemini phản hồi quá lâu. Vui lòng thử lại hoặc chọn ít nguồn hơn.',
    'AI service authentication failed.': 'Gemini từ chối khóa API. Vui lòng kiểm tra khóa trên máy chủ.',
    'Configured AI model is unavailable.': 'Mô hình Gemini đã cấu hình không khả dụng. Vui lòng kiểm tra cấu hình máy chủ.',
    'AI service is not configured.': 'Chưa cấu hình khóa API Gemini trên máy chủ.',
    'AI service rejected the request.': 'Gemini không chấp nhận yêu cầu. Vui lòng thử với ít nguồn hơn.',
    'AI service returned an empty response.': 'Gemini trả về nội dung trống. Vui lòng thử lại.',
  }
  const detail = typeof data?.detail === 'string' ? safeDetails[data.detail] : undefined
  const statusMessage: Record<number, string> = {
    400: 'Tệp PDF không hợp lệ hoặc vượt quá 25 MB.',
    404: 'Tài liệu hoặc trang không còn khả dụng. Vui lòng làm mới nguồn.',
    409: 'PDF gốc đã thay đổi. Hãy đóng và mở lại tài liệu.',
    422: 'Thông tin nhập chưa hợp lệ. Vui lòng kiểm tra lựa chọn và số lượng.',
    500: 'Vui lòng thử lại sau.',
    429: 'Dịch vụ AI đã đạt giới hạn lượt gọi. Vui lòng thử lại sau.',
    502: 'Dịch vụ AI chưa thể xử lý yêu cầu. Vui lòng thử lại sau.',
    503: 'Dịch vụ AI tạm thời quá tải. Vui lòng thử lại sau.',
    504: 'Dịch vụ AI phản hồi quá lâu. Vui lòng thử lại.',
  }
  throw new Error(`${fallback} ${detail || statusMessage[response.status] || 'Vui lòng thử lại sau.'}`)
}

async function json<T>(path: string, fallback: string, init?: RequestInit): Promise<T> {
  const response = await request(path, fallback, init)
  try { return await response.json() as T }
  catch { throw new Error(`${fallback} Phản hồi không hợp lệ.`) }
}

function post(body: unknown): RequestInit {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

export const getHealth = (signal?: AbortSignal) =>
  json<HealthResponse>('health', 'Không thể kết nối dịch vụ.', { signal })
export const getDocuments = (signal?: AbortSignal) =>
  json<DocumentsResponse>('documents', 'Không thể tải danh sách tài liệu.', { signal })
export const getNotebooks = (signal?: AbortSignal) =>
  json<{ notebooks: NotebookInfo[] }>('notebooks', 'Không thể tải sổ ghi chú.', { signal })
export const getNotebook = (id: string) =>
  json<Notebook>(`notebooks/${encodeURIComponent(id)}`, 'Không thể mở sổ ghi chú.')
export const createNotebook = (title: string, icon: string) =>
  json<Notebook>('notebooks', 'Không thể tạo sổ ghi chú.', post({ title, icon }))

// Serialize saves for each notebook so an earlier autosave cannot overwrite a
// newer snapshot, including when navigating between workspaces.
const notebookSaves = new Map<string, Promise<Notebook>>()
export function saveNotebook(id: string, body: NotebookUpdate): Promise<Notebook> {
  const previous = notebookSaves.get(id)
  const saving = (previous ? previous.catch(() => undefined) : Promise.resolve()).then(() =>
    json<Notebook>(`notebooks/${encodeURIComponent(id)}`, 'Không thể lưu sổ ghi chú.', { ...post(body), method: 'PUT' }))
  notebookSaves.set(id, saving)
  void saving.finally(() => { if (notebookSaves.get(id) === saving) notebookSaves.delete(id) }).catch(() => undefined)
  return saving
}
export async function deleteNotebook(id: string) {
  await notebookSaves.get(id)?.catch(() => undefined)
  await request(`notebooks/${encodeURIComponent(id)}`, 'Không thể xóa sổ ghi chú.', { method: 'DELETE' })
}
export async function resetNotebook(id: string, confirmation: string) {
  // Finish pending saves before resetting, so they cannot restore old state.
  await notebookSaves.get(id)?.catch(() => undefined)
  return json<Notebook>(`notebooks/${encodeURIComponent(id)}/reset`, 'Không thể đặt lại sổ tay.', post({ confirmation }))
}
export function uploadDocument(file: File) {
  const body = new FormData()
  body.append('file', file)
  return json<UploadResponse>('documents/upload', 'Không thể thêm nguồn.', { method: 'POST', body })
}
export const askQuestion = (body: ChatRequest) =>
  json<ChatResponse>('chat', 'Không thể tạo câu trả lời.', post(body))
const readingDocumentPath = (notebookId: string, documentId: string) =>
  `notebooks/${encodeURIComponent(notebookId)}/documents/${encodeURIComponent(documentId)}`
export const originalPdfUrl = (notebookId: string, documentId: string) =>
  `${API_BASE_URL}/api/${readingDocumentPath(notebookId, documentId)}/pdf`
export const getReadingDocument = (notebookId: string, documentId: string, signal?: AbortSignal) =>
  json<ReadingDocument>(readingDocumentPath(notebookId, documentId), 'Không thể mở PDF gốc.', { signal })
export const askReadingQuestion = ({ notebookId, ...context }: ReadingChatInput, question: string) =>
  json<ChatResponse>(`notebooks/${encodeURIComponent(notebookId)}/reading/chat`, 'Không thể tạo câu trả lời.', post({ ...context, question, k: 6 }))
export async function downloadOriginalPdf(notebookId: string, documentId: string, filename: string) {
  const response = await request(`${readingDocumentPath(notebookId, documentId)}/pdf?download=true`, 'Không thể tải PDF gốc.')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = filename
  document.body.appendChild(anchor); anchor.click(); anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
export const generateSummary = (body: SummaryRequest) =>
  json<SummaryResponse>('summary', 'Không thể tạo tóm tắt.', post(body))
export const generateMindMap = (body: SummaryRequest) =>
  json<MindMapResponse>('mindmap', 'Không thể tạo sơ đồ tư duy.', post(body))
export const generateQuiz = (body: QuizRequest) =>
  json<QuizResponse>('quiz', 'Không thể tạo quiz.', post(body))
export const generateFlashcards = (body: FlashcardsRequest) =>
  json<FlashcardsResponse>('flashcards', 'Không thể tạo flashcards.', post(body))

export async function downloadExport<F extends ExportFeature>(feature: F, result: ExportResults[F]) {
  const response = await request('export', 'Không thể tải tệp xuống.', post({ feature, result }))
  const blob = await response.blob()
  if (!blob.size) throw new Error('Không thể tải tệp xuống. Tệp nhận được rỗng.')
  const disposition = response.headers.get('Content-Disposition') || ''
  const candidate = disposition.match(/filename="?([^";]+)"?/i)?.[1]?.trim()
  const filename = candidate && /^[a-zA-Z0-9_-]+\.md$/.test(candidate) ? candidate : `${feature}.md`
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
