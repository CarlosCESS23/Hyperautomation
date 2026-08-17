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
consumida pelo gerador. O dashboard principal fica dentro do Excel, na aba
**Resumo**. O PDF é somente uma cópia estática para impressão ou entrega.

### Instalação

No PowerShell, acesse a pasta do projeto e instale as dependências:

```powershell
cd "C:\Users\matutino\Documents\hyperautomation 2\Hyperautomation"
python -m pip install -r requirements.txt
```

### Execução

Informe o caminho da planilha de entrada:

```powershell
python gerar_relatorio.py "C:\Users\matutino\Downloads\inspecao_lotes_10dias.xlsx"
```

Se o arquivo estiver em `Downloads` com o nome
`inspecao_lotes_10dias.xlsx`, o caminho pode ser omitido:

```powershell
python gerar_relatorio.py
```

Saída esperada no terminal:

```text
Relatório: C:\Users\matutino\Documents\hyperautomation 2\Hyperautomation\reports\relatorio_conferencia_lotes.xlsx
Total: 250 | Válido: 150 | Divergência: 50 | Ambíguo: 20 | Erro de Entrada: 30
PDF: gerado
```

### Arquivos gerados

| Arquivo | Finalidade |
| --- | --- |
| `reports/relatorio_conferencia_lotes.xlsx` | Relatório completo e dashboard na aba **Resumo**. |
| `reports/dashboard_resumo.pdf` | Cópia estática do dashboard para impressão. |
| `reports/log_execucao.txt` | Evidência da execução e totais processados. |
| `documentacao/roteiro_apresentacao_exercicio22.md` | Roteiro da apresentação de cinco minutos. |

O Excel possui exatamente seis abas: **Resumo**, **Todos**, **Válidos**,
**Divergências**, **Ambíguos** e **Erros de Entrada**. Os gráficos de rosca e
evolução são objetos nativos do Excel. A duplicidade é verificada por dia e
somente a segunda ocorrência em diante é classificada como divergência.

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
python gerar_relatorio.py "C:\Users\matutino\Downloads\inspecao_lotes_10dias.xlsx" --saida "C:\Users\matutino\Downloads\relatorio_conferencia_lotes.xlsx"
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
