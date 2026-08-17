"""Testes E2E do formulário de cadastro de lotes com Chromium real."""

from pathlib import Path

import pytest


pytestmark = pytest.mark.e2e


@pytest.mark.skip(
    reason=(
        "Dashboard de produção: ambiente autenticado de homologação "
        "ainda não está disponível para a suíte E2E"
    )
)
def test_dashboard_de_producao_exibe_lote_cadastrado():
    """Documenta o fluxo futuro que depende do ambiente de homologação."""


class TestFormularioCadastroLotes:
    def test_pagina_carrega_com_titulo_correto(self, formulario_page):
        assert "Cadastro de Lotes" in formulario_page.page.title()

    def test_campo_numero_lote_aceita_entrada(self, formulario_page):
        formulario_page.preencher_lote("LOTE-2026-0001")
        assert formulario_page.campo_lote.input_value() == "LOTE-2026-0001"

    def test_dropdown_produto_aceita_selecao(self, formulario_page):
        formulario_page.selecionar_produto("1")
        assert formulario_page.campo_produto.input_value() == "1"

    def test_radio_status_pendente_selecionado_por_padrao(self, formulario_page):
        assert formulario_page.obter_status_selecionado() == "pendente"

    def test_formulario_completo_exibe_sucesso(self, formulario_page):
        formulario_page.preencher_lote("LOTE-2026-9999")
        formulario_page.selecionar_produto("2")
        formulario_page.selecionar_status("concluido")
        formulario_page.submeter()
        assert formulario_page.mensagem_sucesso_visivel()

    def test_submissao_sem_produto_nao_exibe_sucesso(self, formulario_page):
        formulario_page.preencher_lote("LOTE-2026-0002")
        formulario_page.submeter()
        assert not formulario_page.mensagem_sucesso_visivel()

    def test_submissao_sem_numero_lote_nao_exibe_sucesso(self, formulario_page):
        formulario_page.selecionar_produto("1")
        formulario_page.submeter()
        assert not formulario_page.mensagem_sucesso_visivel()

    def test_screenshot_capturado_como_evidencia(self, formulario_page):
        caminho = Path(__file__).parent / "screenshots" / "evidencia_formulario.png"
        formulario_page.capturar_evidencia(str(caminho))
        assert caminho.exists()
        assert caminho.stat().st_size > 0
