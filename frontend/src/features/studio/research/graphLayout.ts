import type { GraphNode, GraphEdge } from '../../../types/research'
export interface GraphPoint { x: number; y: number }

// A bounded deterministic layout, independent of the Mind Map tree and model calls.
export function graphLayout(nodes: GraphNode[], edges: GraphEdge[]): Map<string, GraphPoint> {
  const points = nodes.map((_, index) => ({ x: 650 + 380 * Math.cos(index * Math.PI * 2 / Math.max(1, nodes.length)), y: 430 + 280 * Math.sin(index * Math.PI * 2 / Math.max(1, nodes.length)) }))
  const indices = new Map(nodes.map((node, index) => [node.id, index]))
  for (let step = 0; step < 160; step++) {
    const force = nodes.map(() => ({ x: 0, y: 0 }))
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const dx = points[i].x - points[j].x || .01, dy = points[i].y - points[j].y || .01
      const distance = Math.max(35, Math.hypot(dx, dy)), power = 16000 / distance ** 2
      force[i].x += dx / distance * power; force[i].y += dy / distance * power
      force[j].x -= dx / distance * power; force[j].y -= dy / distance * power
    }
    for (const edge of edges) {
      const i = indices.get(edge.source), j = indices.get(edge.target)
      if (i == null || j == null) continue
      const dx = points[j].x - points[i].x, dy = points[j].y - points[i].y, distance = Math.max(1, Math.hypot(dx, dy))
      const power = (distance - 210) * .008
      force[i].x += dx / distance * power; force[i].y += dy / distance * power
      force[j].x -= dx / distance * power; force[j].y -= dy / distance * power
    }
    const cooling = 1 - step / 200
    points.forEach((p, i) => { p.x = Math.max(100, Math.min(1200, p.x + Math.max(-7, Math.min(7, force[i].x)) * cooling)); p.y = Math.max(70, Math.min(790, p.y + Math.max(-7, Math.min(7, force[i].y)) * cooling)) })
  }
  return new Map(nodes.map((node, index) => [node.id, points[index]]))
}
export function searchConcept(value: string) { return value.toLocaleLowerCase().normalize('NFKD').replace(/\p{M}/gu, '').replaceAll('đ', 'd') }
