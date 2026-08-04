"""Fixtures compartilhadas pela suíte de testes."""

from pathlib import Path

import pytest

from src.pages.formulario_lotes_page import PlaywrightFormularioLotesPage


@pytest.fixture
def pagina_html() -> str:
    """Retorna o caminho absoluto do formulário alvo dos testes E2E."""
    caminho = Path(__file__).resolve().parents[1] / "frontend" / "lote-teste.html"
    if not caminho.exists():
        pytest.skip(f"Arquivo {caminho} não encontrado — teste E2E ignorado")
    return str(caminho)


@pytest.fixture
def formulario_page(page, pagina_html) -> PlaywrightFormularioLotesPage:
    """Fornece o Page Object com o formulário aberto em uma aba limpa."""
    formulario = PlaywrightFormularioLotesPage(page=page, pagina_html=pagina_html)
    formulario.abrir()
    return formulario
