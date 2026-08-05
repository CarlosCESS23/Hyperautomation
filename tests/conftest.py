"""Fixtures compartilhadas pela suíte de testes."""

from pathlib import Path
import sys

import pytest

# Permite executar ``pytest tests/e2e/`` de qualquer diretório ou configuração
# de importação do pytest, sem exigir que o projeto esteja instalado como pacote.
RAIZ_PROJETO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from src.pages.formulario_lotes_page import PlaywrightFormularioLotesPage


@pytest.fixture
def pagina_html() -> str:
    """Retorna o caminho absoluto do formulário alvo dos testes E2E."""
    caminho = RAIZ_PROJETO / "web" / "lote-teste.html"
    if not caminho.exists():
        pytest.skip(f"Arquivo {caminho} não encontrado — teste E2E ignorado")
    return str(caminho)


@pytest.fixture
def formulario_page(page, pagina_html) -> PlaywrightFormularioLotesPage:
    """Fornece o Page Object com o formulário aberto em uma aba limpa."""
    formulario = PlaywrightFormularioLotesPage(page=page, pagina_html=pagina_html)
    formulario.abrir()
    return formulario