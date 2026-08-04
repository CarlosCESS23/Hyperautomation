from playwright.sync_api import sync_playwright
import os
import logging

CAMINHO_EVIDENCIA = 'resultados/comprovante_lote_9999.png'

# Código principal de playwright
def executar_cadastro_web(logger : logging):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # headless -> faz que visualizamos o uso desse script pelo navegador
        context = browser.new_context()
        page = context.new_page()

        logger.info("Acessando a página de LOGIN...")
        page.goto("http://127.0.0.1:3000/html/login(1).html")

        # A partir que é carregado a tela, ele vai fazer o preenchimento
        page.get_by_placeholder("seu.usuario@empresa.com").fill("bot.automacao@empresa.com")
        page.get_by_placeholder("Digite sua senha").fill("senha_muito_legal")
        page.get_by_role("button", name="Entrar").click()

        # Vamos criar a pasta resultados/, caso realmente existe, ele não vai criar novamente
        os.makedirs('resultados', exist_ok=True)

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

            logger.info('Sucesso! o Bot teve sucesso e foi printado a evidência')
        except TimeoutError:
            # Caso realmente não deu certo:
            logger.error("Erro de tempo: Não foi possível, pois está fora do tempo de limite")

            # Vamos tirar o print para demostrar que teve o erro
            page.screenshot(path = CAMINHO_EVIDENCIA)
            raise Exception("Falha de Automação, pois carregou fora do esperado")

        browser.close()
        logger.info("Concluido com sucesso")