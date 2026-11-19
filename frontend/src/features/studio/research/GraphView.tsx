import { useId, useMemo, useRef, useState } from 'react'
import { ResultViewerModal } from '../../../components/ResultViewerModal'
import { ExportButton } from '../../../components/ExportButton'
import { GenerationInfo } from '../../../components/GenerationInfo'
import { Icon } from '../../../components/Icon'
import type { Citation, DocumentInfo } from '../../../types/api'
import type { GraphResponse, GroundedStatement } from '../../../types/research'
import { relationLabels } from '../../../types/research'
import { statementNote } from './researchData'
import { EvidenceStatement, ResearchScope } from './ResearchView'
import { graphLayout, searchConcept } from './graphLayout'

export function GraphView({ result, title, onClose, sourceName, documents, onOpenCitation, onNote }: {
  result: GraphResponse; title: string; onClose: () => void; sourceName: (filename: string) => string; documents: DocumentInfo[]
  onOpenCitation?: (citation: Citation) => void; onNote: (title: string, content: string) => boolean
}) {
  const [query, setQuery] = useState(''), [sourceFilter, setSourceFilter] = useState('')
  const [selected, setSelected] = useState<{ kind: 'node' | 'edge'; id: string } | null>(null)
  const [view, setView] = useState<'network' | 'list'>(() => window.innerWidth < 700 ? 'list' : 'network')
  const [list, setList] = useState<'nodes' | 'edges'>('nodes')
  const [camera, setCamera] = useState({ x: 0, y: 0, scale: 1 })
  const canvas = useRef<HTMLDivElement>(null)
  const drag = useRef<{ x: number; y: number; baseX: number; baseY: number; units: number } | null>(null)
  const marker = useId().replaceAll(':', '')
  const points = useMemo(() => graphLayout(result.nodes, result.edges), [result.nodes, result.edges])
  const bounds = useMemo(() => {
    const values = [...points.values()]
    const minX = Math.min(...values.map(p => p.x)), maxX = Math.max(...values.map(p => p.x))
    const minY = Math.min(...values.map(p => p.y)), maxY = Math.max(...values.map(p => p.y))
    const width = Math.max(600, maxX - minX + 240), height = Math.max(360, maxY - minY + 180)
    return { x: (minX + maxX - width) / 2, y: (minY + maxY - height) / 2, width, height, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 }
  }, [points])
  const byId = new Map(result.nodes.map(node => [node.id, node]))
  const byMarker = new Map(result.citations.map(c => [c.source_marker, c]))
  const supportsFilter = (statement: GroundedStatement) => !sourceFilter || statement.evidence.some(ref => byMarker.get(ref.source_marker)?.filename === sourceFilter)
  const edges = result.edges.filter(edge => supportsFilter(edge.statement))
  const endpoints = new Set(edges.flatMap(edge => [edge.source, edge.target]))
  const nodes = result.nodes.filter(node => supportsFilter(node.definition) || endpoints.has(node.id))
  const matches = new Set(nodes.filter(node => searchConcept([node.label, ...node.aliases].join(' ')).includes(searchConcept(query))).map(node => node.id))
  const chosenNode = selected?.kind === 'node' ? nodes.find(node => node.id === selected.id) : null
  const chosenEdge = selected?.kind === 'edge' ? edges.find(edge => edge.id === selected.id) : null
  const rawStatement = chosenNode?.definition || chosenEdge?.statement
  // Filtering the network must not hide evidence required by a merged definition.
  const statement = rawStatement
  const label = chosenNode?.label || (chosenEdge ? `${byId.get(chosenEdge.source)?.label} → ${byId.get(chosenEdge.target)?.label}` : '')
  function zoom(factor: number) { setCamera(old => ({ ...old, scale: Math.max(.35, Math.min(3, old.scale * factor)) })) }
  function reset() { setCamera({ x: 0, y: 0, scale: 1 }) }
  function save() { if (statement && onNote(label, statementNote(label, [statement], result, sourceName))) onClose() }
  function nodeList() {
    return <ul className="knowledge-items" aria-label="Danh sách khái niệm">{nodes.filter(node => matches.has(node.id)).map(node => <li key={node.id}><button type="button" aria-pressed={chosenNode?.id === node.id} onClick={() => setSelected({ kind: 'node', id: node.id })}><strong>{node.label}</strong><span>{node.definition.text}</span></button></li>)}</ul>
  }
  return <ResultViewerModal open title="Mạng tri thức" artifactTitle={title} onClose={onClose} footer={<ExportButton feature="graph" result={result} />}>
    <div className="research-view knowledge-view"><p className="research-goal">{result.goal}</p><GenerationInfo value={result.generation} /><ResearchScope result={result} documents={documents} sourceName={sourceName} />
      <div className="knowledge-controls"><label>Tìm khái niệm<input type="search" aria-label="Tìm khái niệm" placeholder="Tên hoặc tên thay thế…" value={query} onChange={event => setQuery(event.target.value)} /></label><label>Lọc theo nguồn<select aria-label="Lọc graph theo nguồn" value={sourceFilter} onChange={event => setSourceFilter(event.target.value)}><option value="">Tất cả nguồn đã xét</option>{result.sources.map(source => <option value={source.filename} key={source.filename}>{sourceName(source.filename)}</option>)}</select></label></div>
      <div className="knowledge-view-switch"><div role="group" aria-label="Cách xem mạng tri thức"><button type="button" className="button" aria-pressed={view === 'network'} onClick={() => setView('network')}><Icon name="graph" size={16} />Mạng</button><button type="button" className="button" aria-pressed={view === 'list'} onClick={() => setView('list')}><Icon name="list" size={16} />Danh sách</button></div><span>{nodes.length} khái niệm · {edges.length} quan hệ</span></div>
      {!matches.size && <p className="research-missing" role="status">Không tìm thấy khái niệm phù hợp.</p>}
      {view === 'network' ? <>
        <div className="knowledge-zoom"><button type="button" className="button" aria-label="Thu nhỏ mạng" onClick={() => zoom(1 / 1.2)}><Icon name="minus" size={15} /></button><button type="button" className="button" onClick={reset}>Vừa khung · {Math.round(camera.scale * 100)}%</button><button type="button" className="button" aria-label="Phóng to mạng" onClick={() => zoom(1.2)}><Icon name="plus" size={15} /></button></div>
        <div className="knowledge-canvas" ref={canvas} tabIndex={0} role="region" aria-label="Mạng khái niệm; dùng phím mũi tên để di chuyển, cộng/trừ để phóng thu, Home để đặt lại" onKeyDown={event => {
          if (event.target !== event.currentTarget) return
          if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '=', '-', 'Home'].includes(event.key)) event.preventDefault()
          if (event.key === '+' || event.key === '=') zoom(1.2)
          else if (event.key === '-') zoom(1 / 1.2)
          else if (event.key === 'Home') reset()
          else if (event.key.startsWith('Arrow')) setCamera(old => ({ ...old, x: old.x + (event.key === 'ArrowLeft' ? 35 : event.key === 'ArrowRight' ? -35 : 0), y: old.y + (event.key === 'ArrowUp' ? 35 : event.key === 'ArrowDown' ? -35 : 0) }))
        }} onPointerDown={event => { if ((event.target as Element).closest('[data-knowledge-item]')) return; const rect = event.currentTarget.getBoundingClientRect(); drag.current = { x: event.clientX, y: event.clientY, baseX: camera.x, baseY: camera.y, units: Math.max(bounds.width / rect.width, bounds.height / rect.height) }; event.currentTarget.setPointerCapture(event.pointerId) }} onPointerMove={event => { const active = drag.current; if (active) { const x = active.baseX + (event.clientX - active.x) * active.units, y = active.baseY + (event.clientY - active.y) * active.units; setCamera(old => ({ ...old, x, y })) } }} onPointerUp={() => { drag.current = null }} onPointerCancel={() => { drag.current = null }}>
          <svg viewBox={`${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}`} aria-label="Quan hệ giữa các khái niệm"><defs><marker id={marker} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 10 5 0 10Z" fill="currentColor" /></marker></defs>
            <g transform={`translate(${camera.x} ${camera.y}) translate(${bounds.cx} ${bounds.cy}) scale(${camera.scale}) translate(${-bounds.cx} ${-bounds.cy})`}>
              {edges.map(edge => { const a = points.get(edge.source)!, b = points.get(edge.target)!; const dx = b.x - a.x, dy = b.y - a.y, distance = Math.max(1, Math.hypot(dx, dy)); const x2 = b.x - dx / distance * 88, y2 = b.y - dy / distance * 38
                const parallel = edges.filter(item => [item.source, item.target].sort().join('|') === [edge.source, edge.target].sort().join('|'))
                const bend = (parallel.findIndex(item => item.id === edge.id) - (parallel.length - 1) / 2) * 60 * (edge.source < edge.target ? 1 : -1)
                const cx = (a.x + x2) / 2 - dy / distance * bend, cy = (a.y + y2) / 2 + dx / distance * bend
                const path = `M ${a.x} ${a.y} Q ${cx} ${cy} ${x2} ${y2}`
                return <g key={edge.id} data-knowledge-item="edge" role="button" tabIndex={0} aria-label={`${byId.get(edge.source)?.label} ${relationLabels[edge.relation]} ${byId.get(edge.target)?.label}`} className={`knowledge-edge ${chosenEdge?.id === edge.id ? 'active' : ''}`} onClick={() => setSelected({ kind: 'edge', id: edge.id })} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelected({ kind: 'edge', id: edge.id }) } }}><title>{edge.statement.text}</title><path d={path} className="knowledge-edge-hit" /><path d={path} markerEnd={`url(#${marker})`} />{(camera.scale >= .9 || chosenEdge?.id === edge.id) && <text x={a.x / 4 + cx / 2 + x2 / 4} y={a.y / 4 + cy / 2 + y2 / 4 - 7}>{relationLabels[edge.relation]}</text>}</g>
              })}
              {nodes.map(node => { const point = points.get(node.id)!; const active = chosenNode?.id === node.id; const lines = node.label.length > 23 ? [node.label.slice(0, 22), node.label.slice(22, 43) + (node.label.length > 43 ? '…' : '')] : [node.label]
                return <g data-knowledge-item="node" role="button" tabIndex={0} aria-label={`${node.label}: ${node.definition.text}`} aria-pressed={active} key={node.id} transform={`translate(${point.x} ${point.y})`} className={`knowledge-node ${active ? 'active' : ''} ${query && !matches.has(node.id) ? 'dimmed' : ''}`} onClick={() => setSelected({ kind: 'node', id: node.id })} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelected({ kind: 'node', id: node.id }) } }}><title>{[node.label, ...node.aliases].join(' · ')}</title><rect x={-85} y={-30} width={170} height={60} rx={16} />{lines.map((line, index) => <text key={index} textAnchor="middle" x={0} y={lines.length === 1 ? 5 : -3 + index * 18}>{line}</text>)}</g>
              })}
            </g>
          </svg>
        </div><details className="knowledge-keyboard-list"><summary>Chọn khái niệm bằng danh sách</summary>{nodeList()}</details>
      </> : <><div className="knowledge-list-tabs" role="group" aria-label="Danh sách mạng tri thức"><button type="button" className="button" aria-pressed={list === 'nodes'} onClick={() => setList('nodes')}>Khái niệm</button><button type="button" className="button" aria-pressed={list === 'edges'} onClick={() => setList('edges')}>Quan hệ</button></div>{list === 'nodes' ? nodeList() : <ul className="knowledge-items" aria-label="Danh sách quan hệ">{edges.filter(edge => !query || matches.has(edge.source) || matches.has(edge.target)).map(edge => <li key={edge.id}><button type="button" aria-pressed={chosenEdge?.id === edge.id} onClick={() => setSelected({ kind: 'edge', id: edge.id })}><strong>{byId.get(edge.source)?.label} → {byId.get(edge.target)?.label}</strong><span>{relationLabels[edge.relation]} · {edge.statement.text}</span></button></li>)}</ul>}</>}
      {sourceFilter && <p className="research-missing">Bộ lọc giới hạn khái niệm và quan hệ hiển thị. Chi tiết vẫn giữ đủ nguồn hỗ trợ nhận định.</p>}
      <section className="knowledge-detail" aria-label="Chi tiết bằng chứng" aria-live="polite">{statement?.evidence.length ? <><div className="research-section-heading"><h3>{label}</h3><button type="button" className="text-button" onClick={save}>Lưu vào ghi chú</button></div>{chosenEdge && <p className="research-label">{relationLabels[chosenEdge.relation]}</p>}{chosenNode && !!chosenNode.aliases.length && <p className="research-missing">Tên thay thế: {chosenNode.aliases.join(' · ')}</p>}<EvidenceStatement value={statement} result={result} sourceName={sourceName} onOpenCitation={onOpenCitation} /></> : <p className="research-missing">Chọn một khái niệm hoặc quan hệ để xem giải thích và trích đoạn hỗ trợ.</p>}</section>
      <details className="research-scope"><summary>Giới hạn và quan hệ chưa xác nhận</summary><ul className="research-limits">{result.limits.map((limit, index) => <li key={index}>{limit}</li>)}</ul><p>Quan hệ bị loại: {result.discarded_relations}</p>{result.source_notes.map(note => <p key={note.filename}>{sourceName(note.filename)}: {note.detail}</p>)}</details>
    </div>
  </ResultViewerModal>
}
