import { useCallback, useState } from 'react'
import type { NotebookState } from '../../useNotebook'
import type { StudioTool } from '../../types/api'
import { ErrorMessage, LoadingIndicator } from '../../components/Status'
import { SummaryView } from './SummaryView'
import { QuizView } from './QuizView'
import { FlashcardsView } from './FlashcardsView'
import { ResultCard } from '../../components/ResultCard'

const tools: { id: StudioTool; title: string; action: string; loading: string }[] = [
  { id: 'summary', title: 'Tóm tắt', action: 'Tạo tóm tắt', loading: 'Đang tạo tóm tắt...' },
  { id: 'quiz', title: 'Quiz', action: 'Tạo Quiz', loading: 'Đang tạo quiz...' },
  { id: 'flashcards', title: 'Flashcards', action: 'Tạo Flashcards', loading: 'Đang tạo flashcards...' },
]
const emptyMessages: Record<StudioTool, string> = {
  summary: 'Chưa có bản tóm tắt nào.',
  quiz: 'Chưa có Quiz nào.',
  flashcards: 'Chưa có bộ Flashcards nào.',
}

export function StudioPanel({ notebook: n }: { notebook: NotebookState }) {
  const [topics, setTopics] = useState<Record<StudioTool, string>>({ summary: '', quiz: '', flashcards: '' })
  const [counts, setCounts] = useState({ quiz: '3', flashcards: '3' })
  const [viewer, setViewer] = useState<{ type: StudioTool; artifactId: string } | null>(null)
  const closeViewer = useCallback(() => setViewer(null), [])
  return <section className="panel studio-panel" aria-labelledby="studio-title">
    <div className="panel-header"><h2 id="studio-title">Studio</h2><span className="muted">Công cụ học tập</span></div>
    <nav className="tool-tabs" aria-label="Công cụ Studio">
      {tools.map(tool => <button type="button" key={tool.id} aria-pressed={n.activeTool === tool.id}
        aria-controls={`studio-${tool.id}`} className={n.activeTool === tool.id ? 'active' : ''}
        onClick={() => n.setActiveTool(tool.id)}>{tool.title}{n.loading[tool.id] && <span aria-label="Đang tạo"> ·</span>}</button>)}
    </nav>
    <div className="panel-body studio-body">
      {!n.selected.length && <p className="field-hint">Vui lòng chọn ít nhất một tài liệu.</p>}
      {tools.map(tool => <div id={`studio-${tool.id}`} key={tool.id} hidden={n.activeTool !== tool.id}>
        <form className="generation-form" onSubmit={event => {
          event.preventDefault()
          void n.generate(tool.id, topics[tool.id], tool.id === 'summary' ? 3 : Number(counts[tool.id]))
        }}>
          <label htmlFor={`${tool.id}-topic`}>Chủ đề (không bắt buộc)</label>
          <input id={`${tool.id}-topic`} maxLength={10000} placeholder="Để trống để dùng toàn bộ nguồn đã chọn"
            value={topics[tool.id]} onChange={event => setTopics(old => ({ ...old, [tool.id]: event.target.value }))} />
          {tool.id !== 'summary' && <div className="count-control">
            <label htmlFor={`${tool.id}-count`}>{tool.id === 'quiz' ? 'Số câu' : 'Số thẻ'}</label>
            <input id={`${tool.id}-count`} type="number" required min={1} max={tool.id === 'quiz' ? 50 : 100} step={1}
              value={counts[tool.id]} onChange={event => setCounts(old => ({ ...old, [tool.id]: event.target.value }))} />
          </div>}
          <button className="button primary" type="submit" disabled={n.loading[tool.id]}>{tool.action}</button>
        </form>
        {n.loading[tool.id] && <div className="generation-pending"><LoadingIndicator text={tool.loading} /></div>}
        <ErrorMessage message={n.errors[tool.id]} />
        <section className="artifact-results" aria-labelledby={`${tool.id}-results-title`}>
          <h3 id={`${tool.id}-results-title`}>Kết quả đã tạo</h3>
          <div className="artifact-list">
            {tool.id === 'summary' && n.summaryArtifacts.map(artifact => <ResultCard key={artifact.id} {...artifact}
              metadata={`${artifact.result.key_points.length} ý chính · ${artifact.result.citations.length} nguồn`} action="Xem nội dung"
              onOpen={() => setViewer({ type: 'summary', artifactId: artifact.id })} feature="summary" />)}
            {tool.id === 'quiz' && n.quizArtifacts.map(artifact => <ResultCard key={artifact.id} {...artifact}
              metadata={`${artifact.result.items.length} câu hỏi`} action="Bắt đầu Quiz"
              onOpen={() => setViewer({ type: 'quiz', artifactId: artifact.id })} feature="quiz" />)}
            {tool.id === 'flashcards' && n.flashcardArtifacts.map(artifact => <ResultCard key={artifact.id} {...artifact}
              metadata={`${artifact.result.cards.length} thẻ`} action="Xem Flashcards"
              onOpen={() => setViewer({ type: 'flashcards', artifactId: artifact.id })} feature="flashcards" />)}
          </div>
          {!(tool.id === 'summary' ? n.summaryArtifacts.length : tool.id === 'quiz' ? n.quizArtifacts.length : n.flashcardArtifacts.length) &&
            <div className="studio-empty"><p>{emptyMessages[tool.id]}</p><p className="field-hint">Kết quả được giữ trong phiên làm việc này.</p></div>}
        </section>
      </div>)}
    </div>
    {n.summaryArtifacts.map(artifact => <SummaryView key={artifact.id} result={artifact.result} title={artifact.title}
      open={viewer?.type === 'summary' && viewer.artifactId === artifact.id} onClose={closeViewer} />)}
    {n.quizArtifacts.map(artifact => <QuizView key={artifact.id} result={artifact.result} title={artifact.title}
      open={viewer?.type === 'quiz' && viewer.artifactId === artifact.id} onClose={closeViewer} />)}
    {n.flashcardArtifacts.map(artifact => <FlashcardsView key={artifact.id} result={artifact.result} title={artifact.title}
      open={viewer?.type === 'flashcards' && viewer.artifactId === artifact.id} onClose={closeViewer} />)}
  </section>
}
