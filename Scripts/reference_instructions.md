# Referência de Uso — mappings\_reference.json

## Finalidade

O arquivo `mappings_reference.json` é o **blueprint central** para a automação do Neo (emergent.sh) ou de qualquer outro desenvolvedor que implemente consultas automáticas às operadoras de saúde.

Ele descreve, para cada operadora, **onde está o arquivo DOM base**, **qual é o formato do arquivo**, e **quais critérios determinam sucesso ou falha na busca**.&#x20;

---

## Estrutura do arquivo

```json
{
  "_meta": {
    "mappings_dir": "caminho absoluto da pasta docs/mappings",
    "note": "Instruções gerais sobre o conteúdo."
  },
  "providers": {
    "unimed": {
      "source_file": "unimed.html",
      "status": "confirmed",
      "success_criteria": "Retorna dados de plano e cooperativa",
      "failure_criteria": "Mensagem de CPF inválido",
      "dom_snapshot": {
        "format": "html",
        "path": "docs/mappings/unimed.html",
        "size_bytes": 172340
      },
      "notes": "Mapeamento manual confirmado."
    },
    "sulamerica": {
      "source_file": "sulamerica.html",
      "status": "placeholder",
      "success_criteria": "Exige login (CNPJ)",
      "failure_criteria": "Acesso negado sem autenticação",
      "dom_snapshot": {
        "format": "text",
        "path": "docs/mappings/sulamerica.html",
        "size_bytes": 0
      },
      "notes": "Placeholder aguardando credenciais e teste de login."
    }
  }
}
```

---

## Campos principais

| Campo              | Descrição                                                                                         |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| `source_file`      | Nome do arquivo local (HTML ou JSON) com o DOM exportado.                                         |
| `status`           | `confirmed` se o mapeamento é final; `placeholder` se ainda depende de credenciais ou validação.  |
| `success_criteria` | Texto usado para identificar sucesso no resultado da consulta.                                    |
| `failure_criteria` | Texto usado para identificar falha (CPF/CNPJ inexistente, erro, etc.).                            |
| `dom_snapshot`     | Metadados do arquivo: tipo, caminho e tamanho. O Neo deve usar o `path` para carregar o DOM real. |
| `notes`            | Observações sobre o estado do mapeamento.                                                         |

---

## Como usar este arquivo

### 1. **Leitura e identificação de contexto**

Abrir `mappings_reference.json` e iterar sobre `providers`. Para cada provedor:

- Verificar o campo `status`. Se for `placeholder`, o processo deve ser ignorado até novo mapeamento.
- Carregar o arquivo indicado em `dom_snapshot.path`.

### 2. **Interpretação do DOM**

Com o arquivo DOM em mãos (HTML real), o Neo deve:

- Identificar os elementos mencionados no `success_criteria` e `failure_criteria` dentro do HTML.
- Definir seletores (`xpath`/`css`) para esses elementos.
- Gerar código automatizado de scraping (ex.: Selenium, Playwright ou BeautifulSoup) capaz de localizar esses elementos nas execuções futuras.

### 3. **Execução e Validação**

Durante a execução:

- Se o `success_criteria` for encontrado → `status = success`.
- Se o `failure_criteria` for encontrado → `status = not_found`.
- Caso nenhum critério apareça → `status = unknown`, logar snapshot para análise manual.

### 4. **Atualização e versionamento**

- Atualizar o arquivo `mappings_reference.json` sempre que um DOM for revalidado ou alterado.
- O versionamento segue o padrão incremental (novas entradas no topo, sem apagar o histórico).

---

## Regras específicas por operadora

| Operadora          | Critério de sucesso                    | Critério de falha                   | Observação                                                 |
| ------------------ | -------------------------------------- | ----------------------------------- | ---------------------------------------------------------- |
| **Unimed**         | Retorna dados de plano e cooperativa   | Mensagem de CPF inválido            | DOM estável e de fácil parsing.                            |
| **Amil**           | Exibe nome do plano (ex.: OURO)        | Modal “não encontrado”              | Verificar componentes React dinâmicos.                     |
| **Bradesco**       | Modal “Selecione o beneficiário”       | Modal “Beneficiário não encontrado” | DOM carrega em modal; requer busca por texto interno.      |
| **Seguros Unimed** | Exibe informações do plano diretamente | Modal de erro / CPF inválido        | Layout estático; parsing direto via BeautifulSoup.         |
| **SulAmérica**     | Exige login (CNPJ)                     | Acesso negado sem autenticação      | Pipeline autenticado; placeholder até credenciais válidas. |

---

## Integração com Pipelines

- **Pipeline CPF** usa: `unimed`, `amil`, `bradesco`, `unimed_seguros`.
- **Pipeline CNPJ** usa: `sulamerica`.



---

## Boas práticas para desenvolvedores

1. **Nunca sobrescreva** o arquivo `mappings_reference.json` manualmente. Use o script `generate_mappings_reference.py` para recriá-lo.
2. **Valide o formato** antes de executar: o campo `_meta.mappings_dir` deve existir e apontar para a pasta correta.
3. \*\*Adicione comentários somente via \*\***notes** — não altere chaves existentes.
4. **Confirme o encoding** dos arquivos HTML (`UTF-8`) para evitar erros de leitura.

---

**Resumo:** este arquivo é o ponto de verdade (“source of truth”) para o comportamento esperado de cada operadora.&#x20;
