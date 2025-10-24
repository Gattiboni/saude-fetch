# STACK — saude-fetch

## 2025-10-24 — Versão Selenium
**Objetivo:** automatizar o mapeamento estrutural de portais de operadoras de saúde (Amil, Bradesco, SulAmérica, Unimed e Seguros Unimed).

### 1. Componentes principais
| Componente | Tecnologia |
|-------------|-------------|
| Linguagem | Python 3.12 |
| Automação | Selenium + ChromeDriverManager |
| Parsing HTML | BeautifulSoup4 + lxml |
| Logging | logging (nativo Python) |
| Output | JSON + HTML snapshot |

### 2. Estrutura de scripts
```
saude-fetch/
├── Scripts/
│   ├── map_sites_selenium.py
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
1. Executar o script de mapeamento.
2. Geração automática de snapshots e JSON.
3. Validação dos arquivos (estrutura e encoding).
4. Integração futura com Neo (para geração de conectores automáticos).

### 4. Dependências
```bash
selenium==4.25.0
webdriver-manager==4.0.2
pandas==2.2.3
beautifulsoup4==4.12.3
requests==2.32.3
python-dotenv==1.0.1
colorama==0.4.6
lxml==4.9.3
```

### 5. Observações
- Projeto isolado, sem dependência externa.
- Totalmente executável em Windows.
- Pode ser adaptado para execução headless no Vercel ou Railway se necessário.

---

> Documentação consolidada – Projeto **saude-fetch**, versão 2025-10-24.
> Todos os documentos seguem o padrão incremental, com novas entradas sempre no topo.
