import type { MindMapNode } from '../../types/api'

export const NODE_WIDTH = 248
export const NODE_HEIGHT = 100
export const BRANCH_COLORS = ['#c99168', '#719fbc', '#8ead8c', '#b18db7', '#c0aa6b', '#6faeac', '#bd858c', '#9a9ec5']
export interface PositionedNode { id: string; node: MindMapNode; x: number; y: number; color: string }

export function layoutMindMap(root: MindMapNode, collapsed: Set<string>) {
  const nodes: PositionedNode[] = []
  const edges: { from: PositionedNode; to: PositionedNode }[] = []
  function visit(node: MindMapNode, id: string, depth: number, top: number, color: string): { item: PositionedNode; height: number } {
    const children = collapsed.has(id) ? [] : node.children
    let height = 0
    const placed = children.map((child, index) => {
      const result = visit(child, `${id}.${index}`, depth + 1, top + height, depth === 0 ? BRANCH_COLORS[index % BRANCH_COLORS.length] : color)
      height += result.height + 18
      return result.item
    })
    height = Math.max(NODE_HEIGHT, height - (children.length ? 18 : 0))
    const item = { id, node, x: 32 + depth * (NODE_WIDTH + 88), y: top + (height - NODE_HEIGHT) / 2, color }
    nodes.unshift(item)
    placed.forEach(child => edges.push({ from: item, to: child }))
    return { item, height }
  }
  const { height } = visit(root, 'root', 0, 32, BRANCH_COLORS[0])
  return { nodes, edges, width: Math.max(...nodes.map(node => node.x)) + NODE_WIDTH + 32, height: height + 64 }
}

export function countMindMapNodes(root: MindMapNode): number {
  return 1 + root.children.reduce((count, node) => count + countMindMapNodes(node), 0)
}

export function labelLines(label: string): string[] {
  const lines: string[] = []
  let current = ''
  for (const word of label.split(/\s+/)) {
    if ((current + ' ' + word).trim().length > 25 && current) { lines.push(current); current = word }
    else current = (current + ' ' + word).trim()
  }
  if (current) lines.push(current)
  return lines.slice(0, 3).map((line, index) => index === 2 && lines.length > 3 ? `${line.slice(0, 23)}…` : line.length > 25 ? `${line.slice(0, 24)}…` : line)
}
