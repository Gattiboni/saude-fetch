# CHANGELOG — saude-fetch

## 2025-10-24 — Mapeador Selenium e ajustes de ambiente
- Substituição completa do Playwright por **Selenium + ChromeDriverManager** (versão estável para Windows/Python 3.12).
- Adição de logs automáticos e snapshots HTML.
- Implementação de login SulAmérica com credenciais de teste.
- Criação de `map_sites_selenium.py` em `/Scripts/`.
- Atualização do `requirements.txt` para dependências compatíveis.
- Execuções validadas para Unimed e Seguros Unimed.
- Observação: Amil, Bradesco e SulAmérica exigem tratamento dinâmico adicional (JS/Login).