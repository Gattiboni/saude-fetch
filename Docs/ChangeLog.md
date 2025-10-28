==============================
## DOCUMENTO: CHANGELOG.md
==============================

### [2025-10-27] — Integração Neo-1 concluída e merge na main
- Integração completa das features entregues pela branch **Neo-1**:
  - Implementação de drivers para unimed, amil, bradesco, Seguros unimed e SulAmérica (on hold com auth inativo).
  - Adição de autenticação simples com token JWT e login via usuário/senha definidos em `.env`.
  - Implementação de rotas `/api` para health, auth, jobs, reload de mappings e resultados (CSV/JSON/XLSX).
  - Processamento assíncrono com barra de progresso e geração de arquivo XLSX padronizado (`CPF | amil | bradesco | unimed | unimed SEGUROS`), mantendo CPF formatado `xxx.xxx.xxx-xx`.
  - Simplificação de logs com sobrescrita única em `last_run.log`.
  - Implementação de throttling configurável via `.env` (`FETCH_MIN_DELAY`, `FETCH_MAX_DELAY`) e rotação leve de user-agents.
  - Criação de UI com login, abas CPF (ativa) e CNPJ (inativa), resumo por job e indicadores “mapeamento pendente”.
  - Inclusão de scripts `setup.sh` e `setup.bat`, `.env.example` e atalho automático “Fetch Saúde”.
- Merge concluído preservando `Docs/` e `README.md` originais.
- Testes finais validados localmente com fluxo completo (login → upload → processamento → download).

### [2025-10-20] — Estrutura inicial dos pipelines
- Definição dos pipelines CPF e CNPJ (on hold).
- Configuração básica de FastAPI + React + MongoDB.
- Implementação do primeiro fluxo de upload CSV e export JSON/CSV.