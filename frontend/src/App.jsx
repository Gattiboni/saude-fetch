import React, { useEffect, useMemo, useState } from 'react'

const API_BASE = (import.meta?.env?.REACT_APP_BACKEND_URL || import.meta?.env?.VITE_REACT_APP_BACKEND_URL || (typeof process !== 'undefined' ? process?.env?.REACT_APP_BACKEND_URL : '') || 'https://docs-hub-4.preview.emergentagent.com')

async function apiFetch(path, opts = {}) {
  const base = API_BASE
  if (!base) throw new Error('REACT_APP_BACKEND_URL não configurada no ambiente do frontend')
  const url = base + path
  const headers = opts.headers || {}
  const token = localStorage.getItem('token')
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(url, { ...opts, headers })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Erro HTTP ${res.status}`)
  }
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return res
function StatusBar({ jobs }){
  const running = jobs.filter(j => j.status === 'processing').length
  return (
    <div className="w-full h-2 bg-gray-800 rounded" data-testid="progress-bar">
      <div className="h-2 bg-blue-500 rounded" style={{ width: `${Math.min(100, running ? 30 : 100)}%`, transition: 'width 0.4s' }} />
    </div>
  )
}

}

function useJobsPoll(enabled = true) {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!enabled) return
    
    let timer
    const tick = async () => {
      try {
        setLoading(true)
        const data = await apiFetch('/api/jobs')
        setJobs(data.items || [])
        setError('')
      } catch (e) {
        setError(String(e.message || e))
      } finally {
        setLoading(false)
        timer = setTimeout(tick, 2500)
      }
    }
    tick()
    return () => timer && clearTimeout(timer)
  }, [enabled])
  return { jobs, loading, error }
}

function Login({ onSuccess }){
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try{
      const res = await apiFetch('/api/auth/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ username, password }) })
      localStorage.setItem('token', res.token)
      onSuccess()
    }catch(err){ setError(String(err.message||err)) }
    finally{ setLoading(false) }
  }
  return (
    <div className="container">
      <div className="card space-y-4 max-w-md mx-auto">
        <h2 className="text-xl font-semibold">Entrar</h2>
        <form className="space-y-3" onSubmit={submit}>
          <div>
            <label className="label">Usuário</label>
            <input data-testid="login-username" className="input w-full" value={username} onChange={e=>setUsername(e.target.value)} />
          </div>
          <div>
            <label className="label">Senha</label>
            <input data-testid="login-password" type="password" className="input w-full" value={password} onChange={e=>setPassword(e.target.value)} />
          </div>
          {error && <div className="text-red-300" data-testid="login-error">{error}</div>}
          <button data-testid="login-submit-button" className="btn" disabled={loading}>{loading?'Entrando…':'Entrar'}</button>
        </form>
      </div>
    </div>
  )
}

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem('token'))
  const { jobs, loading: listLoading, error: listError } = useJobsPoll(authed)
  const [file, setFile] = useState(null)
  const [type, setType] = useState('auto')
  const [creating, setCreating] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const uploadingDisabled = useMemo(() => !file || creating, [file, creating])

  const createJob = async (e) => {
    e.preventDefault()
    if (!file) return
    try {
      setCreating(true)
      const fd = new FormData()
      fd.append('file', file)
      fd.append('type', type)
      const job = await apiFetch('/api/jobs', { method: 'POST', body: fd })
      console.log('Job created', job)
    } catch (e) {
      alert('Erro ao criar job: ' + (e?.message || e))
    } finally {
      setCreating(false)
      setFile(null)
    }
  }

  if (!authed) return <Login onSuccess={()=> setAuthed(true)} />

  return (
    <div className="container space-y-6" data-testid="saude-fetch-app">
      <header className="space-y-1 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">saude-fetch</h1>
          <p className="label">MVP mínimo para upload de planilhas, processamento local e download do resultado.</p>
        </div>
        <button data-testid="logout-button" className="btn" onClick={()=>{localStorage.removeItem('token'); setAuthed(false)}}>Sair</button>
      </header>

      <nav className="card flex gap-3" data-testid="tabs">
        <button className="btn" data-testid="tab-cpf">Consulta CPF</button>
        <button className="btn opacity-50 cursor-not-allowed" title="Em breve" data-testid="tab-cnpj">Consulta CNPJ (em breve)</button>
      </nav>

      <section className="card space-y-4" data-testid="upload-card">
        <form className="space-y-4" onSubmit={createJob}>
          <div className="space-y-1">
            <label className="label" htmlFor="file">Arquivo (CSV ou Excel)</label>
            <input id="file" data-testid="upload-input-file" type="file" accept=".csv,.xlsx,.xls" className="input w-full" onChange={(e)=> {
              const f = e.target.files?.[0] || null
              setErrorMsg('')
              if (f) {
                const ok = ['text/csv','application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
                if (!ok.includes(f.type) && !/\.(csv|xlsx|xls)$/i.test(f.name)) {
                  setErrorMsg('Arquivo inválido. Envie CSV ou Excel.')
                  setFile(null)
                  return
                }
              }
              setFile(f)
            }} />
          </div>
          <div className="space-y-1">
            <label className="label" htmlFor="type">Tipo</label>
            <select id="type" data-testid="upload-select-type" className="input w-full" value={type} onChange={(e)=> setType(e.target.value)}>
              <option value="auto">Auto</option>
              <option value="cpf">CPF</option>
              <option value="cnpj">CNPJ</option>
            </select>
          </div>
          <div className="flex gap-2">
            <button data-testid="upload-submit-button" className="btn" disabled={uploadingDisabled}>{creating ? 'Processando...' : 'Enviar e processar'}</button>
          </div>
        </form>
      </section>

      <section className="card space-y-3" data-testid="jobs-list-card">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">Execuções recentes</h2>
          <div className="flex items-center gap-3">
            {listLoading && <span className="label" data-testid="jobs-loading">atualizando…</span>}
          </div>
        </div>
        <StatusBar jobs={jobs} />
        {listError && (
          <div className="text-red-300" data-testid="jobs-error">{listError}</div>
        )}
        {errorMsg && (
          <div className="text-red-300" data-testid="upload-error">{errorMsg}</div>
        )}
        <div className="overflow-auto">
          <table className="table" data-testid="jobs-table">
            <thead>
              <tr className="label">
                <th>ID</th>
                <th>Arquivo</th>
                <th>Tipo</th>
                <th>Status</th>
                <th>Total</th>
                <th>OK</th>
                <th>Erros</th>
                <th>Iniciado</th>
                <th>Finalizado</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(j => (
                <tr key={j.id} data-testid={`jobs-row-${j.id}`}>
                  <td className="truncate max-w-[180px]" title={j.id}>{j.id}</td>
                  <td>{j.filename}</td>
                  <td>{j.type}</td>
                  <td>
                    <span className={`badge ${j.status === 'completed' ? 'badge-completed' : j.status === 'failed' ? 'badge-failed' : 'badge-processing'}`}>{j.status}</span>
                  </td>
                  <td>{j.total}</td>
                  <td>{j.success}</td>
                  <td>{j.error}</td>
                  <td className="label">{j.created_at?.replace('T',' ').replace('Z','')}</td>
                  <td className="label">{j.completed_at?.replace('T',' ').replace('Z','') || '-'}</td>
                  <td>
                    <div className="flex gap-2">
                      <a data-testid={`download-csv-${j.id}`} className="btn" href={`${API_BASE}/jobs/${j.id}/results?format=csv`} target="_blank" rel="noreferrer">CSV</a>
                      <a data-testid={`download-json-${j.id}`} className="btn" href={`${API_BASE}/jobs/${j.id}/results?format=json`} target="_blank" rel="noreferrer">JSON</a>
                    </div>
                  </td>
                </tr>
              ))}
              {!jobs.length && (
                <tr>
                  <td colSpan={10} className="label">Nenhuma execução ainda.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <footer className="label" data-testid="footer">
        Backend: variável REACT_APP_BACKEND_URL obrigatória no ambiente do frontend. Endpoints em /api.
      </footer>
    </div>
  )
}
