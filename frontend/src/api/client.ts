import type {
  APIErrorResponse, ChatRequest, ChatResponse, DocumentsResponse, ExportFeature,
  ExportResults, FlashcardsRequest, FlashcardsResponse, HealthResponse,
  QuizRequest, QuizResponse, SummaryRequest, SummaryResponse, UploadResponse,
} from '../types/api'

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
  }
  const detail = typeof data?.detail === 'string' ? safeDetails[data.detail] : undefined
  const statusMessage: Record<number, string> = {
    400: 'Tệp PDF không hợp lệ hoặc vượt quá 25 MB.',
    404: 'Tài liệu hoặc trang không còn khả dụng. Vui lòng làm mới nguồn.',
    422: 'Thông tin nhập chưa hợp lệ. Vui lòng kiểm tra lựa chọn và số lượng.',
    500: 'Vui lòng thử lại sau.',
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
export function uploadDocument(file: File) {
  const body = new FormData()
  body.append('file', file)
  return json<UploadResponse>('documents/upload', 'Không thể thêm nguồn.', { method: 'POST', body })
}
export const askQuestion = (body: ChatRequest) =>
  json<ChatResponse>('chat', 'Không thể tạo câu trả lời.', post(body))
export const generateSummary = (body: SummaryRequest) =>
  json<SummaryResponse>('summary', 'Không thể tạo tóm tắt.', post(body))
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
