"""Testes da auditoria do pipeline híbrido."""

from unittest.mock import Mock

import pandas as pd

from src.auditoria_hibrida import AuditoriaPipelineHibrido
from src.decisao_hibrida import (
    MotivoFallback,
    OrigemDecisao,
    ResultadoDecisaoHibrida,
)
from src.item_processor import processar_item


class ClassificadorControlado:
    """Classificador que retorna uma decisão definida pelo teste."""

    def __init__(
        self,
        decisao: ResultadoDecisaoHibrida,
    ) -> None:
        self.decisao = decisao
        self.chamadas = 0

    def classificar(
        self,
        observacao: str,
    ) -> ResultadoDecisaoHibrida:
        self.chamadas += 1
        return self.decisao


def criar_registro_divergente() -> pd.Series:
    """Cria um lote inexistente na base, acionando a RN05."""

    return pd.Series(
        {
            "lote_id": "LOTE-FORA-DA-BASE",
            "produto": "Produto Teste",
            "linha": "Linha 1",
            "turno": "Manhã",
            "status": "APROVADO",
            "responsavel": "Carlos",
            "data": "15/06/2026",
            "observacao": "Código do lote diferente do cadastro",
        }
    )


def test_divergencia_com_ml_gera_auditoria():
    logger = Mock()

    auditoria = AuditoriaPipelineHibrido(
        execution_id="exec-teste-001",
        logger=logger,
    )

    decisao_ml = ResultadoDecisaoHibrida(
        causa_provavel="erro_codigo",
        origem_decisao=OrigemDecisao.ML,
        confianca_ml=0.92,
        motivo_fallback=None,
        versao_modelo="2.0.0-texto",
    )

    classificador = ClassificadorControlado(decisao_ml)

    resultado = processar_item(
        registro=criar_registro_divergente(),
        data_referencia="15/06/2026",
        lotes_referencia={"LOTE-REFERENCIA"},
        ocorrencia_no_dia=1,
        classificador=classificador,
        auditoria_ml=auditoria,
    )

    assert resultado.classificacao == "Divergência"
    assert resultado.regra_aplicada == "RN05"

    assert classificador.chamadas == 1
    assert len(auditoria.decisoes) == 1

    registro_auditado = auditoria.decisoes[0]

    assert registro_auditado.execution_id == "exec-teste-001"
    assert registro_auditado.lote_id == "LOTE-FORA-DA-BASE"
    assert registro_auditado.causa_provavel == "erro_codigo"
    assert registro_auditado.origem_decisao == "ml"
    assert registro_auditado.confianca_ml == 0.92
    assert registro_auditado.motivo_fallback == ""
    assert registro_auditado.versao_modelo == "2.0.0-texto"
    assert registro_auditado.latencia_ms >= 0

    logger.info.assert_called_once()


def test_fallback_e_auditado_sem_confianca_ficticia():
    auditoria = AuditoriaPipelineHibrido(
        execution_id="exec-teste-002"
    )

    decisao_fallback = ResultadoDecisaoHibrida(
        causa_provavel="nao_classificado",
        origem_decisao=OrigemDecisao.FALLBACK,
        confianca_ml=None,
        motivo_fallback=MotivoFallback.TIMEOUT,
        versao_modelo="",
    )

    classificador = ClassificadorControlado(
        decisao_fallback
    )

    processar_item(
        registro=criar_registro_divergente(),
        data_referencia="15/06/2026",
        lotes_referencia={"LOTE-REFERENCIA"},
        ocorrencia_no_dia=1,
        classificador=classificador,
        auditoria_ml=auditoria,
    )

    registro_auditado = auditoria.decisoes[0]

    assert registro_auditado.origem_decisao == "fallback"
    assert registro_auditado.motivo_fallback == "timeout"
    assert registro_auditado.confianca_ml is None


def test_lotes_repetidos_nao_sao_deduplicados():
    auditoria = AuditoriaPipelineHibrido(
        execution_id="exec-teste-003"
    )

    decisao_ml = ResultadoDecisaoHibrida(
        causa_provavel="erro_codigo",
        origem_decisao=OrigemDecisao.ML,
        confianca_ml=0.90,
        motivo_fallback=None,
        versao_modelo="2.0.0-texto",
    )

    classificador = ClassificadorControlado(decisao_ml)
    registro = criar_registro_divergente()

    for ocorrencia in (1, 2):
        processar_item(
            registro=registro,
            data_referencia="15/06/2026",
            lotes_referencia={"LOTE-REFERENCIA"},
            ocorrencia_no_dia=ocorrencia,
            classificador=classificador,
            auditoria_ml=auditoria,
        )

    assert classificador.chamadas == 2
    assert len(auditoria.decisoes) == 2

    assert [
        decisao.lote_id
        for decisao in auditoria.decisoes
    ] == [
        "LOTE-FORA-DA-BASE",
        "LOTE-FORA-DA-BASE",
    ]