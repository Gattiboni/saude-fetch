import React, { useEffect, useMemo, useState } from 'react'

const API_BASE = (import.meta?.env?.REACT_APP_BACKEND_URL || import.meta?.env?.VITE_REACT_APP_BACKEND_URL || (typeof process !== 'undefined' ? process?.env?.REACT_APP_BACKEND_URL : ''))

async function apiFetch(path, opts = {}) {
  const base = API_BASE
  if (!base) throw new Error('REACT_APP_BACKEND_URL não configurada no ambiente do frontend')
  const url = base + path
  const res = await fetch(url, opts)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Erro HTTP ${res.status}`)
  }
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return res
}

function useJobsPoll() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    let timer
    const tick = async () => {
      try {
        setLoading(true)
        const data = await apiFetch('/jobs')
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
  }, [])
  return { jobs, loading, error }
}

export default function App() {
  const { jobs, loading: listLoading, error: listError } = useJobsPoll()
  const [file, setFile] = useState(null)
  const [type, setType] = useState('auto')
  const [creating, setCreating] = useState(false)
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

  return (
    <div className="container space-y-6" data-testid="saude-fetch-app">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">saude-fetch</h1>
        <p className="label">MVP mínimo para upload de planilhas, processamento local e download do resultado.</p>
      </header>

      <section className="card space-y-4" data-testid="upload-card">
        <form className="space-y-4" onSubmit={createJob}>
          <div className="space-y-1">
            <label className="label" htmlFor="file">Arquivo (CSV ou Excel)</label>
            <input id="file" data-testid="upload-input-file" type="file" accept=".csv,.xlsx,.xls" className="input w-full" onChange={(e)=> setFile(e.target.files?.[0] || null)} />
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
          {listLoading && <span className="label" data-testid="jobs-loading">atualizando…</span>}
        </div>
        {listError && (
          <div className="text-red-300" data-testid="jobs-error">{listError}</div>
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
                      <a data-testid={`download-csv-${j.id}`} className="btn" href={`${API_BASE}/api/jobs/${j.id}/results?format=csv`} target="_blank" rel="noreferrer">CSV</a>
                      <a data-testid={`download-json-${j.id}`} className="btn" href={`${API_BASE}/api/jobs/${j.id}/results?format=json`} target="_blank" rel="noreferrer">JSON</a>
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
