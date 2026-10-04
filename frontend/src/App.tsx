import { useEffect, useState } from 'react'
import { checkBackendHealth } from './api/client'

function App() {
  const [backendStatus, setBackendStatus] = useState('checking...')

  useEffect(() => {
    const controller = new AbortController()

    checkBackendHealth(controller.signal)
      .then(() => setBackendStatus('connected'))
      .catch(() => {
        if (!controller.signal.aborted) setBackendStatus('unavailable')
      })

    return () => controller.abort()
  }, [])

  return (
    <main>
      <h1>Research Notebook</h1>
      <p>React frontend ready.</p>
      <p role="status">Backend status: {backendStatus}</p>
    </main>
  )
}

export default App
