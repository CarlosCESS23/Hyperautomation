from dataclasses import asdict

import pandas as pd
import pytest

from src.decisao_hibrida import (
    MotivoFallback,
    ResultadoDecisaoHibrida,
)
from src.item_processor import processar_item


pytestmark = pytest.mark.unit


CAMPOS_ENRIQUECIMENTO = {
    "causa_provavel",
    "confianca_ml",
    "origem_decisao",
    "motivo_fallback",
    "versao_modelo",
}


class ClassificadorFake:
    def __init__(self, decisao):
        self.decisao = decisao
        self.chamadas = []

    def classificar(self, observacao):
        self.chamadas.append(
            observacao
        )

        return self.decisao


def registro_divergente():
    return pd.Series(
        {
            "lote_id": "LOTE-FORA-DA-BASE",
            "produto": "Produto A",
            "linha": "Linha 1",
            "turno": "MANHÃ",
            "status": "APROVADO",
            "responsavel": "Carlos",
            "data": "18/08/2026",
            "observacao": (
                "Código do produto não localizado."
            ),
        }
    )


def dados_negocio(resultado):
    return {
        campo: valor
        for campo, valor in asdict(
            resultado
        ).items()
        if campo not in CAMPOS_ENRIQUECIMENTO
    }


def test_divergencia_recebe_enriquecimento_ml():
    classificador = ClassificadorFake(
        ResultadoDecisaoHibrida.de_ml(
            causa_provavel="erro_codigo",
            confianca_ml=0.91,
            versao_modelo="2.0.0-texto",
        )
    )

    resultado = processar_item(
        registro=registro_divergente(),
        data_referencia="18/08/2026",
        lotes_referencia={"OUTRO-LOTE"},
        ocorrencia_no_dia=1,
        classificador=classificador,
    )

    assert resultado.classificacao == "Divergência"
    assert resultado.regra_aplicada == "RN05"

    assert resultado.causa_provavel == "erro_codigo"
    assert resultado.confianca_ml == 0.91
    assert resultado.origem_decisao == "ml"
    assert resultado.motivo_fallback == ""
    assert resultado.versao_modelo == "2.0.0-texto"

    assert classificador.chamadas == [
        "Código do produto não localizado."
    ]


def test_fallback_nao_modifica_decisao_de_negocio():
    resultado_regras = processar_item(
        registro=registro_divergente(),
        data_referencia="18/08/2026",
        lotes_referencia={"OUTRO-LOTE"},
        ocorrencia_no_dia=1,
        classificador=ClassificadorFake(
            ResultadoDecisaoHibrida.de_ml(
                causa_provavel="erro_codigo",
                confianca_ml=0.91,
                versao_modelo="2.0.0-texto",
            )
        ),
    )

    resultado_fallback = processar_item(
        registro=registro_divergente(),
        data_referencia="18/08/2026",
        lotes_referencia={"OUTRO-LOTE"},
        ocorrencia_no_dia=1,
        classificador=ClassificadorFake(
            ResultadoDecisaoHibrida.de_fallback(
                motivo=(
                    MotivoFallback
                    .SERVICO_INDISPONIVEL
                ),
            )
        ),
    )

    assert (
        dados_negocio(resultado_regras)
        == dados_negocio(resultado_fallback)
    )

    assert resultado_fallback.causa_provavel == (
        "nao_classificado"
    )

    assert resultado_fallback.confianca_ml is None
    assert resultado_fallback.origem_decisao == "fallback"

    assert resultado_fallback.motivo_fallback == (
        "servico_indisponivel"
    )


def test_registro_valido_nao_chama_classificador():
    classificador = ClassificadorFake(
        ResultadoDecisaoHibrida.de_ml(
            causa_provavel="erro_codigo",
            confianca_ml=0.91,
        )
    )

    registro = registro_divergente()
    registro["lote_id"] = "LOTE-VALIDO"

    resultado = processar_item(
        registro=registro,
        data_referencia="18/08/2026",
        lotes_referencia={"LOTE-VALIDO"},
        ocorrencia_no_dia=1,
        classificador=classificador,
    )

    assert resultado.classificacao == "Válido"
    assert classificador.chamadas == []

    assert resultado.causa_provavel == ""
    assert resultado.confianca_ml is None
    assert resultado.origem_decisao == ""