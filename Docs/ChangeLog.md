# CHANGELOG — saude-fetch

## 2025-10-26 — Separação dos pipelines e integração via Neo (Emergent)
- Introdução de dois pipelines distintos: **CPF** (consultas públicas) e **CNPJ** (SulAmérica autenticada).
- Atualização de documentação e scripts conforme mapeamentos validados (Unimed, Amil, Bradesco, Seguros Unimed).
- Integração completa com o **Neo (emergent.sh)** para geração automática de conectores e execução em lote.
- Manutenção de logs e snapshots em `/docs/mappings/`.
- Documentação reorganizada para refletir a sequência: mapeamento → consolidação → execução automatizada.

## 2025-10-24 — Mapeador Selenium e ajustes de ambiente
- Substituição completa do Playwright por **Selenium + ChromeDriverManager** (versão estável para Windows/Python 3.12).
- Adição de logs automáticos e snapshots HTML.
- Implementação de login SulAmérica com credenciais de teste.
- Criação de `map_sites_selenium.py` em `/Scripts/`.
- Atualização do `requirements.txt` para dependências compatíveis.
- Execuções validadas para Unimed e Seguros Unimed.
- Observação: Amil, Bradesco e SulAmérica exigem tratamento dinâmico adicional (JS/Login).