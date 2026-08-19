"""Camada que integra a validação existente à decisão de ML."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from src.ml_client import MLClient
from src.validacao_lotes import RegistroValidado, validar_registro


ACAO_ML_OFFLINE = "REVISAO_ML_OFFLINE"


def processar_item(
    registro: pd.Series,
    data_referencia: str,
    lotes_referencia: set[str],
    ocorrencia_no_dia: int,
    ml_client: MLClient,
) -> RegistroValidado:
    """Valida o registro e consulta ML somente para itens ambíguos."""

    resultado = validar_registro(
        registro=registro,
        data_referencia=data_referencia,
        lotes_referencia=lotes_referencia,
        ocorrencia_no_dia=ocorrencia_no_dia,
    )

    # As RN01–RN12 continuam sendo a fonte da classificação inicial.
    if resultado.classificacao != "Ambíguo":
        return resultado

    predicao = ml_client.classificar(
        status_raw=str(registro.get("status", "")).strip().upper(),
        turno=str(registro.get("turno", "")).strip().upper(),
        tem_obs=bool(str(registro.get("observacao", "")).strip()),
    )

    if predicao is None:
        return replace(
            resultado,
            motivo=f"{resultado.motivo}; API ML indisponível",
            acao_recomendada=ACAO_ML_OFFLINE,
        )

    return replace(
        resultado,
        motivo=(
            f"{resultado.motivo}; "
            f"ML: {predicao['classe']} "
            f"({predicao['probabilidade']:.2%})"
        ),
        acao_recomendada=str(predicao["nivel_confianca"]),
    )