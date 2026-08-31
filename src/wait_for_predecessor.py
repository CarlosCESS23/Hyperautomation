"""Espera limitada de uma dependência registrada no Maestro."""

from __future__ import annotations

import logging
from time import monotonic, sleep
from typing import Any, Callable, Protocol


LOGGER = logging.getLogger("botcity_permorfer")
STATUS_SUCESSO = frozenset({"FINISHED", "SUCCESS", "COMPLETED"})
STATUS_FALHA = frozenset({"FAILED", "ERROR", "CANCELED", "CANCELLED"})


class TimeoutDependenciaError(TimeoutError):
    """A tarefa predecessora não terminou dentro do limite configurado."""


class DependenciaFalhouError(RuntimeError):
    """A tarefa predecessora terminou com falha controlada."""


class MaestroComGetTask(Protocol):
    def get_task(self, task_id: str) -> Any:
        """Consulta uma tarefa no Maestro."""


def wait_for_predecessor(
    maestro: MaestroComGetTask,
    task_id: str,
    *,
    timeout_seconds: float = 300,
    poll_interval_seconds: float = 5,
    clock: Callable[[], float] = monotonic,
    sleeper: Callable[[float], None] = sleep,
    logger: logging.Logger | None = None,
) -> Any:
    """Aguarda o predecessor, falhando de forma controlada no timeout."""

    if not task_id.strip():
        raise ValueError("task_id do predecessor é obrigatório")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds deve ser maior que zero")
    if poll_interval_seconds <= 0:
        raise ValueError("poll_interval_seconds deve ser maior que zero")

    logger = logger or LOGGER
    inicio = clock()
    while True:
        tarefa = maestro.get_task(task_id)
        status = _status(tarefa)

        if status in STATUS_SUCESSO:
            logger.info(
                "dependencia_concluida",
                extra={
                    "evento": "dependencia_concluida",
                    "predecessor_task_id": task_id,
                    "resultado_predecessor": status,
                },
            )
            return tarefa

        if status in STATUS_FALHA:
            logger.error(
                "dependencia_falhou",
                extra={
                    "evento": "dependencia_falhou",
                    "predecessor_task_id": task_id,
                    "resultado_predecessor": status,
                },
            )
            raise DependenciaFalhouError(
                f"Predecessor {task_id} terminou com status {status}"
            )

        decorrido = clock() - inicio
        if decorrido >= timeout_seconds:
            logger.error(
                "dependencia_timeout",
                extra={
                    "evento": "dependencia_timeout",
                    "predecessor_task_id": task_id,
                    "resultado_predecessor": status,
                    "timeout_seconds": timeout_seconds,
                },
            )
            raise TimeoutDependenciaError(
                f"Timeout de {timeout_seconds}s aguardando {task_id}"
            )

        sleeper(
            min(
                poll_interval_seconds,
                timeout_seconds - decorrido,
            )
        )


def _normalizar_status(
    valor: Any,
) -> str:
    if valor is None:
        return ""

    if hasattr(valor, "value"):
        valor = valor.value

    return str(valor).strip().upper()


def _status(tarefa: Any) -> str:
    """
    Obtém o estado tanto de objetos simulados
    quanto de objetos reais do Maestro.
    """

    status = _normalizar_status(
        getattr(tarefa, "status", None)
    )

    if status:
        return status

    estado = _normalizar_status(
        getattr(tarefa, "state", None)
    )

    finalizacao = _normalizar_status(
        getattr(
            tarefa,
            "finish_status",
            None,
        )
    )

    if estado == "FINISHED" and finalizacao:
        return finalizacao

    return estado or finalizacao
