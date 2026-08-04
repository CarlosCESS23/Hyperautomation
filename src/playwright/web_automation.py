import logging
import os
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from playwright.sync_api import sync_playwright

from src.config import obter_configuracao
from ..pages.formulario_login_pages import PlaywrightFormularioLoginPage
from ..pages.formulario_lotes_page import PlaywrightFormularioLotesPage

# Instanciando o objeto
config = obter_configuracao()


def iniciar_browser(playwright):
    """Inicia o Chromium com as flags necessárias quando executado em container."""
    em_container = os.getenv("ENVIRONMENT", "local") != "local"
    args = []

    if em_container:
        args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ]

    return playwright.chromium.launch(
        headless=True if em_container else obter_configuracao().interface_navegador,
        args=args,
    )


def gerar_relatorio_execucao() -> Path:
    """Registra a execução concluída em um XLSX persistido pelo container."""
    diretorio_saida = Path("data/output")
    diretorio_saida.mkdir(parents=True, exist_ok=True)
    caminho_relatorio = diretorio_saida / "relatorio_execucao_lotes.xlsx"

    workbook = Workbook()
    planilha = workbook.active
    planilha.title = "Execução"
    planilha.append(["data_hora", "status", "evidencia"])
    planilha.append(
        [
            datetime.now().isoformat(timespec="seconds"),
            "sucesso",
            config.caminho_evidencia,
        ]
    )
    workbook.save(caminho_relatorio)
    return caminho_relatorio


# Código principal de playwright
def executar_cadastro_web(logger : logging):
    with sync_playwright() as p:
        # Essa parte será responsável por background, irá verificar se vai abrir o navegador ou não (Pois docker não inicia com navegador)
        browser = iniciar_browser(p)
        context = browser.new_context()
        page = context.new_page()

        # Instanciamos o nosso objeto base
        login_page = PlaywrightFormularioLoginPage(page, f"{config.url_base}/login.html")
        lotes_page = PlaywrightFormularioLotesPage(page, f"{config.url_base}/lotes.html")

        logger.info("Acessando a pagina de LOGIN...")
        login_page.navegar()
        login_page.realizar_login("UsuarioSuperSeguro@gmail.com",'SenhaSuperSeguro')

        # Cria o diretório de screenshots caso ele ainda não exista.
        Path(config.caminho_evidencia).parent.mkdir(parents=True, exist_ok=True)

        logger.info("Aguardando redirecionamento...")

    # Waits e evidências
        try:
            # Aguardamos o elemento de sucesso ficar vísivel
            # Iremos utilizar o ID 'mesagemSucesso' que está presente no HTML
            box_sucesso = page.locator("#mensagemSucesso")
            box_sucesso.wait_for(state='visible',timeout=5000)

            # É necessário que aguarde o 1 segundo de animação
            page.wait_for_load_state("networkidle")

            box_sucesso.screenshot(path=config.caminho_evidencia)
            caminho_relatorio = gerar_relatorio_execucao()

            logger.info(
                "Sucesso! Evidência e relatório gerados em %s e %s",
                config.caminho_evidencia,
                caminho_relatorio,
            )
        except TimeoutError:
            # Caso realmente não deu certo:
            logger.error("Erro de tempo: Não foi possível, pois está fora do tempo de limite")

            # Vamos tirar o print para demostrar que teve o erro
            page.screenshot(path=config.caminho_evidencia)
            raise Exception("Falha de Automação, pois carregou fora do esperado")

        browser.close()
        logger.info("Concluido com sucesso")
