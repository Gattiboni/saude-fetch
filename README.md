# Projeto **saude-fetch** — Guia e Folha de Rosto (ClickUp)

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
3. **Mapeador de DOM (Manual)** – Script Python para mapeamento estrutural dos sites.
4. **Desenvolvimento via Neo (Emergent)** – Geração automatizada dos conectores, pipeline e interface web.
5. **Testes e Validação** – Execução de testes automáticos, avaliação de performance e ajustes.
6. **Entrega Final** – Documentação, versionamento e publicação no Vercel.

---

## Mapeador de DOM

Script em Python executado localmente para capturar a estrutura HTML (estática e dinâmica) dos sites das operadoras. Gera arquivos JSON com mapeamento de elementos essenciais: inputs, botões, labels e identificadores semânticos. Esses arquivos servem como referência para o desenvolvimento automatizado realizado pelo Neo.

---

## Desenvolvimento via Neo (Emergent)

Todas as implementações de conectores, pipelines e interface serão geradas via **Neo (Emergent)**, conforme instruções curtas e direcionadas. O foco é garantir conformidade com a arquitetura definida, deixando espaço para otimização e criatividade do modelo.

**Regras básicas para prompts do Neo:**

- Respeitar interfaces e módulos definidos.
- Implementar apenas o que for solicitado na sprint.
- Executar apenas testes automáticos (pytest).
- Retornar sempre com explicação objetiva da implementação.

---

## Documentação e Entregas

Todos os arquivos de documentação estão em `/docs/`:

- `README.md` — guia principal do projeto.
- `Architecture.md` — visão técnica e diagramas.
- `DecisionLog.md` — decisões de arquitetura e ajustes.
- `Changelog.md` — histórico de alterações e entregas.

---

## Cronograma

- **Início:** 23/10/2025
- **Conclusão prevista:** 27/10/2025
- O trabalho será executado de forma contínua (incluso final de semana) para entrega até segunda-feira.

---

## Responsável

**Alan Gattiboni** — Especialista em Automação e Integração.\
Coordenação técnica, execução de scripts locais e orquestração via Neo.

---

## Status Atual

- Estrutura do projeto definida.
- Cronograma aprovado e distribuído.
- Mapeador de DOM em desenvolvimento.
- Próximas etapas: execução das sprints via Neo e consolidação da entrega final.

