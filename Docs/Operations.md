# OPERATIONS — saude-fetch (Revisado)

## 2025-10-26 — Operação dos pipelines Neo (Emergent)
### Stack atual
- Python 3.12 + Selenium + ChromeDriverManager (para testes locais).
- Neo (emergent.sh) responsável por execução, controle de fluxo e integração com FastAPI.
- Logs e snapshots mantidos em `/docs/mappings/`.

### Execução via Neo
- `pipeline_cpf.py`: consultas públicas (Unimed, Amil, Bradesco, Seguros Unimed).
- `pipeline_cnpj.py`: consulta autenticada (SulAmérica).

### Boas práticas
- Garantir que todos os mapeamentos estejam atualizados em `/docs/mappings/`.
- O Neo deve ler os arquivos de referência `mappings_reference.json` para identificar seletores e fluxos.
- Logs são gerados automaticamente pelo sistema, preservando rastreabilidade.

### Troubleshooting
| Problema | Causa provável | Ação |
|-----------|----------------|------|
| Pipeline não inicia | Mapeamentos incompletos | Verificar JSONs em `/docs/mappings/` |
| Falha na autenticação SulAmérica | Credenciais inválidas | Atualizar `.env` local de teste |
| Resultados inconsistentes | DOM alterado pelo provedor | Regenerar HTML base e consolidar novamente |

## 2025-10-24 — Ambiente e execução do mapeador Selenium
- Stack de automação local (Python 3.12 + Selenium 4.25 + ChromeDriverManager 4.0.2).
- Execução via `map_sites_selenium.py`.
- Boas práticas de execução e logs preservadas.