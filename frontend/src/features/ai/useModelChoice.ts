import { useCallback, useEffect, useRef, useState } from 'react'
import type { ModelChoice } from '../../types/api'
import { getAIStatus, getModels, openAISession, request } from './client'
import type { AIStatus, ModelChoice as CatalogModel } from './client'

import { savedPreference, savePreference, preferenceEvent, preferenceKey } from './modelPreference'

export function useModelChoice() {
  const [initial] = useState(savedPreference)
  const [choice, setChoice] = useState<ModelChoice | null>(initial.choice)
  const [status, setStatus] = useState<AIStatus | null>(null)
  const [server, setServer] = useState<{ provider: 'gemini'; model: string; configured: boolean } | null>(null)
  const [models, setModels] = useState<CatalogModel[]>([])
  const [loadedConnection, setLoadedConnection] = useState('')
  const [loading, setLoading] = useState(true)
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [error, setError] = useState('')
  const [epoch, setEpoch] = useState(0)
  const loadGeneration = useRef(0)
  const refresh = useCallback(() => setEpoch(value => value + 1), [])
  useEffect(() => {
    const generation = ++loadGeneration.current
    let live = true
    void (async () => {
      setLoading(true); setError('')
      try {
        await openAISession()
        const [options, connections] = await Promise.all([
          request<{ server: { provider: 'gemini'; model: string; configured: boolean } }>('options'), getAIStatus(),
        ])
        if (!live || loadGeneration.current !== generation) return
        setServer(options.server); setStatus(connections)
        if (!initial.existed) setChoice(old => old || { provider: 'gemini', model: options.server.model, connection_id: null })
      } catch (reason) { if (live) setError(reason instanceof Error ? reason.message : 'Không thể tải cấu hình model.') }
      finally { if (live) setLoading(false) }
    })()
    return () => { live = false }
  }, [epoch, initial.existed])
  useEffect(() => {
    window.addEventListener('focus', refresh)
    window.addEventListener('yournote-ai-connections-changed', refresh)
    return () => { window.removeEventListener('focus', refresh); window.removeEventListener('yournote-ai-connections-changed', refresh) }
  }, [refresh])
  useEffect(() => {
    function receive(event: Event) {
      const value = event instanceof CustomEvent ? event.detail as ModelChoice : savedPreference().choice
      setChoice(value)
      setError('')
    }
    function storage(event: StorageEvent) { if (event.key === preferenceKey) receive(event) }
    window.addEventListener(preferenceEvent, receive)
    window.addEventListener('storage', storage)
    return () => { window.removeEventListener(preferenceEvent, receive); window.removeEventListener('storage', storage) }
  }, [])
  const connectionId = choice?.connection_id
  const provider = choice?.provider
  const granted = status?.profiles.some(item => item.id === connectionId && item.plan_enabled && item.state === 'connected')
  useEffect(() => {
    let live = true
    if (provider !== 'chatgpt' || !connectionId || !granted) return
    void Promise.resolve().then(() => { if (live) setCatalogLoading(true); return getModels(connectionId) }).then(value => { if (live) { setModels(value.models); setLoadedConnection(connectionId); setError('') } })
      .catch(reason => { if (live) { setModels([]); setLoadedConnection(connectionId); setError(reason.message) } })
      .finally(() => { if (live) setCatalogLoading(false) })
    return () => { live = false }
  }, [provider, connectionId, granted, epoch])
  const choose = useCallback((value: ModelChoice) => {
    if (choice?.provider !== value.provider || choice?.connection_id !== value.connection_id) {
      setModels([]); setCatalogLoading(false)
    }
    setChoice({ ...value }); setError('')
    savePreference(value)
  }, [choice?.provider, choice?.connection_id])
  const ready = !loading && !error && !!choice && (choice.provider === 'gemini'
    ? !!server?.configured && server.model === choice.model && choice.connection_id === null && !choice.reasoning_effort
    : !!granted && loadedConnection === connectionId && !catalogLoading && models.some(model => model.slug === choice.model && (!choice.reasoning_effort || model.supported_reasoning_levels?.includes(choice.reasoning_effort))))
  return { choice, choose, status, server, models: provider === 'chatgpt' && granted && loadedConnection === connectionId ? models : [], loading: loading || (provider === 'chatgpt' && granted && (catalogLoading || loadedConnection !== connectionId)), error, ready, refresh }
}
