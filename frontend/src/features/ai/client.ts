import type { ReasoningEffort } from '../../types/api'
export interface ModelChoice { slug: string; display_name: string; supported_reasoning_levels?: ReasoningEffort[]; default_reasoning_level?: ReasoningEffort | null }
export interface CheckResult {
  model: string; actual_model: string | null; checked_at: number; duration_seconds: number | null
  usage: Record<string, number | null> | null
}
export interface AIProfile {
  id: string; label: string; state: 'connected' | 'permission_required' | 'reconnect_required'
  plan_enabled: boolean; identity_connected: boolean; catalog_checked: boolean; inference_checked: boolean
  last_check: CheckResult | null; welcome_pending: boolean
}
export interface AIStatus {
  profiles: AIProfile[]; active_connection_id: string | null; storage_mode: 'keyring' | 'memory'; error: string | null
  pending: { id: string; state: 'waiting' | 'exchanging'; expires_at: number } | null
}
let csrf = '' // Local CSRF token only. OAuth credentials never enter this module.
let openingSession: Promise<void> | null = null

const messages: Record<string, string> = {
  'Document version changed. Refresh sources and try again.': 'Nội dung nguồn đã thay đổi trong lúc tạo. Hãy làm mới nguồn và gửi lại.',
  'Selected material exceeds the retrieval limit. Choose fewer sources.': 'Phạm vi chọn vượt giới hạn truy xuất. Hãy chọn ít nguồn hoặc một trang cụ thể.',

  'Notebook sources have changed. Save and try again.': 'Nguồn của sổ đã thay đổi. Hãy đợi lưu xong rồi thử lại.',
  'Selected material exceeds the AI task call limit.': 'Phạm vi này cần quá nhiều lượt gọi AI. Hãy chọn ít nguồn hoặc một chủ đề cụ thể hơn.',
  'Too many AI tasks are active.': 'Đang có nhiều tác vụ AI. Hãy đợi hoặc dừng tác vụ đang chạy.',
  'AI task timed out.': 'Tác vụ đã vượt thời gian cho phép và được dừng. Nội dung dở dang không được lưu.',
  'AI service authentication failed.': 'Phiên ChatGPT không còn hợp lệ. Hãy kết nối lại.',
  'ChatGPT plan permission is required.': 'Chưa có quyền dùng gói, hoặc tài khoản bị giới hạn quyền truy cập. Hãy kiểm tra quyền kết nối.',
  'ChatGPT plan usage is unavailable for this account.': 'Tài khoản hoặc workspace chưa đủ điều kiện dùng gói trong ứng dụng này.',
  'AI service quota exceeded.': 'Đã chạm hạn mức áp dụng cho ứng dụng hoặc gói. Hãy mở Quản lý hạn mức.',
  'AI service rate limit exceeded.': 'Đang có quá nhiều yêu cầu. Hãy đợi rồi thử lại.',
  'AI service is temporarily unavailable.': 'Dịch vụ ChatGPT tạm thời chưa khả dụng. Bạn có thể thử lại sau.',
  'AI service timed out.': 'ChatGPT phản hồi quá lâu. Hãy thử lại sau.',
  'AI service returned an empty response.': 'Chưa nhận được phản hồi hoàn tất hợp lệ. Kết nối chưa được xác minh.',
  'Configured AI model is unavailable.': 'Model không còn được cấp quyền. Hãy làm mới danh sách và chọn lại.',
  'AI service does not support this operation.': 'Luồng dùng gói chưa hỗ trợ yêu cầu này.',
  'AI service rejected the request.': 'ChatGPT chưa chấp nhận yêu cầu này. Hãy kiểm tra kết nối và thử lại.',
  'ChatGPT sign-in expired. Please try again.': 'Đã hết thời gian chờ đăng nhập. Hãy bắt đầu lại.',
  'ChatGPT sign-in was not completed.': 'Bạn đã hủy hoặc chưa hoàn tất đăng nhập.',
  'ChatGPT sign-in failed. Please try again.': 'Không thể hoàn tất đăng nhập. Hãy thử lại.',
  'ChatGPT registration is incomplete.': 'Đăng ký kết nối chưa hoàn tất. Hãy thử lại.',
  'ChatGPT sign-in could not be verified.': 'Không xác minh được phiên đăng nhập. Hãy bắt đầu lại.',
  'Another ChatGPT sign-in is in progress.': 'Một cửa sổ khác đang đăng nhập. Hãy hoàn tất hoặc hủy phiên đó.',
  'ChatGPT sign-out is in progress.': 'Đang đăng xuất kết nối này. Hãy đợi hoàn tất.',
  'ChatGPT connection check is already running.': 'Một kiểm tra kết nối đang chạy. Hãy đợi hoàn tất.',
  'ChatGPT connection is already open in another process.': 'Kết nối đang được một tiến trình YourNote khác sử dụng. Hãy chỉ chạy một backend.',
  'Unable to start the local ChatGPT callback listener.': 'Không mở được cổng nhận đăng nhập cục bộ. Hãy kiểm tra backend.',
  'Local AI session expired. Reopen settings.': 'Phiên cài đặt đã hết hạn. Hãy đóng rồi mở lại Cài đặt.',
}
export const connectionError = (detail: string) => messages[detail] || 'Không thể xử lý kết nối AI. Hãy thử lại hoặc mở lại Cài đặt.'

export async function aiResponse(path: string, body?: unknown, signal?: AbortSignal): Promise<Response> {
  let response: Response
  try {
    response = await fetch('/api/ai/' + path, {
      credentials: 'same-origin', cache: 'no-store', method: body === undefined ? 'GET' : 'POST',
      headers: { 'X-YourNote-Local': '1', ...(body === undefined ? {} : { 'Content-Type': 'application/json', 'X-YourNote-CSRF': csrf }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal,
    })
  } catch (reason) { if (signal?.aborted) throw reason; throw new Error('Không kết nối được backend cục bộ. Hãy kiểm tra ứng dụng đang chạy.') }
  if (!response.ok) {
    const result = await response.json().catch(() => null)
    throw new Error(connectionError(typeof result?.detail === 'string' ? result.detail : ''))
  }
  return response
}
export async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await aiResponse(path, body)
  const result = await response.json().catch(() => null)
  if (result === null) throw new Error('Phản hồi kết nối không hợp lệ.')
  return result as T
}
export function openAISession(): Promise<void> {
  // React StrictMode or concurrent mounts must not race two cookie/CSRF pairs.
  if (!openingSession) openingSession = request<{ csrf: string }>('session')
    .then(value => { csrf = value.csrf })
    .finally(() => { openingSession = null })
  return openingSession
}
export const getAIStatus = () => request<AIStatus>('chatgpt')
export const startSignIn = (connection_id: string | null, consent = false) => request<{ launch_path: string }>('chatgpt/sign-in', { connection_id, consent })
export const cancelSignIn = () => request<AIStatus>('chatgpt/sign-in/cancel', {})
const profilePath = (id: string) => 'chatgpt/profiles/' + encodeURIComponent(id)
export const getModels = (id: string) => request<{ models: ModelChoice[] }>(profilePath(id) + '/catalog', {})
export const checkConnection = (id: string, model: string) => request<CheckResult>(profilePath(id) + '/check', { model })
export const selectConnection = (id: string) => request<AIStatus>(profilePath(id) + '/select', {})
export const acknowledgePlan = (id: string) => request<AIStatus>(profilePath(id) + '/notice', {})
export const logoutConnection = (id: string) => request<{ remote_revocation_confirmed: boolean; keyring_cleanup_confirmed: boolean }>(profilePath(id) + '/logout', {})
