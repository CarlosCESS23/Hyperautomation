# Changelog

Este arquivo registra mudanças relevantes do código que está presente no
repositório. O formato segue as categorias de [Keep a
Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

### Adicionado

- Camada única de dez indicadores operacionais e ranking das regras acionadas.
- Abas executivas `Ranking de Regras` e `Dicionário`, totalizando oito abas.
- Geração automática de `resumo_executivo.md` a partir dos mesmos indicadores
  utilizados no Excel.
- Teste de integração consolidado da Aula 24 e checklist reproduzível de
  evidências.

### Alterado

- O dashboard `Resumo` agora apresenta os dez indicadores e preserva os dois
  gráficos nativos do Excel.
- A documentação foi revisada para refletir a automação web atual baseada em
  Playwright, sua execução local e via Docker Compose, as variáveis efetivamente
  usadas e as saídas geradas.

## [1.0.0]

### Adicionado

### Corrigido
* **Resolução de Importações:** Correção do erro `ImportError: attempted relative import` no ambiente de testes.
* **Estrutura de Pacotes:** Substituição de importações relativas por absolutas e adição dos arquivos `__init__.py` nas pastas `src/` e `tests/`.


## [v1.1.0] - 2026-08-03

### Adicionado
* **Automação Web Avançada (Playwright):** Implementada a navegação e interação com o portal web de "Acesso ao Sistema" e "Cadastro de Lotes", injetando os dados auditados.
* **Locators Semânticos:** Substituição de seletores CSS e IDs engessados por localizadores baseados em texto legível e papéis (roles), tornando a automação altamente resiliente a mudanças de front-end.
* **Esperas Dinâmicas e Timeout:** Adição do método `wait_for` integrado a blocos `try/except` para aguardar requisições de forma dinâmica e capturar evidências caso o site demore além do permitido.
* **Evidências em Screenshot:** Captura automática de comprovantes de execução focado estritamente no elemento de sucesso da página, salvos no diretório `/resultados`.
* **Logs Estruturados em JSON:** Implementação da biblioteca `python-json-logger` no `bot.py` injetando automaticamente os contextos `bot_id` e `execution_id` em cada log para facilitar o rastreamento em ferramentas de nuvem.
* **Containerização:** Criação de `Dockerfile` multi-camadas utilizando a imagem oficial da Microsoft (`mcr.microsoft.com/playwright/python:v1.62.0-jammy`) para prover um ambiente 100% isolado, evitando problemas de incompatibilidade de SO.
* **Orquestração com Docker Compose:** Configuração completa do `docker-compose.yml` separando a aplicação em dois serviços comunicáveis pela rede interna:
  * O servidor web Nginx (`frontend`) que hospeda a interface visual.
  * O robô (`bot-conferencia`) operando nativamente em modo *headless*.

### Modificado
* **Configuração de Dependências:** Otimização do `requirements.txt`, mantendo apenas os pacotes de primeiro nível e flexibilizando os bloqueios de versão exatos para garantir um build fluido dentro de distribuições Linux no Docker.
* **Mapeamento de Rotas:** O arquivo principal agora busca a variável `BASE_URL` para gerenciar requisições tanto de `localhost` quanto internas via Compose.

# 3. Atualização do `CHANGELOG.MD`

Como vocês estão adicionando uma camada nova, eu colocaria algo assim no topo:


## [Unreleased]

### Added

- Adicionada camada inicial de Machine Learning para classificação inteligente de lotes.
- Criado script `train_model.py` para geração de dataset sintético e treinamento do classificador.
- Criado dataset fictício com no mínimo 200 amostras.
- Adicionado `RandomForestClassifier` utilizando scikit-learn.
- Adicionadas as features:
  - `status_raw`
  - `turno`
  - `tem_obs`
- Adicionadas as classes:
  - `valido_automatico`
  - `revisar`
  - `recusar_automatico`
- Adicionada serialização do modelo utilizando `joblib`.
- Adicionado artefato do modelo em `models/classificador_lotes.pkl`.
- Adicionado dataset gerado em `data/dataset_lotes.csv`.

### Documentation

- Documentada a arquitetura inicial da camada de Machine Learning.
- Documentada a geração do dataset sintético.
- Documentadas as features e classes utilizadas pelo classificador.
- Documentado o processo de treinamento e serialização do modelo.
- Documentadas as dependências de Machine Learning.
- Adicionada observação sobre as limitações de avaliação utilizando dados sintéticos.

### Planned

- Serviço FastAPI para disponibilização do modelo.
- Endpoint `POST /predict`.
- Endpoint `GET /health`.
- Validação de entrada utilizando Pydantic.
- Integração com `MLClient`.
- Circuit breaker e fallback `REVISAO_ML_OFFLINE`.
- 