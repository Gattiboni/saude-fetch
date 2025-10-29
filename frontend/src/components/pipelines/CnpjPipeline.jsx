import React, { useMemo, useState, useEffect } from 'react'
import { apiFetch } from '../../App'

function ProgressBar({ current, total, etaSeconds }){
  const pct = total ? Math.round((current/total)*100) : 0
  const etaLabel = total && current < total && etaSeconds > 0 ? ` • ETA ~${etaSeconds}s` : ''
  return (
    <div className="space-y-1">
      <div className="label" data-testid="cnpj-progress-label">{total? `Processando ${current} de ${total} (${pct}%)${etaLabel}` : 'Aguardando envio'}</div>
      <div className="w-full h-2 bg-gray-800 rounded" data-testid="cnpj-progress-bar">
        <div className="h-2 bg-blue-500 rounded" style={{ width: `${pct}%`, transition: 'width .3s' }} />
      </div>
    </div>
  )
}

export default function CnpjPipeline(){
  const [file, setFile] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [summary, setSummary] = useState(null)
  const [items, setItems] = useState([])
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const [startTime, setStartTime] = useState(null)
  const [avgTime, setAvgTime] = useState(0)

  const uploadingDisabled = useMemo(()=> running || !file, [running, file])

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setSummary(null); setItems([])
    if (!file){ setError('Selecione um arquivo .csv ou .xlsx.'); return }
    try{
      setRunning(true)
      const text = await file.text()
      const lines = text.split(/\r?\n/).map(l=>l.trim()).filter(Boolean)
      const cnpjs = []
      for (let i=1;i<lines.length;i++){
        const v = lines[i].replace(/\D/g,'')
        if (v.length===14) cnpjs.push(v)
      }
      if (!cnpjs.length){ setError('Nenhum CNPJ válido encontrado.'); return }
      setProgress({ current: 0, total: cnpjs.length })
      setStartTime(Date.now())
      setAvgTime(0)

      const res = await apiFetch('/api/fetch/cnpj', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ cnpjs }) })
      setSummary({ total: res.total, ativos: res.ativos, inativos: res.inativos })
      setItems(res.items || res.resultados || [])
      const processed = res.items?.length || res.resultados?.length || res.total || 0
      const totalItems = res.total || cnpjs.length
      setProgress({ current: processed, total: totalItems })
      if (processed > 0){
        const elapsed = (Date.now() - (startTime || Date.now())) / 1000
        if (elapsed > 0){
          setAvgTime(elapsed / processed)
        }
      }
    }catch(err){
      const msg = String(err?.message||err)
      if (/Faltam credenciais SulAmérica/.test(msg)){
        setError('Faltam credenciais SulAmérica no .env: SUL_CPF, SUL_EMAIL, SUL_PASS, SUL_CORRETORA.')
      } else {
        setError('Erro ao processar CNPJ: ' + msg)
      }
    }finally{
      setRunning(false)
      setFile(null)
      setStartTime(null)
    }
  }

  useEffect(()=>{
    if (!startTime || !running) return
    if (!progress.total) return
    const interval = setInterval(()=>{
      if (!startTime) return
      const elapsed = (Date.now() - startTime) / 1000
      if (elapsed > 0 && progress.current > 0){
        setAvgTime(elapsed / progress.current)
      }
    }, 1000)
    return ()=> clearInterval(interval)
  }, [startTime, running, progress.current, progress.total])

  const downloadXlsx = async () => {
    try{
      const res = await apiFetch('/api/fetch/cnpj/export')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = 'sulamerica_cnpj.xlsx'; a.click(); URL.revokeObjectURL(url)
    }catch(err){ setError('Falha ao baixar XLSX: ' + (err?.message||err)) }
  }

  const etaSeconds = progress.total && avgTime > 0 ? Math.max(0, Math.round((progress.total - progress.current) * avgTime)) : 0

  return (
    <div className="card space-y-4" data-testid="cnpj-pipeline">
      <form className="space-y-4" onSubmit={submit}>
        <div>
          <label className="label">Arquivo (.csv ou .xlsx)</label>
          <input data-testid="cnpj-input-file" type="file" accept=".csv,.xlsx" className="input w-full" onChange={e=> setFile(e.target.files?.[0]||null)} />
        </div>
        {error && <div className="text-red-300" data-testid="cnpj-error">{error}</div>}
        <button className="btn" data-testid="cnpj-submit" disabled={uploadingDisabled}>{running? 'Processando…' : 'Enviar e processar'}</button>
      </form>

      <ProgressBar current={progress.current} total={progress.total} etaSeconds={etaSeconds} />

      {summary && (
        <div className="label flex items-center gap-3" data-testid="cnpj-summary">
          Total: {summary.total} • Ativos: {summary.ativos} • Inativos: {summary.inativos}
          <button className="btn" data-testid="cnpj-download-xlsx" onClick={downloadXlsx}>Baixar XLSX</button>
        </div>
      )}

      {!!items.length && (
        <div className="overflow-auto">
          <table className="table" data-testid="cnpj-results-table">
            <thead>
              <tr className="label"><th>CNPJ</th><th>Status</th><th>Mensagem</th><th>Quando</th></tr>
            </thead>
            <tbody>
              {items.map((it,idx)=> (
                <tr key={idx}>
                  <td>{it.cnpj}</td>
                  <td>{it.status}</td>
                  <td>{it.mensagem_portal || it.mensagem || ''}</td>
                  <td className="label">{it.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
