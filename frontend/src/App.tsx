import { useNotebook } from './useNotebook'
import { AppHeader } from './components/AppHeader'
import { SourcesPanel } from './features/sources/SourcesPanel'
import { ChatPanel } from './features/chat/ChatPanel'
import { StudioPanel } from './features/studio/StudioPanel'

function App() {
  const notebook = useNotebook()

  return (
    <div className="app-shell">
      <AppHeader />
      <main className="workspace">
        <SourcesPanel notebook={notebook} />
        <ChatPanel notebook={notebook} />
        <StudioPanel notebook={notebook} />
      </main>
    </div>
  )
}

export default App
