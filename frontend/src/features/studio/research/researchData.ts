import { citationLocation } from '../../../types/citations'
import type { GroundedStatement, ResearchResult } from '../../../types/research'

export const researchTools = [
  { id: 'comparison', title: 'So sánh tài liệu', icon: 'compare' },
  { id: 'report', title: 'Tổng hợp / Báo cáo', icon: 'report' },
  { id: 'graph', title: 'Mạng tri thức', icon: 'graph' },
] as const

export function statementNote(title: string, statements: GroundedStatement[], result: ResearchResult, sourceName: (filename: string) => string) {
  const byMarker = new Map(result.citations.map(c => [c.source_marker, c]))
  return [title, `Mục tiêu: ${result.goal}`, ...statements.flatMap(statement => [statement.text, ...statement.evidence.map(ref => {
    const citation = byMarker.get(ref.source_marker)
    return `[${ref.source_marker}] ${citation ? `${sourceName(citation.filename)} · ${citationLocation(citation)} · phiên bản ${citation.document_version}` : ''}\n> ${ref.quote}`
  })])].join('\n\n')
}
