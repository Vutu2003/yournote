import type { GenerationMetadata } from '../types/api'
import { effortLabels } from '../features/ai/modelPreference'

export function GenerationInfo({ value }: { value?: GenerationMetadata | null }) {
  if (!value) return null
  const model = value.model || (value.actual_models.length ? value.actual_models.join(', ') : `${value.requested_model} (yêu cầu)`)
  const time = new Date(value.created_at)
  const label = Number.isFinite(time.getTime()) ? time.toLocaleString('vi-VN') : value.created_at
  const tokens = value.usage?.total_tokens
  return <div className="generation-info" title={`Đã hoàn tất · ${value.calls} lượt gọi có kết quả · ${label}${tokens != null ? ` · ${tokens} token do provider báo` : ''}`}>
    <span>{value.provider === 'chatgpt' ? 'ChatGPT' : 'API máy chủ'} · {model}{value.reasoning_effort ? ` · ${effortLabels[value.reasoning_effort]}` : ''}</span><time dateTime={value.created_at}>{label}</time>
  </div>
}
