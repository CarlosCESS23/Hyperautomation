"""Page Object do formulário de cadastro de lotes."""

from pathlib import Path

from playwright.sync_api import Page


class PlaywrightFormularioLotesPage:
    """Encapsula as interações com ``frontend/lote-teste.html``."""

    def __init__(self, page: Page, pagina_html: str) -> None:
        self.__page = page
        self.__pagina_html = pagina_html
        self.__campo_lote = page.locator("#lote")
        self.__campo_produto = page.locator("#produto")
        self.__botao_validar = page.get_by_role("button", name="Processar Lote")
        self.__mensagem_sucesso = page.locator("#mensagemSucesso")

    def abrir(self) -> None:
        """Abre o formulário local no navegador."""
        self.__page.goto(self.__pagina_html)

    def __preencher_lote(self, valor: str) -> None:
        """Preenche o campo Número do Lote."""
        self.__campo_lote.clear()
        self.__campo_lote.fill(valor)

    def __selecionar_produto(self, nome_produto: str) -> None:
        """Seleciona um produto pelo valor do elemento ``option``."""
        self.__campo_produto.select_option(label=nome_produto)

    def __selecionar_status(self, valor: str) -> None:
        """Seleciona o status pelo valor do botão de opção."""
        self.__page.locator(f'input[name="status"][value="{valor}"]').check()

    def __obter_status_selecionado(self) -> str:
        """Retorna o valor do status selecionado."""
        return self.__page.locator('input[name="status"]:checked').input_value()

    def __submeter(self) -> None:
        """Submete o formulário pelo botão Processar Lote."""
        self.__botao_validar.click()

    def __mensagem_sucesso_visivel(self) -> bool:
        """Informa se a mensagem de sucesso está visível."""
        return self.__mensagem_sucesso.is_visible()

    def __capturar_evidencia(self, caminho: str) -> None:
        """Captura a página inteira como evidência PNG."""
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        self.__page.screenshot(path=caminho, full_page=True)

    #Metódo dessa classe será responsavel de efetuar os passos a passos
    def realizar_cadastro(self,lote: str, produto: str,status : str, caminho_evidencia:str = None)  -> None:
        #1. Preenchendo o formulário
        self.__preencher_lote(lote)
        self.__selecionar_produto(produto)
        self.__selecionar_status(status)

        #2. Vamos cliar o botão para processar
        self.__submeter()

        self.__page.wait_for_timeout(1000)
        self.__capturar_evidencia(caminho_evidencia)


