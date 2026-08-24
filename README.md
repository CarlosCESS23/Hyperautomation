# Hyperautomation

![CI](https://github.com/NunesGustavo0/Hyperautomation/actions/workflows/ci-cd.yml/badge.svg)

Automação web de um fluxo demonstrativo de login e cadastro de lotes. O bot usa
Playwright para abrir o portal estático, preencher as credenciais de teste,
confirmar o login e registrar uma evidência da mensagem de sucesso.

> O portal é apenas um ambiente de demonstração: ele não autentica usuários nem
> persiste dados de lotes.

## Dashboard de conferência de lotes

O script `gerar_relatorio.py` processa as dez abas diárias de
`inspecao_lotes_10dias.xlsx` e gera o relatório executivo de conferência. A
lógica RN01–RN12 está centralizada em `src/validacao_lotes.py` e é apenas
consumida pelo gerador. A consolidação dos dez indicadores é feita uma única
vez e o mesmo resultado alimenta o Excel e `resumo_executivo.md`. O dashboard
principal fica dentro do Excel, na aba **Resumo**.

### Instalação

No PowerShell, acesse a pasta do projeto e instale as dependências:

```powershell
cd "C:\caminho\para\Hyperautomation"
python -m pip install -r requirements.txt
```

### Execução

Informe o caminho da planilha de entrada:

```powershell
python gerar_relatorio.py "C:\caminho\para\inspecao_lotes_10dias.xlsx"
```

Se o arquivo estiver em `Downloads` com o nome
`inspecao_lotes_10dias.xlsx`, o caminho pode ser omitido:

```powershell
python gerar_relatorio.py
```

Saída esperada no terminal:

```text
Relatório: C:\caminho\para\Hyperautomation\reports\relatorio_conferencia_lotes.xlsx
Total: 250 | Válido: 150 | Divergência: 50 | Ambíguo: 20 | Erro de Entrada: 30
PDF: gerado
```

### Arquivos gerados

| Arquivo | Finalidade |
| --- | --- |
| `reports/relatorio_conferencia_lotes.xlsx` | Relatório completo e dashboard na aba **Resumo**. |
| `reports/resumo_executivo.md` | Síntese em linguagem de negócio, consistente com o Excel. |
| `reports/dashboard_resumo.pdf` | Cópia estática do dashboard para impressão. |
| `reports/log_execucao.txt` | Evidência da execução e totais processados. |
| `documentacao/roteiro_apresentacao_exercicio22.md` | Roteiro da apresentação de cinco minutos. |

O Excel possui exatamente nove abas: **Resumo**, **Todos**, **Válidos**,
**Divergências**, **Ambíguos**, **Erros de Entrada**, **Ranking de Regras** e
**Dicionário** e **Decisões de ML**. A última preserva a classe, a
probabilidade, o nível de confiança e a latência retornados em cada chamada ao
classificador, sem recalcular a predição. Os gráficos de rosca e evolução são
objetos nativos do Excel. A duplicidade é verificada por dia e somente a segunda
ocorrência em diante é classificada como divergência pelas regras RN01–RN12.

A aba **Resumo** apresenta os dez indicadores operacionais. O ranking usa as
contagens já consolidadas, e o dicionário explica os termos para o público de
negócio. O ganho de tempo é uma estimativa didática de cinco minutos por
registro válido, premissa declarada também no resumo Markdown.

O gabarito operacional é **150 válidos, 50 divergências, 20 ambíguos e 30
erros de entrada**. Assim, há 100 registros problemáticos no total; “100” não
representa apenas a classificação Divergência.

### Verificação rápida dos artefatos

Após gerar o relatório, execute a conferência independente, que usa somente a
biblioteca padrão do Python:

```powershell
python scripts/verificar_exercicio22.py
```

Ela valida nomes das abas, totais, gráficos nativos, ausência de gráficos
colados como imagem, log e PDF. O resultado esperado termina com
`ACEITE DO EXERCÍCIO 22: APROVADO`.

Para abrir os resultados:

```powershell
# Abrir a pasta
explorer ".\reports"

# Abrir o dashboard dentro do Excel
Start-Process ".\reports\relatorio_conferencia_lotes.xlsx"

# Abrir a cópia em PDF
Start-Process ".\reports\dashboard_resumo.pdf"
```

### Definir outro local de saída

```powershell
python gerar_relatorio.py "C:\entrada\inspecao_lotes_10dias.xlsx" --saida "C:\saida\relatorio_conferencia_lotes.xlsx"
```

Nesse caso, o PDF e o log são gravados na mesma pasta escolhida para o Excel.

## O que o bot executa

1. Acessa `/login.html` no endereço definido por `URL_BASE`.
2. Preenche o usuário e a senha de demonstração definidos no código.
3. Clica em **Entrar** e espera a mensagem de sucesso do login.
4. Salva uma captura dessa mensagem em `screenshots/comprovante_lote_9999.png`.
5. Gera um relatório de execução em `data/output/relatorio_execucao_lotes.xlsx`.
6. Registra eventos em JSON no terminal e em `logs/botcity_permofer.log`.

O redirecionamento posterior para `lote-teste.html` é realizado pelo próprio
portal, após 1,2 segundo. O bot não preenche nem envia o formulário de lote
nesta versão.

## Estrutura

| Caminho | Responsabilidade |
| --- | --- |
| `bot.py` | Ponto de entrada e configuração do log estruturado. |
| `src/playwright/web_automation.py` | Fluxo automatizado no navegador. |
| `src/pages/formulario_lotes_page.py` | Page Object do formulário de cadastro de lotes. |
| `src/config.py` | Endereço do portal, modo do navegador e caminhos locais. |
| `frontend/` | Portal estático usado na demonstração. |
| `tests/e2e/` | Testes E2E do formulário executados em Chromium real. |
| `tests/conftest.py` | Fixtures compartilhadas da suíte E2E. |
| `.github/workflows/ci-cd.yml` | Testes automatizados e publicação de evidências no CI. |
| `docker-compose.yml` | Serviços do portal Nginx e do bot. |
| `logs/`, `data/output/` e `screenshots/` | Saídas persistidas da execução. |
| `documentacao/` | PDD, BPMN e materiais de referência do projeto. |

## Pré-requisitos

- Python 3.12 ou superior (conforme `pyproject.toml`);
- Docker e Docker Compose, para a execução em contêiner; ou
- um ambiente Python com os navegadores do Playwright instalados, para a
  execução local.

## Execução com Docker

Esta é a forma mais simples de executar o ambiente completo, pois o Compose
inicia o portal e só inicia o bot quando ele estiver disponível.

```bash
# Construir a imagem do bot
docker compose build

# Executar o bot e suas dependências
docker compose run --rm bot-conferencia
```

Ao finalizar, verifique:

```bash
ls logs/
ls data/output/
ls screenshots/
```

Para encerrar e remover os contêineres:

```bash
docker compose down
```

Para manter o portal disponível após a execução isolada do bot, execute
`docker compose up --build`. O portal pode ser aberto em
`http://localhost:8081/login.html` enquanto os serviços estiverem em execução.

## Execução local

Crie o ambiente, instale as dependências e o Chromium do Playwright:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Em outro terminal, sirva a pasta `frontend`:

```bash
python -m http.server 8080 --directory frontend
```

Então execute o bot:

```bash
python bot.py
```

Por padrão, o navegador é executado sem interface. Para acompanhar a execução,
defina `HEADLESS=false` antes do comando do bot:

```bash
HEADLESS=false python bot.py
```

## Testes automatizados

### Pré-requisitos e instalação

A suíte requer Python 3.12 ou superior, conforme `requires-python` em
`pyproject.toml`. Para preparar um ambiente local a partir da raiz do
repositório, crie e ative um ambiente virtual, instale as dependências de
desenvolvimento e teste e instale o Chromium usado pelo Playwright:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

No PowerShell, somente o comando de ativação muda:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

A instalação dos pacotes e do navegador exige acesso à internet apenas nessa
etapa. Depois que o ambiente está preparado, a suíte não acessa a internet,
não exige credenciais e não depende de arquivos manuais não versionados. O
formulário E2E é aberto diretamente do arquivo estático local; não é necessário
iniciar o servidor HTTP.

### Organização da suíte

| Caminho | Finalidade |
| --- | --- |
| `tests/unit/` | Valida funções e regras de negócio isoladamente, com dependências simuladas. |
| `tests/integration/` | Valida a integração entre leitura da planilha, processamento e geração do relatório. |
| `tests/e2e/` | Valida fluxos completos, incluindo o pipeline de relatório e o formulário local em Chromium real. |
| `tests/conftest.py` | Centraliza fixtures e fábricas compartilhadas para registros, planilhas, Base de Referência, data/hora e páginas do Playwright. |

Os testes de regressão permanecem no diretório da camada à qual pertencem e
recebem também o marker `regression`; portanto, não existe um diretório
`tests/regression/` separado.

As planilhas e os relatórios criados pelos testes de integração e do pipeline
E2E são gravados em diretórios temporários fornecidos pela fixture `tmp_path` e
são descartados pelo Pytest. A Base de Referência, os arquivos de entrada e a
data/hora de execução são controlados por fixtures, mocks e `monkeypatch`, o
que torna esses cenários determinísticos. O teste visual do formulário mantém
apenas a evidência `tests/e2e/screenshots/evidencia_formulario.png`, ignorada
pelo Git.

### Comandos de execução

Execute a suíte completa:

```bash
python -m pytest -q
```

### Cobertura e evidência da suíte completa

O `pytest-cov` mede tanto `src/`, onde estão as regras RN01–RN12, quanto
`gerar_relatorio.py`, responsável pela leitura, processamento e geração do
relatório Excel. As fontes, o limite global de **80%**, a exibição das linhas
não cobertas e o diretório HTML estão centralizados em `pyproject.toml`.

Após instalar `requirements-dev.txt`, gere a evidência reproduzível com:

```bash
python -m pytest --cov --cov-report=term-missing --cov-report=html -rsxX
```

O comando executa a suíte completa, falha se a cobertura total for inferior a
80%, mantém `skip`, `xfail` e `xpass` visíveis no resumo e cria o relatório
navegável em `htmlcov/index.html`. Para anexar a evidência à entrega, compacte
a pasta `htmlcov/` depois da execução e anexe o arquivo compactado no canal da
entrega. Não versione essa pasta: `htmlcov/`, `.coverage`, `.coverage.*` e
`coverage.xml` estão no `.gitignore` por serem artefatos locais reproduzíveis.

As lacunas relevantes que permanecem deliberadamente visíveis são:

| Trecho | Justificativa |
| --- | --- |
| `src/config.py` e `src/pages/formulario_login_pages.py` | Pertencem ao fluxo separado do bot/Login e dependem da configuração do Maestro e do portal; não fazem parte das RN01–RN12 nem do pipeline do relatório desta entrega. |
| `gerar_relatorio.py`: rejeição de estrutura inválida e ausência opcional do Matplotlib | São caminhos defensivos; a suíte desta entrega usa a estrutura válida de dez abas e possui a dependência de PDF instalada. |
| `gerar_relatorio.py`: guarda de execução `__main__` | O E2E chama `main()` com argumentos controlados para evitar depender de arquivos manuais e do diretório de trabalho. |
| `src/pages/formulario_lotes_page.py`: URL HTTP e método agregado legado | O E2E abre o HTML local diretamente e testa as operações públicas individualmente. |

Esses trechos não são omitidos da medição e continuam destacados no relatório
para revisão futura; nenhum módulo ou bloco funcional é excluído apenas para
elevar o percentual.

Execute cada camada separadamente por marker:

```bash
python -m pytest -m unit -q
python -m pytest -m integration -q
python -m pytest -m regression -q
python -m pytest -m e2e -q
```

Markers podem ser combinados com expressões. Este exemplo executa testes
marcados como unitários ou de integração:

```bash
python -m pytest -m "unit or integration" -q
```

Para executar um arquivo específico ou um único teste, informe o caminho ou o
node ID:

```bash
python -m pytest tests/unit/test_normalizar_status.py -q
python -m pytest tests/unit/test_normalizar_status.py::test_rn04_normaliza_status_aprovada_para_aprovado -q
```

Para listar os markers registrados e suas descrições:

```bash
python -m pytest --markers
```

Para exibir no resumo as razões dos casos ignorados ou esperadamente falhos,
incluindo resultados inesperadamente aprovados, execute:

```bash
python -m pytest -rsxX -q
```

`skip` indica que o teste não pode ou não deve ser executado nas condições
atuais, como o cenário que aguarda um ambiente autenticado de homologação.
`xfail` executa o teste, mas registra a falha conhecida como esperada. Os casos
`xfail` usam `strict=True` quando aplicável: se um deles passar sem que a marca
seja removida, o resultado `XPASS(strict)` faz a suíte falhar e sinaliza que a
expectativa precisa ser revisada.

Para acompanhar o navegador nos testes de formulário, use:

```bash
python -m pytest tests/e2e/test_formulario_lotes_e2e.py -v --headed
python -m pytest tests/e2e/test_formulario_lotes_e2e.py -v --headed --slowmo=500
```

## Integração contínua

O workflow em `.github/workflows/ci-cd.yml` executa os jobs de testes e
container:

1. `test`: executa a suíte unitária quando ela estiver presente;
2. `test-e2e`: instala as dependências, instala o Chromium com as bibliotecas
   necessárias, executa `pytest tests/e2e/ -v --tb=short` e publica as capturas
   em `tests/e2e/screenshots/` como artefato do GitHub Actions.
3. `build-docker`: constrói a imagem, executa `bot-conferencia` no Compose,
   confirma a geração de logs, relatório e screenshot, e publica essas
   evidências como artefato.

Os jobs E2E e Docker só começam após a conclusão do job de testes unitários.
Os screenshots e evidências são enviados mesmo quando algum teste falha,
facilitando o diagnóstico no CI.

## Configuração

O bot lê as variáveis de ambiente do processo. Para usar o modelo incluído,
copie-o e exporte seu conteúdo no terminal antes de executar o bot:

```bash
cp .env.example .env
set -a
source .env
set +a
```

As variáveis efetivamente usadas pelo fluxo atual são:

| Variável | Padrão | Finalidade |
| --- | --- | --- |
| `URL_BASE` | `http://localhost:8080` | URL do portal a ser automatizado. |
| `HEADLESS` | `true` | Use `false` para abrir a janela do Chromium. |
| `BOT_ID` | `bot-auditoria-local` | Identificador incluído em cada linha de log. |
| `EXECUCAO_ID` | `exec_dev_001` | Identificador da execução incluído nos logs. |

`MAESTRO_*`, `VAULT_ENABLED`, `AUDITORIA_DATAPOOL_LABEL` e as variáveis de
credencial permanecem no modelo para uma futura integração com o BotCity
Maestro. Elas não são consultadas por `bot.py` nem enviam dados ao Maestro na
implementação atual.

Embora `src/config.py` tenha uma função para carregar um arquivo `.env`, o
fluxo iniciado por `python bot.py` não a chama nesta versão. Por isso, somente
criar o arquivo `.env` não altera a execução local sem exportá-lo, como no
exemplo acima.

## Saídas e diagnóstico

- `logs/debug_login.png`: captura feita logo após abrir a página de login;
- `logs/botcity_permofer.log`: eventos em JSON com `bot_id` e `execution_id`;
- `screenshots/comprovante_lote_9999.png`: evidência do sucesso ou, em caso de
  timeout, captura da tela de erro.
- `data/output/relatorio_execucao_lotes.xlsx`: relatório gerado após uma
  execução bem-sucedida.

Se a execução expirar, confirme que o portal está acessível em
`$URL_BASE/login.html` e que os seletores da página não foram alterados. O
tempo de espera da mensagem de sucesso é de cinco segundos.

## Materiais complementares

- [PDD da equipe](documentacao/PDD/pdd_equipe1.docx)
- [Diagrama BPMN](documentacao/BPMN/AS_IS_TO_DO.bpmn)
- [Referência de Docker](documentacao/documentos_referencia/docker/docker.html)
- [Referência de CI/CD](documentacao/documentos_referencia/CI-CD/ci-cd.html)
- [Referência de Gitflow](documentacao/documentos_referencia/gitflow/gitflow.html)

## Limitações atuais

- As credenciais preenchidas pelo bot estão fixas no código e são exclusivas do
  ambiente de demonstração.
- Não há validação de planilhas, fila/DataPool ou envio de artefatos ao BotCity
  no código presente neste repositório.
- O nome `executar_cadastro_web` é legado: o fluxo implementado automatiza o
  login e coleta sua evidência.

## Machine Learning e API FastAPI

### Objetivo

A camada de Machine Learning auxilia na decisão sobre registros que o motor de
regras RN01–RN12 classificou como **Ambíguos**. O modelo não substitui as regras
de negócio: registros válidos, divergentes ou com erro de entrada continuam
seguindo diretamente para o relatório, sem consulta à API.

O serviço utiliza um `RandomForestClassifier` e recebe três características:

| Campo | Valores esperados | Finalidade |
| --- | --- | --- |
| `status_raw` | `APROVADO`, `REPROVADO`, `PENDENTE` ou `EM_ANALISE` | Representa o status informado na planilha. |
| `turno` | `MANHA`, `TARDE` ou `NOITE` | Identifica o turno da inspeção. |
| `tem_obs` | `true` ou `false` | Informa se o registro possui observação. |

A resposta contém a classe prevista, a probabilidade e o nível de confiança.
As variações `EM ANALISE`, `EM ANÁLISE` e `EM_ANALISE` são normalizadas para
`EM_ANALISE` antes da predição.

### Fluxo de processamento

```text
Planilha com dez abas diárias
  ↓
Leitura e validação de todos os registros
  ↓
Motor de regras RN01–RN12
  ↓
Registro ambíguo?
  ├── Não → mantém a decisão das regras
  └── Sim → item_processor
              ↓
          AuditoriaDecisoesML
              ↓
          MLClient + circuit breaker
              ↓
          API FastAPI
              ↓
          modelo Random Forest
```

Cada chamada ao classificador, inclusive quando a API está indisponível, é
registrada no log estruturado e na aba **Decisões de ML** do relatório. A
latência é medida sem repetir a predição.

Se ocorrer timeout, falha de conexão, erro HTTP ou resposta inválida, o
`MLClient` retorna `None` e o processamento continua. O registro recebe a ação
`REVISAO_ML_OFFLINE`, sem inventar classe ou probabilidade. Após cinco falhas
consecutivas, o circuit breaker é aberto e bloqueia novas tentativas de rede até
ser reiniciado ou resetado.

### Organização dos arquivos

| Caminho | Responsabilidade |
| --- | --- |
| `train_model.py` | Gera o dataset controlado, treina o Random Forest e serializa o modelo. |
| `data/dataset_lotes.csv` | Dataset gerado pelo script de treinamento. |
| `models/classificador_lotes.pkl` | Modelo treinado carregado pela API. |
| `api_ml/main.py` | Aplicação FastAPI, validação da entrada, healthcheck e predição. |
| `api_ml/Dockerfile` | Imagem do serviço de Machine Learning. |
| `api_ml/requirements.txt` | Dependências exclusivas do container da API. |
| `src/ml_client.py` | Cliente HTTP resiliente e circuit breaker. |
| `src/item_processor.py` | Integra as regras RN01–RN12 à decisão de ML. |
| `src/ml_decisions.py` | Audita decisões online e offline, latência e dados da resposta. |
| `gerar_relatorio.py` | Processa as dez abas e envia a auditoria para o Excel. |
| `docker-compose.yml` | Configura o serviço `api_ml`, a porta 8000 e o healthcheck. |
| `tests/unit/` | Testes isolados da API, cliente, processador e auditoria. |
| `tests/integration/` | Testes do fluxo Excel, auditoria e sabotagem da API. |
| `tests/e2e/` | Testes do pipeline completo de geração do relatório. |

### Pré-requisitos

Para a execução local:

- Python 3.12 ou superior;
- `pip` e suporte à criação de ambiente virtual;
- dependências de `requirements-dev.txt`;
- arquivo `models/classificador_lotes.pkl`, já versionado ou gerado novamente
  por `train_model.py`.

Para a execução em contêiner:

- Docker Desktop no Windows, ou Docker Engine no Linux;
- Docker Compose v2, disponível pelo comando `docker compose`;
- daemon do Docker iniciado.

As portas `8000` e `8081` devem estar livres quando a API ML e o portal forem
executados pelo Compose.

### Preparação do ambiente local

Na raiz do repositório, crie o ambiente virtual e instale as dependências.

Linux ou macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

### Treinar ou recriar o modelo

O repositório já contém o modelo serializado. Execute este passo somente para
recriar o dataset e treinar uma nova cópia:

```bash
python train_model.py
```

O comando gera ou atualiza:

```text
data/dataset_lotes.csv
models/classificador_lotes.pkl
```

Ao final, o terminal exibe o relatório de classificação do conjunto de teste e
os caminhos dos arquivos gerados.

### Executar a API ML localmente

Com o ambiente virtual ativo e o modelo disponível, execute:

```bash
python -m uvicorn api_ml.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

No Windows PowerShell, o mesmo comando pode ser escrito em uma linha:

```powershell
python -m uvicorn api_ml.main:app --host 0.0.0.0 --port 8000 --reload
```

Endereços disponíveis:

| Endereço | Uso |
| --- | --- |
| `http://localhost:8000/health` | Confirma se o modelo foi carregado. |
| `http://localhost:8000/docs` | Interface Swagger para testar a API. |
| `http://localhost:8000/redoc` | Documentação alternativa da API. |

O healthcheck saudável retorna:

```json
{
  "status": "healthy",
  "modelo_carregado": true
}
```

### Testar uma predição local

Linux, macOS ou Git Bash:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "status_raw": "EM ANÁLISE",
    "turno": "MANHA",
    "tem_obs": false
  }'
