==============================
## DOCUMENTO: STACK.md
==============================

### Arquitetura Técnica — Estado Atual (2025-10-27)

#### Backend
- **Framework:** FastAPI + Uvicorn
- **Banco:** MongoDB via `motor` (assíncrono)
- **Processamento:** `pandas` + `openpyxl`
- **Autenticação:** JWT (`APP_USER`, `APP_PASS`, `APP_SECRET`)
- **Drivers:** unimed, amil, bradesco, Seguros unimed, SulAmérica (inativo)
- **Throttling:** configurável via `.env` (`FETCH_MIN_DELAY`, `FETCH_MAX_DELAY`)
- **Logs:** sobrescreve `last_run.log`
- **Reload mappings:** endpoint `/api/mappings/reload`
- **Arquivos de saída:** CSV, JSON, XLSX (formato fixo, CPF como texto)

#### Frontend
- **Framework:** Vite + React + TailwindCSS
- **Autenticação:** Login → token armazenado no `localStorage`
- **Funcionalidades:**
  - Upload CSV/XLSX
  - Progresso (%) por execução
  - Resumo por job (Consultados/Sucesso/Falhas)
  - Downloads: CSV/JSON/XLSX
  - Badge “mapeamento pendente”
- **Abas:** CPF (ativa) / CNPJ (inativa)

#### Configuração e Deploy Local
- `.env.example` completo com comentários.
- `setup.sh` e `setup.bat` automatizam instalação e criação de atalho “Fetch Saúde”.
- Execução local via `make setup` (alternativa técnica).

#### Estrutura de pastas
```
saude-fetch/
├─ app/
│  ├─ backend/
│  │  ├─ server.py
│  │  ├─ drivers/
│  │  ├─ utils/auth.py
│  │  └─ data/logs/
│  ├─ frontend/
│  └─ data/
├─ scripts/
│  ├─ setup.sh
│  └─ setup.bat
├─ Docs/
├─ .env.example
└─ README.md
```

#### Testes e Logs
- Agente automático não é mais necessário após merge final.
- Testes locais confirmam estabilidade completa do fluxo.