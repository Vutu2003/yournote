import type { TaskProgress } from '../../types/research'
import type { ModelChoice, ChatResponse, LearningResponse } from '../../types/api'
import { aiResponse, connectionError, openAISession } from './client'
import { readSSE } from './sse'

export interface TaskInput {
  id: string; notebook_id: string; feature: string; model: ModelChoice
  input: unknown; sources?: { filenames: string[]; pages: number[]; document_versions?: Record<string, string> }
}
export async function runTask<T extends ChatResponse | LearningResponse>(task: TaskInput, signal: AbortSignal, onDelta: (text: string) => void, onProgress?: (progress: TaskProgress) => void): Promise<T> {
  await openAISession()
  signal.throwIfAborted()
  const response = await aiResponse('tasks', task, signal)
  if (!response.body) throw new Error('Không nhận được luồng phản hồi.')
  let result: T | null = null
  let terminal = false
  await readSSE(response.body, event => {
    if (terminal) throw new Error('Có dữ liệu sau khi tác vụ đã kết thúc.')
    if (event.type === 'started') {
      if (event.task_id !== task.id || event.notebook_id !== task.notebook_id) throw new Error('Tác vụ phản hồi không khớp sổ tay.')
    } else if (event.type === 'delta') {
      if (typeof event.text !== 'string') throw new Error('Nội dung phản hồi không hợp lệ.')
      onDelta(event.text)
    } else if (event.type === 'completed') {
      const value = event.result as T
      if (!value?.generation || value.generation.status !== 'completed' || value.generation.request_id !== task.id || value.generation.notebook_id !== task.notebook_id) {
        throw new Error('Kết quả hoàn tất không khớp tác vụ.')
      }
      result = value; terminal = true
    } else if (event.type === 'error') {
      throw new Error(connectionError(typeof event.detail === 'string' ? event.detail : ''))
    } else if (event.type === 'cancelled') {
      throw new DOMException('Đã dừng tác vụ.', 'AbortError')
    } else if (event.type === 'progress') {
      if (typeof event.stage !== 'string') throw new Error('Tiến trình phản hồi không hợp lệ.')
      onProgress?.(event as unknown as TaskProgress)
    } else if (event.type !== 'progress') throw new Error('Sự kiện phản hồi chưa được hỗ trợ.')
  }, signal)
  signal.throwIfAborted()
  if (!terminal || !result) throw new Error('Chưa nhận được kết quả hoàn tất. Nội dung dở dang không được lưu.')
  return result
}
export async function cancelTask(id: string) {
  try { await openAISession(); await aiResponse(`tasks/${encodeURIComponent(id)}/cancel`, {}) } catch { /* Disconnect also cancels upstream. */ }
}
