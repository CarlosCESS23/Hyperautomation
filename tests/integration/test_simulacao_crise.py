"""Testes reproduzíveis dos cinco cenários de crise da apresentação.

Nenhum teste acessa serviços reais. API ML, Telegram, Email, base de
referência e espera de retry são substituídos por objetos controlados.
"""

import logging
from unittest.mock import Mock

import pandas as pd
import pytest

from gerar_relatorio import ler_e_validar
from src.auditoria_hibrida import AuditoriaPipelineHibrido
from src.base_referencia import ConfiguracaoRetryBase
from src.classificador_divergencia import ClassificadorDivergencia
from src.decisao_hibrida import MotivoFallback, OrigemDecisao
from src.item_processor import processar_item
from src.ml_client import (
    MLServiceUnavailableError,
    MLTimeoutError,
)

"""Simulação reproduzível dos cinco cenários da apresentação."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import requests

from src.alerta_pipeline_sem_ml import (
    avaliar_e_alertar_pipeline_sem_ml,
)
from src.base_referencia import (
    ConfiguracaoRetryBase,
    StatusBaseReferencia,
    consultar_base_com_retry,
)
from src.classificador_divergencia import ClassificadorDivergencia
from src.decisao_hibrida import MotivoFallback, OrigemDecisao
from src.ml_client import MLClient

from src.sistema_alertas import (
    Alerta,
    ResultadoAlerta,
    Severidade,
    SistemaAlertas,
)
from src.validacao_lotes import RegistroValidado


OBSERVACOES = (
    "Código digitado incorretamente",
    "Faltou peça na doca três",
    "Lançamento duplicado pelo operador",
)


class CanalSimulado:
    def __init__(self, nome: str, sucesso: bool, erro: str | None = None):
        self.nome = nome
        self.sucesso = sucesso
        self.erro = erro
        self.alertas: list[Alerta] = []

    def enviar(self, alerta: Alerta) -> ResultadoAlerta:
        self.alertas.append(alerta)
        return ResultadoAlerta(
            sucesso=self.sucesso,
            canal=self.nome,
            erro=self.erro,
        )


def salvar_evidencia(
    diretorio: Path,
    cenario: str,
    **dados,
) -> Path:
    """Cria artefato que pode ser anexado à evidência da apresentação."""

    caminho = diretorio / f"evidencia_{cenario}.json"
    caminho.write_text(
        json.dumps(
            {"cenario": cenario, **dados},
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return caminho


def eventos_do_logger(logger: Mock) -> list[str]:
    eventos = []
    for metodo in (
        logger.info,
        logger.warning,
        logger.error,
        logger.critical,
    ):
        eventos.extend(
            chamada.kwargs["extra"]["evento"]
            for chamada in metodo.call_args_list
        )
    return eventos


def classificar_lote(classificador: ClassificadorDivergencia):
    return [
        classificador.classificar(observacao)
        for observacao in OBSERVACOES
    ]


def registro_divergencia(indice, decisao) -> RegistroValidado:
    return RegistroValidado(
        data_referencia="15/06/2026",
        lote=f"LOTE-{indice:03d}",
        produto="Produto",
        linha="Linha 1",
        turno="Manhã",
        status="REPROVADO",
        responsavel="Operador",
        data_inspecao="15/06/2026",
        observacao=OBSERVACOES[indice - 1],
        classificacao="Divergência",
        motivo="Lote não encontrado na referência",
        acao_recomendada="Revisar",
        causa_provavel=decisao.causa_provavel,
        confianca_ml=decisao.confianca_ml,
        origem_decisao=decisao.origem_decisao.value,
        motivo_fallback=(
            decisao.motivo_fallback.value
            if decisao.motivo_fallback is not None
            else ""
        ),
        versao_modelo=decisao.versao_modelo,
    )


def comprovar_aviso_sem_ml(decisoes):
    alertas = Mock()
    registros = [
        registro_divergencia(indice, decisao)
        for indice, decisao in enumerate(decisoes, start=1)
    ]
    avaliacao = avaliar_e_alertar_pipeline_sem_ml(
        registros,
        alertas,
        execution_id="exec-crise",
        correlation_id="corr-crise",
    )
    return avaliacao, alertas


def test_cenario_1_base_referencia_instavel_recupera_e_continua(
    tmp_path,
):
    consulta = Mock(
        side_effect=[
            ConnectionError("rede instável"),
            {"LOTE-001", "LOTE-002", "LOTE-003"},
        ]
    )
    logger = Mock()
    resultado = consultar_base_com_retry(
        consulta,
        configuracao=ConfiguracaoRetryBase(
            max_tentativas=3,
            backoff_seconds=0,
        ),
        sleeper=Mock(),
        logger=logger,
    )

    # A falha temporária é recuperada e o lote inteiro permanece disponível.
    assert resultado.status is StatusBaseReferencia.DISPONIVEL
    assert resultado.tentativas == 2
    assert len(resultado.lotes) == 3
    eventos = eventos_do_logger(logger)
    assert "base_referencia_retry_agendado" in eventos
    assert "base_referencia_consulta_sucesso" in eventos
    evidencia = salvar_evidencia(
        tmp_path,
        "base_instavel",
        lote_concluido=True,
        tentativas=resultado.tentativas,
        eventos=eventos,
    )
    assert evidencia.is_file()


def test_cenario_2_servico_ml_fora_do_ar_usa_fallback_e_avisa(
    tmp_path,
):
    session = Mock()
    session.post.side_effect = requests.ConnectionError("ML offline")
    classificador = ClassificadorDivergencia(
        MLClient(session=session, limite_falhas=10),
        ml_enabled=True,
        confianca_minima=0.75,
    )

    decisoes = classificar_lote(classificador)
    avaliacao, alertas = comprovar_aviso_sem_ml(decisoes)

    assert len(decisoes) == len(OBSERVACOES)
    assert all(
        decisao.motivo_fallback
        is MotivoFallback.SERVICO_INDISPONIVEL
        for decisao in decisoes
    )
    assert avaliacao.alerta_disparado is True
    assert alertas.enviar_alerta.call_args.kwargs["severidade"] == "AVISO"
    evidencia = salvar_evidencia(
        tmp_path,
        "ml_fora_ar",
        lote_concluido=True,
        fallbacks=[d.motivo_fallback.value for d in decisoes],
        alerta="AVISO",
    )
    assert "servico_indisponivel" in evidencia.read_text(encoding="utf-8")


def test_cenario_3_ml_acima_timeout_usa_fallback_e_avisa(tmp_path):
    session = Mock()
    session.post.side_effect = requests.Timeout("resposta acima do limite")
    cliente = MLClient(session=session, timeout=0.01, limite_falhas=10)
    classificador = ClassificadorDivergencia(
        cliente,
        ml_enabled=True,
        confianca_minima=0.75,
    )

    decisoes = classificar_lote(classificador)
    avaliacao, _ = comprovar_aviso_sem_ml(decisoes)

    assert len(decisoes) == len(OBSERVACOES)
    assert all(
        decisao.motivo_fallback is MotivoFallback.TIMEOUT
        for decisao in decisoes
    )
    assert all(
        chamada.kwargs["timeout"] == 0.01
        for chamada in session.post.call_args_list
    )
    assert avaliacao.alerta_disparado is True
    evidencia = salvar_evidencia(
        tmp_path,
        "ml_timeout",
        lote_concluido=True,
        fallback="timeout",
        timeout_seconds=cliente.timeout,
        alerta="AVISO",
    )
    assert evidencia.is_file()


def test_cenario_4_ml_baixa_confianca_descarta_resposta_e_avisa(
    tmp_path,
):
    cliente = Mock()
    cliente.classificar_observacao.return_value = {
        "causa_provavel": "erro_codigo",
        "confianca_ml": 0.40,
        "versao_modelo": "crise-v1",
    }
    classificador = ClassificadorDivergencia(
        cliente,
        ml_enabled=True,
        confianca_minima=0.75,
    )

    decisoes = classificar_lote(classificador)
    avaliacao, _ = comprovar_aviso_sem_ml(decisoes)

    assert len(decisoes) == len(OBSERVACOES)
    assert all(
        decisao.origem_decisao is OrigemDecisao.FALLBACK
        and decisao.motivo_fallback is MotivoFallback.BAIXA_CONFIANCA
        and decisao.confianca_ml is None
        for decisao in decisoes
    )
    assert avaliacao.alerta_disparado is True
    evidencia = salvar_evidencia(
        tmp_path,
        "ml_baixa_confianca",
        lote_concluido=True,
        confianca_recebida=0.40,
        limiar=0.75,
        fallback="baixa_confianca",
        alerta="AVISO",
    )
    assert evidencia.is_file()


def test_cenario_5_telegram_indisponivel_entrega_por_email_e_continua(
    tmp_path,
):
    telegram = CanalSimulado(
        "telegram",
        sucesso=False,
        erro="canal_indisponivel",
    )
    email = CanalSimulado("email", sucesso=True)
    logger = Mock()
    sistema = SistemaAlertas(telegram, email, logger=logger)

    resultado = sistema.enviar(
        Alerta(
            Severidade.CRITICO,
            "Infraestrutura degradada durante a simulação",
            contexto={
                "execution_id": "exec-crise",
                "correlation_id": "corr-crise",
            },
        )
    )

    assert resultado.sucesso is True
    assert resultado.canal == "email"
    assert resultado.fallback_acionado is True
    assert len(telegram.alertas) == 1
    assert len(email.alertas) == 1
    evidencia = salvar_evidencia(
        tmp_path,
        "telegram_indisponivel",
        lote_concluido=True,
        alerta_entregue=resultado.sucesso,
        canal=resultado.canal,
        fallback_canal=resultado.fallback_acionado,
        tentativas=[t.to_dict() for t in resultado.tentativas],
        eventos=eventos_do_logger(logger),
    )
    assert json.loads(evidencia.read_text(encoding="utf-8"))[
        "canal"
    ] == "email"
