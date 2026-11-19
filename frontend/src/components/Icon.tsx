import type { CSSProperties } from 'react'
import { APP_NAME } from '../brand'

const paths = {
  compare: <><rect x="2" y="4" width="8" height="16" rx="2" /><rect x="14" y="4" width="8" height="16" rx="2" /><path d="M5 9h2M5 13h2M17 9h2M17 13h2" /></>,
  report: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8ZM14 2v6h6M8 12h8M8 16h8M8 19h4" /></>,
  graph: <><circle cx="5" cy="6" r="3" /><circle cx="19" cy="7" r="3" /><circle cx="12" cy="19" r="3" /><path d="m8 6 8 1M7 9l4 7M17 10l-4 6" /></>,
  mindmap: <><rect x="2" y="9" width="6" height="6" rx="1.5" /><rect x="16" y="2" width="6" height="5" rx="1.5" /><rect x="16" y="9.5" width="6" height="5" rx="1.5" /><rect x="16" y="17" width="6" height="5" rx="1.5" /><path d="M8 12h4m0-7.5v15M12 4.5h4M12 12h4m-4 7.5h4" /></>,
  settings: <><path d="m9.5 3-.6 2.2-1.6.9-2.2-.6-2.5 4.3 1.6 1.6v1.8l-1.6 1.6 2.5 4.3 2.2-.6 1.6.9.6 2.2h5l.6-2.2 1.6-.9 2.2.6 2.5-4.3-1.6-1.6v-1.8l1.6-1.6-2.5-4.3-2.2.6-1.6-.9-.6-2.2Z" /><circle cx="12" cy="12" r="3" /></>,
  copy: <><rect x="8" y="8" width="12" height="13" rx="2" /><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3" /></>,
  download: <><path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4" /></>,
  minus: <path d="M5 12h14" />,
  expand: <><path d="M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5" /></>,
  book: <><path d="M12 5c-3-2-6-2-10-1v15c4-1 7-1 10 1 3-2 6-2 10-1V4c-4-1-7-1-10 1ZM12 5v15" /><path d="M5 8h3M5 12h3M16 8h3M16 12h3" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M5 19l1.5-1.5M17.5 6.5 19 5" /></>,
  moon: <path d="M20.5 13A8.5 8.5 0 0 1 11 3.5 8.5 8.5 0 1 0 20.5 13Z" />,
  bolt: <path d="m13 2-9 12h7l-1 8 10-13h-7l1-7Z" />,
  arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,
  send: <path d="m5 12 7-7 7 7M12 5v15" />,
  summary: <><rect x="4" y="3" width="16" height="18" rx="3" /><path d="M8 8h8M8 12h8M8 16h4" /></>,
  quiz: <><rect x="4" y="3" width="16" height="18" rx="3" /><path d="M10 9a2 2 0 1 1 3 1.7c-1 .5-1 1-1 2.3M12 17h.01" /></>,
  cards: <><rect x="7" y="7" width="13" height="14" rx="2" /><path d="M16 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h2M11 12h5M11 16h3" /></>,
  panelLeft: <><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M9 4v16M6 8v8" /></>,
  panelRight: <><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M15 4v16M18 8v8" /></>,
  upload: <><path d="M12 16V3m-5 5 5-5 5 5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4" /></>,
  refresh: <><path d="M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 13 2M5 16a8 8 0 0 0 13 2" /></>,
  notebook: <><path d="M5 3h13a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" /><path d="M8 3v18M11 8h5M11 12h5" /></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
  list: <><path d="M8 6h13M8 12h13M8 18h13" /><path d="M3 6h.01M3 12h.01M3 18h.01" /></>,
  more: <><circle cx="12" cy="5" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="12" cy="19" r="1" /></>,
  back: <path d="m12 5-7 7 7 7M5 12h15" />,
  chevron: <path d="m9 5 7 7-7 7" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  edit: <><path d="m14 5 5 5M4 20l5-1L20 8a2.1 2.1 0 0 0-5-5L4 14Z" /></>,
  trash: <><path d="M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7" /></>,
  chat: <path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2V11.5a9.5 9.5 0 0 1 19 0Z" />,
  source: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8ZM14 2v6h6M8 13h8M8 17h5" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
} as const

export function Icon({ name, size = 20, style }: { name: keyof typeof paths; size?: number; style?: CSSProperties }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}>{paths[name]}</svg>
}

export function Brand() {
  return <span className="brand"><span className="brand-mark"><svg width="28" height="28" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M16 8C12.5 5.8 7.7 5 3 6v20c4.7-1 9.5-.2 13 2 3.5-2.2 8.3-3 13-2V6c-4.7-1-9.5-.2-13 2Z" />
    <path d="M16 8v20M7 11c2-.1 3.6.3 5 1M7 16c2-.1 3.6.3 5 1M20 12c1.4-.7 3-1.1 5-1M20 17c1.4-.7 3-1.1 5-1" />
  </svg></span><span className="brand-wordmark">{APP_NAME}</span></span>
}
