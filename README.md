# Hyperautomation

Automação web de um fluxo demonstrativo de login e cadastro de lotes. O bot usa
Playwright para abrir o portal estático, preencher as credenciais de teste,
confirmar o login e registrar uma evidência da mensagem de sucesso.

> O portal é apenas um ambiente de demonstração: ele não autentica usuários nem
> persiste dados de lotes.

## O que o bot executa

1. Acessa `/login.html` no endereço definido por `URL_BASE`.
2. Preenche o usuário e a senha de demonstração definidos no código.
3. Clica em **Entrar** e espera a mensagem de sucesso do login.
4. Salva uma captura dessa mensagem em `resultados/comprovante_lote_9999.png`.
5. Registra eventos em JSON no terminal e em `logs/botcity_permofer.log`.

O redirecionamento posterior para `lote-teste.html` é realizado pelo próprio
portal, após 1,2 segundo. O bot não preenche nem envia o formulário de lote
nesta versão.

## Estrutura

| Caminho | Responsabilidade |
| --- | --- |
| `bot.py` | Ponto de entrada e configuração do log estruturado. |
| `src/playwright/web_automation.py` | Fluxo automatizado no navegador. |
| `src/config.py` | Endereço do portal, modo do navegador e caminhos locais. |
| `frontend/` | Portal estático usado na demonstração. |
| `docker-compose.yml` | Serviços do portal Nginx e do bot. |
| `resultados/` e `logs/` | Saídas geradas durante a execução. |
| `documentacao/` | PDD, BPMN e materiais de referência do projeto. |

## Pré-requisitos

- Python 3.12 ou superior (conforme `pyproject.toml`);
- Docker e Docker Compose, para a execução em contêiner; ou
- um ambiente Python com os navegadores do Playwright instalados, para a
  execução local.

## Execução com Docker Compose

Esta é a forma mais simples de executar o ambiente completo, pois o Compose
inicia o portal e só inicia o bot quando ele estiver disponível.

```bash
docker compose up --build
```

Ao finalizar, verifique:

```bash
ls resultados/comprovante_lote_9999.png
tail -n 20 logs/botcity_permofer.log
```

Para encerrar e remover os contêineres:

```bash
docker compose down
```

O portal pode ser aberto em `http://localhost:8080/login.html` enquanto os
serviços estiverem em execução.

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
- `resultados/comprovante_lote_9999.png`: evidência do sucesso ou, em caso de
  timeout, captura da tela de erro.

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
- Não há validação de planilhas, fila/DataPool, testes automatizados ou envio de
  artefatos ao BotCity no código presente neste repositório.
- O nome `executar_cadastro_web` é legado: o fluxo implementado automatiza o
  login e coleta sua evidência.
