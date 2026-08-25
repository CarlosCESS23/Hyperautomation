from unittest.mock import Mock

from openpyxl import load_workbook
import pytest
import requests

from gerar_relatorio import ler_e_validar
from src.classificador_divergencia import (
    ClassificadorDivergencia,
)
from src.ml_client import MLClient
from tests.integration.test_fluxo_relatorio_excel import (
    ABAS_ENTRADA,
    criar_planilha_controlada,
)


pytestmark = pytest.mark.integration


def test_sabotagem_api_nao_interrompe_processamento(
    tmp_path,
):
    entrada = tmp_path / "entrada_sabotagem.xlsx"

    criar_planilha_controlada(
        entrada
    )

    workbook = load_workbook(
        entrada
    )

    primeira_aba = workbook[
        ABAS_ENTRADA[0]
    ]

    lotes_adicionados = {
        f"LOTE-OFFLINE-{numero:03d}"
        for numero in range(1, 7)
    }

    for lote_id in sorted(
        lotes_adicionados
    ):
        primeira_aba.append(
            (
                lote_id,
                "Produto Offline",
                "Linha 1",
                "Manhã",
                "APROVADO",
                "Carlos",
                "15/06/2026",
                "Código não localizado na base",
            )
        )

    workbook.save(entrada)
    workbook.close()

    session = Mock()

    session.post.side_effect = (
        requests.ConnectionError(
            "API indisponível"
        )
    )

    ml_client = MLClient(
        base_url="http://api-sabotada:8000",
        limite_falhas=5,
        session=session,
    )

    classificador = ClassificadorDivergencia(
        cliente_ml=ml_client,
        ml_enabled=True,
        confianca_minima=0.75,
    )

    registros = ler_e_validar(
        entrada,
        classificador=classificador,
    )

    resultados_adicionados = [
        resultado
        for resultado in registros
        if resultado.lote in lotes_adicionados
    ]

    assert len(registros) == 10
    assert len(resultados_adicionados) == 6

    assert all(
        resultado.classificacao == "Divergência"
        for resultado in resultados_adicionados
    )

    assert all(
        resultado.regra_aplicada == "RN05"
        for resultado in resultados_adicionados
    )

    assert all(
        resultado.origem_decisao == "fallback"
        for resultado in resultados_adicionados
    )

    assert all(
        resultado.motivo_fallback
        == "servico_indisponivel"
        for resultado in resultados_adicionados
    )

    assert session.post.call_count == 5
    assert ml_client.falhas_consecutivas == 5
    assert ml_client.circuito_aberto is True