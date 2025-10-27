# Projeto **saude-fetch** — Guia e Folha de Rosto (Atualizado 2025-10-27)

**Repositório:** [https://github.com/Gattiboni/saude-fetch](https://github.com/Gattiboni/saude-fetch)

---

## Visão Geral

O **saude-fetch** é uma ferramenta de automação para qualificação de CPFs e CNPJs em portais de operadoras de saúde — **Unimed**, **Amil**, **Bradesco**, **Seguros Unimed** e **SulAmérica** — retornando informações de planos ativos de forma auditável e escalável.

O sistema adota uma arquitetura modular e segura, com backend em **FastAPI** e frontend em **React**, permitindo consultas em lote, geração de relatórios e logs auditáveis.  
A aplicação roda localmente, com instalação simplificada e autenticação mínima.

---

## Estrutura do Projeto

| Diretório / Módulo | Função |
| ------------------- | ------- |
| **app/backend/** | FastAPI, endpoints, drivers e processamento assíncrono. |
| **app/frontend/** | Interface React (Vite + Tailwind). |
| **app/data/** | Uploads, exports e logs (`last_run.log`). |
| **docs/mappings/** | Arquivos JSON de mapeamento DOM por operadora. |
| **scripts/** | Scripts `setup.sh` e `setup.bat` para instalação e atalho. |
| **Docs/** | Documentação técnica e operacional consolidada. |

---

## Funcionalidades Principais

- Upload de listas CSV/XLSX (CPFs ou CNPJs).  
- Processamento em background com barra de progresso (%).  
- Login local com usuário e senha do `.env`.  
- Geração de relatórios em **CSV**, **JSON** e **XLSX**.  
- Resumo final por execução: “Consultados / Sucesso / Falhas”.  
- Drivers configuráveis via `/docs/mappings`.  
- Endpoint `/api/mappings/reload` para recarregar mappings sem restart.  
- Logs simples e sobrescritos em `last_run.log`.  
- Criação automática de atalho “Fetch Saúde” no desktop.

---

## Fluxo de Execução Local

1. **Instalação**
   - Clonar o repositório.  
   - Executar `setup.bat` (Windows) ou `bash setup.sh` (Linux/Mac).  
   - O script cria `.venv`, instala dependências e gera o atalho **Fetch Saúde**.

2. **Login**
   - Acessar `http://localhost:3000`.  
   - Entrar com `APP_USER` e `APP_PASS` definidos no `.env`.

3. **Consulta CPF**
   - Selecionar aba **Consulta CPF**.  
   - Upload de CSV/XLSX com CPFs.  
   - Acompanhar progresso e visualizar o resumo.  
   - Baixar resultados em **XLSX** (`CPF | AMIL | BRADESCO | UNIMED | UNIMED SEGUROS`).

4. **Consulta CNPJ**
   - Aba exibida, mas **inativa** (aguarda credenciais SulAmérica).

5. **Reload de Mapeamentos**
   - Inserir arquivos JSON em `/docs/mappings`.  
   - Executar `POST /api/mappings/reload` para recarregar sem reiniciar.

---

## Estrutura Técnica (Stack)

### Backend
- **FastAPI + Uvicorn**
- **MongoDB (motor assíncrono)**
- **pandas + openpyxl**
- **JWT Auth** (`APP_USER`, `APP_PASS`, `APP_SECRET`)
- **Drivers:** Unimed, Amil, Bradesco, Seguros Unimed, SulAmérica (auth inativo)
- **Throttling:** `FETCH_MIN_DELAY`, `FETCH_MAX_DELAY` configuráveis

### Frontend
- **Vite + React + TailwindCSS**
- **Login + token localStorage**
- **Uploads / Downloads / Progresso / Resumo / Badge “pendente”**

---

## Logs e Auditoria

- Log único: `app/data/logs/last_run.log`.  
- Exportação manual opcional.  
- Resultados gerados em CSV/JSON/XLSX com timestamp e identificador de job.

---

## Operadoras e Regras

| Operadora | Critério de Sucesso | Critério de Falha |
| ---------- | ------------------- | ----------------- |
| **Unimed** | Dados de plano e cooperativa | CPF inválido |
| **Amil** | Exibe nome do plano | Modal “não encontrado” |
| **Bradesco** | Modal “Selecione o beneficiário” | “Beneficiário não encontrado” |
| **Seguros Unimed** | Informações de plano | Erro / CPF inválido |
| **SulAmérica** | Login necessário (CNPJ) | Acesso negado |

---

## Documentação Relacionada

| Documento | Conteúdo |
| ---------- | -------- |
| **Docs/Documentacao_Consolidada_SaudeFetch_Atualizada_2025-10-27.txt** | Logs, decisões, stack e operações completas. |
| **Docs/DecisionLog.md** | Decisões técnicas e de arquitetura. |
| **Docs/ChangeLog.md** | Histórico de entregas e merges. |
| **Docs/Operations.md** | Guia operacional e instruções de uso. |
| **Docs/Stack.md** | Arquitetura técnica detalhada. |

---

## Cronograma

| Etapa | Data |
| ----- | ---- |
| Início | 23/10/2025 |
| Conclusão (Merge Final) | 27/10/2025 |
| Fase Atual | Testes locais e integração dos mappings reais |

---

## Responsável

**Alan Gattiboni** — Coordenação técnica, setup e integração local.  
Repositório e versionamento mantidos sob **branch principal `main`** (Docs e README imutáveis em merges).
