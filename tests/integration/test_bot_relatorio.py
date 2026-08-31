"""Testes de integração do Bot C de relatório e alertas."""

from datetime import datetime
from unittest.mock import Mock
from dataclasses import replace

from src.bots.bot_relatorio import (
    StatusBotRelatorio,
    executar_bot_relatorio,
)
from src.validacao_lotes import RegistroValidado


def criar_registro(origem_decisao: str) -> RegistroValidado:
    return RegistroValidado(
        data_referencia="15/06/2026",
        lote="LOTE-001",
        produto="Produto",
        linha="Linha 1",
        turno="A",
        status="REPROVADO",
        responsavel="Operador",
        data_inspecao="15/06/2026",
        observacao="Peça faltando",
        classificacao="Divergência",
        motivo="Diferença identificada",
        acao_recomendada="Revisar lote",
        origem_decisao=origem_decisao,
        causa_provavel="falha_operacional",
    )


def test_bot_relatorio_gera_uma_vez_e_consolida_origens(
    tmp_path,
):
    saida = tmp_path / "relatorio.xlsx"
    gerador = Mock()
    alertas = Mock()
    registros = [
        criar_registro("ml"),
        criar_registro("fallback"),
        criar_registro("fallback"),
    ]

    resultado = executar_bot_relatorio(
        registros,
        saida,
        execution_id="exec-001",
        correlation_id="corr-001",
        sistema_alertas=alertas,
        gerador_relatorio=gerador,
        momento=datetime(2026, 6, 15, 10, 0),
    )

    assert resultado.sucesso is True
    assert resultado.status is StatusBotRelatorio.CONCLUIDO
    assert resultado.consolidacao.quantidade_ml == 1
    assert resultado.consolidacao.quantidade_fallback == 2
    gerador.assert_called_once()
    alertas.enviar_alerta.assert_called_once()


def test_falha_de_alerta_nao_impede_relatorio_e_encerramento(
    tmp_path,
):
    gerador = Mock()
    alertas = Mock()
    alertas.enviar_alerta.side_effect = RuntimeError(
        "Telegram indisponível"
    )
    logger = Mock()

    resultado = executar_bot_relatorio(
        [criar_registro("fallback")],
        tmp_path / "relatorio.xlsx",
        execution_id="exec-002",
        correlation_id="corr-002",
        sistema_alertas=alertas,
        gerador_relatorio=gerador,
        logger=logger,
    )

    assert resultado.sucesso is True
    assert (
        resultado.status
        is StatusBotRelatorio.CONCLUIDO_SEM_ALERTA
    )
    assert resultado.caminho_relatorio is not None
    assert resultado.alerta_enviado is False
    assert "Telegram indisponível" in resultado.erro_alerta
    gerador.assert_called_once()

    eventos = [
        chamada.kwargs["extra"]["evento"]
        for chamada in logger.info.call_args_list
    ]
    assert eventos == [
        "bot_relatorio_iniciado",
        "cadeia_encerrada",
    ]


def test_bot_relatorio_apenas_repassa_resultados_ao_gerador(
    tmp_path,
):
    registros = [criar_registro("ml")]
    recebidos = []

    def gerador(registros_recebidos, _saida, _momento):
        recebidos.extend(registros_recebidos)

    executar_bot_relatorio(
        registros,
        tmp_path / "relatorio.xlsx",
        execution_id="exec-003",
        correlation_id="corr-003",
        gerador_relatorio=gerador,
    )

    # O mesmo resultado produzido pelo Bot B chega ao relatório sem ser
    # recalculado ou enriquecido novamente pelo Bot C.
    assert recebidos == registros
    assert recebidos[0] is registros[0]


def test_falha_do_relatorio_nao_tenta_notificar(
    tmp_path,
):
    gerador = Mock(side_effect=OSError("disco indisponível"))
    alertas = Mock()

    resultado = executar_bot_relatorio(
        [criar_registro("ml")],
        tmp_path / "relatorio.xlsx",
        execution_id="exec-004",
        correlation_id="corr-004",
        sistema_alertas=alertas,
        gerador_relatorio=gerador,
    )

    assert resultado.sucesso is False
    assert resultado.status is StatusBotRelatorio.ERRO_RELATORIO
    gerador.assert_called_once()
    alertas.enviar_alerta.assert_not_called()

def test_alerta_de_conclusao_possui_resumo_operacional(
    tmp_path,
):
    saida = (
        tmp_path
        / "relatorio_conferencia.xlsx"
    )

    registro_valido = replace(
        criar_registro(""),
        lote="LOTE-VALIDO",
        classificacao="Válido",
        causa_provavel="",
    )

    divergencia_ml = replace(
        criar_registro("ml"),
        lote="LOTE-ML",
        classificacao="Divergência",
    )

    divergencia_fallback = replace(
        criar_registro("fallback"),
        lote="LOTE-FALLBACK",
        classificacao="Divergência",
    )

    erro_entrada = replace(
        criar_registro(""),
        lote="LOTE-ERRO",
        classificacao="Erro de Entrada",
        causa_provavel="",
    )

    registros = [
        registro_valido,
        divergencia_ml,
        divergencia_fallback,
        erro_entrada,
    ]

    gerador = Mock()
    alertas = Mock()

    alertas.enviar_alerta.return_value = Mock(
        sucesso=True,
        erro=None,
    )

    resultado = executar_bot_relatorio(
        registros,
        saida,
        execution_id="exec-resumo-001",
        correlation_id="corr-resumo-001",
        sistema_alertas=alertas,
        gerador_relatorio=gerador,
        momento=datetime(
            2026,
            8,
            27,
            10,
            30,
        ),
    )

    assert resultado.sucesso is True

    alertas.enviar_alerta.assert_called_once()

    chamada = (
        alertas.enviar_alerta
        .call_args
        .kwargs
    )

    mensagem = chamada["mensagem"]

    assert "Status: CONCLUÍDO" in mensagem
    assert "Total de registros: 4" in mensagem
    assert "Válidos: 1" in mensagem
    assert "Divergências: 2" in mensagem
    assert "Ambíguos: 0" in mensagem
    assert "Erros de entrada: 1" in mensagem
    assert "Registros que exigem atenção: 3" in mensagem

    assert "Decisões por ML: 1" in mensagem
    assert "Decisões por fallback: 1" in mensagem
    assert "Sem origem híbrida: 2" in mensagem

    assert "exec-resumo-001" in mensagem
    assert "corr-resumo-001" in mensagem
    assert str(saida.resolve()) in mensagem

    contexto = chamada["contexto"]

    assert contexto["total_registros"] == 4
    assert contexto["total_divergencias"] == 2
    assert contexto["total_erros_entrada"] == 1