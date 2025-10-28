import React, { useMemo, useState } from 'react'
import { apiFetch } from '../../App'

function ProgressBar({ current, total }){
  const pct = total ? Math.round((current/total)*100) : 0
  return (
    <div className="space-y-1">
      <div className="label" data-testid="cnpj-progress-label">{total? `Processando ${current} de ${total}…` : 'Aguardando envio'}</div>
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

      const res = await apiFetch('/api/fetch/cnpj', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ cnpjs }) })
      setSummary({ total: res.total, ativos: res.ativos, inativos: res.inativos })
      setItems(res.items || res.resultados || [])
      setProgress({ current: res.items?.length || res.resultados?.length || res.total || 0, total: res.total || cnpjs.length })
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
    }
  }

  const downloadXlsx = async () => {
    try{
      const res = await apiFetch('/api/fetch/cnpj/export')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = 'sulamerica_cnpj.xlsx'; a.click(); URL.revokeObjectURL(url)
    }catch(err){ setError('Falha ao baixar XLSX: ' + (err?.message||err)) }
  }

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

      <ProgressBar current={progress.current} total={progress.total} />

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
