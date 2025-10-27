==============================
## DOCUMENTO: OPERATIONS.md
==============================

### Execução Local — Pós-Merge Neo-1

#### Setup e inicialização
1. Clonar o repositório e confirmar branch `main` atualizada.
2. Rodar o script correspondente ao sistema operacional:
   - Windows: `setup.bat`
   - Linux/Mac: `bash setup.sh`
3. O script cria `.venv`, instala dependências, copia `.env.example` para `.env` e gera atalho **“Fetch Saúde”** no desktop.
4. Após o setup, abrir o atalho ou acessar manualmente `http://localhost:3000`.

#### Login
- Entrar com credenciais definidas no `.env` (`APP_USER`, `APP_PASS`).
- Token de sessão é válido por 24h.

#### Consulta CPF
1. Selecionar aba “Consulta CPF” (ativa por padrão).
2. Fazer upload do CSV com lista de CPFs.
3. Acompanhar o progresso percentual (em %) e visualizar o resumo final.
4. Fazer download dos resultados em CSV, JSON ou XLSX.
   - XLSX inclui colunas fixas: `CPF | AMIL | BRADESCO | UNIMED | UNIMED SEGUROS`.

#### Consulta CNPJ
- Aba visível, mas funcionalidade **on hold** (SulAmérica exige autenticação).

#### Reload de mappings
- Endpoint: `POST /api/mappings/reload`
- Uso: após inserir novos arquivos JSON em `/docs/mappings`.
- Permite recarregar configurações sem reiniciar o backend.

#### Logs
- Log único por execução: `app/data/logs/last_run.log`.
- Exportação opcional (manual).

#### Teste e Validação
- Teste funcional local com `Lista CPF.csv`.
- Esperado: resultados “mapeamento pendente” até inclusão de mappings reais.
