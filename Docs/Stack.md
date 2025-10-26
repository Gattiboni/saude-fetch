# STACK — saude-fetch (Revisado)

## 2025-10-26 — Integração final com Neo (Emergent)
**Objetivo:** padronizar o ambiente e delegar automação ao Neo.

### 1. Componentes principais
| Componente | Tecnologia |
|-------------|-------------|
| Linguagem | Python 3.12 |
| Automação | Selenium + ChromeDriverManager / Neo (emergent.sh) |
| Parsing HTML | BeautifulSoup4 + lxml |
| Logging | logging (nativo Python) / emergent logs |
| Output | JSON + HTML snapshot / JSON consolidado |

### 2. Estrutura atualizada
```bash
saude-fetch/
├── Scripts/
│   ├── map_sites_full_v2.py
│   ├── pipeline_cpf.py
│   ├── pipeline_cnpj.py
│   └── requirements.txt
├── docs/
│   ├── mappings/
│   │   ├── *.json
│   │   └── *.html
│   ├── CHANGELOG.md
│   ├── DECISION_LOG.md
│   ├── OPERATIONS.md
│   └── STACK.md
└── README.md
```

### 3. Fluxo de operação
1. Neo lê os mapeamentos e gera automaticamente os conectores.
2. Execução dos pipelines CPF e CNPJ.
3. Consolidação dos resultados em `consolidated_mappings.json`.
4. Logs e snapshots versionados em `/docs/mappings/`.

### 4. Dependências
```bash
selenium==4.25.0
webdriver-manager==4.0.2
beautifulsoup4==4.12.3
lxml==4.9.3
requests==2.32.3
python-dotenv==1.0.1
pandas==2.2.3
colorama==0.4.6
```

### 5. Observações
- Neo (Emergent) é responsável pelo deploy e execução orquestrada.
- Scripts locais servem apenas para depuração e validação manual.
- Estrutura mantida compatível com o padrão incremental de documentação.

## 2025-10-24 — Versão Selenium
**Objetivo:** automatizar o mapeamento estrutural de portais de operadoras de saúde (Amil, Bradesco, SulAmérica, Unimed e Seguros Unimed).
- Componentes, fluxo e dependências originais mantidos.
- Atualização de compatibilidade confirmada para Windows e execução local.

---

✅ **Documentação consolidada — versão 2025-10-26.**  
Todos os documentos seguem o padrão incremental, com novas entradas sempre no topo.