"""Page Object do formulário de cadastro de lotes."""

from pathlib import Path

from playwright.sync_api import Page


class PlaywrightFormularioLotesPage:
    """Encapsula as interações com ``frontend/lote-teste.html``."""

    def __init__(self, page: Page, pagina_html: str) -> None:
        self.page = page
        self.pagina_html = pagina_html
        self.campo_lote = page.locator("#lote")
        self.campo_produto = page.locator("#produto")
        self.botao_validar = page.get_by_role("button", name="Processar Lote")
        self.mensagem_sucesso = page.locator("#mensagemSucesso")

    def abrir(self) -> None:
        """Abre o formulário local no navegador."""
        self.page.goto(Path(self.pagina_html).as_uri())

    def preencher_lote(self, valor: str) -> None:
        """Preenche o campo Número do Lote."""
        self.campo_lote.clear()
        self.campo_lote.fill(valor)

    def selecionar_produto(self, valor: str) -> None:
        """Seleciona um produto pelo valor do elemento ``option``."""
        self.campo_produto.select_option(valor)

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
