import React, { useEffect, useMemo, useState } from 'react'
import { apiFetch, API_BASE } from '../../App'

function ProgressBar({ current, total }){
  const pct = total ? Math.round((current/total)*100) : 0
  return (
    <div className="space-y-1">
      <div className="label" data-testid="cpf-progress-label">{total? `Processando ${current} de ${total}…` : 'Aguardando envio'}</div>
      <div className="w-full h-2 bg-gray-800 rounded" data-testid="cpf-progress-bar">
        <div className="h-2 bg-blue-500 rounded" style={{ width: `${pct}%`, transition: 'width .3s' }} />
      </div>
    </div>
  )
}

export default function CpfPipeline(){
  const [file, setFile] = useState(null)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [job, setJob] = useState(null)
  const [status, setStatus] = useState(null) // latest job status
  const [logText, setLogText] = useState('')

  const uploadingDisabled = useMemo(() => !file || creating, [file, creating])

  const validateFile = (f) => {
    setError('')
    if (!f) return false
    const ok = ['text/csv','application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
    if (!ok.includes(f.type) && !/\.(csv|xlsx)$/i.test(f.name)){
      setError('Arquivo inválido. Envie CSV ou Excel (.csv ou .xlsx).')
      return false
    }
    return true
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!validateFile(file)) return
    try{
      setCreating(true)
      setError('')
      setJob(null)
      setStatus(null)
      setLogText('')
      const fd = new FormData()
      fd.append('file', file)
      const j = await apiFetch('/api/jobs', { method:'POST', body: fd })
      setJob(j)
      setStatus(j)
    }catch(err){ setError('Erro ao enviar arquivo: ' + (err?.message||err)) }
    finally{ setCreating(false); setFile(null) }
  }

  // polling do job
  useEffect(()=>{
    if (!job?.id) return
    let stopped = false
    let timer
    const tick = async () => {
      try{
        const s = await apiFetch(`/api/jobs/${job.id}`)
        if (stopped) return
        setStatus(s)
        if (s.status !== 'processing'){
          // carregar log
          try{
            const res = await apiFetch(`/api/jobs/${job.id}/log`)
            const text = await res.text()
            setLogText(text)
          }catch(e){ /* opcional */ }
          return
        }
      }catch(e){ /* ignore, re-tenta */ }
      timer = setTimeout(tick, 1500)
    }
    tick()
    return ()=>{ stopped = true; timer && clearTimeout(timer) }
  }, [job?.id])

  const downloadXlsx = async () => {
    if (!status?.id) return
    try{
      const res = await apiFetch(`/api/jobs/${status.id}/results?format=xlsx`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = `${status.id}.xlsx`; a.click(); URL.revokeObjectURL(url)
    }catch(err){ setError('Falha ao baixar XLSX: ' + (err?.message||err)) }
  }

  const current = status?.processed || 0
  const total = status?.total || 0

  return (
    <div className="card space-y-4" data-testid="cpf-pipeline">
      <form className="space-y-4" onSubmit={submit}>
        <div>
          <label className="label">Arquivo (.csv ou .xlsx)</label>
          <input data-testid="cpf-input-file" type="file" accept=".csv,.xlsx" className="input w-full" onChange={e=> setFile(e.target.files?.[0]||null)} />
        </div>
        {error && <div className="text-red-300" data-testid="cpf-error">{error}</div>}
        <button className="btn" data-testid="cpf-submit" disabled={uploadingDisabled}>{creating? 'Enviando…' : 'Enviar e processar'}</button>
      </form>

      <ProgressBar current={current} total={total} />

      {status && status.status !== 'processing' && (
        <div className="space-y-2" data-testid="cpf-summary">
          <div className="label">Total: {status.total} • OK: {status.success} • Erros: {status.error}</div>
          <button className="btn" data-testid="cpf-download-xlsx" onClick={downloadXlsx}>Baixar XLSX</button>
        </div>
      )}

      {!!logText && (
        <div className="space-y-2" data-testid="cpf-log">
          <div className="label">Log da última execução</div>
          <pre className="label whitespace-pre-wrap bg-gray-900 p-2 rounded" style={{maxHeight: 220, overflow: 'auto'}}>{logText}</pre>
        </div>
      )}
    </div>
  )
}
