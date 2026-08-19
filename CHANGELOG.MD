# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue o padrão [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

### Adicionado

- Camada única de dez indicadores operacionais e ranking das regras acionadas.
- Abas executivas `Ranking de Regras` e `Dicionário`, totalizando oito abas.
- Geração automática de `resumo_executivo.md` a partir dos mesmos indicadores utilizados no Excel.
- Serviço `api_ml` com FastAPI, endpoints `GET /health` e `POST /predict` e modelo serializado carregado no ciclo de vida da aplicação.
- Serviço `api_ml` no Docker Compose, com porta `8000` exposta e healthcheck baseado em `/health`.
- Cliente resiliente `MLClient` em `src/ml_client.py` para consumo isolado da API de Machine Learning.
- Circuit breaker que abre após cinco falhas consecutivas e permite reset manual.
- Camada `src/item_processor.py` para integrar a decisão de ML após a validação das regras RN01–RN12.
- Fallback `REVISAO_ML_OFFLINE` quando a API ML está indisponível.

### Alterado

- O fluxo de geração do relatório passou a utilizar o `item_processor` para os registros ambíguos, preservando as regras RN01–RN12 como fonte primária de classificação.
- A API ML normaliza as variações `EM ANALISE`, `EM ANÁLISE` e `EM_ANALISE` para a codificação utilizada pelo modelo.
- A documentação foi atualizada com os comandos de execução, validação da API, fallback e circuit breaker.

## [1.0.0]

### Corrigido

- Correção do erro de importação relativa no ambiente de testes.
- Substituição de importações relativas por absolutas e adição dos arquivos `__init__.py` nas pastas `src/` e `tests/`.

## [1.1.0] - 2026-08-03

### Adicionado

- Automação web com Playwright para login e cadastro de lotes.
- Locators semânticos, esperas dinâmicas, tratamento de timeout e evidências em screenshot.
- Logs estruturados em JSON com `bot_id` e `execution_id`.
- Containerização do bot e orquestração inicial com Docker Compose.

### Alterado

- Atualização das dependências e da configuração de URLs para execução local e em contêiner.