```

Windows PowerShell:

```powershell
$body = @{
    status_raw = "EM ANÁLISE"
    turno = "MANHA"
    tem_obs = $false
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8000/predict" `
    -ContentType "application/json" `
    -Body $body
```

Exemplo de resposta:

```json
{
  "classe": "revisar",
  "probabilidade": 0.92,
  "nivel_confianca": "acao_automatica"
}
```

Os valores da predição dependem do conteúdo do modelo serializado.

### Gerar o relatório usando a API local

O `MLClient` precisa apontar para `http://localhost:8000` quando o relatório é
executado na máquina host.

Linux ou macOS:

```bash
ML_API_URL=http://localhost:8000 python gerar_relatorio.py \
  "./inspecao_lotes_10dias.xlsx" \
  --saida "./reports/relatorio_ml_online.xlsx"
```

Windows PowerShell:

```powershell
$env:ML_API_URL = "http://localhost:8000"
python gerar_relatorio.py `
    ".\inspecao_lotes_10dias.xlsx" `
    --saida ".\reports\relatorio_ml_online.xlsx"
```

Substitua o caminho da planilha pelo arquivo usado na sua execução. Dentro da
rede do Docker Compose, a URL interna da API é `http://api_ml:8000`.

### Executar com Docker Compose

Na raiz do repositório, valide e inicie somente a API ML:

```bash
docker compose config
docker compose up -d --build api_ml
docker compose ps api_ml
```

O serviço deve aparecer com o estado `healthy`. Para acompanhar a inicialização
e confirmar o carregamento do modelo:

```bash
docker compose logs -f api_ml
```

Em outro terminal, teste o endpoint:

```bash
curl http://localhost:8000/health
```

No Windows PowerShell também é possível usar:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Para iniciar todos os serviços do projeto:

```bash
docker compose up -d --build
```

Para parar somente a API ou encerrar todo o ambiente:

```bash
docker compose stop api_ml
docker compose down
```

### Validar o fallback e o circuit breaker

Com o serviço parado, execute novamente o relatório apontando para a API local:

```bash
docker compose stop api_ml
ML_API_URL=http://localhost:8000 python gerar_relatorio.py \
  "./inspecao_lotes_10dias.xlsx" \
  --saida "./reports/relatorio_ml_offline.xlsx"
```

O resultado esperado é:

- o processamento da planilha termina normalmente;
- registros ambíguos recebem `REVISAO_ML_OFFLINE`;
- as primeiras cinco chamadas tentam acessar a API;
- o circuit breaker abre após a quinta falha consecutiva;
- chamadas seguintes são auditadas, mas não acessam a rede;
- a aba **Decisões de ML** diferencia chamadas online e offline.

Para restaurar o serviço:

```bash
docker compose up -d api_ml
```

### Executar os testes

Testes específicos da camada ML:

```bash
python -m pytest tests/unit/test_api_ml.py -q
python -m pytest tests/unit/test_ml_client.py -q
python -m pytest tests/unit/test_item_processor.py -q
python -m pytest tests/unit/test_ml_decisions_unit.py -q
python -m pytest tests/integration/test_auditoria_decisoes_ml.py -q
python -m pytest tests/integration/test_sabotagem_api_ml.py -q
```

Suíte sem os testes E2E:

```bash
python -m pytest --ignore=tests/e2e -q
```

Suíte completa, incluindo integração e E2E:

```bash
python -m pytest -q
```

Na última validação desta versão, a suíte completa apresentou:

```text
81 passed
```

Para gerar a evidência de cobertura:

```bash
python -m pytest --cov --cov-report=term-missing --cov-report=html -rsxX
```

O projeto exige cobertura global mínima de 80%, conforme `pyproject.toml`.

### Diagnóstico rápido

| Sintoma | Verificação |
| --- | --- |
| Docker informa que não encontrou `docker_engine` no Windows | Abra o Docker Desktop e aguarde o daemon iniciar antes de executar o Compose. |
| `/health` retorna `modelo_carregado: false` | Confirme a existência de `models/classificador_lotes.pkl` e verifique `docker compose logs api_ml`. |
| A porta 8000 já está em uso | Encerre o processo existente ou altere o mapeamento de porta no Compose. |
| O relatório gera `REVISAO_ML_OFFLINE` inesperadamente | Confirme `ML_API_URL`, teste `/health` e verifique se o serviço está `healthy`. |
| O Compose rejeita o healthcheck | Execute `docker compose config` e mantenha o comando Python em uma única entrada válida da lista `test`. |