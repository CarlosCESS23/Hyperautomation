"""Integra as regras RN01–RN12 ao enriquecimento híbrido."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from src.classificador_divergencia import (
    ClassificadorDivergencia,
)
from src.decisao_hibrida import (
    ResultadoDecisaoHibrida,
)
from src.validacao_lotes import (
    RegistroValidado,
    validar_registro,
)


def _enriquecer_resultado(
    resultado: RegistroValidado,
    decisao: ResultadoDecisaoHibrida,
) -> RegistroValidado:
    """Adiciona somente informações produzidas pela camada híbrida."""

    motivo_fallback = (
        decisao.motivo_fallback.value
        if decisao.motivo_fallback is not None
        else ""
    )

    return replace(
        resultado,
        causa_provavel=decisao.causa_provavel,
        confianca_ml=decisao.confianca_ml,
        origem_decisao=decisao.origem_decisao.value,
        motivo_fallback=motivo_fallback,
        versao_modelo=decisao.versao_modelo,
    )


def processar_item(
    registro: pd.Series,
    data_referencia: str,
    lotes_referencia: set[str],
    ocorrencia_no_dia: int,
    classificador: ClassificadorDivergencia,
) -> RegistroValidado:
    """Aplica as regras e enriquece somente divergências.

    Os campos de negócio retornados pelas RN01–RN12 não são
    modificados pela decisão de Machine Learning.
    """

    resultado_regras = validar_registro(
        registro=registro,
        data_referencia=data_referencia,
        lotes_referencia=lotes_referencia,
        ocorrencia_no_dia=ocorrencia_no_dia,
    )

    # O novo ML sugere somente causas de divergências.
    if resultado_regras.classificacao != "Divergência":
        return resultado_regras

    decisao_hibrida = classificador.classificar(
        resultado_regras.observacao
    )

    return _enriquecer_resultado(
        resultado_regras,
        decisao_hibrida,
    )