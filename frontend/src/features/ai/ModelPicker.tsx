import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { CSSProperties } from 'react'
import type { NotebookState } from '../../useNotebook'
import type { ModelChoice as CatalogModel } from './client'
import { Icon } from '../../components/Icon'
import { effortLabels } from './modelPreference'
import './models.css'

export function ModelPicker({ controls: c, onSettings, settingsDisabled }: {
  controls: NotebookState['modelControls']; onSettings: () => void; settingsDisabled: boolean
}) {
  const [open, setOpen] = useState(false)
  const [list, setList] = useState(false)
  const [search, setSearch] = useState('')
  const [position, setPosition] = useState({ left: 12, bottom: 12, width: 320, maxHeight: 400 })
  const trigger = useRef<HTMLButtonElement>(null)
  const panel = useRef<HTMLDivElement>(null)
  const id = useId()
  const choice = c.choice
  const profile = c.status?.profiles.find(item => item.id === choice?.connection_id)
  const choices: CatalogModel[] = choice?.provider === 'chatgpt' ? c.models
    : c.server?.configured ? [{ slug: c.server.model, display_name: c.server.model }] : []
  const selected = choices.find(item => item.slug === choice?.model)
  const levels = selected?.supported_reasoning_levels || []
  const effort = choice?.reasoning_effort ?? selected?.default_reasoning_level
  const sliderLevels = selected?.default_reasoning_level ? levels : [null, ...levels]
  const effortIndex = sliderLevels.indexOf(effort ?? null)
  const showList = list || !levels.length
  const label = c.loading ? 'Đang tải model…' : selected?.display_name || 'Chọn model'
  const hint = c.loading ? 'Đang tải danh sách model…' : c.error ? c.error
    : choice?.provider === 'chatgpt' && (!profile?.plan_enabled || profile.state !== 'connected') ? 'Mở Cài đặt để kết nối hoặc cấp lại quyền.'
      : !c.ready && choice?.model ? 'Lựa chọn cũ không còn khả dụng. Hãy chọn lại model.'
        : !choices.length ? 'Chưa có model khả dụng. Kiểm tra kết nối trong Cài đặt.' : ''

  function close(restore = false) { setOpen(false); if (restore) trigger.current?.focus() }
  useLayoutEffect(() => {
    if (!open) return
    function place() {
      const rect = trigger.current?.getBoundingClientRect()
      if (!rect) return
      const width = Math.min(336, window.innerWidth - 24)
      setPosition({ width, left: Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)),
        bottom: Math.max(12, window.innerHeight - rect.top + 8), maxHeight: Math.max(100, rect.top - 20) })
    }
    place()
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    return () => { window.removeEventListener('resize', place); window.removeEventListener('scroll', place, true) }
  }, [open])
  useEffect(() => {
    if (!open) return
    panel.current?.focus({ preventScroll: true })
    function outside(event: PointerEvent) {
      if (!panel.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) setOpen(false)
    }
    function keyboard(event: KeyboardEvent) {
      if (event.key === 'Escape') { event.preventDefault(); setOpen(false); trigger.current?.focus() }
    }
    function focus(event: FocusEvent) {
      if (!panel.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', keyboard)
    document.addEventListener('focusin', focus)
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', keyboard); document.removeEventListener('focusin', focus) }
  }, [open])

  return <div className="model-picker">
    <button ref={trigger} type="button" className="model-trigger" aria-label={`Chọn model: ${label}`}
      aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? id : undefined} title="Chọn model cho Chat và Studio"
      onClick={() => { setList(false); setSearch(''); setOpen(value => !value) }}>
      <Icon name="bolt" size={15} /><span>{label}</span>
      {c.ready && effort && <span className="model-trigger-effort">{effortLabels[effort]}</span>}
      {!c.loading && !c.ready && <span className="model-attention" aria-label="Cần chọn lại" />}
      <span className="model-chevron" aria-hidden="true">⌄</span>
    </button>
    {open && createPortal(<div id={id} ref={panel} tabIndex={-1} className="model-popover" role="dialog" aria-label="Chọn model và mức suy luận"
      style={{ position: 'fixed', ...position }}>
      <div className="model-popover-top"><span><Icon name="bolt" size={16} /><span className={showList ? undefined : 'sr-only'}>{showList ? 'Chọn model' : 'Mức suy luận'}</span></span>
        <button type="button" className="model-icon-action" aria-label={showList ? 'Làm mới danh sách model' : 'Đặt lại mức suy luận'} disabled={c.loading}
          onClick={() => { if (showList) c.refresh(); else if (choice) c.choose({ ...choice, reasoning_effort: null }) }}><Icon name="refresh" size={15} /></button>
      </div>
      {showList ? <>
        {choices.length > 5 && <input className="model-search" aria-label="Tìm model" placeholder="Tìm model…" value={search} onChange={event => setSearch(event.target.value)} />}
        <div className="model-options" role="group" aria-label="Model được cấp quyền">
          {choices.filter(item => item.display_name.toLocaleLowerCase().includes(search.toLocaleLowerCase()) || item.slug.toLowerCase().includes(search.toLowerCase())).map(item => <button
            type="button" className="model-option" key={item.slug} aria-pressed={item.slug === choice?.model} disabled={c.loading}
            onClick={() => {
              if (!choice) return
              c.choose({ ...choice, model: item.slug, reasoning_effort: item.slug === choice.model ? choice.reasoning_effort : null })
              if (item.supported_reasoning_levels?.length) { setList(false); setSearch('') } else close(true)
            }}><span>{item.display_name}<small>{item.slug}</small></span><span className="model-option-check" aria-hidden="true">{item.slug === choice?.model ? '✓' : ''}</span></button>)}
          {!c.loading && !!choices.length && !choices.some(item => (item.display_name + item.slug).toLocaleLowerCase().includes(search.toLocaleLowerCase())) && <p className="model-popover-note">Không tìm thấy model.</p>}
        </div>
      </> : <>
        <div className="model-effort-value">{effort ? effortLabels[effort] : 'Mặc định'}</div>
        <button className="model-current" type="button" onClick={() => setList(true)}>{label}<span aria-hidden="true">›</span></button>
        <div className="model-effort-control">
          <div className="model-slider-track" aria-hidden="true" style={{ '--effort-progress': `${effortIndex < 0 || sliderLevels.length < 2 ? 0 : effortIndex / (sliderLevels.length - 1) * 100}%` } as CSSProperties}>
            {sliderLevels.map(level => <i key={level || 'default'} />)}
          </div>
          <input type="range" min={0} max={Math.max(0, sliderLevels.length - 1)} step={1} value={Math.max(0, effortIndex)}
            aria-label="Mức suy luận" aria-valuetext={effort ? effortLabels[effort] : 'Mặc định của model'} disabled={sliderLevels.length < 2}
            onChange={event => { if (choice) c.choose({ ...choice, reasoning_effort: sliderLevels[Number(event.target.value)] }) }} />
        </div>
        <div className="model-effort-labels"><span>{sliderLevels[0] ? effortLabels[sliderLevels[0]] : 'Mặc định'}</span><span>{effortLabels[levels.at(-1)!]}</span></div>
        <p className="model-popover-note">Mức cao hơn cần thêm thời gian và hạn mức.</p>
      </>}
      {hint && <p className="model-popover-note model-picker-warning" role="status">{hint}</p>}
      <div className="model-popover-footer"><span>Áp dụng cho Chat và Studio</span><button type="button" aria-label="Mở cài đặt AI và hạn mức" disabled={settingsDisabled}
        onClick={() => { close(); onSettings() }} title={settingsDisabled ? 'Đợi hoặc dừng tác vụ trước khi mở Cài đặt' : 'Kết nối AI và hạn mức'}><Icon name="settings" size={17} /></button></div>
    </div>, document.body)}
  </div>
}
