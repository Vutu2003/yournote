import type { ModelChoice, ReasoningEffort } from '../../types/api'

export const effortLabels: Record<ReasoningEffort, string> = {
  none: 'Tắt', minimal: 'Tối thiểu', low: 'Thấp', medium: 'Vừa', high: 'Cao', xhigh: 'Rất cao', max: 'Tối đa',
}
export const preferenceKey = 'yournote.model.preference.v1'
export const preferenceEvent = 'yournote-model-preference-changed'
export function savedPreference(): { choice: ModelChoice | null; existed: boolean } {
  try {
    const raw = localStorage.getItem(preferenceKey)
    if (!raw) return { choice: null, existed: false }
    const value = JSON.parse(raw)
    if (['gemini', 'chatgpt'].includes(value.provider) && typeof value.model === 'string' && value.model.length <= 255
      && (value.connection_id === null || typeof value.connection_id === 'string' && value.connection_id.length <= 64)
      && (value.reasoning_effort == null || Object.hasOwn(effortLabels, value.reasoning_effort))) {
      return { choice: { provider: value.provider, model: value.model, connection_id: value.connection_id,
        reasoning_effort: value.reasoning_effort ?? null }, existed: true }
    }
  } catch { return { choice: null, existed: true } }
  return { choice: null, existed: true }
}
export function savePreference(value: ModelChoice) {
  const safe: ModelChoice = { provider: value.provider, model: value.model, connection_id: value.connection_id,
    reasoning_effort: value.reasoning_effort ?? null }
  try { localStorage.setItem(preferenceKey, JSON.stringify(safe)) } catch { /* Works in RAM for this session. */ }
  window.dispatchEvent(new CustomEvent(preferenceEvent, { detail: safe }))
}
