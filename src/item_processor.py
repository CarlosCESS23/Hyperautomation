"""Camada que integra a validação existente à decisão de ML."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from src.ml_client import MLClient
from src.validacao_lotes import RegistroValidado, validar_registro
from src.ml_decisions import AuditoriaDecisoesML

ACAO_ML_OFFLINE = "REVISAO_ML_OFFLINE"
payload_ml = {
    "status_raw": "APROVADO",
    "turno": "MANHA",
    "tem_obs": True,
}


def processar_item(
    registro: pd.Series,
    data_referencia: str,
    lotes_referencia: set[str],
    ocorrencia_no_dia: int,
    ml_client: MLClient,
    auditoria_ml: AuditoriaDecisoesML | None = None,
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

    payload_ml = {
        "status_raw": str(
            registro.get("status", "")
        ).strip().upper(),
        "turno": str(
            registro.get("turno", "")
        ).strip().upper(),
        "tem_obs": bool(
            str(
                registro.get("observacao", "")
            ).strip()
        ),
    }

    # Quando uma auditoria foi fornecida, ela executa e registra
    # a chamada realizada pelo MLClient.
    if auditoria_ml is not None:
        predicao = auditoria_ml.classificar(
            lote_id=str(
                registro.get("lote_id", "")
            ),
            classificador=ml_client.classificar,
            **payload_ml,
        )

    # Mantém compatibilidade com testes e usos que ainda não
    # fornecem uma instância de auditoria.
    else:
        predicao = ml_client.classificar(
            **payload_ml,
        )

    # Quando uma auditoria foi fornecida, ela executa e vai registrar

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