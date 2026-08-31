"""Testes do log JSON utilizado pela execução dos três bots."""

from io import StringIO
import json
import logging

import pytest

from executar_pipeline_bots import FormatadorJSON
from src.auditoria_hibrida import (
    AuditoriaPipelineHibrido,
)
from src.decisao_hibrida import (
    MotivoFallback,
    ResultadoDecisaoHibrida,
)


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "motivo",
    [
        MotivoFallback.ML_DESATIVADO,
        MotivoFallback.SERVICO_INDISPONIVEL,
        MotivoFallback.TIMEOUT,
        MotivoFallback.BAIXA_CONFIANCA,
        MotivoFallback.RESPOSTA_INVALIDA,
    ],
)
def test_log_json_preserva_motivo_especifico_do_fallback(
    motivo,
):
    saida_log = StringIO()

    handler = logging.StreamHandler(
        saida_log
    )
    handler.setFormatter(
        FormatadorJSON()
    )

    logger = logging.getLogger(
        f"teste-log-{motivo.value}"
    )
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    auditoria = AuditoriaPipelineHibrido(
        execution_id="exec-log-001",
        logger=logger,
    )

    decisao = (
        ResultadoDecisaoHibrida.de_fallback(
            motivo=motivo,
        )
    )

    auditoria.registrar(
        lote_id="LOTE-LOG-001",
        decisao=decisao,
        latencia_ms=12.5,
    )

    linha = saida_log.getvalue().strip()

    assert linha

    dados = json.loads(linha)

    assert dados["evento"] == (
        "decisao_pipeline_hibrido"
    )
    assert dados["execution_id"] == (
        "exec-log-001"
    )
    assert dados["lote_id"] == (
        "LOTE-LOG-001"
    )
    assert dados["origem_decisao"] == (
        "fallback"
    )
    assert dados["motivo_fallback"] == (
        motivo.value
    )
    assert dados["causa_provavel"] == (
        "nao_classificado"
    )
    assert dados["confianca_ml"] is None
    assert dados["latencia_ms"] == 12.5