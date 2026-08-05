from playwright.sync_api import Page

class PlaywrightFormularioLoginPage:
    def __init__(self,page: Page,paginaHTML: str):
        """
        Quando é instanciado, inicializamos a página e mapeamos os elementos (locators) da interface
        de login.
        Os seletores (que são ID, NAME, CSS) devem corresponder qual label que queira captura
        """
        self.__page = page

        #Mapeamento de Locators
        self.__paginaHTML = paginaHTML
        self.__input_usuario = page.locator("#usuario")
        self.__input_senha = page.locator("#senha")
        self.__botao_entrar = page.locator("button[type='submit']")

    def navegar(self):
            """
            Acessando a página de login.
            """
            self.__page.goto(self.__paginaHTML)

    def __preencher_credenciais(self, usuario: str, senha: str):
            """
            Preenchendo os campos de usuário e senha
            """
            #Limpando o campo, caso o usuário tenha digitado algo
            self.__input_usuario.clear()
            self.__input_senha.clear()

            self.__input_usuario.fill(usuario)
            self.__input_senha.fill(senha)

    def __submeter(self):
            """preencher_credenciais
            O Bot clica no botão de login
            """
            self.__page.get_by_role("button", name="Entrar").click()

    def realizar_login(self, usuario: str, senha: str):
            """
            Método que realizará os procedimentos de login (Chamando os métodos e fazendo passo a passo)
            """
            self.__preencher_credenciais(usuario,senha)
            self.__submeter()

