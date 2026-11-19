import { useCallback, useState } from 'react'
import type { NotebookState } from '../../useNotebook'
import type { Citation, LegacyGenerationTool } from '../../types/api'
import { ErrorMessage, LoadingIndicator } from '../../components/Status'
import { SummaryView } from './SummaryView'
import { QuizView } from './QuizView'
import { FlashcardsView } from './FlashcardsView'
import { ResultCard } from '../../components/ResultCard'
import { Icon } from '../../components/Icon'
import { MindMapView } from './MindMapView'
import { countMindMapNodes } from './mindmapLayout'
import { NotesPanel } from './NotesPanel'
import { ResearchTools } from './research/ResearchTools'
import { researchTools } from './research/researchData'

const tools: { id: LegacyGenerationTool; title: string; action: string; loading: string; icon: 'summary' | 'quiz' | 'cards' | 'mindmap' }[] = [
  { id: 'summary', title: 'Tóm tắt', action: 'Tạo tóm tắt', loading: 'Đang tạo tóm tắt...', icon: 'summary' },
  { id: 'quiz', title: 'Quiz', action: 'Tạo Quiz', loading: 'Đang tạo quiz...', icon: 'quiz' },
  { id: 'flashcards', title: 'Flashcards', action: 'Tạo Flashcards', loading: 'Đang tạo flashcards...', icon: 'cards' },
  { id: 'mindmap', title: 'Sơ đồ tư duy', action: 'Tạo sơ đồ tư duy', loading: 'Đang tạo sơ đồ tư duy...', icon: 'mindmap' },
]
const emptyMessages: Record<LegacyGenerationTool, string> = {
  summary: 'Chưa có bản tóm tắt nào.',
  quiz: 'Chưa có Quiz nào.',
  flashcards: 'Chưa có bộ Flashcards nào.',
  mindmap: 'Chưa có sơ đồ tư duy nào.',
}

