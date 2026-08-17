"""Page Object do formulário de cadastro de lotes."""

from pathlib import Path

from playwright.sync_api import Page


class PlaywrightFormularioLotesPage:
    """Encapsula as interações com ``web/lote-teste.html``."""

    def __init__(self, page: Page, pagina_html: str) -> None:
        self.page = page
        self.pagina_html = pagina_html
        self.campo_lote = page.locator("#lote")
        self.campo_produto = page.locator("#produto")
        self.botao_validar = page.get_by_role("button", name="Processar Lote")
        self.mensagem_sucesso = page.locator("#mensagemSucesso")

    def abrir(self) -> None:
        """Abre o formulário no navegador. Tendo suporte para HTML e também para file///."""
        if self.pagina_html.startswith("http"):
            self.page.goto(self.pagina_html)
        else:
            # Converte o caminho do arquivo para o formato file:///... exigido pelo Playwright
            caminho_absoluto = Path(self.pagina_html).resolve()
            self.page.goto(caminho_absoluto.as_uri())

    def preencher_lote(self, valor: str) -> None:
        """Preenche o campo Número do Lote."""
        self.campo_lote.clear()
        self.campo_lote.fill(valor)

    def selecionar_produto(self, valor: str) -> None:
        """Seleciona um produto pelo atributo 'value' do elemento ``option``."""
        self.campo_produto.select_option(value=valor)

    def selecionar_status(self, valor: str) -> None:
        """Seleciona o status pelo valor do botão de opção."""
        self.page.locator(f'input[name="status"][value="{valor}"]').check()

    def obter_status_selecionado(self) -> str:
        """Retorna o valor do status selecionado."""
        return self.page.locator('input[name="status"]:checked').input_value()

    def submeter(self) -> None:
        """Submete o formulário pelo botão Processar Lote."""
        self.botao_validar.click()

    def mensagem_sucesso_visivel(self) -> bool:
        """Informa se a mensagem de sucesso está visível."""
        return self.mensagem_sucesso.is_visible()

    def capturar_evidencia(self, caminho: str) -> None:
        """Captura a página inteira como evidência PNG."""
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=caminho, full_page=True)

    #Metódo dessa classe será responsavel de efetuar os passos a passos
    def realizar_cadastro(self,lote: str, produto: str,status : str, caminho_evidencia:str = None)  -> None:
        #1. Preenchendo o formulário
        self.preencher_lote(lote)
        self.selecionar_produto(produto)
        self.selecionar_status(status)

        #2. Vamos cliar o botão para processar
        self.submeter()

        self.page.wait_for_timeout(1000)
        self.capturar_evidencia(caminho_evidencia)


