from playwright.sync_api import sync_playwright


# Código principal de playwright
def executar_cadastro_web():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # headless -> faz que visualizamos o uso desse script pelo navegador
        context = browser.new_context()
        page = context.new_page()

        print("Acessando a página de LOGIN...")
        page.goto("http://127.0.0.1:3000/html/login(1).html")

        # A partir que é carregado a tela, ele vai fazer o preenchimento
        page.get_by_placeholder("seu.usuario@empresa.com").fill("bot.automacao@empresa.com")
        page.get_by_placeholder("Digite sua senha").fill("senha_muito_legal")
        page.get_by_role("button", name="Entrar").click()

        print("Aguardando redirecionamento...")

        #Após o bot clica em submit, vamos aguardar o carregamento de outra página
        page.wait_for_url("**/lote-teste.html")

        print("Sucesso!!!\nAcessando a página de Cadastro de Lotes")

        # Agora, chegamos na parte de preenchimento de cadastro, é preencher o formulário
        page.get_by_label("Número do Lote *").fill("LOTE-2026-9999")

        page.get_by_label("Produto *").select_option("2")

        # O Bot vai clicar em processamento
        page.get_by_label("Em Processamento").check()

        # Agora vamos submeter
        page.get_by_role("button", name="Processar Lote").click()

        print("Formulario preenchido com sucesso, vamos pausar para visualização")
        page.wait_for_timeout(3000)

        browser.close()
        print("Concluido com sucesso")