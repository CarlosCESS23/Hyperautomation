"""Testes do executor Maestro do Bot A."""

from types import SimpleNamespace
from unittest.mock import Mock

from botcity.maestro import (
    AutomationTaskFinishStatus,
)

from src.bots.bot_entrada_maestro import (
    executar_tarefa_bot_a,
)


def criar_resultado_bot_a_sucesso():
    return SimpleNamespace(
        sucesso=True,
        mensagem=(
            "Estrutura da planilha validada"
        ),
        status=SimpleNamespace(
            value="pronto_para_conferencia",
        ),
        execution_id="exec-001",
        correlation_id="corr-001",
        parametros_bot_b=SimpleNamespace(
            caminho_entrada=(
                "/tmp/inspecoes.xlsx"
            ),
        ),
    )


def test_bot_a_cria_tarefa_bot_b_e_finaliza_com_sucesso():
    maestro = Mock()

    maestro.get_execution.return_value = (
        SimpleNamespace(
            task_id=100,
            parameters={
                "caminho_entrada": (
                    "/tmp/inspecoes.xlsx"
                ),
            },
        )
    )

    executor_bot_a = Mock(
        return_value=(
            criar_resultado_bot_a_sucesso()
        )
    )

    disparador_bot_b = Mock(
        return_value=SimpleNamespace(
            id=200,
        )
    )

    # Primeiro, executamos o comportamento testado.
    codigo = executar_tarefa_bot_a(
        maestro=maestro,
        executor_bot_a=executor_bot_a,
        disparador_bot_b=disparador_bot_b,
    )

    # Depois, verificamos o resultado e as chamadas.
    assert codigo == 0

    executor_bot_a.assert_called_once_with(
        "/tmp/inspecoes.xlsx",
        execution_id=None,
        correlation_id=None,
    )

    maestro.post_artifact.assert_called_once_with(
        task_id="100",
        artifact_name=(
            "entrada_bot_a_100.xlsx"
        ),
        filepath="/tmp/inspecoes.xlsx",
    )

    disparador_bot_b.assert_called_once_with(
        maestro,
        predecessor_task_id="100",
        resultado_predecessor=(
            "pronto_para_conferencia"
        ),
        execution_id="exec-001",
        correlation_id="corr-001",
        parametros={
            "entrada_task_id": "100",
            "entrada_artefato": (
                "entrada_bot_a_100.xlsx"
            ),
        },
    )

    maestro.finish_task.assert_called_once_with(
        task_id="100",
        status=(
            AutomationTaskFinishStatus.SUCCESS
        ),
        message=(
            "Bot A concluído. "
            "Tarefa do Bot B criada."
        ),
        total_items=1,
        processed_items=1,
        failed_items=0,
    )


def test_bot_a_sem_caminho_finaliza_com_falha(
    monkeypatch,
):
    monkeypatch.delenv(
        "CAMINHO_ENTRADA",
        raising=False,
    )

    maestro = Mock()

    maestro.get_execution.return_value = (
        SimpleNamespace(
            task_id=101,
            parameters={},
        )
    )

    executor_bot_a = Mock()
    disparador_bot_b = Mock()

    codigo = executar_tarefa_bot_a(
        maestro=maestro,
        executor_bot_a=executor_bot_a,
        disparador_bot_b=disparador_bot_b,
    )

    assert codigo == 1

    executor_bot_a.assert_not_called()
    disparador_bot_b.assert_not_called()

    maestro.finish_task.assert_called_once_with(
        task_id="101",
        status=(
            AutomationTaskFinishStatus.FAILED
        ),
        message=(
            "Parâmetro caminho_entrada "
            "não informado"
        ),
        total_items=1,
        processed_items=0,
        failed_items=1,
    )


def test_bot_a_rejeita_entrada_e_nao_cria_bot_b():
    maestro = Mock()

    maestro.get_execution.return_value = (
        SimpleNamespace(
            task_id=102,
            parameters={
                "caminho_entrada": (
                    "/tmp/invalida.xlsx"
                ),
            },
        )
    )

    resultado_falha = SimpleNamespace(
        sucesso=False,
        mensagem="Planilha inválida",
        execution_id="exec-002",
        correlation_id="corr-002",
        parametros_bot_b=None,
    )

    executor_bot_a = Mock(
        return_value=resultado_falha,
    )

    disparador_bot_b = Mock()

    codigo = executar_tarefa_bot_a(
        maestro=maestro,
        executor_bot_a=executor_bot_a,
        disparador_bot_b=disparador_bot_b,
    )

    assert codigo == 1
    disparador_bot_b.assert_not_called()

    maestro.finish_task.assert_called_once_with(
        task_id="102",
        status=(
            AutomationTaskFinishStatus.FAILED
        ),
        message="Planilha inválida",
        total_items=1,
        processed_items=0,
        failed_items=1,
    )

def test_bot_a_utiliza_caminho_do_ambiente(
    monkeypatch,
):
    caminho = "/tmp/inspecoes.xlsx"

    monkeypatch.setenv(
        "CAMINHO_ENTRADA",
        caminho,
    )

    maestro = Mock()

    maestro.get_execution.return_value = (
        SimpleNamespace(
            task_id=103,
            parameters={},
        )
    )

    resultado = criar_resultado_bot_a_sucesso()

    executor_bot_a = Mock(
        return_value=resultado,
    )

    disparador_bot_b = Mock(
        return_value=SimpleNamespace(
            id=200,
        ),
    )

    executar_tarefa_bot_a(
        maestro=maestro,
        executor_bot_a=executor_bot_a,
        disparador_bot_b=disparador_bot_b,
    )

    executor_bot_a.assert_called_once_with(
        caminho,
        execution_id=None,
        correlation_id=None,
    )