export function StudioPanel({ notebook: n, collapsed = false, onCollapse, onOpenCitation, onShowChat }: { notebook: NotebookState; collapsed?: boolean; onCollapse?: () => void; onOpenCitation?: (citation: Citation) => void; onShowChat?: () => void }) {
  const [topics, setTopics] = useState<Record<LegacyGenerationTool, string>>({ summary: '', quiz: '', flashcards: '', mindmap: '' })
  const [counts, setCounts] = useState({ quiz: '3', flashcards: '3' })
  const [viewer, setViewer] = useState<{ type: LegacyGenerationTool; artifactId: string } | null>(null)
  const closeViewer = useCallback(() => setViewer(null), [])
  function deleteArtifact(tool: LegacyGenerationTool, id: string) {
    n.deleteArtifact(tool, id)
    if (viewer?.type === tool && viewer.artifactId === id) setViewer(null)
    window.requestAnimationFrame(() => document.getElementById(`${tool}-results-title`)?.focus({ preventScroll: true }))
  }
  const artifactCounts = { summary: n.summaryArtifacts.length, quiz: n.quizArtifacts.length, flashcards: n.flashcardArtifacts.length, mindmap: n.mindmapArtifacts.length }
  const viewedMap = viewer?.type === 'mindmap' ? n.mindmapArtifacts.find(artifact => artifact.id === viewer.artifactId) : null
  return <section id="notebook-studio-panel" className="panel studio-panel" hidden={collapsed} aria-labelledby="studio-title">
    <div className="panel-header"><span className="panel-heading"><Icon name="cards" size={18} /><h2 id="studio-title">Studio</h2></span>{onCollapse && <button type="button" className="icon-button collapse-panel" aria-label="Thu gọn Studio" onClick={onCollapse}><Icon name="panelRight" size={18} /></button>}</div>
    <div className="panel-body studio-body">
    <nav className="tool-tabs" aria-label="Công cụ Studio">
      {tools.map(tool => <button type="button" key={tool.id} aria-pressed={n.activeTool === tool.id}
        aria-controls={`studio-${tool.id}`} className={n.activeTool === tool.id ? 'active' : ''}
        onClick={() => { n.setActiveTool(tool.id); requestAnimationFrame(() => document.getElementById(`studio-${tool.id}`)?.scrollIntoView({ block: 'nearest' })) }}><span className={`tool-symbol tool-${tool.id}`}><Icon name={tool.icon} size={20} /></span><span className="tool-description"><strong>{tool.title}</strong></span>{n.loading[tool.id] ? <span className="loading-dot" aria-label="Đang tạo" /> : <Icon name="chevron" size={15} />}</button>)}
      {researchTools.map(tool => <button type="button" key={tool.id} aria-pressed={n.activeTool === tool.id} aria-controls={`studio-${tool.id}`} className={n.activeTool === tool.id ? 'active' : ''} onClick={() => { n.setActiveTool(tool.id); requestAnimationFrame(() => document.getElementById(`studio-${tool.id}`)?.scrollIntoView({ block: 'nearest' })) }}><span className={`tool-symbol tool-${tool.id}`}><Icon name={tool.icon} size={20} /></span><span className="tool-description"><strong>{tool.title}</strong></span>{n.loading[tool.id] ? <span className="loading-dot" aria-label="Đang tạo" /> : <Icon name="chevron" size={15} />}</button>)}
      <button type="button" aria-pressed={n.activeTool === 'notes'} aria-controls="studio-notes" className={`notes-tool ${n.activeTool === 'notes' ? 'active' : ''}`} onClick={() => n.setActiveTool('notes')}>
        <span className="tool-symbol tool-notes"><Icon name="edit" size={20} /></span><span className="tool-description"><strong>Ghi chú</strong></span><span className="count-badge">{n.notes.length}</span>
      </button>
    </nav>
      {!n.selected.length && n.activeTool !== 'notes' && <p className="field-hint">Vui lòng chọn ít nhất một tài liệu.</p>}
      <ResearchTools notebook={n} onOpenCitation={onOpenCitation} />
      <div id="studio-notes" hidden={n.activeTool !== 'notes'}><NotesPanel key={n.notes[0]?.id || 'empty'} notebook={n} /></div>
      {tools.map(tool => <div id={`studio-${tool.id}`} key={tool.id} hidden={n.activeTool !== tool.id}>
        <form className={`generation-form form-${tool.id}`} onSubmit={event => {
          event.preventDefault()
          void n.generate(tool.id, topics[tool.id], tool.id === 'quiz' || tool.id === 'flashcards' ? Number(counts[tool.id]) : 3)
        }}>
          <label htmlFor={`${tool.id}-topic`}>Chủ đề (không bắt buộc)</label>
          <input id={`${tool.id}-topic`} maxLength={10000} placeholder="Toàn bộ nguồn đã chọn"
            value={topics[tool.id]} onChange={event => setTopics(old => ({ ...old, [tool.id]: event.target.value }))} />
          {(tool.id === 'quiz' || tool.id === 'flashcards') && <div className="count-control">
            <label htmlFor={`${tool.id}-count`}>{tool.id === 'quiz' ? 'Số câu' : 'Số thẻ'}</label>
            <input id={`${tool.id}-count`} type="number" required min={1} max={tool.id === 'quiz' ? 50 : 100} step={1}
              value={counts[tool.id]} onChange={event => setCounts(old => ({ ...old, [tool.id]: event.target.value }))} />
          </div>}
          <button className="button primary" type="submit" disabled={n.loading[tool.id] || !n.selected.length || !n.modelControls.ready}><Icon name={tool.icon} size={16} />{tool.action}<Icon name="arrow" size={15} /></button>
        </form>
        {n.loading[tool.id] && <div className="generation-pending"><LoadingIndicator text={tool.loading} /><button type="button" className="button" onClick={() => n.cancel(tool.id)}>Dừng tạo</button></div>}
        {n.operationStatus[tool.id] === 'cancelled' && <p className="operation-cancelled" role="status">Đã dừng. Không lưu nội dung chưa hoàn tất.</p>}
        <ErrorMessage message={n.errors[tool.id]} />
        <section className="artifact-results" aria-labelledby={`${tool.id}-results-title`}>
          <h3 id={`${tool.id}-results-title`} tabIndex={-1}><Icon name="notebook" size={16} />Nội dung đã tạo<span className="count-badge">{artifactCounts[tool.id]}</span></h3>
          <div className="artifact-list">
            {tool.id === 'summary' && n.summaryArtifacts.map(artifact => <ResultCard key={artifact.id} {...artifact}
              metadata={`${artifact.result.key_points.length} ý chính · ${artifact.result.citations.length} nguồn`} action="Xem nội dung"
              onOpen={() => setViewer({ type: 'summary', artifactId: artifact.id })} onDelete={() => deleteArtifact('summary', artifact.id)} feature="summary" />)}
            {tool.id === 'quiz' && n.quizArtifacts.map(artifact => <ResultCard key={artifact.id} {...artifact}
              metadata={`${artifact.result.items.length} câu hỏi`} action="Bắt đầu Quiz"
              onOpen={() => setViewer({ type: 'quiz', artifactId: artifact.id })} onDelete={() => deleteArtifact('quiz', artifact.id)} feature="quiz" />)}
            {tool.id === 'flashcards' && n.flashcardArtifacts.map(artifact => <ResultCard key={artifact.id} {...artifact}
              metadata={`${artifact.result.cards.length} thẻ`} action="Xem Flashcards"
              onOpen={() => setViewer({ type: 'flashcards', artifactId: artifact.id })} onDelete={() => deleteArtifact('flashcards', artifact.id)} feature="flashcards" />)}
            {tool.id === 'mindmap' && n.mindmapArtifacts.map(artifact => <ResultCard key={artifact.id} {...artifact}
              metadata={`${countMindMapNodes(artifact.result.root)} ý · ${artifact.result.citations.length} trích dẫn`} action="Mở sơ đồ"
              onOpen={() => setViewer({ type: 'mindmap', artifactId: artifact.id })} onDelete={() => deleteArtifact('mindmap', artifact.id)} feature="mindmap" />)}
          </div>
          {!artifactCounts[tool.id] &&
            <div className="studio-empty"><p>{emptyMessages[tool.id]}</p></div>}
        </section>
      </div>)}
    </div>
    {n.summaryArtifacts.map(artifact => <SummaryView key={artifact.id} result={artifact.result} title={artifact.title}
      open={viewer?.type === 'summary' && viewer.artifactId === artifact.id} onClose={closeViewer} sourceName={n.sourceName} />)}
    {n.quizArtifacts.map(artifact => <QuizView key={artifact.id} result={artifact.result} title={artifact.title}
      open={viewer?.type === 'quiz' && viewer.artifactId === artifact.id} onClose={closeViewer} sourceName={n.sourceName} />)}
    {n.flashcardArtifacts.map(artifact => <FlashcardsView key={artifact.id} result={artifact.result} title={artifact.title}
      open={viewer?.type === 'flashcards' && viewer.artifactId === artifact.id} onClose={closeViewer} sourceName={n.sourceName} />)}
    {viewedMap && <MindMapView result={viewedMap.result} title={viewedMap.title} open onClose={closeViewer} sourceName={n.sourceName}
      onOpenCitation={citation => { closeViewer(); onOpenCitation?.(citation) }}
      onAsk={(label, filenames) => { if (n.prepareMindMapQuestion(label, filenames)) { closeViewer(); onShowChat?.() } }} />}
  </section>
}
