import { useCallback, useState } from 'react'
import type { NotebookState } from '../../../useNotebook'
import type { Citation } from '../../../types/api'
import type { ReportMode, ResearchTool } from '../../../types/research'
import { ErrorMessage } from '../../../components/Status'
import { Icon } from '../../../components/Icon'
import { ResultCard } from '../../../components/ResultCard'
import { ResearchView } from './ResearchView'
import { GraphView } from './GraphView'
import { researchTools } from './researchData'
import './research.css'

const stageLabels: Record<string, string> = { preparing: 'Chuẩn bị phạm vi', plan: 'Đã lập kế hoạch', examining: 'Đang xét riêng từng nguồn', generating: 'Đang đọc và phân tích', synthesizing: 'Đang tổng hợp bằng chứng', building_graph: 'Đang dựng mạng có bằng chứng', validating: 'Đang kiểm tra kết quả' }
export function ResearchTools({ notebook: n, onOpenCitation }: { notebook: NotebookState; onOpenCitation?: (citation: Citation) => void }) {
  const [goals, setGoals] = useState({ comparison: '', report: '', graph: '' })
  const [criteria, setCriteria] = useState('Khái niệm chính\nĐiều kiện áp dụng\nĐiểm khác biệt cần lưu ý')
  const [mode, setMode] = useState<ReportMode>('study_guide')
  const [viewer, setViewer] = useState<{ tool: ResearchTool; id: string } | null>(null)
  const close = useCallback(() => setViewer(null), [])
  const compared = viewer?.tool === 'comparison' ? n.comparisonArtifacts.find(a => a.id === viewer.id) : null
  const report = viewer?.tool === 'report' ? n.reportArtifacts.find(a => a.id === viewer.id) : null
  const graph = viewer?.tool === 'graph' ? n.graphArtifacts.find(a => a.id === viewer.id) : null
  const viewed = compared || report
  const criteriaList = criteria.split('\n').map(v => v.trim()).filter(Boolean)
  return <>
    {researchTools.map(tool => {
      const artifacts = tool.id === 'comparison' ? n.comparisonArtifacts : tool.id === 'report' ? n.reportArtifacts : n.graphArtifacts
      const progress = n.taskProgress[tool.id]
      const invalidSources = n.selected.length > 6 || n.selected.length < (tool.id === 'comparison' ? 2 : 1)
      return <div id={`studio-${tool.id}`} key={tool.id} hidden={n.activeTool !== tool.id} className="research-tool">
        <h3>{tool.title}</h3><p className="field-hint">{tool.id === 'comparison' ? 'Đối chiếu theo tiêu chí, phân biệt mâu thuẫn với khác điều kiện áp dụng.' : tool.id === 'report' ? 'Tạo nội dung học tập có dẫn chứng, kèm phạm vi và giới hạn.' : 'Khám phá khái niệm và quan hệ có trích đoạn hỗ trợ, tách biệt với sơ đồ tư duy.'}</p>
        <form className="generation-form" onSubmit={event => { event.preventDefault(); void n.generateResearch(tool.id, goals[tool.id], criteriaList, mode) }}>
          <label htmlFor={`${tool.id}-goal`}>Bạn muốn làm rõ điều gì?</label><textarea id={`${tool.id}-goal`} rows={2} required maxLength={2000} placeholder="Ví dụ: Đối chiếu cách giải thích và điều kiện áp dụng…" value={goals[tool.id]} onChange={event => setGoals(old => ({ ...old, [tool.id]: event.target.value }))} />
          <div className="research-suggestions" aria-label="Mục tiêu gợi ý">{(tool.id === 'comparison' ? ['Đối chiếu khái niệm và điều kiện áp dụng', 'Tìm điểm thống nhất và khác biệt cần ôn tập'] : tool.id === 'report' ? ['Lập đề cương ôn tập các khái niệm chính', 'Giải thích chủ đề dựa trên các tài liệu đã chọn'] : ['Liên kết khái niệm và điều kiện áp dụng', 'Khám phá quan hệ để hệ thống hóa kiến thức']).map(goal => <button type="button" className="text-button" key={goal} onClick={() => setGoals(old => ({ ...old, [tool.id]: goal }))}>{goal}</button>)}</div>
          {tool.id === 'comparison' ? <><label htmlFor="comparison-criteria">Tiêu chí so sánh · mỗi dòng một tiêu chí</label><textarea id="comparison-criteria" rows={3} maxLength={960} value={criteria} onChange={event => setCriteria(event.target.value)} /><p className="field-hint">Từ 1 đến 6 tiêu chí. Có thể thêm thông tin bạn muốn kiểm tra nhưng chưa chắc tài liệu có đề cập.</p></>
            : tool.id === 'report' ? <><label htmlFor="report-mode">Dạng nội dung</label><select id="report-mode" value={mode} onChange={event => setMode(event.target.value as ReportMode)}><option value="study_guide">Đề cương ôn tập</option><option value="explanation">Giải thích chủ đề</option><option value="synthesis">Báo cáo tổng hợp</option></select></> : null}
          <div className="research-plan"><strong>{n.selected.length} nguồn đang chọn</strong><p>Xét riêng từng nguồn, tối đa 6 đoạn/nguồn. {tool.id === 'graph' ? 'Tối đa 50 khái niệm và 100 quan hệ; chỉ giữ cạnh có bằng chứng.' : 'Sau đó tổng hợp các ý có bằng chứng.'} Tối đa 6 nguồn; có thể dừng trong lúc tạo. Dự kiến tối đa {n.selected.length + (tool.id === 'graph' ? 0 : 1)} lượt AI.</p></div>
          {invalidSources && <p className="field-hint">{tool.id === 'comparison' ? 'Chọn từ 2 đến 6 nguồn ở bảng Nguồn tài liệu.' : 'Chọn từ 1 đến 6 nguồn ở bảng Nguồn tài liệu.'}</p>}
          <button type="submit" className="button primary" disabled={invalidSources || !n.modelControls.ready || n.loading[tool.id] || !goals[tool.id].trim() || tool.id === 'comparison' && (criteriaList.length < 1 || criteriaList.length > 6 || new Set(criteriaList.map(v => v.toLocaleLowerCase())).size !== criteriaList.length)}><Icon name={tool.icon} size={17} />{tool.id === 'comparison' ? 'Tạo so sánh' : tool.id === 'report' ? 'Tạo nội dung' : 'Tạo mạng tri thức'}</button>
        </form>
        {n.loading[tool.id] && <div className="research-progress" role="status"><p>{stageLabels[progress?.stage || 'preparing'] || 'Đang xử lý…'}{progress?.total_steps ? ` · ${progress.completed_steps || 0}/${progress.total_steps} bước` : ''}</p>{progress?.source_count != null && <span>Tác vụ này: {progress.source_count} nguồn · {progress.chunk_count} đoạn · tối đa {progress.planned_calls} lượt AI.</span>}{progress?.total_steps && <progress max={progress.total_steps} value={progress.completed_steps || 0} />}<button type="button" className="button" onClick={() => n.cancel(tool.id)}>Dừng tạo</button></div>}
        {n.operationStatus[tool.id] === 'cancelled' && <p className="operation-cancelled" role="status">Đã dừng. Không lưu kết quả chưa hoàn tất.</p>}<ErrorMessage message={n.errors[tool.id]} />
        <section className="artifact-results"><h3 id={`${tool.id}-results-title`} tabIndex={-1}>Nội dung đã tạo <span className="count-badge">{artifacts.length}</span></h3>
          {!artifacts.length && <p className="field-hint">Chưa có kết quả. Chọn nguồn và nhập mục tiêu để bắt đầu.</p>}
          {tool.id === 'comparison' ? n.comparisonArtifacts.map(artifact => <ResultCard key={artifact.id} {...artifact} metadata={`${artifact.result.criteria.length} tiêu chí · ${artifact.result.sources.length} nguồn đã xét`} action="Xem so sánh" onOpen={() => setViewer({ tool: tool.id, id: artifact.id })} onDelete={() => { n.deleteArtifact(tool.id, artifact.id); if (viewer?.id === artifact.id) close() }} feature="comparison" />)
            : tool.id === 'report' ? n.reportArtifacts.map(artifact => <ResultCard key={artifact.id} {...artifact} metadata={`${artifact.result.sections.length} mục · ${artifact.result.sources.length} nguồn đã xét`} action="Xem nội dung" onOpen={() => setViewer({ tool: tool.id, id: artifact.id })} onDelete={() => { n.deleteArtifact(tool.id, artifact.id); if (viewer?.id === artifact.id) close() }} feature="report" />) : n.graphArtifacts.map(artifact => <ResultCard key={artifact.id} {...artifact} metadata={`${artifact.result.nodes.length} khái niệm · ${artifact.result.edges.length} quan hệ`} action="Khám phá mạng" onOpen={() => setViewer({ tool: tool.id, id: artifact.id })} onDelete={() => { n.deleteArtifact(tool.id, artifact.id); if (viewer?.id === artifact.id) close() }} feature="graph" />)}
        </section>
      </div>
    })}
    {graph && <GraphView result={graph.result} title={graph.title} onClose={close} onNote={n.saveResearchNote} documents={n.documents} sourceName={n.sourceName} onOpenCitation={citation => { close(); onOpenCitation?.(citation) }} />}
    {viewed && <ResearchView result={viewed.result} title={viewed.title} onClose={close} onNote={n.saveResearchNote} documents={n.documents} sourceName={n.sourceName} onOpenCitation={citation => { close(); onOpenCitation?.(citation) }} />}
  </>
}
