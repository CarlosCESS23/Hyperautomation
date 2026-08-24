import pandas as pd
import pytest
from unittest.mock import Mock

from src.item_processor import ACAO_ML_OFFLINE, processar_item
from src.ml_decisions import (
    AuditoriaDecisoesML,
    STATUS_OFFLINE,
)



class MLIndisponivel:
    def classificar(self, **kwargs):
        return None


@pytest.mark.unit
def test_item_ambiguo_usa_fallback_quando_ml_esta_indisponivel():
    registro = pd.Series(
        {
            "lote_id": "LOTE-001",
            "produto": "Produto A",
            "linha": "L1",
            "turno": "MANHA",
            "status": "EM ANALISE",
            "responsavel": "Carlos",
            "data": "18/08/2026",
            "observacao": "",
        }
    )

    resultado = processar_item(
        registro=registro,
        data_referencia="18/08/2026",
        lotes_referencia={"LOTE-001"},
        ocorrencia_no_dia=1,
        ml_client=MLIndisponivel(),
    )

    assert resultado.classificacao == "Ambíguo"
    assert resultado.acao_recomendada == ACAO_ML_OFFLINE
    assert "API ML indisponível" in resultado.motivo

@pytest.mark.unit
def test_item_ambiguo_registra_auditoria_quando_ml_esta_offline():
    """
    Verifica se uma chamada offline é registrada pela auditoria
    sem impedir o fallback REVISAO_ML_OFFLINE.
    """

    registro = pd.Series(
        {
            "lote_id": "LOTE-OFFLINE-001",
            "produto": "Produto A",
            "linha": "L1",
            "turno": "MANHA",
            "status": "EM ANALISE",
            "responsavel": "Carlos",
            "data": "18/08/2026",
            "observacao": "",
        }
    )

    logger = Mock()

    auditoria = AuditoriaDecisoesML(
        logger=logger,
    )

    resultado = processar_item(
        registro=registro,
        data_referencia="18/08/2026",
        lotes_referencia={
            "LOTE-OFFLINE-001"
        },
        ocorrencia_no_dia=1,
        ml_client=MLIndisponivel(),
        auditoria_ml=auditoria,
    )

    # O processamento continua usando o fallback.
    assert resultado.classificacao == "Ambíguo"
    assert resultado.acao_recomendada == ACAO_ML_OFFLINE
    assert "API ML indisponível" in resultado.motivo

    # A chamada offline precisa aparecer na auditoria.
    assert len(auditoria.decisoes) == 1

    decisao = auditoria.decisoes[0]

    assert decisao.lote_id == "LOTE-OFFLINE-001"
    assert decisao.status_chamada == STATUS_OFFLINE
    assert decisao.classe_prevista is None
    assert decisao.probabilidade is None
    assert decisao.nivel_confianca is None
    assert decisao.detalhe_erro == "API ML indisponível"
    assert decisao.latencia_ms >= 0

    # Confirma que o evento foi enviado ao logger.
    logger.info.assert_called_once()

    evento = logger.info.call_args.kwargs["extra"]

    assert evento["evento"] == "decisao_ml"
    assert evento["lote_id"] == "LOTE-OFFLINE-001"
    assert evento["status_chamada"] == STATUS_OFFLINE@pytest.mark.unit
def test_item_ambiguo_registra_auditoria_quando_ml_esta_offline():
    """
    Verifica se uma chamada offline é registrada pela auditoria
    sem impedir o fallback REVISAO_ML_OFFLINE.
    """

    registro = pd.Series(
        {
            "lote_id": "LOTE-OFFLINE-001",
            "produto": "Produto A",
            "linha": "L1",
            "turno": "MANHA",
            "status": "EM ANALISE",
            "responsavel": "Carlos",
            "data": "18/08/2026",
            "observacao": "",
        }
    )

    logger = Mock()

    auditoria = AuditoriaDecisoesML(
        logger=logger,
    )

    resultado = processar_item(
        registro=registro,
        data_referencia="18/08/2026",
        lotes_referencia={
            "LOTE-OFFLINE-001"
        },
        ocorrencia_no_dia=1,
        ml_client=MLIndisponivel(),
        auditoria_ml=auditoria,
    )

    # O processamento continua usando o fallback.
    assert resultado.classificacao == "Ambíguo"
    assert resultado.acao_recomendada == ACAO_ML_OFFLINE
    assert "API ML indisponível" in resultado.motivo

    # A chamada offline precisa aparecer na auditoria.
    assert len(auditoria.decisoes) == 1

    decisao = auditoria.decisoes[0]

    assert decisao.lote_id == "LOTE-OFFLINE-001"
    assert decisao.status_chamada == STATUS_OFFLINE
    assert decisao.classe_prevista is None
    assert decisao.probabilidade is None
    assert decisao.nivel_confianca is None
    assert decisao.detalhe_erro == "API ML indisponível"
    assert decisao.latencia_ms >= 0

    # Confirma que o evento foi enviado ao logger.
    logger.info.assert_called_once()

    evento = logger.info.call_args.kwargs["extra"]

    assert evento["evento"] == "decisao_ml"
    assert evento["lote_id"] == "LOTE-OFFLINE-001"
    assert evento["status_chamada"] == STATUS_OFFLINE