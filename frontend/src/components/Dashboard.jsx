import React, { useState } from 'react'
import CpfPipeline from './pipelines/CpfPipeline'
import CnpjPipeline from './pipelines/CnpjPipeline'

export default function Dashboard({ onLogout }){
  const [view, setView] = useState('') // '', 'cpf', 'cnpj'

  return (
    <div className="container space-y-6" data-testid="dashboard">
      <header className="space-y-1 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">saude-fetch</h1>
          <p className="label">Selecione um pipeline para iniciar</p>
        </div>
        <button data-testid="logout-button" className="btn" onClick={onLogout}>Sair</button>
      </header>

      {!view && (
        <section className="card grid grid-cols-1 sm:grid-cols-2 gap-4" data-testid="pipeline-selector">
          <button className="btn" data-testid="select-cpf" onClick={()=> setView('cpf')}>Consulta CPF</button>
          <button className="btn" data-testid="select-cnpj" onClick={()=> setView('cnpj')}>Consulta CNPJ (SulAmérica)</button>
        </section>
      )}

      {view==='cpf' && (
        <section className="space-y-4" data-testid="cpf-pipeline-section">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">Pipeline CPF</h2>
            <button className="btn" data-testid="back-to-dashboard" onClick={()=> setView('')}>Voltar</button>
          </div>
          <CpfPipeline />
        </section>
      )}

      {view==='cnpj' && (
        <section className="space-y-4" data-testid="cnpj-pipeline-section">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">Pipeline CNPJ (SulAmérica)</h2>
            <button className="btn" data-testid="back-to-dashboard" onClick={()=> setView('')}>Voltar</button>
          </div>
          <CnpjPipeline />
        </section>
      )}
    </div>
  )
}
