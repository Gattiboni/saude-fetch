import React, { useEffect, useMemo, useState } from 'react'
import { apiFetch, API_BASE } from '../../App'

function ProgressBar({ current, total, etaSeconds }){
  const pct = total ? Math.round((current/total)*100) : 0
  const etaLabel = total && current < total && etaSeconds > 0 ? ` • ETA ~${etaSeconds}s` : ''
  return (
    <div className="space-y-1">
      <div className="label" data-testid="cpf-progress-label">
        {total ? `Processando ${current} de ${total} (${pct}%)${etaLabel}` : 'Aguardando envio'}
      </div>
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
  const [status, setStatus] = useState(null)
  const [logText, setLogText] = useState('')
  const [startTime, setStartTime] = useState(null)
  const [avgTime, setAvgTime] = useState(0)
  const [manualToken, setManualToken] = useState('')
  const [manualInfo, setManualInfo] = useState('')
  const [manualCpfs, setManualCpfs] = useState('')
  const [manualError, setManualError] = useState('')
  const [manualBusy, setManualBusy] = useState(false)
  const [manualResults, setManualResults] = useState(null)
  const [manualFeedback, setManualFeedback] = useState('')
  const [copyFeedback, setCopyFeedback] = useState('')

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
      setStartTime(Date.now())
      setAvgTime(0)
    }catch(err){ setError('Erro ao enviar arquivo: ' + (err?.message||err)) }
    finally{ setCreating(false); setFile(null) }
  }

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
          try{
            const res = await apiFetch(`/api/jobs/${job.id}/log`)
            const text = await res.text()
            setLogText(text)
          }catch(e){ }
          setStartTime(null)
          return
        }
      }catch(e){ }
      timer = setTimeout(tick, 1500)
    }
    tick()
    return ()=>{ stopped = true; timer && clearTimeout(timer) }
  }, [job?.id])

  useEffect(()=>{
    if (!job?.id){
      setStartTime(null)
      setAvgTime(0)
    }
  }, [job?.id])

  useEffect(()=>{
    if (!startTime || !status?.processed || !status?.total) return
    if (status.processed <= 0) return
    if (status.status !== 'processing') return
    const elapsed = (Date.now() - startTime) / 1000
    if (elapsed > 0){
      setAvgTime(elapsed / status.processed)
    }
  }, [status?.processed, status?.status, startTime])

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
  const etaSeconds = total && avgTime > 0 ? Math.max(0, Math.round((total - current) * avgTime)) : 0

  const manualIdentifiers = useMemo(
    () =>
      manualCpfs
        .split(/[\s,;]+/)
        .map(v => v.replace(/[^\d]/g, '').trim())
        .filter(Boolean),
    [manualCpfs]
  )

  const startManualAmil = async () => {
    setManualError('')
    setManualResults(null)
    setManualInfo('')
    setManualFeedback('')
    try{
      setManualBusy(true)
      const res = await apiFetch('/api/manual/amil/start', { method: 'POST' })
      setManualToken(res.token)
      setManualInfo(res.note || 'Navegador aberto. Cole o link da Amil e carregue a página.')
    }catch(err){
      setManualError(err?.message || 'Falha ao iniciar navegador manual.')
    }finally{
      setManualBusy(false)
    }
  }

  const runManualAmil = async () => {
    setManualError('')
    setManualResults(null)
    const identifiers = manualIdentifiers
    if (!manualToken){
      setManualError('Inicie o navegador manual antes de executar a busca.')
      return
    }
    if (!identifiers.length){
      setManualError('Informe ao menos um CPF para consulta manual.')
      return
    }
    try{
      setManualBusy(true)
      const res = await apiFetch('/api/manual/amil/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: manualToken, identifiers }),
      })
      setManualResults(res.results || [])
    }catch(err){
      setManualError(err?.message || 'Falha ao executar busca manual.')
    }finally{
      setManualBusy(false)
    }
  }

  const handleManualUpload = async (event) => {
    setManualError('')
    setManualFeedback('')
    const f = event.target.files?.[0]
    if (!f) return
    const fd = new FormData()
    fd.append('file', f)
    try{
      setManualBusy(true)
      const res = await apiFetch('/api/manual/amil/upload', {
        method: 'POST',
        body: fd,
      })
      const { valid = [], invalid = [], total = 0 } = res || {}
      setManualCpfs(valid.join('\n'))
      setManualResults(null)
      setManualFeedback(`${valid.length} identificadores válidos carregados. ${invalid.length} inválidos de ${total} encontrados.`)
      if (invalid.length) {
        setManualError(`Alguns CPFs são inválidos ou não puderam ser lidos (${invalid.length}).`)
      }
    }catch(err){
      setManualError(err?.message || 'Falha ao processar arquivo.')
      setManualFeedback('')
    }finally{
      setManualBusy(false)
      event.target.value = ''
    }
  }

  const copyManualLink = async () => {
    try{
      await navigator.clipboard.writeText('https://www.amil.com.br/institucional/#/servicos/saude/rede-credenciada/amil/busca-avancada')
      setCopyFeedback('Link copiado!')
      setTimeout(() => setCopyFeedback(''), 1500)
    }catch(err){
      setManualError('Não foi possível copiar o link automaticamente.')
    }
  }

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

      <ProgressBar current={current} total={total} etaSeconds={etaSeconds} />

      <div className="space-y-3 border border-dashed border-blue-500/40 rounded p-4">
        <div className="label font-semibold">Fluxo manual Amil</div>
        <p className="label text-sm text-blue-200">
          Utilize este modo quando o site bloquear automações. Um navegador real será aberto e você deverá carregar a página da Amil manualmente antes de executar a busca.
        </p>
        <div className="flex gap-2 flex-wrap">
          <button className="btn" type="button" onClick={copyManualLink} disabled={manualBusy}>
            {copyFeedback || 'Copiar link'}
          </button>
          <label className="btn cursor-pointer">
            Escolher arquivo
            <input
              type="file"
              accept=".csv,.xls,.xlsx"
              className="hidden"
              onChange={handleManualUpload}
              disabled={manualBusy}
            />
          </label>
          <button className="btn" type="button" disabled={manualBusy} onClick={startManualAmil}>
            Abrir Amil (manual)
          </button>
          <button
            className="btn"
            type="button"
            disabled={manualBusy || !manualToken || manualIdentifiers.length === 0}
            onClick={runManualAmil}
          >
            Executar busca Amil
          </button>
        </div>
        {manualInfo && <div className="label text-green-200">{manualInfo}</div>}
        {manualFeedback && <div className="label text-blue-200 text-sm">{manualFeedback}</div>}
        <textarea
          className="input w-full h-24 resize-none"
          placeholder="Cole aqui os CPFs (um por linha ou separados por vírgula) para executar manualmente na Amil"
          value={manualCpfs}
          onChange={e => setManualCpfs(e.target.value)}
          disabled={manualBusy}
        />
        {manualError && <div className="text-red-300">{manualError}</div>}
        {manualResults && manualResults.length > 0 && (
          <div className="label text-sm text-emerald-200 space-y-2">
            <div>Resultados recebidos: {manualResults.length}</div>
            <div className="bg-gray-900/60 p-2 rounded max-h-40 overflow-auto text-xs">
              {manualResults.map((r, idx) => (
                <div key={idx} className="py-1 border-b border-gray-800 last:border-0">
                  <strong>{r.identifier}</strong> — {r.status} {r.plan ? `| ${r.plan}` : ''} {r.message ? `| ${r.message}` : ''}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

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
