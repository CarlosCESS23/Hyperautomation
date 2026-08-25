from dataclasses import asdict

import pandas as pd
import pytest

from src.classificador_divergencia import (
    ClassificadorDivergencia,
)
from src.item_processor import processar_item
from src.ml_client import (
    MLServiceUnavailableError,
)


pytestmark = pytest.mark.integration


CAMPOS_ENRIQUECIMENTO = {
    "causa_provavel",
    "confianca_ml",
    "origem_decisao",
    "motivo_fallback",
    "versao_modelo",
}


class ClienteComSucesso:
    def __init__(self):
        self.chamadas = []

    def classificar_observacao(
        self,
        *,
        observacao,
    ):
        self.chamadas.append(
            observacao
        )

        return {
            "causa_provavel": "erro_codigo",
            "confianca_ml": 0.92,
            "versao_modelo": "2.0.0-texto",
        }


class ClienteIndisponivel:
    def __init__(self):
        self.chamadas = []

    def classificar_observacao(
        self,
        *,
        observacao,
    ):
        self.chamadas.append(
            observacao
        )

        raise MLServiceUnavailableError(
            "API offline"
        )


def criar_registro_divergente():
    return pd.Series(
        {
            "lote_id": "LOTE-NAO-CADASTRADO",
            "produto": "Produto A",
            "linha": "Linha 1",
            "turno": "MANHÃ",
            "status": "APROVADO",
            "responsavel": "Carlos",
            "data": "18/08/2026",
            "observacao": (
                "Código informado não existe."
            ),
        }
    )


def somente_negocio(resultado):
    return {
        campo: valor
        for campo, valor in asdict(
            resultado
        ).items()
        if campo not in CAMPOS_ENRIQUECIMENTO
    }


def processar_com(classificador):
    return processar_item(
        registro=criar_registro_divergente(),
        data_referencia="18/08/2026",
        lotes_referencia={"OUTRO-LOTE"},
        ocorrencia_no_dia=1,
        classificador=classificador,
    )


def test_decisao_de_negocio_independe_do_ml():
    cliente_sucesso = ClienteComSucesso()
    cliente_offline = ClienteIndisponivel()
    cliente_desativado = ClienteComSucesso()

    resultado_ml = processar_com(
        ClassificadorDivergencia(
            cliente_ml=cliente_sucesso,
            ml_enabled=True,
            confianca_minima=0.75,
        )
    )

    resultado_offline = processar_com(
        ClassificadorDivergencia(
            cliente_ml=cliente_offline,
            ml_enabled=True,
            confianca_minima=0.75,
        )
    )

    resultado_desativado = processar_com(
        ClassificadorDivergencia(
            cliente_ml=cliente_desativado,
            ml_enabled=False,
            confianca_minima=0.75,
        )
    )

    assert (
        somente_negocio(resultado_ml)
        == somente_negocio(resultado_offline)
        == somente_negocio(resultado_desativado)
    )

    assert resultado_ml.classificacao == "Divergência"
    assert resultado_offline.classificacao == "Divergência"
    assert resultado_desativado.classificacao == "Divergência"

    assert resultado_ml.regra_aplicada == "RN05"
    assert resultado_offline.regra_aplicada == "RN05"
    assert resultado_desativado.regra_aplicada == "RN05"

    assert resultado_ml.causa_provavel == "erro_codigo"
    assert resultado_ml.confianca_ml == 0.92
    assert resultado_ml.origem_decisao == "ml"

    assert resultado_offline.causa_provavel == (
        "nao_classificado"
    )
    assert resultado_offline.origem_decisao == "fallback"
    assert resultado_offline.motivo_fallback == (
        "servico_indisponivel"
    )

    assert resultado_desativado.causa_provavel == (
        "nao_classificado"
    )
    assert resultado_desativado.origem_decisao == "fallback"
    assert resultado_desativado.motivo_fallback == (
        "ml_desativado"
    )

    assert cliente_sucesso.chamadas == [
        "Código informado não existe."
    ]

    assert cliente_offline.chamadas == [
        "Código informado não existe."
    ]

    # A feature flag impede a chamada.
    assert cliente_desativado.chamadas == []