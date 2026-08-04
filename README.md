# Hyperautomation

![CI](https://github.com/NunesGustavo0/Hyperautomation/actions/workflows/ci-cd.yml/badge.svg)

Automação web de um fluxo demonstrativo de login e cadastro de lotes. O bot usa
Playwright para abrir o portal estático, preencher as credenciais de teste,
confirmar o login e registrar uma evidência da mensagem de sucesso.

> O portal é apenas um ambiente de demonstração: ele não autentica usuários nem
> persiste dados de lotes.

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

## Testes End-to-End (E2E)

A suíte E2E valida o formulário `web/lote-teste.html` com Chromium real.
Ela exercita o Page Object `PlaywrightFormularioLotesPage`, incluindo entrada
de lote, seleção de produto e status, validação de campos obrigatórios,
submissão e captura de evidência. Como o formulário é estático, os testes o
abrem diretamente do sistema de arquivos; não é necessário iniciar o servidor
HTTP para esta suíte.

Após instalar as dependências e o Chromium conforme a seção anterior, execute:

```bash
pytest tests/e2e/ -v
```

Para acompanhar o navegador durante a execução:

```bash
pytest tests/e2e/ -v --headed
pytest tests/e2e/ -v --headed --slowmo=500
```

Os oito cenários cobertos são:

- carregamento da página com o título esperado;
- preenchimento do número do lote;
- seleção de produto;
- status `Pendente` selecionado por padrão;
- submissão completa com mensagem de sucesso;
- bloqueio de sucesso sem produto;
- bloqueio de sucesso sem número do lote;
- geração de screenshot como evidência.

A evidência é gerada em `tests/e2e/screenshots/evidencia_formulario.png`.
Esse arquivo é ignorado pelo Git para não versionar resultados de execução.

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
