import pandas as pd
import pytest

from src.item_processor import ACAO_ML_OFFLINE, processar_item


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