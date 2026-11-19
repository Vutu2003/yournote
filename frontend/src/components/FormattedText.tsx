import type { ReactNode } from 'react'

function inline(text: string, onSource?: (marker: string) => void): ReactNode[] {
  const parts: ReactNode[] = []
  const pattern = /\*\*([^*\n]+)\*\*|`([^`\n]+)`|(\[S\d+(?:,\s*S\d+)*\])/g
  let position = 0
  for (const match of text.matchAll(pattern)) {
    if (match.index > position) parts.push(text.slice(position, match.index))
    parts.push(match[1] ? <strong key={match.index}>{match[1]}</strong> : match[2] ? <code key={match.index}>{match[2]}</code> : onSource ? <span key={match.index}>{match[3].match(/S\d+/g)!.map(marker => <button type="button" className="inline-citation" key={marker} title={`Mở nguồn ${marker} trong tài liệu`} onClick={() => onSource(marker)}>[{marker}]</button>)}</span> : <span className="inline-citation" key={match.index}>{match[3]}</span>)
    position = match.index + match[0].length
  }
  if (position < text.length) parts.push(text.slice(position))
  return parts
}

// Render only basic text formatting. Source/model text never becomes HTML.
export function FormattedText({ text, onSource }: { text: string; onSource?: (marker: string) => void }) {
  const blocks: ReactNode[] = []
  const lines = text.split('\n').map(line => line.trimEnd())
  for (let index = 0; index < lines.length;) {
    const line = lines[index].trim()
    if (!line) { index++; continue }
    const heading = line.match(/^#{1,4}\s+(.+)$/)
    if (heading) { blocks.push(<h3 key={index}>{inline(heading[1], onSource)}</h3>); index++; continue }
    if (/^(?:[-*]|\d+[.)])\s+/.test(line)) {
      const start = index
      const ordered = /^\d/.test(line)
      const items: ReactNode[] = []
      while (index < lines.length && (ordered ? /^\s*\d+[.)]\s+/ : /^\s*[-*]\s+/).test(lines[index])) {
        items.push(<li key={index}>{inline(lines[index].replace(/^\s*(?:[-*]|\d+[.)])\s+/, ''), onSource)}</li>)
        index++
      }
      blocks.push(ordered ? <ol key={start}>{items}</ol> : <ul key={start}>{items}</ul>)
      continue
    }
    const start = index
    const paragraph: string[] = []
    while (index < lines.length && lines[index].trim() && !/^\s*(?:#{1,4}\s|[-*]\s|\d+[.)]\s)/.test(lines[index])) paragraph.push(lines[index++])
    blocks.push(<p key={start}>{inline(paragraph.join('\n'), onSource)}</p>)
  }
  return <div className="formatted-text">{blocks}</div>
}
