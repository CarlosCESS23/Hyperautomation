from playwright.sync_api import Page

class PlaywrightFormularioLoginPage:
    def __init__(self,page: Page,paginaHTML: str):
        """
        Quando é instanciado, inicializamos a página e mapeamos os elementos (locators) da interface
        de login.
        Os seletores (que são ID, NAME, CSS) devem corresponder qual label que queira captura
        """
        self.page = page

        #Mapeamento de Locators
        self.paginaHTML = paginaHTML
        self.input_usuario = page.locator("#usuario")
        self.input_senha = page.locator("#senha")
        self.botao_entrar = page.locator("button[type='submit']")

        def navegar(self):
            """
            Acessando a página de login.
            """
            self.page.goto(self.paginaHTML)

        def preencher_credenciais(self,usuario : str, senha : str):
            """
            Preenchendo os campos de usuário e senha
            """
            self.input_usuario.fill(usuario)
            self.input_senha.fill(senha)

        def submeter(self):
            """
            O Bot clica no botão de login
            """
            self.botao_entrar.click()

        def realizar_login(self,usuario : str, senha : str):
            """
            Método que realizará os procedimentos de login (Chamando os métodos e fazendo passo a passo)
            """
            self.preencher_credenciais(usuario,senha)
            self.submeter()

