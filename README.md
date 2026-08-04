# Bot de Inspeção de Lotes Diários

## Objetivo
Automatizar o processo de auditoria, conferência e cadastramento de lotes diários da qualidade no portal web corporativo. 
O robô atua validando dados em retaguarda e operacionalizando a interface gráfica da aplicação web por meio de simulações 
de ações humanas, com geração contínua de evidências visuais e logs rastreáveis.

## Ideia
Este projeto implementa uma arquitetura híbrida focada em **Hyperautomation**. Ao usar a infraestrutura do Docker, 
o projeto sobe e orquestra o próprio ambiente hospedeiro do portal web (simulando um cenário produtivo), junto com o 
*performer* robótico contido em Python. Todo o rastreio da operação emula as melhores práticas de logs estruturados 
(JSON), tornando o robô facilmente monitorável num ecossistema de nuvem (Datadog, Kibana, etc).

## 📂 Estrutura de Diretórios
```text
conferencia-lotes-qualidade/
   bot.py               # Orquestrador central e injeção do logger
   requirements.txt     # Pacotes principais (Playwright, Pandas, Maestro, JSON-logger)
   Dockerfile           # Receita de construção da imagem Linux (Jammy) do bot
   docker-compose.yml   # Orquestrador de serviços (Frontend Nginx + Bot Python)
   .env                 # Variáveis de ambiente e credenciais locais (ignorado no git)
   CHANGELOG.md         # Histórico de modificações
   README.md            # Documentação principal
   frontend/            # Páginas web da aplicação-alvo mapeadas pelo Nginx
       login.html
       lote-teste.html
   data/
       samples/         # Planilhas de entrada para o modo offline
   logs/                # Logs JSON estruturados de cada passo de execução
   resultados/          # Evidências geradas (.png) e planilhas processadas
   src/                 
       config.py              # Concentrador de leitura do .env
       playwright/
           web_automation.py  # Ações e comandos de simulação na interface
```

## Requisito e Biblioteca

* Docker e Docker Compose (V2+).
* Python 3.12+ (Para ambientes de desenvolvimento local sem contaieners)

* **Principais bibliotecas que estão sendo utilizada:**
  * `playwright:` É o principal de automação de navegadores em web
  * `python-json-loggers:` Estruturador oficial para transformações do logging nativo em JSON rastreável.
  * `botcity-maestro-sdk`: SDK oficial para telemetria no servidor do Maestro
  * `pandas` e `numpy`: Leitura de matrizes no processamento de planilhas locais

### Como executar:

#### 1. Clonando e Configurando o ambiente
primeiro, clone o repositório em sua máquina. Após isso coopie o arquivo `env.example` e renomeie para `.env`.
Configure a FLAG HEADLESS para definir se o container deve mostrar a interface do navegador durante o processo de teste
ou não, e preenche a URL interna do compose:


```bash
git clone <url-do-repositorio>
cd Hyperautomation


# para arquivo .env
BASE_URL=http://frontend
HEADLESS=true
BOT_ID=bot-conferencia-docker
EXECUCAO_ID=exec-0001
```
#### 2. Disparando os Container (Docker compose)
Agora, toda aplicação está modularizada. Não ŕe preciso instalar o Python nativamente na sua máquina
com o Docker ligado, execute:

`docker compose up --build`

Isso fará com que:

1. Um servidor Nginx levante na porta 8080, servindo as páginas localizadas na pasta `frontend`
2. O *bot* em sua imagem customizada do Playwright seja ligada logo na sequência, conecntado-se ao Nginx via rede interna
, procedendo com as rotinas de preenchimento, e salvando o .png final.

Após isso, acompanhe a execução do bot, que ele mostrará as fotos comprovando o sucesso e estrá salvas no mapeamento local em
`resultados/` e também uma telemetria da operação poderá ser lida nativamente através do log estruturado localizado em `logs/botcity_permofer.log`