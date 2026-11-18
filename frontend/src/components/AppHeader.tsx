import { APP_NAME } from '../brand'

export function AppHeader() {
  return <header className="app-header">
    <span className="notebook-symbol" aria-hidden="true">YN</span>
    <div><h1>{APP_NAME}</h1><p>Khám phá và học từ tài liệu của bạn</p></div>
  </header>
}
