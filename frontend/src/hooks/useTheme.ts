import { useEffect, useState } from 'react'

export function useTheme() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => document.documentElement.dataset.theme === 'light' ? 'light' : 'dark')
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'light' ? '#f4f4f8' : '#09090d')
    try { localStorage.setItem('research-notebook-theme', theme) } catch { /* The current tab still supports theme switching. */ }
  }, [theme])
  return { theme, toggleTheme: () => setTheme(old => old === 'dark' ? 'light' : 'dark') }
}
