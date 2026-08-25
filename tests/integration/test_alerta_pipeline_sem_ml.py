"""Testes do alerta obrigatório de pipeline sem ML."""

from unittest.mock import Mock

from src.alerta_pipeline_sem_ml import (
    avaliar_e_alertar_pipeline_sem_ml,
)
from src.validacao_lotes import RegistroValidado


def registro(classificacao: str, origem: str = "") -> RegistroValidado:
    return RegistroValidado(
        data_referencia="15/06/2026",
        lote="LOTE-001",
        produto="Produto",
        linha="Linha 1",
        turno="A",
        status="REPROVADO",
        responsavel="Operador",
        data_inspecao="15/06/2026",
        observacao="Observação",
        classificacao=classificacao,
        motivo="Motivo",
        acao_recomendada="Revisar",
        origem_decisao=origem,
    )


def avaliar(registros, alertas):
    return avaliar_e_alertar_pipeline_sem_ml(
        registros,
        alertas,
        execution_id="exec-001",
        correlation_id="corr-001",
    )


def test_cem_por_cento_de_fallback_gera_aviso():
    alertas = Mock()

    resultado = avaliar(
        [
            registro("Divergência", "fallback"),
            registro("Divergência", "fallback"),
            registro("Válido"),
        ],
        alertas,
    )

    assert resultado.total_divergencias == 2
    assert resultado.total_fallback == 2
    assert resultado.proporcao_fallback == 1.0
    assert resultado.alerta_disparado is True
    chamada = alertas.enviar_alerta.call_args.kwargs
    assert chamada["severidade"] == "AVISO"
    assert "100%" in chamada["mensagem"]
    assert chamada["contexto"]["execution_id"] == "exec-001"


def test_uso_parcial_de_ml_nao_gera_aviso_de_pipeline_sem_ml():
    alertas = Mock()

    resultado = avaliar(
        [
            registro("Divergência", "fallback"),
            registro("Divergência", "ml"),
        ],
        alertas,
    )

    assert resultado.proporcao_fallback == 0.5
    assert resultado.alerta_disparado is False
    alertas.enviar_alerta.assert_not_called()


def test_execucao_sem_divergencias_nao_gera_falso_positivo():
    alertas = Mock()

    resultado = avaliar(
        [registro("Válido"), registro("Erro de Entrada")],
        alertas,
    )

    assert resultado.total_divergencias == 0
    assert resultado.proporcao_fallback == 0.0
    assert resultado.alerta_disparado is False
    alertas.enviar_alerta.assert_not_called()


def test_aviso_e_delegado_ao_sistema_com_fallback_de_canal():
    # O sistema simulado representa Telegram indisponível e entrega por email.
    resultado_multicanal = Mock(
        sucesso=True,
        canal="email",
        fallback_utilizado=True,
    )
    alertas = Mock()
    alertas.enviar_alerta.return_value = resultado_multicanal

    resultado = avaliar(
        [registro("Divergência", "fallback")],
        alertas,
    )

    assert resultado.alerta_disparado is True
    assert resultado.resultado_alerta is resultado_multicanal
    assert resultado.resultado_alerta.canal == "email"
    alertas.enviar_alerta.assert_called_once()
