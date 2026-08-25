"""Integração do retry da infraestrutura crítica de referência."""

from unittest.mock import Mock

from gerar_relatorio import ler_e_validar
from src.base_referencia import (
    ConfiguracaoRetryBase,
    StatusBaseReferencia,
    consultar_base_com_retry,
)


def test_falha_temporaria_e_recuperada_com_backoff_linear():
    consulta = Mock(
        side_effect=[
            ConnectionError("rede instável"),
            TimeoutError("base lenta"),
            {"LOTE-001", "LOTE-002"},
        ]
    )
    sleeper = Mock()

    resultado = consultar_base_com_retry(
        consulta,
        configuracao=ConfiguracaoRetryBase(
            max_tentativas=4,
            backoff_seconds=2,
        ),
        sleeper=sleeper,
    )

    assert resultado.sucesso is True
    assert resultado.status is StatusBaseReferencia.DISPONIVEL
    assert resultado.tentativas == 3
    assert resultado.lotes == {"LOTE-001", "LOTE-002"}
    assert consulta.call_count == 3
    assert [chamada.args[0] for chamada in sleeper.call_args_list] == [
        2,
        4,
    ]


def test_falha_persistente_retorna_pendente_revisao_sem_travar():
    consulta = Mock(side_effect=OSError("base indisponível"))
    sleeper = Mock()
    logger = Mock()

    resultado = consultar_base_com_retry(
        consulta,
        configuracao=ConfiguracaoRetryBase(
            max_tentativas=3,
            backoff_seconds=1,
        ),
        sleeper=sleeper,
        logger=logger,
    )

    assert resultado.sucesso is False
    assert (
        resultado.status
        is StatusBaseReferencia.PENDENTE_REVISAO
    )
    assert resultado.tentativas == 3
    assert resultado.lotes == frozenset()
    assert "base indisponível" in resultado.erro
    assert consulta.call_count == 3
    assert [chamada.args[0] for chamada in sleeper.call_args_list] == [
        1,
        2,
    ]

    evento = logger.error.call_args.kwargs["extra"]
    assert evento["evento"] == "infraestrutura_degradada"
    assert evento["componente"] == "base_referencia"
    assert evento["tentativas"] == 3
    assert evento["status_fallback"] == "PENDENTE_REVISAO"


def test_tentativas_e_fallback_sao_registrados_no_log():
    logger = Mock()

    consultar_base_com_retry(
        Mock(side_effect=ConnectionError("sem conexão")),
        configuracao=ConfiguracaoRetryBase(
            max_tentativas=2,
            backoff_seconds=0,
        ),
        sleeper=Mock(),
        logger=logger,
    )

    tentativas = [
        chamada.kwargs["extra"]["tentativa"]
        for chamada in logger.warning.call_args_list
    ]
    assert tentativas == [1, 2]
    assert logger.error.call_args.kwargs["extra"][
        "status_fallback"
    ] == "PENDENTE_REVISAO"


def test_configuracao_de_tentativas_pode_vir_do_ambiente(
    monkeypatch,
):
    monkeypatch.setenv("BASE_REFERENCIA_MAX_TENTATIVAS", "5")
    monkeypatch.setenv("BASE_REFERENCIA_BACKOFF_SECONDS", "0.25")

    configuracao = ConfiguracaoRetryBase.de_ambiente()

    assert configuracao.max_tentativas == 5
    assert configuracao.backoff_seconds == 0.25


def test_resultado_de_infraestrutura_nao_usa_fallback_de_ml():
    resultado = consultar_base_com_retry(
        Mock(side_effect=OSError("indisponível")),
        configuracao=ConfiguracaoRetryBase(
            max_tentativas=1,
            backoff_seconds=0,
        ),
        sleeper=Mock(),
    )

    assert resultado.status.value == "PENDENTE_REVISAO"
    assert not hasattr(resultado, "origem_decisao")
    assert not hasattr(resultado, "motivo_fallback")


def test_pipeline_marca_lote_pendente_sem_consultar_ml(
    planilha_controlada_factory,
):
    entrada = planilha_controlada_factory()
    consulta = Mock(side_effect=ConnectionError("base fora do ar"))
    classificador = Mock()

    registros = ler_e_validar(
        entrada,
        classificador=classificador,
        consulta_base_referencia=consulta,
        configuracao_retry_base=ConfiguracaoRetryBase(
            max_tentativas=2,
            backoff_seconds=0,
        ),
        sleeper_base=Mock(),
    )

    assert len(registros) == 20
    assert {
        registro.status for registro in registros
    } == {"PENDENTE_REVISAO"}
    assert {
        registro.classificacao for registro in registros
    } == {"PENDENTE_REVISAO"}
    assert all(registro.origem_decisao == "" for registro in registros)
    classificador.classificar.assert_not_called()
