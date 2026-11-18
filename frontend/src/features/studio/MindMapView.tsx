import { useEffect, useMemo, useRef, useState } from 'react'
import type { Citation, MindMapResponse } from '../../types/api'
import { ResultViewerModal } from '../../components/ResultViewerModal'
import { CitationList } from '../../components/CitationList'
import { ExportButton } from '../../components/ExportButton'
import { Icon } from '../../components/Icon'
import { BRANCH_COLORS, countMindMapNodes, labelLines, layoutMindMap, NODE_HEIGHT, NODE_WIDTH } from './mindmapLayout'
import './mindmap.css'

type View = { x: number; y: number; scale: number }
const clampScale = (scale: number) => Math.max(.08, Math.min(3, scale))

export function MindMapView({ result, title, open, onClose, sourceName, onOpenCitation, onAsk }: {
  result: MindMapResponse; title: string; open: boolean; onClose: () => void
  sourceName: (filename: string) => string; onOpenCitation?: (citation: Citation) => void
  onAsk: (label: string, filenames: string[]) => void
}) {
  const [collapsed, setCollapsed] = useState<Set<string>>(() => countMindMapNodes(result.root) > 22
    ? new Set(result.root.children.map((_, index) => `root.${index}`)) : new Set())
  const [selectedId, setSelectedId] = useState('root')
  const [size, setSize] = useState({ width: 800, height: 500 })
  const [view, setView] = useState<View>({ x: 32, y: 32, scale: 1 })
  const viewport = useRef<HTMLDivElement>(null)
  const svg = useRef<SVGSVGElement>(null)
  const drag = useRef<{ x: number; y: number } | null>(null)
  const graph = useMemo(() => layoutMindMap(result.root, collapsed), [result.root, collapsed])
  const selected = graph.nodes.find(node => node.id === selectedId) || graph.nodes[0]
  const citations = result.citations.filter(citation => selected.node.source_markers.includes(citation.source_marker))
  const total = countMindMapNodes(result.root)

  function fitView(width = size.width, height = size.height): View {
    const scale = clampScale(Math.min((width - 24) / graph.width, (height - 24) / graph.height, 1.2))
    return { scale, x: (width - graph.width * scale) / 2, y: (height - graph.height * scale) / 2 }
  }
  useEffect(() => {
    if (!open || !viewport.current) return
    const observer = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect
      if (!width || !height) return
      setSize({ width, height })
      const scale = clampScale(Math.min((width - 24) / graph.width, (height - 24) / graph.height, 1.2))
      setView({ scale, x: (width - graph.width * scale) / 2, y: (height - graph.height * scale) / 2 })
    })
    observer.observe(viewport.current)
    return () => observer.disconnect()
  }, [open, graph.width, graph.height])
  useEffect(() => {
    if (!open || !viewport.current) return
    const element = viewport.current
    function wheel(event: WheelEvent) {
      event.preventDefault()
      const rect = element.getBoundingClientRect()
      const x = event.clientX - rect.left, y = event.clientY - rect.top
      setView(old => {
        const scale = clampScale(old.scale * Math.exp(-event.deltaY * .0015))
        return { scale, x: x - (x - old.x) * scale / old.scale, y: y - (y - old.y) * scale / old.scale }
      })
    }
    element.addEventListener('wheel', wheel, { passive: false })
    return () => element.removeEventListener('wheel', wheel)
  }, [open])
  function zoom(factor: number) {
    setView(old => {
      const scale = clampScale(old.scale * factor)
      return { scale, x: size.width / 2 - (size.width / 2 - old.x) * scale / old.scale, y: size.height / 2 - (size.height / 2 - old.y) * scale / old.scale }
    })
  }
  function toggle(id: string) {
    setSelectedId(id)
    setCollapsed(old => {
      const next = new Set(old)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }
  function downloadSvg() {
    if (!svg.current) return
    const clone = svg.current.cloneNode(true) as SVGSVGElement
    const originals = [svg.current, ...svg.current.querySelectorAll('*')]
    const copies = [clone, ...clone.querySelectorAll('*')]
    originals.forEach((element, index) => {
      const style = getComputedStyle(element)
      for (const property of ['fill', 'stroke', 'stroke-width', 'font-size', 'font-family', 'font-weight', 'opacity']) {
        (copies[index] as SVGElement).style.setProperty(property, style.getPropertyValue(property))
      }
    })
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
    clone.setAttribute('viewBox', `0 0 ${graph.width} ${graph.height}`)
    clone.setAttribute('width', String(graph.width)); clone.setAttribute('height', String(graph.height))
    clone.querySelector('.mindmap-transform')?.removeAttribute('transform')
    clone.style.background = getComputedStyle(viewport.current!).backgroundColor
    const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml;charset=utf-8' }))
    const link = document.createElement('a'); link.href = url; link.download = 'so-do-tu-duy.svg'
    document.body.appendChild(link); link.click(); link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return <ResultViewerModal open={open} title="Sơ đồ tư duy" artifactTitle={title} onClose={onClose} footer={<>
    <span className="mindmap-count">{graph.nodes.length}/{total} ý · {result.citations.length} trích dẫn</span>
    <div className="mindmap-export"><button type="button" className="button subtle" onClick={downloadSvg}><Icon name="download" size={15} />Tải SVG</button><ExportButton feature="mindmap" result={result} /></div>
  </>}>
    <div className="mindmap-view">
      <div className="mindmap-toolbar" role="group" aria-label="Điều khiển sơ đồ">
        <button type="button" className="icon-button" aria-label="Thu nhỏ sơ đồ" onClick={() => zoom(1 / 1.25)}><Icon name="minus" size={17} /></button>
        <span className="mindmap-scale" aria-live="polite">{Math.round(view.scale * 100)}%</span>
        <button type="button" className="icon-button" aria-label="Phóng to sơ đồ" onClick={() => zoom(1.25)}><Icon name="plus" size={17} /></button>
        <button type="button" className="button subtle" onClick={() => setView(fitView())}><Icon name="expand" size={15} />Vừa màn hình</button>
        <button type="button" className="button subtle mindmap-expand-all" onClick={() => setCollapsed(new Set())}>Mở tất cả</button>
      </div>
      <div className="mindmap-content">
        <div ref={viewport} className="mindmap-canvas" aria-label="Vùng sơ đồ tư duy">
          <svg ref={svg} width="100%" height="100%" viewBox={`0 0 ${size.width} ${size.height}`} role="group" aria-label={`Sơ đồ: ${result.root.label}`} tabIndex={0}
            onPointerDown={event => {
              if ((event.target as Element).closest('[data-mindmap-node]') || event.button !== 0) return
              drag.current = { x: event.clientX, y: event.clientY }; event.currentTarget.setPointerCapture(event.pointerId)
            }} onPointerMove={event => {
              if (!drag.current) return
              const dx = event.clientX - drag.current.x, dy = event.clientY - drag.current.y
              drag.current = { x: event.clientX, y: event.clientY }
              setView(old => ({ ...old, x: old.x + dx, y: old.y + dy }))
            }} onPointerUp={() => { drag.current = null }} onPointerCancel={() => { drag.current = null }}
            onKeyDown={event => {
              if (event.target !== event.currentTarget) return
              const movement: Record<string, [number, number]> = { ArrowLeft: [40, 0], ArrowRight: [-40, 0], ArrowUp: [0, 40], ArrowDown: [0, -40] }
              if (movement[event.key]) { event.preventDefault(); const [dx, dy] = movement[event.key]; setView(old => ({ ...old, x: old.x + dx, y: old.y + dy })) }
              if (event.key === '+' || event.key === '=') { event.preventDefault(); zoom(1.25) }
              if (event.key === '-') { event.preventDefault(); zoom(1 / 1.25) }
              if (event.key === 'Home') { event.preventDefault(); setView(fitView()) }
            }}>
            <g className="mindmap-transform" transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>
              {graph.edges.map(({ from, to }) => <path key={to.id} className="mindmap-edge" fill="none" stroke={to.color} strokeWidth="2" opacity=".65" d={`M${from.x + NODE_WIDTH},${from.y + NODE_HEIGHT / 2} C${from.x + NODE_WIDTH + 44},${from.y + NODE_HEIGHT / 2} ${to.x - 44},${to.y + NODE_HEIGHT / 2} ${to.x},${to.y + NODE_HEIGHT / 2}`} />)}
              {graph.nodes.map(item => <g key={item.id} data-mindmap-node={item.id} transform={`translate(${item.x} ${item.y})`}>
                <g role="button" tabIndex={open ? 0 : -1} aria-label={`Ý: ${item.node.label}`} aria-pressed={selected.id === item.id} className={`mindmap-node ${selected.id === item.id ? 'selected' : ''}`} onClick={() => setSelectedId(item.id)}
                  onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedId(item.id) } }}>
                  <title>{item.node.label}</title>
                  <rect className="mindmap-node-bg" width={NODE_WIDTH} height={NODE_HEIGHT} rx="13" stroke={item.color} strokeWidth={selected.id === item.id ? 2.5 : 1.2} />
                  <rect x="0" y="22" width="3" height="44" rx="1.5" fill={item.color} />
                  <text className="mindmap-node-label" x="15" y="22">{labelLines(item.node.label).map((line, index) => <tspan key={index} x="15" dy={index ? 17 : 0}>{line}</tspan>)}</text>
                  <text className="mindmap-node-source" x="15" y="71">{item.node.source_markers.slice(0, 4).join(' · ')}{item.node.source_markers.length > 4 ? ' …' : ''}</text>
                </g>
                {!!item.node.children.length && <g className="mindmap-collapse" role="button" tabIndex={open ? 0 : -1} aria-label={`${collapsed.has(item.id) ? 'Mở rộng' : 'Thu gọn'} nhánh ${item.node.label}`} aria-expanded={!collapsed.has(item.id)} onClick={() => toggle(item.id)}
                  onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); toggle(item.id) } }}>
                  <circle cx={NODE_WIDTH} cy={NODE_HEIGHT / 2} r="12" stroke={item.color} strokeWidth="1.3" />
                  <text x={NODE_WIDTH} y={NODE_HEIGHT / 2 + 4} textAnchor="middle">{collapsed.has(item.id) ? '+' : '−'}</text>
                </g>}
              </g>)}
            </g>
          </svg>
        </div>
        <aside className="mindmap-detail" aria-label="Chi tiết ý đã chọn">
          <span className="mindmap-detail-marker" style={{ background: selected.color || BRANCH_COLORS[0] }} />
          <h3>{selected.node.label}</h3>
          {selected.node.description && <p className="prose">{selected.node.description}</p>}
          <button type="button" className="button" onClick={() => onAsk(selected.node.label, [...new Set(citations.map(citation => citation.filename))])}><Icon name="chat" size={16} />Hỏi về ý này</button>
          <CitationList key={selected.id} citations={citations} collapsed={false} label="Trích dẫn" sourceName={sourceName} onOpenCitation={onOpenCitation} />
        </aside>
      </div>
    </div>
  </ResultViewerModal>
}
