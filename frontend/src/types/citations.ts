import type { Citation } from './api'

export function citationsForMarkers(citations: Citation[], markers: string[]) {
  const normalized = markers.map(marker => marker.replace(/[[\]]/g, ''))
  return citations.filter(citation => normalized.includes(citation.source_marker))
}
