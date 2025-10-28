# Especificações Técnicas — Projeto saude-fetch

## 1. Propósito

Definir os requisitos técnicos essenciais para a implementação completa do sistema **saude-fetch**, garantindo clareza sobre o escopo e os resultados obrigatórios, sem restringir a autonomia criativa ou técnica na construção das soluções.

---

## 2. Estrutura Geral

O projeto baseia-se em dois pipelines independentes:

### Pipeline 1 — CPF

- Operadoras: **unimed**, **amil**, **bradesco**, **Seguros unimed**.
- Realizar consultas públicas e não autenticadas de CPFs, retornando informações estruturadas de planos e categorias.
- Gerar evidências e resultados consistentes conforme os critérios binários de sucesso e falha.

### Pipeline 2 — CNPJ

- Operadora: **SulAmérica**.
- Executar consultas autenticadas via login com CNPJ. Atualmente em *hold* até a liberação de credenciais de teste.
- Manter a mesma estrutura e formato de resultados do pipeline CPF.

---

## 3. Requisitos Essenciais (Must Haves)

### 3.1. Mapeamento e automação

- Mapear completamente o **DOM** de cada página de operadora.
- Localizar o campo de entrada (CPF ou CNPJ), acionar o botão de busca e capturar o resultado exibido.
- Distinguir automaticamente entre sucesso, falha e comportamento indefinido.
- Salvar resultados de forma auditável (JSON e logs estruturados).

### 3.2. Consultas em lote

- Aceitar **upload de arquivos CSV** contendo múltiplos CPFs/CNPJs.
- Processar de forma escalável, suportando dezenas a milhares de registros.
- Tratar cada item individualmente, com status registrado (success/failure/unknown).

### 3.3. Interface e experiência

- Criar uma interface web simples, intuitiva e responsiva.
- Incluir obrigatoriamente:
  - Campo para upload de CSV.
  - Indicadores de progresso (processando / concluído / falha parcial).
  - Exibição resumida de resultados.
- Garantir design claro e eficiente.

### 3.4. Outputs e estrutura de dados

- Exportar resultados em formatos **JSON** e **CSV**.
- Incluir em cada registro:
  - Identificador (CPF/CNPJ)
  - Operadora
  - Status da consulta (success / failure / unknown)
  - Informações relevantes do plano (quando aplicável)
  - Timestamp e logs de execução.
- Consolidar comportamentos esperados das operadoras em arquivo apropriado.

### 3.5. Logs e rastreabilidade

- Gerar logs detalhados e legíveis em cada execução, contendo data, hora e contexto da operação.
- Separar logs de erro e sucesso para facilitar auditoria e depuração.

---

## 4. Integração e modularidade

- Estruturar o sistema de forma modular, permitindo atualização, teste e execução independente de cada pipeline.
- Adaptar scripts conforme alterações nas páginas das operadoras, mantendo o padrão de saída.
- Manter a automação e a inteligência de execução sob controle e rastreabilidade.

---

## 5. Critérios de Sucesso

- Executar de forma completa e estável os pipelines CPF e CNPJ.
- Garantir resultados coerentes e reproduzíveis com os CPFs/CNPJs de teste.
- Disponibilizar interface funcional para uploads e visualização dos resultados.
- Manter outputs padronizados e documentação atualizada.

---

## 6. Liberdade de Implementação

- Utilizar qualquer linguagem, framework ou biblioteca adequada.
- Definir livremente estratégias de scraping, automação ou renderização.
- Organizar a estrutura interna dos scripts e métodos de controle de fluxo conforme necessidade.

O que não é negociável:

- **Conformidade com os critérios binários e estrutura de outputs.**
- **Rastreabilidade completa e geração de evidências.**
- **Execução segura, ética e conforme boas práticas de scraping responsável.**

---

## 7. Observações Finais

Este documento serve como referência técnica e operacional, definindo o padrão de entrega e qualidade esperada.\
Tudo o que não está explicitamente proibido é permitido, desde que atenda às condições acima e mantenha rastreabilidade e consistência nos resultados.

No caso de qualquer ambiguidade, qualquer assistente deve parar o que está construindo e interagir fazendo quantas perguntas forem necessárias.

