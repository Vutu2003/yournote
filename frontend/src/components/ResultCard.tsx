import { useCallback, useEffect, useState } from 'react'
import type { ExportFeature, ExportResults } from '../types/api'
import { ExportButton } from './ExportButton'
import { Icon } from './Icon'
import { ResultViewerModal } from './ResultViewerModal'
import { GenerationInfo } from './GenerationInfo'

const timeFormat = new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Ho_Chi_Minh' })

export function ResultCard<F extends ExportFeature>({ id, title, topic, createdAt, sourceFilenames, metadata, action, onOpen, onDelete, feature, result }: {
  id: string; title: string; topic: string | null; createdAt: number; sourceFilenames: string[]
  metadata: string; action: string; onOpen: () => void; onDelete: () => void; feature: F; result: ExportResults[F]
}) {
  const [fresh, setFresh] = useState(true)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const closeDelete = useCallback(() => setConfirmingDelete(false), [])
  useEffect(() => {
    const timer = window.setTimeout(() => setFresh(false), 800)
    return () => window.clearTimeout(timer)
  }, [])
  return <article className={`result-card${fresh ? ' result-complete' : ''}`} aria-label={title} data-artifact-id={id}>
    <div className="result-card-heading"><span className="result-check" aria-hidden="true">✓</span><h3 title={title}>{title}</h3>
      <button type="button" className="icon-button result-card-delete" aria-label={`Xóa nội dung ${title}`} title="Xóa nội dung" onClick={() => setConfirmingDelete(true)}><Icon name="trash" size={16} /></button>
    </div>
    <div className="result-card-context">
      <span title={sourceFilenames.join('\n')}>{sourceFilenames.length} tài liệu</span>
      <time dateTime={new Date(createdAt).toISOString()} title={new Date(createdAt).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })}>{timeFormat.format(createdAt)}</time>
    </div>
    {topic && <p className="result-card-topic" title={topic}>Chủ đề: {topic}</p>}
    <p className="result-card-metadata">{metadata}</p>
    <GenerationInfo value={result.generation} />
    <div className="result-card-actions">
      <button className="button" type="button" onClick={onOpen}>{action}</button>
      <ExportButton feature={feature} result={result} />
    </div>
    {confirmingDelete && <ResultViewerModal open title="Xóa nội dung đã tạo?" artifactTitle={title} onClose={closeDelete} footer={<>
      <button type="button" className="button" onClick={closeDelete}>Hủy</button>
      <button type="button" className="button danger" onClick={onDelete}><Icon name="trash" size={16} />Xóa nội dung</button>
    </>}>
      <p className="prose">Nội dung này sẽ được xóa khỏi Studio của sổ tay. Các tài liệu nguồn vẫn được giữ nguyên.</p>
    </ResultViewerModal>}
  </article>
}
