==============================
## DOCUMENTO: DECISIONLOG.md
==============================

### [2025-10-27] — Decisões da fase Neo
- **Entrega sem empacotamento automático:** o build final entrega apenas o código funcional; o empacotamento e execução local são realizados manualmente.
- **Autenticação mínima:** login local obrigatório via `.env` (APP_USER/PASS) com token JWT.
- **Logs otimizados:** apenas o último log completo é mantido (`last_run.log`), exportação manual opcional.
- **Padrão de saída:** XLSX consolidado com cabeçalhos fixos e CPF formatado como texto.
- **Throttling configurável:** via `.env`, garantindo estabilidade e prevenção de bloqueio por scraping.
- **Reload de mappings:** endpoint `/api/mappings/reload` ativa leitura dos JSONs sem reinício.
- **Docs e README imutáveis:** sempre preservados durante merges e sincronizações.
- **Fluxo de testes local:** execução validada internamente, sem dependência de agentes externos após o merge final.

### [2025-10-22] — Decisões de arquitetura inicial
- Separação de pipelines CPF/CNPJ.
- Exportação padronizada (JSON/CSV).
- Estrutura modular de drivers e logs por operadora.
- Uso de MongoDB com UUIDs como identificadores únicos.