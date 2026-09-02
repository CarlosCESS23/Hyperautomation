"""Testes do adaptador BotCity do Capstone."""

from __future__ import annotations

from concurrent.futures import (
    ThreadPoolExecutor,
)
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.adapters.orquestrador_botcity import (
    AdaptadorOrquestradorBotCity,
    ConflitoIdempotenciaError,
    RepositorioIdempotenciaSQLite,
)


def criar_adaptador(
    *,
    maestro: Mock,
    caminho_banco: Path,
    test: bool = False,
) -> AdaptadorOrquestradorBotCity:
    """Cria o adaptador com um banco isolado."""

    repositorio = (
        RepositorioIdempotenciaSQLite(
            caminho_banco
        )
    )

    return AdaptadorOrquestradorBotCity(
        maestro=maestro,
        repositorio=repositorio,
        test=test,
    )


def test_adaptador_cria_tarefa_no_maestro(
    tmp_path: Path,
):
    """Encaminha os dados corretamente ao SDK."""

    maestro = Mock()

    maestro.create_task.return_value = (
        SimpleNamespace(
            id=101,
        )
    )

    adaptador = criar_adaptador(
        maestro=maestro,
        caminho_banco=(
            tmp_path
            / "idempotencia.sqlite3"
        ),
    )

    tarefa = (
        adaptador
        .criar_tarefa_idempotente(
            activity_label=(
                "carlos_souza-"
                "coleta-web-v1"
            ),
            parameters={
                "execution_id": (
                    "exec-001"
                ),
                "correlation_id": (
                    "corr-001"
                ),
            },
            idempotency_key=(
                "exec-001:"
                "carlos_souza-"
                "coleta-web-v1"
            ),
            priority=5,
        )
    )

    assert tarefa.task_id == "101"

    assert tarefa.criada is True

    assert (
        tarefa.activity_label
        == (
            "carlos_souza-"
            "coleta-web-v1"
        )
    )

    maestro.create_task.assert_called_once_with(
        activity_label=(
            "carlos_souza-"
            "coleta-web-v1"
        ),
        parameters={
            "execution_id": (
                "exec-001"
            ),
            "correlation_id": (
                "corr-001"
            ),
            "idempotency_key": (
                "exec-001:"
                "carlos_souza-"
                "coleta-web-v1"
            ),
        },
        test=False,
        priority=5,
    )


def test_adaptador_aceita_task_id_do_sdk(
    tmp_path: Path,
):
    """Aceita versões que retornam task_id."""

    maestro = Mock()

    maestro.create_task.return_value = (
        SimpleNamespace(
            task_id="task-200",
        )
    )

    adaptador = criar_adaptador(
        maestro=maestro,
        caminho_banco=(
            tmp_path
            / "idempotencia.sqlite3"
        ),
        test=True,
    )

    tarefa = (
        adaptador
        .criar_tarefa_idempotente(
            activity_label=(
                "bot-teste"
            ),
            parameters={
                "execution_id": (
                    "exec-002"
                ),
            },
            idempotency_key=(
                "exec-002:bot-teste"
            ),
        )
    )

    assert (
        tarefa.task_id
        == "task-200"
    )

    maestro.create_task.assert_called_once_with(
        activity_label="bot-teste",
        parameters={
            "execution_id": (
                "exec-002"
            ),
            "idempotency_key": (
                "exec-002:bot-teste"
            ),
        },
        test=True,
        priority=0,
    )


def test_segunda_chamada_reutiliza_tarefa(
    tmp_path: Path,
):
    """A mesma chave não chama o Maestro novamente."""

    maestro = Mock()

    maestro.create_task.return_value = (
        SimpleNamespace(
            id=301,
        )
    )

    adaptador = criar_adaptador(
        maestro=maestro,
        caminho_banco=(
            tmp_path
            / "idempotencia.sqlite3"
        ),
    )

    argumentos = {
        "activity_label": (
            "bot-idempotente"
        ),
        "parameters": {
            "execution_id": (
                "exec-003"
            ),
            "correlation_id": (
                "corr-003"
            ),
        },
        "idempotency_key": (
            "exec-003:bot-idempotente"
        ),
        "priority": 0,
    }

    primeira = (
        adaptador
        .criar_tarefa_idempotente(
            **argumentos
        )
    )

    segunda = (
        adaptador
        .criar_tarefa_idempotente(
            **argumentos
        )
    )

    assert (
        primeira.task_id
        == segunda.task_id
        == "301"
    )

    assert primeira.criada is True
    assert segunda.criada is False

    maestro.create_task.assert_called_once()


