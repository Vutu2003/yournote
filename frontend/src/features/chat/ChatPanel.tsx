import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { NotebookState } from '../../useNotebook'
import { ChatAnswer } from './ChatAnswer'
import { ErrorMessage, LoadingIndicator } from '../../components/Status'

export function ChatPanel({ notebook: n }: { notebook: NotebookState }) {
  const [question, setQuestion] = useState('')
  const bottom = useRef<HTMLDivElement>(null)
  useEffect(() => { bottom.current?.scrollIntoView({ block: 'nearest' }) }, [n.chat.length, n.pendingQuestion])
  async function send(event?: FormEvent) {
    event?.preventDefault()
    if (await n.send(question)) setQuestion('')
  }
  return <section className="panel chat-panel" aria-labelledby="chat-title">
    <div className="panel-header"><h2 id="chat-title">Trò chuyện</h2><span className="muted">Dựa trên nguồn đã chọn</span></div>
    <div className="conversation" aria-busy={!!n.loading.chat}>
      {!n.chat.length && !n.pendingQuestion && <div className="empty-chat">
        <span className="empty-symbol" aria-hidden="true">?</span>
        <h3>Bắt đầu từ một câu hỏi</h3>
        <p>Chọn nguồn tài liệu, rồi đặt câu hỏi để khám phá nội dung cùng trích dẫn.</p>
      </div>}
      {n.chat.map((result, index) => <article className="chat-turn" key={index}>
        <div className="user-message"><h3>Bạn</h3><p className="prose">{result.question}</p></div>
        <ChatAnswer result={result} />
      </article>)}
      {n.pendingQuestion && <div className="pending-turn"><div className="user-message"><h3>Bạn</h3><p className="prose">{n.pendingQuestion}</p></div>
        <LoadingIndicator text="Đang tạo câu trả lời..." /></div>}
      <div ref={bottom} />
    </div>
    <form className="chat-composer" onSubmit={send}>
      {!n.selected.length && <p className="field-hint">Vui lòng chọn ít nhất một tài liệu.</p>}
      <ErrorMessage message={n.errors.chat} />
      <label className="sr-only" htmlFor="chat-question">Câu hỏi</label>
      <div className="composer-row">
        <textarea id="chat-question" placeholder="Hỏi tài liệu..." value={question} maxLength={10000} rows={2}
          disabled={n.loading.chat} onChange={event => setQuestion(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault()
              if (!n.loading.chat) void send()
            }
          }} />
        <button className="button primary" type="submit" disabled={n.loading.chat}>Gửi</button>
      </div>
      <p className="field-hint composer-hint">Enter để gửi · Shift+Enter để xuống dòng. Kiểm tra trích dẫn khi sử dụng câu trả lời.</p>
    </form>
  </section>
}
