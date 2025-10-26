# Projeto **saude-fetch** — Guia e Folha de Rosto (Revisado)

**Repositório:** [https://github.com/Gattiboni/saude-fetch](https://github.com/Gattiboni/saude-fetch)

---

## Visão Geral

O **saude-fetch** é uma ferramenta de automação projetada para realizar consultas públicas em portais de operadoras de saúde (Amil, Bradesco, SulAmérica, Unimed e Seguros Unimed) a partir de listas de CPFs ou CNPJs, retornando informações sobre planos ativos, categorias e status.

O sistema foi desenhado para ser modular, seguro e escalável — respeitando boas práticas de scraping responsável e conformidade legal. O projeto adota uma arquitetura limpa, separando o núcleo em módulos independentes e permitindo que cada operadora tenha seu próprio driver.

---

## Estrutura do Projeto

| Módulo             | Função                                                         |
| ------------------ | -------------------------------------------------------------- |
| **core/**          | Núcleo principal: logs, exceções e controle de execução.       |
| **config/**        | Variáveis de ambiente e parâmetros globais.                    |
| **utils/**         | Funções auxiliares (tratamento de CPF/CNPJ, CSV/Excel, tempo). |
| **drivers/**       | Conectores específicos por operadora.                          |
| **pipelines/**     | Orquestração de execuções em lote e geração de relatórios.     |
| **web/**           | API e frontend mínimo para upload/download de arquivos.        |
| **docs/mappings/** | Saída do mapeador DOM com estrutura detalhada de cada site.    |

---

## Fases Principais (Sprints)

1. **Preparação e Ambiente** – Criação do repositório, configuração local e documentação base.
2. **Núcleo e Estrutura** – Definição da arquitetura e implementação de módulos fundamentais.
3. **Mapeamento e Consolidação** – Exportação manual dos HTMLs e geração de JSONs de referência. Consolidação dos mapeamentos para definir o comportamento binário das operadoras (CPF válido / inválido).
4. **Desenvolvimento via Neo (Emergent)** – Geração automatizada dos conectores, pipelines e interface web pelo Neo (emergent.sh).
5. **Testes e Validação** – Execução de testes automáticos, avaliação de performance e ajustes.
6. **Entrega Final** – Documentação, versionamento e publicação.

---

## Mapeamento de DOM e Regras de Consulta

O processo de mapeamento é manual e serve como base para o comportamento esperado de cada operadora. As consultas seguem um padrão binário:

| Operadora          | Critério de sucesso                    | Critério de falha                   |
| ------------------ | -------------------------------------- | ----------------------------------- |
| **Unimed**         | Retorna dados de plano e cooperativa   | Mensagem de CPF inválido            |
| **Amil**           | Exibe nome do plano (ex.: "OURO")      | Modal “não encontrado”              |
| **Bradesco**       | Modal “Selecione o beneficiário”       | Modal “Beneficiário não encontrado” |
| **Seguros Unimed** | Exibe informações do plano diretamente | Modal de erro / CPF inválido        |
| **SulAmérica**     | Exige login (CNPJ)                     | Acesso negado sem autenticação      |

Esses comportamentos são consolidados em `/docs/mappings/mappings_reference.json`, usado como blueprint para o Neo.

---

## Desenvolvimento via Neo (Emergent)

Todas as implementações de conectores, pipelines e interface são geradas e executadas pelo **Neo (emergent.sh)**, que assume a camada de automação completa.

**Funções do Neo:**

* Geração automática dos scripts `pipeline_cpf.py` e `pipeline_cnpj.py`.
* Criação de conectores baseados nos JSONs de mapeamento validados.
* Execução orquestrada das consultas em lote, com logs e exportação de resultados.
* Deploy da aplicação e integração com camada FastAPI + frontend.

**Diretrizes para prompts do Neo:**

* Seguir os mapeamentos e regras binárias confirmadas.
* Respeitar a estrutura modular e a documentação existente.
* Gerar resultados consistentes com os artefatos em `/docs/mappings/`.

---

## Documentação e Entregas

Todos os arquivos de documentação estão em `/docs/`:

* `README.md` — guia principal do projeto.
* `Architecture.md` — visão técnica e diagramas.
* `DecisionLog.md` — decisões de arquitetura e ajustes.
* `Changelog.md` — histórico de alterações e entregas.

---

## Cronograma

* **Início:** 23/10/2025
* **Conclusão prevista:** 27/10/2025
* O trabalho será executado de forma contínua (inclui final de semana) até a entrega final.

---

## Responsável

**Alan Gattiboni** — Especialista em Automação e Integração.
Coordenação técnica, execução de scripts locais e orquestração via Neo.

---

## Status Atual

* Estrutura do projeto definida.
* Mapeamentos de DOM concluídos e validados.
* Consolidação de dados em andamento.
* Próximas etapas: geração dos pipelines via Neo e integração completa.
