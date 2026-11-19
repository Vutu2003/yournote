import { useCallback, useEffect, useState } from 'react'
import { ErrorMessage } from '../../components/Status'
import {
  acknowledgePlan, cancelSignIn, checkConnection, connectionError, getAIStatus, getModels,
  logoutConnection, openAISession, selectConnection, startSignIn,
} from './client'
import type { AIStatus, ModelChoice } from './client'
import './connections.css'
import { useModelChoice } from './useModelChoice'
import { Icon } from '../../components/Icon'

export function AIConnections() {
  const controls = useModelChoice()
  const [status, setStatus] = useState<AIStatus | null>(null)
  const [models, setModels] = useState<ModelChoice[]>([])
  const [model, setModel] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [launch, setLaunch] = useState('')
  const profile = status?.profiles.find(item => item.id === status.active_connection_id)
    || (status?.profiles.length === 1 ? status.profiles[0] : undefined)
  const profileId = profile?.id
  const enabled = profile?.plan_enabled
  const pendingId = status?.pending?.id
  const refresh = useCallback(async () => { setStatus(await getAIStatus()) }, [])

  useEffect(() => {
    let live = true
    void openAISession().then(getAIStatus).then(value => { if (live) setStatus(value) })
      .catch(reason => { if (live) setError(reason instanceof Error ? reason.message : 'Không thể tải kết nối AI.') })
    return () => { live = false }
  }, [])
  useEffect(() => {
    if (!pendingId) return
    const timer = window.setInterval(() => { void refresh().catch(reason => setError(reason.message)) }, 1500)
    return () => window.clearInterval(timer)
  }, [pendingId, refresh])
  useEffect(() => {
    let live = true
    if (!profileId || !enabled || pendingId) return
    void getModels(profileId).then(value => { if (live) { setModels(value.models); setModel('') } })
      .catch(reason => { if (live) setError(reason.message) })
    return () => { live = false }
  }, [profileId, enabled, pendingId])

  async function act(name: string, action: () => Promise<void>) {
    if (busy) return
    setBusy(name); setError(''); setNotice('')
    try { await action() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Không thể xử lý kết nối.') }
    finally { setBusy(''); window.dispatchEvent(new Event('yournote-ai-connections-changed')) }
  }
  async function signIn(id: string | null, consent = false) {
    const popup = window.open('about:blank', '_blank')
    if (popup) popup.opener = null
    await act('signin', async () => {
      try {
        const result = await startSignIn(id, consent)
        // Only a same-origin launch ticket may be navigated to; never a returned arbitrary URL.
        if (!result.launch_path.startsWith('/api/ai/chatgpt/sign-in/launch?ticket=')) throw new Error('Đường dẫn đăng nhập không hợp lệ.')
        if (popup) popup.location.href = result.launch_path
        else setLaunch(result.launch_path)
        await refresh()
      } catch (reason) { popup?.close(); throw reason }
    })
  }

  return <section className="ai-connections" aria-labelledby="ai-connections-title" aria-busy={Boolean(busy)}>
    <div className="ai-section-heading"><h3 id="ai-connections-title">Kết nối AI</h3></div>
    <div className="ai-service-card">
      <label className="ai-field">Dịch vụ dùng cho Chat và Studio
        <select aria-label="Dịch vụ AI" value={controls.choice?.provider || ''} disabled={controls.loading || Boolean(busy)} onChange={event => {
          const provider = event.target.value as 'gemini' | 'chatgpt'
          controls.choose(provider === 'gemini'
            ? { provider, model: controls.server?.model || '', connection_id: null }
            : { provider, model: '', connection_id: profileId || null })
        }}>
          <option value="" disabled>Chọn dịch vụ…</option><option value="gemini">API máy chủ</option><option value="chatgpt">Gói ChatGPT</option>
        </select>
      </label>
      <p>Chọn dịch vụ và tài khoản tại đây. Đổi model ngay trong ô trò chuyện; lựa chọn áp dụng cả cho Studio.</p>
    </div>
    <div className="ai-section-heading"><h4>Tài khoản ChatGPT</h4><span className="ai-provider-label">ChatGPT</span></div>
    <p>Kết nối tài khoản và cấp quyền để kiểm tra việc sử dụng gói ChatGPT hiện có. Hạn mức được dùng chung với các ứng dụng được hỗ trợ.</p>
    {!status && !error && <p role="status">Đang tải kết nối…</p>}
    {status && <>
      <p className="ai-storage-note">{status.storage_mode === 'keyring'
        ? 'Phiên được bảo vệ bằng keyring của hệ điều hành.'
        : 'Máy chưa có keyring khả dụng. Phiên chỉ giữ trong RAM và sẽ mất khi backend dừng; không lưu token vào file.'}</p>
      {status.profiles.length > 0 && <label className="ai-field">Tài khoản / đăng ký đã lưu
        <select value={profileId || ''} disabled={Boolean(busy) || Boolean(status.pending)} onChange={event => {
          const id = event.target.value
          setModels([]); setModel('')
          void act('select', async () => { setStatus(await selectConnection(id)); if (controls.choice?.provider === 'chatgpt' && controls.choice.connection_id !== id) controls.choose({ provider: 'chatgpt', model: '', connection_id: id }) })
        }}>
          {!profileId && <option value="">Chọn kết nối…</option>}
          {status.profiles.map(item => <option key={item.id} value={item.id}>{item.label} · {item.id.slice(0, 6)}</option>)}
        </select>
      </label>}
      {profile && <div className="ai-connection-state" role="status">
        <strong>{profile.state === 'connected' ? 'Đã kết nối · Có quyền dùng gói'
          : profile.state === 'permission_required' ? 'Đã đăng nhập · Chưa có quyền dùng gói' : 'Cần kết nối lại'}</strong>
        {controls.choice?.provider === 'chatgpt' && controls.choice.connection_id !== profile.id && <button type="button" className="button" onClick={() => controls.choose({ provider: 'chatgpt', model: '', connection_id: profile.id })}>Dùng tài khoản này</button>}
        <span>Đăng nhập, tải danh sách model và hoàn tất yêu cầu AI là ba bước xác minh riêng.</span>
      </div>}
      {profile?.welcome_pending && <div className="ai-welcome" role="status">
        <strong>Bạn đang sử dụng gói ChatGPT</strong>
        <p>Các yêu cầu AI đủ điều kiện sẽ dùng hạn mức của gói. Bạn có thể quản lý quyền và hạn mức trong Cài đặt ChatGPT.</p>
        <button type="button" className="button" disabled={Boolean(busy)} onClick={() => void act('notice', async () => { setStatus(await acknowledgePlan(profile.id)) })}>Tôi đã hiểu</button>
      </div>}
      {status.pending ? <div className="ai-pending" role="status">
        <strong>{status.pending.state === 'exchanging' ? 'Đang xác minh đăng nhập…' : 'Đang chờ bạn đăng nhập trong tab mới…'}</strong>
        <p>Hãy đăng nhập và xem xét quyền được yêu cầu. Phiên chờ tự hết hạn sau 5 phút.</p>
        {launch && <a className="button" href={launch} target="_blank" rel="noopener noreferrer">Mở trang đăng nhập</a>}
        <button type="button" className="button" disabled={Boolean(busy)} onClick={() => void act('cancel', async () => { setStatus(await cancelSignIn()); setLaunch('') })}>Hủy đăng nhập</button>
      </div> : <div className="ai-actions">
        <button type="button" className="button chatgpt-signin" data-oai-siwc-button disabled={Boolean(busy)} onClick={() => void signIn(profileId || null)}>Continue with ChatGPT</button>
        {profile && <button type="button" className="button" disabled={Boolean(busy)} onClick={() => void signIn(null)}>Thêm tài khoản</button>}
        {profile?.state === 'permission_required' && <button type="button" className="button" disabled={Boolean(busy)} onClick={() => void signIn(profile.id, true)}>Cấp quyền dùng gói</button>}
      </div>}
      {profile?.plan_enabled && <div className="ai-check">
        <label className="ai-field">Model dùng cho phép kiểm tra
          <select value={model} disabled={Boolean(busy)} onChange={event => setModel(event.target.value)}>
            <option value="">Chọn model được cấp quyền…</option>
            {models.map(item => <option key={item.slug} value={item.slug}>{item.display_name}</option>)}
          </select>
        </label>
        <p>Kiểm tra gửi một yêu cầu AI ngắn và tiêu thụ hạn mức của gói. Chỉ chạy khi bạn bấm nút bên dưới.</p>
        <div className="ai-actions">
          <button type="button" className="button" disabled={Boolean(busy)} onClick={() => void act('models', async () => {
            const result = await getModels(profile.id); setModels(result.models); setModel(''); await refresh()
          })}>Làm mới model</button>
          <button type="button" className="button primary" disabled={!model || Boolean(busy) || Boolean(status.pending)} onClick={() => void act('check', async () => {
            await checkConnection(profile.id, model); await refresh(); setNotice('Yêu cầu AI ngắn đã hoàn tất. Kết nối inference đã được xác minh.')
          })}>{busy === 'check' ? 'Đang kiểm tra…' : 'Kiểm tra kết nối'}</button>
        </div>
        {profile.last_check && <p className="ai-check-success">Lần hoàn tất gần nhất: {new Date(profile.last_check.checked_at * 1000).toLocaleString('vi-VN')} · {profile.last_check.actual_model || profile.last_check.model}</p>}
      </div>}
      {profile && <button type="button" className="text-button ai-signout" disabled={Boolean(busy) || Boolean(status.pending)} onClick={() => void act('logout', async () => {
        const result = await logoutConnection(profile.id)
        setModels([]); setModel(''); await refresh()
        setNotice(result.remote_revocation_confirmed ? 'Đã đăng xuất cục bộ và xác nhận thu hồi phiên phía ChatGPT.'
          : 'Đã đăng xuất cục bộ. Chưa xác nhận được thu hồi phiên phía ChatGPT; bạn có thể ngắt kết nối trong Cài đặt ChatGPT.')
        if (!result.keyring_cleanup_confirmed) setError('Chưa xác nhận xóa bản ghi trong keyring. Kết nối này đã bị vô hiệu hóa trong YourNote.')
      })}>{busy === 'logout' ? 'Đang đăng xuất…' : 'Đăng xuất kết nối này'}</button>}
      <div className="ai-usage-card" aria-labelledby="ai-usage-title">
        <div className="ai-usage-icon"><Icon name="clock" size={22} /></div>
        <div><h4 id="ai-usage-title">Hạn mức sử dụng</h4>
          <p>Hạn mức gói được dùng chung với ChatGPT và các ứng dụng được hỗ trợ. Xem mức sử dụng và thời điểm đặt lại trong tài khoản ChatGPT.</p>
          <a className="button" href="https://chatgpt.com/settings/usage" target="_blank" rel="noopener noreferrer">Xem hạn mức ChatGPT <span aria-hidden="true">↗</span></a>
          <p className="ai-usage-caption">Mở trang chính thức · YourNote chưa đồng bộ số liệu hạn mức.</p>
        </div>
      </div>
      <div className="ai-links"><a href="https://chatgpt.com/settings" target="_blank" rel="noopener noreferrer">Quản lý quyền kết nối trong ChatGPT ↗</a></div>
      {status.error && <ErrorMessage message={connectionError(status.error)} />}
    </>}
    {busy && <p role="status">Đang xử lý…</p>}
    {notice && <p className="ai-notice" role="status">{notice}</p>}
    <ErrorMessage message={error} />
  </section>
}
