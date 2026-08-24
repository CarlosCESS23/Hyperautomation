"""Teste integrado da sabotagem da API de Machine Learning."""

from datetime import datetime
import json
import logging
from unittest.mock import Mock

from openpyxl import load_workbook
import pytest
from pythonjsonlogger import jsonlogger
import requests

import gerar_relatorio
from gerar_relatorio import (
    gerar_excel,
    ler_e_validar,
)
from src.item_processor import ACAO_ML_OFFLINE
from src.ml_client import MLClient
from src.ml_decisions import (
    AuditoriaDecisoesML,
    STATUS_OFFLINE,
)
from tests.integration.test_fluxo_relatorio_excel import (
    ABAS_ENTRADA,
    criar_planilha_controlada,
)


pytestmark = pytest.mark.integration


def test_sabotagem_api_nao_interrompe_processamento(
    tmp_path,
    monkeypatch,
):
    """
    Simula a API completamente indisponível.

    O teste comprova o fallback, o circuit breaker,
    o log de auditoria e o relatório Excel.
    """

    entrada = tmp_path / "entrada_sabotagem.xlsx"
    saida = tmp_path / "relatorio_sabotagem.xlsx"
    arquivo_log = tmp_path / "sabotagem_ml.jsonl"

    criar_planilha_controlada(entrada)

    # A planilha original já possui um registro ambíguo.
    # Adicionamos mais seis para totalizar sete chamadas ao ML.
    workbook = load_workbook(entrada)

    base_referencia = workbook[
        "Base_Referencia"
    ]

    primeira_aba = workbook[
        ABAS_ENTRADA[0]
    ]

    for numero in range(1, 7):
        lote_id = (
            f"LOTE-OFFLINE-{numero:03d}"
        )

        # O lote precisa existir na base para não ser
        # classificado como divergência pela RN05.
        base_referencia.append([
            lote_id
        ])

        primeira_aba.append(
            (
                lote_id,
                f"Produto Offline {numero}",
                "Linha 1",
                "Manhã",
                "EM ANÁLISE",
                "Carlos",
                "15/06/2026",
                "",
            )
        )

    workbook.save(entrada)
    workbook.close()

    # Session simulada que sempre apresenta erro de conexão.
    session = Mock()

    session.post.side_effect = requests.ConnectionError(
        "API ML indisponível durante a sabotagem"
    )

    ml_client = MLClient(
        base_url="http://api-ml-sabotada:8000",
        limite_falhas=5,
        session=session,
    )

    # ler_e_validar() cria um MLClient internamente.
    # O monkeypatch faz a função utilizar o cliente controlado.
    monkeypatch.setattr(
        gerar_relatorio,
        "MLClient",
        lambda: ml_client,
    )

    # Configura um arquivo de log JSON real.
    logger = logging.getLogger(
        f"teste.sabotagem.{id(tmp_path)}"
    )

    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.FileHandler(
        arquivo_log,
        encoding="utf-8",
    )

    handler.setFormatter(
        jsonlogger.JsonFormatter()
    )

    logger.addHandler(handler)

    auditoria = AuditoriaDecisoesML(
        logger=logger,
    )

    registros = ler_e_validar(
        entrada,
        auditoria_ml=auditoria,
    )

    gerar_excel(
        registros=registros,
        saida=saida,
        momento=datetime(
            2026,
            8,
            24,
            12,
        ),
        decisoes_ml=auditoria.decisoes,
    )

    handler.close()
    logger.removeHandler(handler)

    # A entrada possui quatro registros originais
    # e seis registros adicionados pelo teste.
    assert len(registros) == 10

    registros_offline = [
        registro
        for registro in registros
        if (
            registro.acao_recomendada
            == ACAO_ML_OFFLINE
        )
    ]

    # Um ambíguo original + seis adicionados.
    assert len(registros_offline) == 7

    assert all(
        "API ML indisponível"
        in registro.motivo
        for registro in registros_offline
    )

    # O cliente tenta acessar a rede somente cinco vezes.
    assert session.post.call_count == 5

    assert ml_client.falhas_consecutivas == 5
    assert ml_client.circuito_aberto is True

    # Mesmo com apenas cinco tentativas de rede,
    # todas as sete chamadas são auditadas.
    assert len(auditoria.decisoes) == 7

    assert all(
        decisao.status_chamada
        == STATUS_OFFLINE
        for decisao in auditoria.decisoes
    )

    assert all(
        decisao.classe_prevista is None
        for decisao in auditoria.decisoes
    )

    assert all(
        decisao.probabilidade is None
        for decisao in auditoria.decisoes
    )

    # Verifica o arquivo JSON de auditoria.
    eventos = [
        json.loads(linha)
        for linha in arquivo_log
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert len(eventos) == 7

    assert all(
        evento["evento"] == "decisao_ml"
        for evento in eventos
    )

    assert all(
        evento["status_chamada"]
        == STATUS_OFFLINE
        for evento in eventos
    )

    assert all(
        evento["detalhe_erro"]
        == "API ML indisponível"
        for evento in eventos
    )

    # Verifica a aba do relatório.
    relatorio = load_workbook(
        saida,
        data_only=True,
    )

    assert "Decisões de ML" in relatorio.sheetnames

    aba_ml = relatorio[
        "Decisões de ML"
    ]

    # Uma linha de cabeçalho e sete decisões.
    assert aba_ml.max_row - 1 == 7

    lotes_auditados = [
        aba_ml.cell(linha, 1).value
        for linha in range(
            2,
            aba_ml.max_row + 1,
        )
    ]

    assert len(lotes_auditados) == 7
    assert "LOTE-AMBIGUO" in lotes_auditados
    assert "LOTE-OFFLINE-001" in lotes_auditados
    assert "LOTE-OFFLINE-006" in lotes_auditados

    # Sem predição, o relatório deve informar indisponibilidade.
    classes_registradas = [
        aba_ml.cell(linha, 2).value
        for linha in range(
            2,
            aba_ml.max_row + 1,
        )
    ]

    assert all(
        classe == "NÃO DISPONÍVEL"
        for classe in classes_registradas
    )

    relatorio.close()