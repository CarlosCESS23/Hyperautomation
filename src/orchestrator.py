"""Orquestração da cadeia de bots no BotCity Maestro."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Mapping, Protocol


LOGGER = logging.getLogger("botcity_permorfer")

BOT_A_ENTRADA = "gustavo_nunes-entrada-v1"
BOT_B_CONFERENCIA = "gustavo_nunes-conferencia-v1"
BOT_C_RELATORIO = "gustavo_nunes-relatorio-v1"


@dataclass(frozen=True)
class BotRegistrado:
    """Identificação de um bot que deve ser cadastrado no Maestro."""

    etapa: str
    activity_label: str


BOTS_REGISTRADOS = (
    BotRegistrado("bot_a", BOT_A_ENTRADA),
    BotRegistrado("bot_b", BOT_B_CONFERENCIA),
    BotRegistrado("bot_c", BOT_C_RELATORIO),
)


class MaestroComCreateTask(Protocol):
    """Parte do SDK necessária para disparar a próxima tarefa."""

    def create_task(
        self,
        activity_label: str,
        parameters: dict[str, object],
        test: bool = False,
        priority: int = 0,
        min_execution_date: Any = None,
    ) -> Any:
        """Cria uma tarefa no Maestro."""


def criar_tarefa_sucessora(
    maestro: MaestroComCreateTask,
    *,
    activity_label: str,
    predecessor: str,
    resultado_predecessor: str,
    execution_id: str,
    correlation_id: str,
    parametros: Mapping[str, object] | None = None,
    test: bool = False,
    priority: int = 0,
    logger: logging.Logger | None = None,
) -> Any:
    """Cria uma tarefa sucessora com rastreamento obrigatório da cadeia."""

    campos_obrigatorios = {
        "activity_label": activity_label,
        "predecessor": predecessor,
        "resultado_predecessor": resultado_predecessor,
        "execution_id": execution_id,
        "correlation_id": correlation_id,
    }
    vazios = [
        nome
        for nome, valor in campos_obrigatorios.items()
        if not isinstance(valor, str) or not valor.strip()
    ]
    if vazios:
        raise ValueError(
            "Campos obrigatórios vazios: " + ", ".join(vazios)
        )

    payload = dict(parametros or {})
    # Os valores rastreáveis são definidos por esta camada e não podem ser
    # substituídos acidentalmente por parâmetros livres do chamador.
    payload.update(
        {
            "predecessor": predecessor,
            "resultado_predecessor": resultado_predecessor,
            "execution_id": execution_id,
            "correlation_id": correlation_id,
        }
    )

    tarefa = maestro.create_task(
        activity_label=activity_label,
        parameters=payload,
        test=test,
        priority=priority,
    )

    (logger or LOGGER).info(
        "tarefa_sucessora_criada",
        extra={
            "evento": "tarefa_sucessora_criada",
            "bot_destino": activity_label,
            **payload,
            "task_id": _task_id(tarefa),
        },
    )
    return tarefa


def disparar_bot_b(
    maestro: MaestroComCreateTask,
    *,
    resultado_predecessor: str,
    execution_id: str,
    correlation_id: str,
    parametros: Mapping[str, object] | None = None,
    **opcoes: Any,
) -> Any:
    """Dispara o Bot B após o encerramento controlado do Bot A."""

    return criar_tarefa_sucessora(
        maestro,
        activity_label=BOT_B_CONFERENCIA,
        predecessor=BOT_A_ENTRADA,
        resultado_predecessor=resultado_predecessor,
        execution_id=execution_id,
        correlation_id=correlation_id,
        parametros=parametros,
        **opcoes,
    )


def disparar_bot_c(
    maestro: MaestroComCreateTask,
    *,
    resultado_predecessor: str,
    execution_id: str,
    correlation_id: str,
    parametros: Mapping[str, object] | None = None,
    **opcoes: Any,
) -> Any:
    """Dispara o Bot C após o encerramento controlado do Bot B."""

    return criar_tarefa_sucessora(
        maestro,
        activity_label=BOT_C_RELATORIO,
        predecessor=BOT_B_CONFERENCIA,
        resultado_predecessor=resultado_predecessor,
        execution_id=execution_id,
        correlation_id=correlation_id,
        parametros=parametros,
        **opcoes,
    )


def _task_id(tarefa: Any) -> str | None:
    """Obtém o identificador sem depender de uma versão específica do SDK."""

    for atributo in ("task_id", "id"):
        valor = getattr(tarefa, atributo, None)
        if valor is not None:
            return str(valor)
    return None
