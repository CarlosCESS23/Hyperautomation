# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue o padrão [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

## [1.2.0] - 2026-08-24

### Adicionado

- Serviço `api_ml` com FastAPI, endpoints `GET /health` e `POST /predict` e carregamento do modelo Random Forest durante a inicialização.
- Cliente resiliente `MLClient` para isolar o consumo da API e abrir o circuit breaker após cinco falhas consecutivas.
- Camada `item_processor` para consultar o Machine Learning somente após a classificação das regras RN01–RN12.
- Auditoria das chamadas online e offline, com status, latência, classe prevista, probabilidade, nível de confiança e detalhe do erro.
- Aba `Decisões de ML` no relatório Excel, preenchida com as chamadas realmente realizadas durante o processamento.
- Fallback `REVISAO_ML_OFFLINE` para registros ambíguos quando a API não fornece uma predição.
- Teste integrado de sabotagem da API, cobrindo sete chamadas auditadas, cinco tentativas HTTP e abertura do circuit breaker.

### Alterado

- O fluxo de leitura passou a processar todas as dez abas diárias antes de retornar os registros validados.
- Lotes duplicados passaram a ser preservados para que a segunda ocorrência continue permitindo a aplicação da RN11.
- Uma única instância de `AuditoriaDecisoesML` passou a acompanhar o fluxo completo e alimentar o log e o relatório Excel.
- A API passou a normalizar `EM ANALISE`, `EM ANÁLISE` e `EM_ANALISE` para a codificação esperada pelo modelo.
- O healthcheck do serviço `api_ml` passou a validar o JSON de `/health` e considerar o container saudável somente quando `modelo_carregado` é `true`.

### Corrigido

- Retorno antecipado de `ler_e_validar()`, que encerrava o processamento após a primeira aba e fazia o E2E encontrar somente dois dos vinte registros esperados.
- Descarte de lotes duplicados causado pelo processamento condicionado ao bloco da primeira ocorrência.
- Exceção ao auditar respostas `None` durante a indisponibilidade da API ML.
- `NameError` da função auxiliar `_campo`, mantendo-a disponível no escopo do módulo.
- Ausência de `payload_ml` na chamada do classificador dentro do fluxo de auditoria.
- Falha de coleta do Pytest causada por arquivos unitário e de integração com o mesmo nome de módulo.
- Ausência das decisões offline no log estruturado e na aba `Decisões de ML`.

## [1.1.0] - 2026-08-03

### Adicionado

- Automação web com Playwright para login e cadastro de lotes.
- Locators semânticos, esperas dinâmicas, tratamento de timeout e evidências em screenshot.
- Logs estruturados em JSON com `bot_id` e `execution_id`.
- Containerização do bot e orquestração inicial com Docker Compose.

### Alterado

- Atualização das dependências e da configuração de URLs para execução local e em contêiner.

## [1.0.0]

### Corrigido

- Correção do erro de importação relativa no ambiente de testes.
- Substituição de importações relativas por absolutas e adição dos arquivos `__init__.py` nas pastas `src/` e `tests/`.