def test_mesma_chave_rejeita_payload_diferente(
    tmp_path: Path,
):
    """A chave não pode representar duas tarefas."""

    maestro = Mock()

    maestro.create_task.return_value = (
        SimpleNamespace(
            id=401,
        )
    )

    adaptador = criar_adaptador(
        maestro=maestro,
        caminho_banco=(
            tmp_path
            / "idempotencia.sqlite3"
        ),
    )

    adaptador.criar_tarefa_idempotente(
        activity_label="bot-conflito",
        parameters={
            "execution_id": (
                "exec-004"
            ),
            "valor": "primeiro",
        },
        idempotency_key=(
            "exec-004:bot-conflito"
        ),
    )

    with pytest.raises(
        ConflitoIdempotenciaError,
        match=(
            "reutilizada com payload "
            "diferente"
        ),
    ):
        adaptador.criar_tarefa_idempotente(
            activity_label=(
                "bot-conflito"
            ),
            parameters={
                "execution_id": (
                    "exec-004"
                ),
                "valor": "segundo",
            },
            idempotency_key=(
                "exec-004:bot-conflito"
            ),
        )

    maestro.create_task.assert_called_once()


def test_falha_do_maestro_nao_reserva_chave(
    tmp_path: Path,
):
    """Uma falha permite nova tentativa posterior."""

    maestro = Mock()

    maestro.create_task.side_effect = [
        RuntimeError(
            "Maestro indisponível"
        ),
        SimpleNamespace(
            id=501,
        ),
    ]

    adaptador = criar_adaptador(
        maestro=maestro,
        caminho_banco=(
            tmp_path
            / "idempotencia.sqlite3"
        ),
    )

    argumentos = {
        "activity_label": (
            "bot-recuperavel"
        ),
        "parameters": {
            "execution_id": (
                "exec-005"
            ),
        },
        "idempotency_key": (
            "exec-005:bot-recuperavel"
        ),
    }

    with pytest.raises(
        RuntimeError,
        match="Maestro indisponível",
    ):
        adaptador.criar_tarefa_idempotente(
            **argumentos
        )

    tarefa = (
        adaptador
        .criar_tarefa_idempotente(
            **argumentos
        )
    )

    assert tarefa.task_id == "501"
    assert tarefa.criada is True

    assert (
        maestro.create_task.call_count
        == 2
    )


def test_duas_instancias_compartilham_idempotencia(
    tmp_path: Path,
):
    """Dois adaptadores não criam tarefas duplicadas."""

    caminho_banco = (
        tmp_path
        / "idempotencia.sqlite3"
    )

    maestro_um = Mock()
    maestro_dois = Mock()

    maestro_um.create_task.return_value = (
        SimpleNamespace(
            id=601,
        )
    )

    maestro_dois.create_task.return_value = (
        SimpleNamespace(
            id=602,
        )
    )

    adaptador_um = criar_adaptador(
        maestro=maestro_um,
        caminho_banco=caminho_banco,
    )

    adaptador_dois = criar_adaptador(
        maestro=maestro_dois,
        caminho_banco=caminho_banco,
    )

    argumentos = {
        "activity_label": (
            "bot-concorrente"
        ),
        "parameters": {
            "execution_id": (
                "exec-006"
            ),
        },
        "idempotency_key": (
            "exec-006:bot-concorrente"
        ),
    }

    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:
        futuro_um = executor.submit(
            adaptador_um
            .criar_tarefa_idempotente,
            **argumentos,
        )

        futuro_dois = executor.submit(
            adaptador_dois
            .criar_tarefa_idempotente,
            **argumentos,
        )

        resultado_um = futuro_um.result(
            timeout=10
        )

        resultado_dois = (
            futuro_dois.result(
                timeout=10
            )
        )

    assert (
        resultado_um.task_id
        == resultado_dois.task_id
    )

    assert sorted(
        (
            resultado_um.criada,
            resultado_dois.criada,
        )
    ) == [
        False,
        True,
    ]

    total_chamadas = (
        maestro_um.create_task.call_count
        + maestro_dois.create_task.call_count
    )

    assert total_chamadas == 1


def test_parametro_nao_serializavel_e_rejeitado(
    tmp_path: Path,
):
    """O Maestro deve receber somente JSON válido."""

    maestro = Mock()

    adaptador = criar_adaptador(
        maestro=maestro,
        caminho_banco=(
            tmp_path
            / "idempotencia.sqlite3"
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "somente valores "
            "serializáveis em JSON"
        ),
    ):
        adaptador.criar_tarefa_idempotente(
            activity_label=(
                "bot-invalido"
            ),
            parameters={
                "objeto": object(),
            },
            idempotency_key=(
                "exec-007:bot-invalido"
            ),
        )

    maestro.create_task.assert_not_called()