"""Testes do executor Maestro do Bot C."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from botcity.maestro import (
    AutomationTaskFinishStatus,
)

from src.bots.bot_relatorio_maestro import (
    executar_tarefa_bot_c,
)


def test_bot_c_baixa_resultado_e_publica_relatorio(
    tmp_path,
):
    maestro = Mock()

    maestro.get_execution.return_value = (
        SimpleNamespace(
            task_id=300,
            parameters={
                "predecessor_task_id": "200",
                "resultado_bot_b_task_id": (
                    "200"
                ),
                "resultado_bot_b_artefato": (
                    "resultado_bot_b_200.json"
                ),
                "execution_id": "exec-001",
                "correlation_id": "corr-001",
            },
        )
    )

    artefato = SimpleNamespace(
        id=50,
        task_id=200,
        name="resultado_bot_b_200.json",
        filename="resultado_bot_b_200.json",
    )

    maestro.list_artifacts.return_value = [
        artefato,
    ]

    maestro.get_artifact.return_value = (
        "resultado_bot_b_200.json",
        b'{"resultado": "teste"}',
    )

    espera_predecessor = Mock()

    registros = (
        SimpleNamespace(),
        SimpleNamespace(),
    )

    resultado_bot_b = SimpleNamespace(
        sucesso=True,
        execution_id="exec-001",
        correlation_id="corr-001",
        registros=registros,
        total_registros=2,
    )

    carregador = Mock(
        return_value=resultado_bot_b,
    )

    caminho_relatorio = (
        tmp_path
        / "relatorio_conferencia_lotes.xlsx"
    )

    def executar_relatorio(
        registros_recebidos,
        caminho_saida,
        **opcoes,
    ):
        Path(caminho_saida).write_bytes(
            b"relatorio"
        )

        return SimpleNamespace(
            sucesso=True,
            mensagem=(
                "Relatório gerado e "
                "cadeia encerrada"
            ),
            caminho_relatorio=str(
                caminho_saida
            ),
        )

    executor_bot_c = Mock(
        side_effect=executar_relatorio,
    )

    sistema_alertas = Mock()

    codigo = executar_tarefa_bot_c(
        maestro=maestro,
        espera_predecessor=(
            espera_predecessor
        ),
        carregador=carregador,
        executor_bot_c=executor_bot_c,
        sistema_alertas=sistema_alertas,
        diretorio_trabalho=tmp_path,
    )

    assert codigo == 0

    espera_predecessor.assert_called_once_with(
        maestro,
        "200",
    )

    maestro.list_artifacts.assert_called_once_with(
        days=7,
    )

    maestro.get_artifact.assert_called_once_with(
        artifact_id=50,
    )

    caminho_resultado = (
        tmp_path
        / "resultado_bot_b_200.json"
    )

    assert caminho_resultado.is_file()

    carregador.assert_called_once_with(
        caminho_resultado,
    )

    executor_bot_c.assert_called_once_with(
        registros,
        caminho_relatorio,
        execution_id="exec-001",
        correlation_id="corr-001",
        sistema_alertas=sistema_alertas,
    )

    maestro.post_artifact.assert_called_once_with(
        task_id="300",
        artifact_name=(
            "relatorio_conferencia_lotes.xlsx"
        ),
        filepath=str(caminho_relatorio),
    )

    maestro.finish_task.assert_called_once_with(
        task_id="300",
        status=(
            AutomationTaskFinishStatus.SUCCESS
        ),
        message=(
            "Bot C concluído. "
            "Relatório publicado."
        ),
        total_items=2,
        processed_items=2,
        failed_items=0,
    )


def test_bot_c_falha_quando_artefato_nao_existe(
    tmp_path,
):
    maestro = Mock()

    maestro.get_execution.return_value = (
        SimpleNamespace(
            task_id=301,
            parameters={
                "predecessor_task_id": "200",
                "resultado_bot_b_task_id": (
                    "200"
                ),
                "resultado_bot_b_artefato": (
                    "resultado_inexistente.json"
                ),
                "execution_id": "exec-002",
                "correlation_id": "corr-002",
            },
        )
    )

    maestro.list_artifacts.return_value = []

    executor_bot_c = Mock()
    carregador = Mock()
    sistema_alertas = Mock()
    espera_predecessor = Mock()

    codigo = executar_tarefa_bot_c(
        maestro=maestro,
        espera_predecessor=(
            espera_predecessor
        ),
        carregador=carregador,
        executor_bot_c=executor_bot_c,
        sistema_alertas=sistema_alertas,
        diretorio_trabalho=tmp_path,
    )

    assert codigo == 1

    carregador.assert_not_called()
    executor_bot_c.assert_not_called()
    maestro.post_artifact.assert_not_called()

    chamada = (
        maestro.finish_task.call_args.kwargs
    )

    assert chamada["task_id"] == "301"

    assert (
        chamada["status"]
        == AutomationTaskFinishStatus.FAILED
    )

    assert "não encontrado" in chamada["message"]