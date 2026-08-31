"""Integração contratual da cadeia com o SDK do Maestro."""

from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from src.orchestrator import (
    BOTS_REGISTRADOS,
    BOT_A_ENTRADA,
    BOT_B_CONFERENCIA,
    BOT_C_RELATORIO,
    disparar_bot_b,
    disparar_bot_c,
)
from src.wait_for_predecessor import (
    DependenciaFalhouError,
    TimeoutDependenciaError,
    wait_for_predecessor,
)


def test_cadeia_preserva_task_id_do_predecessor():
    maestro = Mock()

    tarefa_b = SimpleNamespace(
        id=200,
    )

    tarefa_c = SimpleNamespace(
        id=300,
    )

    maestro.create_task.side_effect = [
        tarefa_b,
        tarefa_c,
    ]

    criada_b = disparar_bot_b(
        maestro,
        predecessor_task_id="100",
        resultado_predecessor=(
            "pronto_para_conferencia"
        ),
        execution_id="exec-cadeia-001",
        correlation_id="corr-cadeia-001",
        parametros={
            "caminho_entrada": (
                "/tmp/inspecoes.xlsx"
            ),
        },
    )

    criada_c = disparar_bot_c(
        maestro,
        predecessor_task_id=str(criada_b.id),
        resultado_predecessor=(
            "conferencia_concluida"
        ),
        execution_id="exec-cadeia-001",
        correlation_id="corr-cadeia-001",
        parametros={
            "resultado_bot_b": (
                "/tmp/resultado_bot_b.json"
            ),
        },
    )

    assert criada_b.id == 200
    assert criada_c.id == 300

    chamadas = maestro.create_task.call_args_list

    parametros_bot_b = (
        chamadas[0].kwargs["parameters"]
    )

    parametros_bot_c = (
        chamadas[1].kwargs["parameters"]
    )

    assert (
        parametros_bot_b["predecessor_task_id"]
        == "100"
    )

    assert (
        parametros_bot_c["predecessor_task_id"]
        == "200"
    )

    assert (
        parametros_bot_b["execution_id"]
        == parametros_bot_c["execution_id"]
        == "exec-cadeia-001"
    )

    assert (
        parametros_bot_b["correlation_id"]
        == parametros_bot_c["correlation_id"]
        == "corr-cadeia-001"
    )


def test_tres_bots_possuem_nomenclatura_de_registro():
    nomes = [
        bot.activity_label
        for bot in BOTS_REGISTRADOS
    ]

    assert nomes == [
        "gustavo_nunes-entrada-v1",
        "gustavo_nunes-conferencia-v1",
        "gustavo_nunes-relatorio-v1",
    ]

    assert len(set(nomes)) == 3


def test_bot_a_dispara_bot_b_com_rastreabilidade_completa():
    maestro = Mock()

    tarefa = SimpleNamespace(
        task_id="task-b-001",
    )

    maestro.create_task.return_value = tarefa

    criada = disparar_bot_b(
        maestro,
        predecessor_task_id="task-a-001",
        resultado_predecessor=(
            "pronto_para_conferencia"
        ),
        execution_id="exec-001",
        correlation_id="corr-001",
        parametros={
            "caminho_entrada": "/tmp/lote.xlsx",
        },
    )

    assert criada is tarefa

    maestro.create_task.assert_called_once_with(
        activity_label=BOT_B_CONFERENCIA,
        parameters={
            "caminho_entrada": "/tmp/lote.xlsx",
            "predecessor": BOT_A_ENTRADA,
            "predecessor_task_id": (
                "task-a-001"
            ),
            "resultado_predecessor": (
                "pronto_para_conferencia"
            ),
            "execution_id": "exec-001",
            "correlation_id": "corr-001",
        },
        test=False,
        priority=0,
    )


def test_bot_b_dispara_bot_c_com_rastreabilidade_completa():
    maestro = Mock()

    tarefa = SimpleNamespace(
        task_id="task-c-001",
    )

    maestro.create_task.return_value = tarefa

    criada = disparar_bot_c(
        maestro,
        predecessor_task_id="task-b-001",
        resultado_predecessor=(
            "conferencia_concluida"
        ),
        execution_id="exec-002",
        correlation_id="corr-002",
        parametros={
            "resultado_bot_b": (
                "resultados/lote.json"
            ),
        },
    )

    assert criada is tarefa

    maestro.create_task.assert_called_once_with(
        activity_label=BOT_C_RELATORIO,
        parameters={
            "resultado_bot_b": (
                "resultados/lote.json"
            ),
            "predecessor": BOT_B_CONFERENCIA,
            "predecessor_task_id": (
                "task-b-001"
            ),
            "resultado_predecessor": (
                "conferencia_concluida"
            ),
            "execution_id": "exec-002",
            "correlation_id": "corr-002",
        },
        test=False,
        priority=0,
    )


def test_espera_termina_quando_predecessor_conclui():
    maestro = Mock()

    pendente = SimpleNamespace(
        status="RUNNING",
    )

    concluida = SimpleNamespace(
        status="FINISHED",
    )

    maestro.get_task.side_effect = [
        pendente,
        concluida,
    ]

    tempos = iter(
        (
            0.0,
            0.0,
        )
    )

    resultado = wait_for_predecessor(
        maestro,
        "task-a-001",
        timeout_seconds=10,
        poll_interval_seconds=1,
        clock=lambda: next(tempos),
        sleeper=Mock(),
    )

    assert resultado is concluida

    assert maestro.get_task.call_args_list == [
        call("task-a-001"),
        call("task-a-001"),
    ]


def test_timeout_nao_deixa_dependencia_bloqueada():
    maestro = Mock()

    maestro.get_task.return_value = (
        SimpleNamespace(
            status="RUNNING",
        )
    )

    tempos = iter(
        (
            0.0,
            0.0,
            5.0,
        )
    )

    with pytest.raises(
        TimeoutDependenciaError,
    ):
        wait_for_predecessor(
            maestro,
            "task-b-002",
            timeout_seconds=5,
            poll_interval_seconds=5,
            clock=lambda: next(tempos),
            sleeper=Mock(),
        )

    assert maestro.get_task.call_count == 2


def test_falha_controlada_do_predecessor_e_detectada():
    maestro = Mock()

    maestro.get_task.return_value = (
        SimpleNamespace(
            status="FAILED",
        )
    )

    with pytest.raises(
        DependenciaFalhouError,
    ):
        wait_for_predecessor(
            maestro,
            "task-a-erro",
            sleeper=Mock(),
        )

    maestro.get_task.assert_called_once_with(
        "task-a-erro"
    )