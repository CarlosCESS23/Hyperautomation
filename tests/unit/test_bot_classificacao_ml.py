"""Testes unitários do Bot E de classificação híbrida."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from src.bots.bot_classificacao_ml import (
    ConfiguracaoClassificacaoML,
    criar_observacao_ml,
    executar_bot_classificacao_ml,
)
from src.contratos_capstone import (
    ArtefatoClassificacaoML,
    ArtefatoConsolidacao,
    EnvelopeAuditoria,
    EstadoExecucao,
    FonteDados,
    RegistroConsolidado,
)
from src.decisao_hibrida import (
    MotivoFallback,
    ResultadoDecisaoHibrida,
)


EXECUTION_ID = "exec-ml-001"
CORRELATION_ID = "corr-ml-001"
TASK_ID_D = "task-consolidacao-400"
TASK_ID_E = "task-classificacao-500"


def criar_registro_consolidado(
    *,
    lote_id: str = "LOTE-001",
) -> RegistroConsolidado:
    """Cria um registro válido produzido pelo Bot D."""

    return RegistroConsolidado(
        lote_id=lote_id,
        produto="Sensor de temperatura",
        quantidade_estoque=5,
        quantidade_pedida=8,
        status_estoque="ESTOQUE_BAIXO",
        status_pedido="PENDENTE",
        classificacao_deterministica=(
            "ESTOQUE_INSUFICIENTE"
        ),
        motivo=(
            "A quantidade disponível é menor "
            "que a quantidade pedida."
        ),
        regras_aplicadas=(
            "RD04",
        ),
        fontes_disponiveis=(
            FonteDados.DESKTOP,
            FonteDados.WEB,
        ),
        modo_degradado=False,
    )


def criar_artefato_consolidacao(
    caminho: Path,
    *,
    estado: EstadoExecucao = (
        EstadoExecucao.CONCLUIDO
    ),
    execution_id: str = EXECUTION_ID,
    correlation_id: str = CORRELATION_ID,
) -> Path:
    """Cria o arquivo que seria produzido pelo Bot D."""

    artefato = ArtefatoConsolidacao(
        auditoria=EnvelopeAuditoria(
            execution_id=execution_id,
            correlation_id=correlation_id,
            bot_id="bot-d-consolidacao",
            task_id=TASK_ID_D,
            estado=estado,
            predecessor=(
                "bot-b-coleta-desktop"
                "+bot-c-coleta-web"
            ),
            predecessor_task_id=(
                "task-desktop-200,"
                "task-web-300"
            ),
            resultado_predecessor=(
                "fontes_avaliadas"
            ),
        ),
        registros=(
            criar_registro_consolidado(),
        ),
    )

    caminho.write_text(
        artefato.para_json(),
        encoding="utf-8",
    )

    return caminho


def executar_bot_e(
    *,
    tmp_path: Path,
    caminho_entrada: Path,
    classificador: Mock,
):
    """Executa o Bot E usando caminhos temporários."""

    caminho_saida = (
        tmp_path
        / "registros_classificados.json"
    )

    resultado = executar_bot_classificacao_ml(
        caminho_consolidacao=(
            caminho_entrada
        ),
        execution_id=EXECUTION_ID,
        correlation_id=CORRELATION_ID,
        task_id=TASK_ID_E,
        predecessor_task_id=TASK_ID_D,
        configuracao=(
            ConfiguracaoClassificacaoML(
                caminho_artefato=(
                    caminho_saida
                )
            )
        ),
        classificador=classificador,
    )

    return resultado, caminho_saida


def ler_resultado(
    caminho: Path,
) -> ArtefatoClassificacaoML:
    """Lê o JSON produzido pelo Bot E."""

    return ArtefatoClassificacaoML.de_json(
        caminho.read_text(
            encoding="utf-8"
        )
    )


def test_observacao_ml_possui_dados_do_registro():
    """O texto enviado ao ML deve explicar a divergência."""

    registro = criar_registro_consolidado()

    observacao = criar_observacao_ml(
        registro
    )

    assert "LOTE-001" in observacao
    assert (
        "Sensor de temperatura"
        in observacao
    )
    assert (
        "ESTOQUE_INSUFICIENTE"
        in observacao
    )
    assert (
        "quantidade em estoque 5"
        in observacao
    )
    assert (
        "quantidade pedida 8"
        in observacao
    )
    assert (
        "status do estoque ESTOQUE_BAIXO"
        in observacao
    )
    assert (
        "status do pedido PENDENTE"
        in observacao
    )


def test_bot_e_salva_decisao_do_ml(
    tmp_path,
):
    """Uma resposta confiável do ML deve ser preservada."""

    entrada = criar_artefato_consolidacao(
        tmp_path / "consolidacao.json"
    )

    classificador = Mock()

    classificador.classificar.return_value = (
        ResultadoDecisaoHibrida.de_ml(
            causa_provavel=(
                "falha_de_planejamento"
            ),
            confianca_ml=0.91,
            versao_modelo="capstone-1.0",
        )
    )

    resultado, saida = executar_bot_e(
        tmp_path=tmp_path,
        caminho_entrada=entrada,
        classificador=classificador,
    )

    assert resultado.sucesso is True
    assert (
        resultado.estado
        == EstadoExecucao.CONCLUIDO
    )
    assert resultado.total_registros == 1
    assert resultado.total_ml == 1
    assert resultado.total_fallback == 0
    assert saida.is_file()

    artefato = ler_resultado(saida)

    assert (
        artefato.auditoria.execution_id
        == EXECUTION_ID
    )
    assert (
        artefato.auditoria.correlation_id
        == CORRELATION_ID
    )
    assert (
        artefato.auditoria.task_id
        == TASK_ID_E
    )

    registro = artefato.registros[0]

    assert (
        registro.origem_decisao
        == "ml"
    )
    assert (
        registro.causa_provavel
        == "falha_de_planejamento"
    )
    assert registro.confianca_ml == 0.91
    assert (
        registro.versao_modelo
        == "capstone-1.0"
    )
    assert registro.motivo_fallback is None

    # A sugestão do ML não modifica
    # a classificação das regras.
    assert (
        registro.classificacao_final
        == "ESTOQUE_INSUFICIENTE"
    )

    classificador.classificar.assert_called_once()


def test_bot_e_usa_fallback_no_timeout(
    tmp_path,
):
    """Timeout do ML não deve interromper o lote."""

    entrada = criar_artefato_consolidacao(
        tmp_path / "consolidacao.json"
    )

    classificador = Mock()

    classificador.classificar.return_value = (
        ResultadoDecisaoHibrida.de_fallback(
            motivo=MotivoFallback.TIMEOUT,
        )
    )

    resultado, saida = executar_bot_e(
        tmp_path=tmp_path,
        caminho_entrada=entrada,
        classificador=classificador,
    )

    assert resultado.sucesso is True
    assert (
        resultado.estado
        == EstadoExecucao.CONCLUIDO_DEGRADADO
    )
    assert resultado.total_ml == 0
    assert resultado.total_fallback == 1

    artefato = ler_resultado(saida)

    registro = artefato.registros[0]

    assert (
        registro.origem_decisao
        == "fallback"
    )
    assert (
        registro.causa_provavel
        == "nao_classificado"
    )
    assert (
        registro.motivo_fallback
        == "timeout"
    )
    assert registro.confianca_ml is None

    assert (
        registro.classificacao_final
        == "ESTOQUE_INSUFICIENTE"
    )


def test_bot_e_preserva_modo_degradado_do_bot_d(
    tmp_path,
):
    """Uma consolidação degradada continua degradada."""

    entrada = criar_artefato_consolidacao(
        tmp_path / "consolidacao.json",
        estado=(
            EstadoExecucao
            .CONCLUIDO_DEGRADADO
        ),
    )

    classificador = Mock()

    classificador.classificar.return_value = (
        ResultadoDecisaoHibrida.de_ml(
            causa_provavel=(
                "falha_de_planejamento"
            ),
            confianca_ml=0.93,
            versao_modelo="capstone-1.0",
        )
    )

    resultado, saida = executar_bot_e(
        tmp_path=tmp_path,
        caminho_entrada=entrada,
        classificador=classificador,
    )

    assert resultado.sucesso is True
    assert (
        resultado.estado
        == EstadoExecucao.CONCLUIDO_DEGRADADO
    )
    assert resultado.total_ml == 1
    assert resultado.total_fallback == 0

    artefato = ler_resultado(saida)

    assert (
        artefato.auditoria.estado
        == EstadoExecucao.CONCLUIDO_DEGRADADO
    )


def test_excecao_do_classificador_vira_fallback(
    tmp_path,
):
    """Uma exceção inesperada não pode interromper o Bot E."""

    entrada = criar_artefato_consolidacao(
        tmp_path / "consolidacao.json"
    )

    classificador = Mock()

    classificador.classificar.side_effect = (
        RuntimeError(
            "API ML interrompeu a conexão"
        )
    )

    resultado, saida = executar_bot_e(
        tmp_path=tmp_path,
        caminho_entrada=entrada,
        classificador=classificador,
    )

    assert resultado.sucesso is True
    assert (
        resultado.estado
        == EstadoExecucao.CONCLUIDO_DEGRADADO
    )
    assert resultado.total_ml == 0
    assert resultado.total_fallback == 1

    artefato = ler_resultado(saida)

    registro = artefato.registros[0]

    assert (
        registro.origem_decisao
        == "fallback"
    )
    assert (
        registro.motivo_fallback
        == "servico_indisponivel"
    )
    assert (
        registro.causa_provavel
        == "nao_classificado"
    )


def test_bot_e_rejeita_correlation_id_de_outra_execucao(
    tmp_path,
):
    """Um artefato de outra cadeia não pode ser classificado."""

    entrada = criar_artefato_consolidacao(
        tmp_path / "consolidacao_invalida.json",
        correlation_id="corr-outra-execucao",
    )

    classificador = Mock()

    resultado, saida = executar_bot_e(
        tmp_path=tmp_path,
        caminho_entrada=entrada,
        classificador=classificador,
    )

    assert resultado.sucesso is False
    assert (
        resultado.estado
        == EstadoExecucao.FALHOU
    )
    assert resultado.total_registros == 0
    assert resultado.total_ml == 0
    assert resultado.total_fallback == 0
    assert resultado.erro is not None
    assert "correlation_id" in resultado.erro

    classificador.classificar.assert_not_called()

    artefato = ler_resultado(saida)

    assert (
        artefato.auditoria.estado
        == EstadoExecucao.FALHOU
    )
    assert artefato.registros == ()