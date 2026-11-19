import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const target = env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
  const url = new URL(target)
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) || url.protocol !== 'http:') {
    throw new Error('AI connection proxy requires a local HTTP backend.')
  }
  const proxy = { '/api/ai': { target, changeOrigin: true } }
  return {
    plugins: [react()],
    optimizeDeps: { include: ['pdfjs-dist'] },
    server: { proxy },
    preview: { proxy },
  }
})
