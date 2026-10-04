import { useState } from 'react'
import type { FlashcardsResponse } from '../../types/api'
import { CitationList } from '../../components/CitationList'
import { citationsForMarkers } from '../../types/citations'
import { ExportButton } from '../../components/ExportButton'
import { ResultViewerModal } from '../../components/ResultViewerModal'

export function FlashcardsView({ result, title, open, onClose }: { result: FlashcardsResponse; title: string; open: boolean; onClose: () => void }) {
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const card = result.cards[index]
  function move(next: number) { setIndex(next); setRevealed(false) }
  return <ResultViewerModal open={open} title="Flashcards" artifactTitle={title} onClose={onClose} pageKey={index} footer={<>
    {!!result.cards.length && <nav className="item-navigation" aria-label="Điều hướng flashcards">
      <button className="button subtle" type="button" disabled={index === 0} onClick={() => move(index - 1)}>Thẻ trước</button>
      <span className="page-indicator" aria-live="polite">{index + 1} / {result.cards.length}</span>
      <button className="button subtle" type="button" disabled={index >= result.cards.length - 1} onClick={() => move(index + 1)}>Thẻ tiếp theo</button>
    </nav>}
    <ExportButton feature="flashcards" result={result} />
  </>}>
    <article className="viewer-result" aria-label="Kết quả flashcards">
    {!card ? <p>Chưa tạo được thẻ từ nguồn này. Thử chọn nguồn hoặc chủ đề khác.</p> : <>
      <p className="item-counter">Thẻ {index + 1} / {result.cards.length}</p>
      <div className="flashcard-front"><h3>Câu hỏi</h3><p className="prose">{card.front}</p></div>
      {!revealed && <button className="button" type="button" onClick={() => setRevealed(true)}>Hiển thị đáp án</button>}
      {revealed && <div className="flashcard-back"><h3>Đáp án</h3><p className="prose">{card.back}</p>
        {card.hint && <p className="field-hint">Gợi ý: {card.hint}</p>}
        <CitationList citations={citationsForMarkers(result.citations, card.source_markers)} label="Nguồn tham chiếu" />
      </div>}
    </>}
    </article>
  </ResultViewerModal>
}
