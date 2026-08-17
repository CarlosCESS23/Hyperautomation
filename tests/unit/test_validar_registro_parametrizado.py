"""Cenários parametrizados do contrato de negócio de RN01 a RN12."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.validacao_lotes import validar_registro


pytestmark = pytest.mark.unit


@pytest.fixture
def criar_registro():
    """Cria registros isolados a partir de um exemplo válido."""
    registro_base = {
        "lote_id": "LOTE-001",
        "produto": "Produto A",
        "linha": "Linha 1",
        "turno": "Manhã",
        "status": "APROVADO",
        "responsavel": "Ana",
        "data": "15/08/2026",
        "observacao": "Inspeção concluída",
    }

    def fabrica(**alteracoes):
        return pd.Series(registro_base | alteracoes, dtype=object)

    return fabrica


@pytest.mark.parametrize(
    (
        "regra",
        "dados_registro",
        "lote_na_base",
        "ocorrencia_no_dia",
        "classificacao_esperada",
        "motivo_esperado",
        "status_esperado",
    ),
    [
        pytest.param(
            "RN01",
            {},
            True,
            1,
            "Válido",
            "Registro em conformidade",
            "APROVADO",
            id="rn01-registro-com-estrutura-valida",
        ),
        pytest.param(
            "RN02",
            {"produto": ""},
            True,
            1,
            "Erro de Entrada",
            "Campo obrigatório vazio: produto",
            "APROVADO",
            id="rn02-produto-obrigatorio-ausente",
        ),
        pytest.param(
            "RN03",
            {"lote_id": "  LOTE-001  ", "responsavel": "  Ana  "},
            True,
            1,
            "Válido",
            "Registro em conformidade",
            "APROVADO",
            id="rn03-campos-textuais-normalizados",
        ),
        pytest.param(
            "RN04",
            {"status": "ok"},
            True,
            1,
            "Válido",
            "Registro em conformidade",
            "APROVADO",
            id="rn04-status-ok-reconhecido",
        ),
        pytest.param(
            "RN05",
            {},
            False,
            1,
            "Divergência",
            "Lote não encontrado na base de referência",
            "APROVADO",
            id="rn05-lote-divergente-da-base-referencia",
        ),
        pytest.param(
            "RN06",
            {"status": "nok", "observacao": "Falha dimensional"},
            True,
            1,
            "Válido",
            "Registro em conformidade",
            "REPROVADO",
            id="rn06-status-nok-normalizado",
        ),
        pytest.param(
            "RN07",
            {"status": "REPROVADO", "observacao": "   "},
            True,
            1,
            "Divergência",
            "Lote reprovado sem observação",
            "REPROVADO",
            id="rn07-reprovado-sem-observacao",
        ),
        pytest.param(
            "RN08",
            {"status": "PENDENTE", "observacao": ""},
            True,
            1,
            "Válido",
            "Registro em conformidade",
            "PENDENTE",
            id="rn08-pendente-sem-observacao-permitido",
        ),
        pytest.param(
            "RN09",
            {"status": "EM ANÁLISE"},
            True,
            1,
            "Ambíguo",
            "Status não reconhecido: EM ANÁLISE",
            "EM ANÁLISE",
            id="rn09-status-desconhecido-ambiguo",
        ),
        pytest.param(
            "RN10",
            {"status": "REPROVADO", "observacao": "Falha dimensional"},
            True,
            1,
            "Válido",
            "Registro em conformidade",
            "REPROVADO",
            id="rn10-reprovado-com-observacao",
        ),
        pytest.param(
            "RN11",
            {},
            True,
            2,
            "Divergência",
            "Duplicidade no dia 15/08/2026 (ocorrência 2)",
            "APROVADO",
            id="rn11-segunda-ocorrencia-duplicada-no-dia",
        ),
        pytest.param(
            "RN12",
            {"data": "2026-08-15"},
            True,
            1,
            "Erro de Entrada",
            "Data ausente ou fora do formato DD/MM/AAAA",
            "APROVADO",
            id="rn12-data-em-formato-invalido",
        ),
    ],
)
def test_validar_registro_aplica_regras_rn01_a_rn12(
    criar_registro,
    regra,
    dados_registro,
    lote_na_base,
    ocorrencia_no_dia,
    classificacao_esperada,
    motivo_esperado,
    status_esperado,
):
    # Arrange
    registro = criar_registro(**dados_registro)
    base_referencia = MagicMock(name=f"base_referencia_{regra.lower()}")
    base_referencia.__contains__.return_value = lote_na_base

    # Act
    resultado = validar_registro(
        registro,
        data_referencia="15/08/2026",
        lotes_referencia=base_referencia,
        ocorrencia_no_dia=ocorrencia_no_dia,
    )

    # Assert
    assert resultado.classificacao == classificacao_esperada
    assert resultado.motivo == motivo_esperado
    assert resultado.status == status_esperado

    if classificacao_esperada == "Erro de Entrada":
        base_referencia.__contains__.assert_not_called()
    else:
        base_referencia.__contains__.assert_called_once_with("LOTE-001")
