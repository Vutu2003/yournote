/** Incremental UTF-8/SSE decoding. Network chunks are not event boundaries. */
export async function readSSE(stream: ReadableStream<Uint8Array>, onEvent: (value: Record<string, unknown>) => void, signal: AbortSignal) {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const abort = () => { void reader.cancel().catch(() => undefined) }
  signal.addEventListener('abort', abort, { once: true })
  try {
    while (true) {
      signal.throwIfAborted()
      const { value, done } = await reader.read()
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })
      buffer = buffer.replace(/\r\n/g, '\n')
      if (buffer.length > 8_000_000) throw new Error('Phản hồi quá lớn để xử lý.')
      let boundary: number
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        const lines = frame.split('\n').filter(line => line.startsWith('data:'))
        if (!lines.length) continue
        const data = lines.map(line => line.slice(5).replace(/^ /, '')).join('\n')
        let parsed: unknown
        try { parsed = JSON.parse(data) } catch { throw new Error('Sự kiện phản hồi không hợp lệ.') }
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Sự kiện phản hồi không hợp lệ.')
        onEvent(parsed as Record<string, unknown>)
      }
      if (done) {
        signal.throwIfAborted()
        if (buffer.trim()) throw new Error('Luồng phản hồi kết thúc giữa sự kiện.')
        return
      }
    }
  } finally {
    signal.removeEventListener('abort', abort)
    await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}
