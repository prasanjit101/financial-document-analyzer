
import './App.css'
import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './lib/authStore'
import { AuthCard } from './components/AuthCard'
import { Home } from './components/Home'
import { Analysis } from './components/Analysis'

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

  if (!token || !user) return <AuthCard />

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/analysis/:jobId" element={<Analysis />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
