# Lista de Tarefas — Projeto saude-fetch (versão final revisada para Neo)

## 1. Estrutura e contexto

- Garantir que o repositório `saude-fetch` contenha apenas documentação, parâmetros e referências de execução.
- Todo o código de execução e automação será gerado e operado pelo **Neo (emergent.sh)**.

---

## 2. Pipelines

### 2.1 Pipeline CPF

- Operadoras: **Unimed**, **Amil**, **Bradesco**, **Seguros Unimed**.
- Funções:
  - Acessar automaticamente os links definidos.
  - Mapear completamente o comportamento das páginas (inputs, botões, modais e respostas).
  - Registrar e classificar as respostas conforme os critérios binários de sucesso/falha.
  - Gerar um output consolidado com o mapeamento validado.

### 2.2 Pipeline CNPJ

- Operadora: **SulAmérica**.
- Mantido em *hold* até disponibilização das credenciais de teste.
- Deve seguir o mesmo padrão estrutural e de logs do pipeline CPF.

---

## 3. Interface e mecânica da ferramenta

- Implementar lógica para consultas em lote (ex.: upload de CSV com múltiplos CPFs).
- Garantir performance estável para volumes variáveis (de 3 até milhares de CPFs).
- Exibir resultados com status, plano e mensagens correspondentes.
- Gerar payloads no formato padronizado (`JSON` e `CSV`) conforme as especificações do projeto.

---

## 4. Mapeamento e outputs

- Gerar **mapa completo e correto** de cada operadora, contendo campos de entrada, botões e critérios de sucesso/falha.
- Consolidar os resultados em `/docs/mappings/results/`.
- Produzir arquivos individuais e um consolidado final (`mappings_reference.json`) para referência futura.

---

## 5. Parametrização

- Usar os CPFs de teste fornecidos como baseline “true”:
  | Operadora      | URL                                                                                                                                                                                              | CPF de teste   |
  | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- |
  | Unimed         | [https://www.unimed.coop.br/site/guia-medico#/](https://www.unimed.coop.br/site/guia-medico#/)                                                                                                   | 958.817.007-91 |
  | Amil           | [https://www.amil.com.br/institucional/#/servicos/saude/rede-credenciada/amil/busca-avancada](https://www.amil.com.br/institucional/#/servicos/saude/rede-credenciada/amil/busca-avancada)       | 162.366.007-67 |
  | Bradesco       | [https://www.bradescoseguros.com.br/clientes/produtos/plano-saude/consulta-de-rede-referenciada](https://www.bradescoseguros.com.br/clientes/produtos/plano-saude/consulta-de-rede-referenciada) | 876.259.387-00 |
  | Seguros Unimed | [https://www.segurosunimed.com.br/guia-medico/](https://www.segurosunimed.com.br/guia-medico/)                                                                                                   | 006.105.100-45 |

---

## 6. Testes e validação

- Testar as consultas em lote usando os CPFs base e novos dados.
- Garantir consistência dos retornos e estabilidade das execuções.
- Registrar métricas de tempo, taxa de sucesso e logs de eventuais falhas.

---

**Resultado esperado:** pipelines funcionais e documentados, outputs claros e estruturados, e toda a automação sob controle e execução do Neo (Emergent).

