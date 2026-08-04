from playwright.sync_api import sync_playwright
import os
import logging
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from src.config import INTERFACE_NAVEGADOR, CAMINHO_EVIDENCIA, URL_BASE


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
        headless=True if em_container else INTERFACE_NAVEGADOR,
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
            CAMINHO_EVIDENCIA,
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

        logger.info("Acessando a pagina de LOGIN...")
        page.goto(f"{URL_BASE}/login.html")
        page.screenshot(path="logs/debug_login.png")

        # A partir que é carregado a tela, ele vai fazer o preenchimento
        page.get_by_placeholder("seu.usuario@empresa.com").fill("bot.automacao@empresa.com")
        page.get_by_placeholder("Digite sua senha").fill("senha_muito_legal")
        page.get_by_role("button", name="Entrar").click()

        # Cria o diretório de screenshots caso ele ainda não exista.
        Path(CAMINHO_EVIDENCIA).parent.mkdir(parents=True, exist_ok=True)

        logger.info("Aguardando redirecionamento...")

    # Waits e evidências
        try:
            # Aguardamos o elemento de sucesso ficar vísivel
            # Iremos utilizar o ID 'mesagemSucesso' que está presente no HTML
            box_sucesso = page.locator("#mensagemSucesso")
            box_sucesso.wait_for(state='visible',timeout=5000)

            # É necessário que aguarde o 1 segundo de animação
            page.wait_for_timeout(timeout=1000)

            box_sucesso.screenshot(path = CAMINHO_EVIDENCIA)
            caminho_relatorio = gerar_relatorio_execucao()

            logger.info(
                "Sucesso! Evidência e relatório gerados em %s e %s",
                CAMINHO_EVIDENCIA,
                caminho_relatorio,
            )
        except TimeoutError:
            # Caso realmente não deu certo:
            logger.error("Erro de tempo: Não foi possível, pois está fora do tempo de limite")

            # Vamos tirar o print para demostrar que teve o erro
            page.screenshot(path = CAMINHO_EVIDENCIA)
            raise Exception("Falha de Automação, pois carregou fora do esperado")

        browser.close()
        logger.info("Concluido com sucesso")
