# Changelog

Todas as mudanças relevantes deste projeto são documentadas neste arquivo.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o versionamento segue [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Planejado

- Automatizar a atualização dos bots no Maestro após a criação das três
  automações e validação das credenciais do ambiente.
- Substituir gradualmente segredos locais pelas Credenciais do Maestro.
- Ampliar as evidências da apresentação com métricas das execuções reais.

## [2.0.0] - 2026-08-31

### Adicionado

- Pipeline distribuído em três bots: entrada, conferência e relatório.
- Entrypoints específicos para execução dos Bots A, B e C pelo BotCity Runner.
- Cliente do Maestro compatível com execução local e `from_sys_args()` no
  Runner.
- Criação automática das tarefas sucessoras A → B → C.
- Propagação de `predecessor`, `predecessor_task_id`,
  `resultado_predecessor`, `execution_id` e `correlation_id`.
- Publicação da planilha validada pelo Bot A como artefato no Maestro.
- Download de artefatos do predecessor pelos Bots B e C.
- Serialização do resultado intermediário do Bot B em JSON.
- Publicação do relatório Excel final pelo Bot C.
- Camada `maestro_artifacts` para localização, download e upload de arquivos.
- Retentativas para erros de dados e envio de itens não processados para dead
  letter.
- Logs estruturados das transições entre os três bots.
- Alertas pelo Telegram como canal principal.
- E-mail como fallback para eventos `ERRO` e `CRÍTICO`.
- Auditoria do canal tentado, canal de entrega, falhas e acionamento do
  fallback.
- Resumo operacional no corpo dos alertas e suporte a anexos.
- Simulação automatizada dos cenários de crise: base instável, ML indisponível,
  timeout de ML, confiança abaixo do limiar e Telegram indisponível.
- Empacotamento independente dos três bots para o Maestro.
- Validação dos pacotes ZIP no CI, incluindo bloqueio de `.env`, `.pyc` e
  `__pycache__`.
- Fallback de `caminho_entrada` para `CAMINHO_ENTRADA` no ambiente local do
  Runner.
- Testes unitários dos executores Maestro, cliente, artefatos e transferência
  do resultado do Bot B.
- Testes de integração da orquestração, rastreabilidade, canais de alerta,
  dead letter e simulação de crise.

### Alterado

- Labels e Bot IDs padronizados para:
  - `carlos_souza-entrada-v1`;
  - `carlos_souza-conferencia-v1`;
  - `carlos_souza-relatorio-v1`.
- O processamento monolítico passou a disponibilizar uma cadeia orquestrada
  sem remover a possibilidade de demonstração local.
- O Bot A passou a aceitar `caminho_entrada` pela tarefa e, quando ausente,
  consultar `CAMINHO_ENTRADA` no `.env` do Fedora.
- O Bot B passou a receber a planilha por artefato, evitando depender do caminho
  de arquivos da tarefa predecessora.
- O Bot C passou a receber o resultado intermediário por artefato e publicar o
  relatório final no Orquestrador.
- O modelo de classificação foi alterado de `RandomForest` para
  `LogisticRegression`, reduzindo tamanho e complexidade e facilitando a
  interpretação das probabilidades no dataset controlado.
- A decisão híbrida passou a registrar origem da decisão, causa provável,
  confiança, motivo do fallback, versão do modelo e latência.
- O CI foi separado em jobs de testes unitários, integração, crise, E2E, API ML
  e pacotes do Maestro.
- O gate final do CI passou a considerar explicitamente a simulação de crise e
  o empacotamento do Maestro.
- O README passou a documentar Fedora, ML local, Docker Compose, cadeia de bots,
  alertas, testes, CI e deploy pelo Easy Deploy.

### Corrigido

- Retorno ausente na leitura e validação da planilha que produzia
  `NoneType is not iterable`.
- Auditoria de ML que não preservava todas as decisões quando a API falhava.
- Referência inexistente `_campo` durante a criação de registros de auditoria.
- Payload ausente nas chamadas do cliente ML.
- Incompatibilidades de configuração de `ml_api_url`,
  `pipeline_hibrido_enabled` e valores booleanos.
- Grafia da mensagem de validação de valor numérico.
- Importação e serialização da função de normalização do modelo.
- Importação ausente de `unicodedata` no treinamento.
- Ausência de `causa_provavel` nos dados utilizados pelos relatórios.
- Decisão bem-sucedida de ML sem classe prevista.
- Auditoria vazia durante a sabotagem controlada da API ML.
- Fallback de alertas que não acionava o e-mail após falha do Telegram.
- Exceções de canais de alerta que interrompiam o pipeline.
- Chamadas duplicadas e dependência nula do sistema de alertas no Bot C.
- Preservação de registros duplicados necessários para identificação da RN11.
- Encaminhamento de erros de dados para dead letter sem interromper o lote.
- Geração do relatório após a presença de registros enviados para dead letter.
- Propagação incorreta ou fixa do `predecessor_task_id`.
- Importações circulares entre executores e testes do Maestro.
- Localização de artefatos ausente nos executores dos Bots B e C.
- Divergência entre o payload esperado e o payload enviado ao criar tarefas no
  Maestro.
- Job final do CI que consultava `RESULTADO_CRISE` sem possuir o job ou a
  variável correspondente.
- Caminho inexistente do teste `test_simulacao_crise.py` na execução do CI.
- Contaminação de testes unitários pelo valor real de `CAMINHO_ENTRADA` do
  `.env`.

### Segurança

- Arquivos `.env` foram excluídos dos pacotes enviados ao Maestro.
- Logs e mensagens de erro não exibem tokens do Telegram nem senhas SMTP.
- Credenciais permanecem fora do controle de versão.
- O e-mail utiliza senha de aplicativo e TLS quando configurados.

### Validado

- Suítes unitárias, de integração e dos executores Maestro executadas com
  sucesso após as correções.
- Build e healthcheck da API ML pelo Docker Compose.
- Envio real de e-mail por SMTP.
- Fallback de Telegram para e-mail em falha controlada.
- Execução real da cadeia A → B → C no BotCity Maestro.
- Geração e publicação do relatório Excel final pelo Bot C.

## [1.1.0] - 2026-08-03

### Adicionado

- Automação web com Playwright para login e cadastro de lotes.
- Locators semânticos, esperas dinâmicas e evidências em screenshot.
- Logs estruturados em JSON com `bot_id` e `execution_id`.
- Containerização inicial e orquestração com Docker Compose.

### Alterado

- Atualização das dependências e URLs para execução local e em container.

## [1.0.0]

### Corrigido

- Importações relativas incompatíveis com o ambiente de testes.
- Adição dos arquivos `__init__.py` necessários para os pacotes Python.
