"""Testes unitários da normalização de status de inspeção."""

import pytest

from src.validacao_lotes import normalizar_status


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        pytest.param("OK", "APROVADO", id="ok-maiusculo"),
        pytest.param("ok", "APROVADO", id="ok-minusculo"),
        pytest.param("  Ok  ", "APROVADO", id="ok-misto-com-espacos"),
        pytest.param("APROVADO", "APROVADO", id="aprovado-maiusculo"),
        pytest.param("aprovado", "APROVADO", id="aprovado-minusculo"),
        pytest.param("  Aprovado  ","APROVADO",id="aprovado-misto-com-espacos",),
        pytest.param("REPROVADO", "REPROVADO", id="reprovado-maiusculo"),
        pytest.param("reprovado", "REPROVADO", id="reprovado-minusculo"),
        pytest.param( "  Reprovado  ","REPROVADO",id="reprovado-misto-com-espacos",),
    ],
)
def test_normaliza_status_reconhecido(entrada, esperado):
    # Arrange
    status = entrada
    # Act
    resultado = normalizar_status(status)
    # Assert
    assert resultado == esperado
@pytest.mark.regression
@pytest.mark.parametrize(
    "entrada",
    [
        pytest.param("NOK", id="nok-maiusculo"),
        pytest.param("nok", id="nok-minusculo"),
        pytest.param("NoK", id="nok-caixa-mista"),
        pytest.param("  nOk  ",id="nok-caixa-mista-com-espacos", ),
    ],
)
def test_regressao_normaliza_nok_para_reprovado(entrada):
    """
    Protegendo contra regressão a conversão crítica de NOK para reprovado
    """

    # Arrange
    status = entrada

    #Act
    resultado = normalizar_status(status)

    # Assert
    assert resultado == 'REPROVADO'

@pytest.mark.parametrize(
    "entrada",
    [
        pytest.param("", id="string-vazia"),
        pytest.param("   ", id="somente-espacos"),
        pytest.param(None, id="valor-ausente-none"),
    ],
)
def test_normaliza_status_vazio_ou_ausente_para_string_vazia(entrada):
    # Arrange
    status = entrada

    # Act
    resultado = normalizar_status(status)

    # Assert
    assert resultado == ""


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        pytest.param("PENDENTE", "PENDENTE", id="pendente-reconhecido-sem-mapeamento"),
        pytest.param("EM ANALISE", "EM ANALISE", id="desconhecido-maiusculo"),
        pytest.param(
            "  Em Analise  ", "EM ANALISE", id="desconhecido-misto-com-espacos"
        ),
    ],
)
def test_preserva_status_nao_mapeado_apos_tratamento(entrada, esperado):
    # Arrange
    status = entrada

    # Act
    resultado = normalizar_status(status)

    # Assert
    assert resultado == esperado
