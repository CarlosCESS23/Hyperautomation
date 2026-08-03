from playwright.sync_api import sync_playwright


# Código principal de playwright
def executar_cadastro_web():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # headless -> faz que visualizamos o uso desse script pelo navegador
        page = browser.new_page()
        context = page.new_context()

        print("Acessando a página de LOGIN...")
        page.goto("http://localhost:8080/login.html")

        # A partir que é carregado a tela, ele vai fazer o preenchimento
        page.fill('#usuario','usuarioautomatizado@empresa.com')
        page.fill('#senha','senha_muito_legal')
        page.click('.btn-submit')

        print("Aguardando redirecionamento...")

        #Após o bot clica em submit, vamos aguardar o carregamento de outra página
        page.wait_for_timeout("**/lote-teste.html")

        print("Sucesso!!!\nAcessando a página de Cadastro de Lotes")

        # Agora, chegamos na parte de preenchimento de cadastro, é preencher o formulário
        page.fill('#lote','LOTE-2026-9999')
        page.select_option('#produto','2')
        # O Bot vai clicar em processamento
        page.click("input[value='processamento']")
        # Agora vamos submeter
        page.click('.btn-submit')
        print("Formulario preenchido com sucesso, vamos pausar para visualização")
        page.wait_for_timeout(3000)

        browser.close()
        print("Concluido com sucesso")