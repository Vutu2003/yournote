import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { NotebookState } from '../../useNotebook'
import { ChatAnswer } from './ChatAnswer'
import { ErrorMessage, LoadingIndicator } from '../../components/Status'
import { Icon } from '../../components/Icon'
import { FormattedText } from '../../components/FormattedText'
import type { ChatContext, Citation } from '../../types/api'
import type { ReadingChatInput } from '../../types/reading'

function TurnContext({ context, sourceName }: { context?: ChatContext | null; sourceName: (filename: string) => string }) {
  if (!context) return null
  return <details className="chat-context"><summary>{context.selection ? `Đoạn chọn · ${sourceName(context.selection.filename)} · trang ${context.selection.page}` : context.scope === 'document' ? sourceName(context.filenames[0]) : `Toàn bộ sổ · ${context.filenames.length} nguồn`}</summary>
    {context.selection ? <blockquote>{context.selection.text}</blockquote> : <p>{context.filenames.map(sourceName).join(' · ')}</p>}
  </details>
}

export function ChatPanel({ notebook: n, title, icon, createdAt, reading, onOpenCitation }: {
  notebook: NotebookState; title: string; icon: string; createdAt: string
  reading?: ReadingChatInput & { onScopeChange: (scope: 'document' | 'notebook') => void }
  onOpenCitation?: (citation: Citation) => void
}) {
  const [question, setQuestion] = useState('')
  const conversation = useRef<HTMLDivElement>(null)
  const questionInput = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    if (!n.questionDraft) return
    setQuestion(n.questionDraft.text)
    questionInput.current?.focus()
  }, [n.questionDraft])
  const suggestions = [
    { title: 'Tóm tắt Abstract', question: 'Hãy tóm tắt phần Abstract trong các nguồn đã chọn.' },
    { title: 'Giải thích khái niệm', question: 'Giải thích các khái niệm chính trong tài liệu và mối liên hệ giữa chúng.' },
    { title: 'So sánh phương pháp', question: 'Những phương pháp nào được đề cập trong các nguồn đã chọn và chúng khác nhau như thế nào?' },
  ]
  useEffect(() => {
    const element = conversation.current
    if (element) element.scrollTo({ top: element.scrollHeight })
  }, [n.chat.length, n.pendingQuestion])
  async function send(event?: FormEvent) {
    event?.preventDefault()
    if (await n.send(question, reading)) setQuestion('')
  }
  return <section className="panel chat-panel" aria-labelledby="chat-title">
    <div className="panel-header chat-panel-header"><span className="panel-heading"><Icon name="chat" size={17} /><h2 id="chat-title">Trò chuyện</h2></span>{reading && <select className="reading-scope" aria-label="Phạm vi trả lời" value={reading.scope} disabled={n.loading.chat} onChange={event => reading.onScopeChange(event.target.value as 'document' | 'notebook')}><option value="document">Tài liệu đang mở</option><option value="notebook">Toàn bộ sổ</option></select>}</div>
    <div className="conversation" ref={conversation} aria-busy={!!n.loading.chat}>
      {!n.chat.length && !n.pendingQuestion && <div className="notebook-introduction">
        <div className="introduction-top"><span className="notebook-cover-icon" aria-hidden="true">{icon}</span></div>
        <h2>{reading ? n.sourceName(n.documents.find(doc => doc.document_id === reading.document_id)?.filename || '') : title}</h2>
        <div className="notebook-context"><span><Icon name="source" size={14} />{n.documents.length} nguồn tài liệu</span><span><Icon name="clock" size={14} />{new Intl.DateTimeFormat('vi-VN', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(createdAt))}</span></div>
        {n.summaryArtifacts.length > 0 && <div className="welcome-summary"><h3>Tóm tắt gần nhất</h3><div className="welcome-summary-text"><FormattedText text={n.summaryArtifacts[0].result.summary} /></div></div>}
        <div className="question-suggestions" role="group" aria-label="Câu hỏi gợi ý">{suggestions.map(item => <button type="button" className="question-suggestion" key={item.title} disabled={(!reading && !n.selected.length) || !!n.loading.chat} onClick={() => { setQuestion(item.question); questionInput.current?.focus() }}>
          <span>{item.title}</span><Icon name="arrow" size={16} />
        </button>)}</div>
      </div>}
      {n.chat.map((result, index) => <article className="chat-turn" key={index}>
        <div className="user-message"><h3>Bạn</h3><TurnContext context={result.context} sourceName={n.sourceName} /><p className="prose">{result.question}</p></div>
        <ChatAnswer result={result} onOpenCitation={onOpenCitation} sourceName={n.sourceName} />
      </article>)}
      {n.pendingQuestion && <div className="pending-turn"><div className="user-message"><h3>Bạn</h3><TurnContext context={n.pendingContext} sourceName={n.sourceName} /><p className="prose">{n.pendingQuestion}</p></div>
        <LoadingIndicator text="Đang tạo câu trả lời..." /></div>}
    </div>
    <form className="chat-composer" onSubmit={send}>
      {!reading && !n.selected.length && <p className="field-hint">Vui lòng chọn ít nhất một tài liệu.</p>}
      <ErrorMessage message={n.errors.chat} />
      <label className="sr-only" htmlFor="chat-question">Câu hỏi</label>
      <div className="composer-row">
        <span className="composer-icon"><Icon name="bolt" size={21} /></span>
        <textarea ref={questionInput} id="chat-question" placeholder="Nhập câu hỏi…" title="Enter để gửi · Shift+Enter để xuống dòng" value={question} maxLength={10000} rows={2}
          disabled={n.loading.chat} onChange={event => setQuestion(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault()
              if (!n.loading.chat) void send()
            }
          }} />
        <span className="composer-source-count">{reading ? reading.scope === 'document' ? 1 : n.documents.length : n.selected.length} nguồn</span>
        <button className="button primary send-button" type="submit" aria-label="Gửi câu hỏi" disabled={n.loading.chat || !question.trim() || (!reading && !n.selected.length)}><Icon name="send" size={19} /><span className="sr-only">Gửi</span></button>
      </div>
    </form>
  </section>
}
