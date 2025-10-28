import React, { useState } from 'react'
import { apiFetch } from '../App'

export default function Login({ onSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      console.log('[LOGIN] Iniciando login...')
      const res = await apiFetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })

      if (!res?.token) {
        throw new Error('Token ausente na resposta do servidor.')
      }

      console.log('[LOGIN] Token recebido:', res.token)
      localStorage.setItem('token', res.token)

      // Garante persistência antes de acionar o App
      await new Promise((resolve) => setTimeout(resolve, 150))

      console.log('[LOGIN] Token salvo. Chamando onSuccess()...')
      onSuccess?.(res.token)
    } catch (err) {
      console.error('[LOGIN] Erro:', err)
      setError(String(err.message || err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container" data-testid="login-screen">
      <div className="card space-y-4 max-w-md mx-auto">
        <h1 className="text-2xl font-semibold">saude-fetch</h1>
        <h2 className="text-xl font-semibold">Entrar</h2>
        <form className="space-y-3" onSubmit={submit}>
          <div>
            <label className="label">Usuário</label>
            <input
              data-testid="login-username"
              className="input w-full"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Senha</label>
            <input
              data-testid="login-password"
              type="password"
              className="input w-full"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && (
            <div className="text-red-300" data-testid="login-error">
              {error}
            </div>
          )}
          <button
            data-testid="login-submit-button"
            className="btn"
            disabled={loading}
          >
            {loading ? 'Entrando…' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}
