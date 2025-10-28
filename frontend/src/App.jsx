import React, { useEffect, useState } from 'react'
import Login from './components/Login'
import Dashboard from './components/Dashboard'

// ---- BEGIN env resolution: Vite + compat + fallback ----
let API_BASE = ''

try {
  const ve = import.meta?.env || {}
  API_BASE =
    ve.VITE_BACKEND_URL ||
    ve.VITE_REACT_APP_BACKEND_URL ||
    ve.VITE_REACT_BACKEND_URL ||
    ve.REACT_APP_BACKEND_URL ||
    ''
  if (!API_BASE && typeof process !== 'undefined' && process?.env)
    API_BASE = process.env.REACT_APP_BACKEND_URL || ''
} catch {
  API_BASE = ''
}

// fallback final: assume localhost se estiver em dev
if (
  !API_BASE &&
  typeof window !== 'undefined' &&
  window.location.hostname === 'localhost'
) {
  API_BASE = 'http://localhost:8001'
}
// ---- END env resolution ----

export { API_BASE }

// ---- BEGIN fetch util ----
export async function apiFetch(path, opts = {}) {
  const base = API_BASE
  if (!base)
    throw new Error('Backend URL não configurada (VITE_BACKEND_URL ou localhost)')

  const url = base + path
  const headers = { ...(opts.headers || {}) }
  const token = localStorage.getItem('token')
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url, { ...opts, headers })

  if (res.status === 401 || res.status === 403) {
    localStorage.removeItem('token')
    sessionStorage.clear()
    window.location.reload()
    throw new Error('Token expirado ou inválido. Refaça o login.')
  }

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `Erro HTTP ${res.status}`)
  }

  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return res
}
// ---- END fetch util ----

// ---- BEGIN main app ----
export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '')
  const authed = !!token

  useEffect(() => {
    if (token) localStorage.setItem('token', token)
  }, [token])

  // valida o token inicial
  useEffect(() => {
    const validateToken = async () => {
      const t = localStorage.getItem('token')
      if (!t) return
      try {
        const res = await fetch(`${API_BASE}/ping`, {
          headers: { Authorization: `Bearer ${t}` },
        })
        if (!res.ok) throw new Error('Token inválido')
      } catch {
        localStorage.removeItem('token')
        sessionStorage.clear()
        setToken('')
      }
    }
    validateToken()
  }, [])

  if (!authed)
    return (
      <Login
        onSuccess={(newToken) => {
          localStorage.setItem('token', newToken)
          setToken(newToken)
        }}
      />
    )

  return (
    <Dashboard
      onLogout={() => {
        localStorage.removeItem('token')
        sessionStorage.clear()
        setToken('')
      }}
    />
  )
}
// ---- END main app ----
