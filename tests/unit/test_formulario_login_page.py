from unittest.mock import MagicMock

import pytest

from src.pages.formulario_login_pages import PlaywrightFormularioLoginPage


pytestmark = pytest.mark.unit


def test_navega_e_realiza_login():
    pagina = MagicMock()
    usuario = MagicMock()
    senha = MagicMock()
    pagina.locator.side_effect = [usuario, senha, MagicMock()]
    botao = pagina.get_by_role.return_value
    formulario = PlaywrightFormularioLoginPage(pagina, "http://portal/login")

    formulario.navegar()
    formulario.realizar_login("operador", "segredo-de-teste")

    pagina.goto.assert_called_once_with("http://portal/login")
    usuario.clear.assert_called_once()
    usuario.fill.assert_called_once_with("operador")
    senha.fill.assert_called_once_with("segredo-de-teste")
    botao.click.assert_called_once()
