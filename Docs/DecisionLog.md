# DECISION_LOG — saude-fetch

## 2025-10-24 — Adaptação para qualificação por tipo de consulta
**Decisão:** Separar o fluxo de qualificação entre CPFs e CNPJs para melhor compatibilidade com interfaces que exigem autenticação (ex.: SulAmérica).
**Motivos:**
- SulAmérica requer login e navegação dedicada; demais operadoras são públicas.
- Evita falhas de sessão e simplifica futuras integrações de UI.
**Impactos:**
- No front-end haverá dois botões distintos: "Qualificar CPF" e "Qualificar CNPJ".
- Cada botão acionará o fluxo correspondente (público ou autenticado).

## 2025-10-24 — Troca de Playwright por Selenium
**Decisão:** Mudar a stack de automação de Playwright para **Selenium**, garantindo compatibilidade com Windows e estabilidade de execução.
**Motivos:**
- Playwright apresentava falhas de build e cache (versões de Chromium conflitantes).
- Selenium é amplamente suportado e mais previsível para scripts locais.
**Impactos:**
- Novo script `map_sites_selenium.py` substitui o anterior.
- Dependências ajustadas (`selenium`, `webdriver-manager`).
- Processo de mapeamento permanece igual — snapshots HTML e JSON com elementos DOM.

## 2025-10-23 — Adoção de estrutura rastreável para documentação
**Decisão:** Consolidar todos os documentos em `/docs/` com histórico incremental no topo de cada arquivo.
**Motivo:** Garantir rastreabilidade total e auditabilidade contínua.
**Impacto:** Novo fluxo de versionamento documental unificado.