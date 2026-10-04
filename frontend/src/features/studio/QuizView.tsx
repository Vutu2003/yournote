import { useId, useState } from 'react'
import type { QuizResponse } from '../../types/api'
import { CitationList } from '../../components/CitationList'
import { citationsForMarkers } from '../../types/citations'
import { ExportButton } from '../../components/ExportButton'
import { ResultViewerModal } from '../../components/ResultViewerModal'

export function QuizView({ result, title, open, onClose }: { result: QuizResponse; title: string; open: boolean; onClose: () => void }) {
  const answerGroup = useId()
  const [index, setIndex] = useState(0)
  const [option, setOption] = useState<number | null>(null)
  const [checked, setChecked] = useState(false)
  const item = result.items[index]
  function move(next: number) { setIndex(next); setOption(null); setChecked(false) }
  return <ResultViewerModal open={open} title="Quiz" artifactTitle={title} onClose={onClose} pageKey={index} footer={<>
    {!!result.items.length && <nav className="item-navigation" aria-label="Điều hướng quiz">
      <button className="button subtle" type="button" disabled={index === 0} onClick={() => move(index - 1)}>Câu trước</button>
      <span className="page-indicator" aria-live="polite">{index + 1} / {result.items.length}</span>
      <button className="button subtle" type="button" disabled={index >= result.items.length - 1} onClick={() => move(index + 1)}>Câu tiếp theo</button>
    </nav>}
    <ExportButton feature="quiz" result={result} />
  </>}>
    <article className="viewer-result" aria-label="Kết quả quiz">
    {!item ? <p>Chưa tạo được câu hỏi từ nguồn này. Thử chọn nguồn hoặc chủ đề khác.</p> : <>
      <p className="item-counter">Câu {index + 1} / {result.items.length}</p>
      <fieldset className="quiz-options" disabled={checked}>
        <legend>{item.question}</legend>
        {item.options.map((text, optionIndex) => <label className={`quiz-option ${option === optionIndex ? 'selected' : ''}`} key={optionIndex}>
          <input type="radio" name={answerGroup} value={optionIndex} checked={option === optionIndex} onChange={() => setOption(optionIndex)} />
          <span>{text}</span>
        </label>)}
      </fieldset>
      <button className="button" type="button" disabled={option === null || checked} onClick={() => setChecked(true)}>Kiểm tra đáp án</button>
      {checked && <div className="quiz-feedback" role="status">
        <p className={option === item.correct_index ? 'success-message' : 'incorrect-message'}>{option === item.correct_index ? 'Chính xác!' : 'Chưa chính xác.'}</p>
        <p><strong>Đáp án đúng:</strong> {item.options[item.correct_index]}</p>
        <p className="prose">{item.explanation}</p>
        <CitationList citations={citationsForMarkers(result.citations, item.source_markers)} label="Nguồn tham chiếu" />
      </div>}
    </>}
    </article>
  </ResultViewerModal>
}
