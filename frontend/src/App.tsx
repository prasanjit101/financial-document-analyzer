
import './App.css'
import { useEffect } from 'react'
import { useAuthStore } from './lib/authStore'
import { AuthCard } from './components/AuthCard'
import { Home } from './components/Home'

function App() {
  const { token, user, hydrate, refreshMe } = useAuthStore()

  useEffect(() => {
    hydrate()
  }, [hydrate])

  useEffect(() => {
    if (token && !user) {
      void refreshMe()
    }
  }, [token, user, refreshMe])

  return !token || !user ? <AuthCard /> : <Home />
}

export default App
