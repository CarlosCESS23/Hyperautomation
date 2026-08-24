"""Testes da auditoria das decisões de Machine Learning."""

from unittest.mock import Mock

import pytest

from src.ml_decisions import (
    AuditoriaDecisoesML,
    STATUS_OFFLINE,
)


pytestmark = pytest.mark.unit


def test_auditoria_registra_api_offline_sem_lancar_excecao():
    """
    Quando o classificador retorna None, a auditoria deve
    registrar a indisponibilidade sem interromper o fluxo.
    """

    logger = Mock()

    auditoria = AuditoriaDecisoesML(
        logger=logger
    )

    resposta = auditoria.classificar(
        lote_id="LOTE-OFFLINE-001",
        classificador=lambda: None,
    )

    # A resposta original do classificador continua sendo None.
    assert resposta is None

    # Mesmo sem predição, uma decisão de auditoria foi criada.
    assert len(auditoria.decisoes) == 1

    decisao = auditoria.decisoes[0]

    assert decisao.lote_id == "LOTE-OFFLINE-001"
    assert decisao.status_chamada == STATUS_OFFLINE
    assert decisao.classe_prevista is None
    assert decisao.probabilidade is None
    assert decisao.nivel_confianca is None
    assert decisao.detalhe_erro == "API ML indisponível"
    assert decisao.latencia_ms >= 0

    # Verifica se o evento também foi enviado ao logger.
    logger.info.assert_called_once()

    chamada_logger = logger.info.call_args

    assert chamada_logger.args[0] == "decisao_ml"

    evento = chamada_logger.kwargs["extra"]

    assert evento["evento"] == "decisao_ml"
    assert evento["lote_id"] == "LOTE-OFFLINE-001"
    assert evento["status_chamada"] == STATUS_OFFLINE
    assert evento["classe_prevista"] is None
    assert evento["probabilidade"] is None
    assert evento["detalhe_erro"] == "API ML indisponível"