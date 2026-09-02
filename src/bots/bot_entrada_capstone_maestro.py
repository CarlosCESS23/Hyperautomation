"""Ponto de entrada do Bot A do Capstone para o BotCity Maestro."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable

from botcity.maestro import AutomationTaskFinishStatus
from dotenv import load_dotenv

from src.adapters.orquestrador_botcity import (
    AdaptadorOrquestradorBotCity,
)
from src.bots.bot_entrada import executar_bot_entrada
from src.maestro_client import criar_cliente_maestro_runner
from src.orquestracao_capstone import (
    ServicoOrquestracaoCapstone,
)


LOGGER = logging.getLogger("botcity_permorfer")


def _texto_opcional(valor: object) -> str | None:
    """Converte valores opcionais para texto não vazio."""

    if valor is None:
        return None

    texto = str(valor).strip()

    return texto or None


def _criar_servico_orquestracao(
    maestro: Any,
) -> ServicoOrquestracaoCapstone:
    """Cria o serviço usando o adaptador concreto do BotCity."""

    porta = (
        AdaptadorOrquestradorBotCity
        .de_ambiente(
            maestro=maestro,
        )
    )

    return ServicoOrquestracaoCapstone(
        porta,
    )


def executar_tarefa_bot_a_capstone(
    *,
    maestro: Any = None,
    executor_bot_a: Callable[..., Any] | None = None,
    servico_orquestracao: Any = None,
    logger: logging.Logger | None = None,
) -> int:
    """
    Executa o Bot A e agenda o início do fluxo Capstone.

    Responsabilidades:

    1. Receber a planilha.
    2. Validar sua estrutura.
    3. Publicá-la como artefato no Maestro.
    4. Agendar os Bots B, C e D.
    5. Preservar execution_id e correlation_id.
    """

    load_dotenv()

    logger = logger or LOGGER

    if maestro is None:
        maestro = criar_cliente_maestro_runner()

    executor = (
        executor_bot_a
        if executor_bot_a is not None
        else executar_bot_entrada
    )

    execucao = maestro.get_execution()

    task_id = str(execucao.task_id)

    parametros = dict(
        execucao.parameters or {}
    )

    caminho_entrada = (
        _texto_opcional(
            parametros.get("caminho_entrada")
        )
        or _texto_opcional(
            os.getenv("CAMINHO_ENTRADA")
        )
    )

    if caminho_entrada is None:
        maestro.finish_task(
            task_id=task_id,
            status=AutomationTaskFinishStatus.FAILED,
            message=(
                "Parâmetro caminho_entrada "
                "não informado"
            ),
            total_items=1,
            processed_items=0,
            failed_items=1,
        )

        return 1

    execution_id = _texto_opcional(
        parametros.get("execution_id")
    )

    correlation_id = _texto_opcional(
        parametros.get("correlation_id")
    )

    try:
        resultado = executor(
            caminho_entrada,
            execution_id=execution_id,
            correlation_id=correlation_id,
        )

        if not resultado.sucesso:
            maestro.finish_task(
                task_id=task_id,
                status=(
                    AutomationTaskFinishStatus.FAILED
                ),
                message=resultado.mensagem,
                total_items=1,
                processed_items=0,
                failed_items=1,
            )

            return 1

        parametros_sucessores = (
            resultado.parametros_bot_b
        )

        if parametros_sucessores is None:
            raise RuntimeError(
                "Bot A terminou sem os parâmetros "
                "necessários para os sucessores"
            )

        caminho_validado = Path(
            parametros_sucessores.caminho_entrada
        )

        extensao = (
            caminho_validado.suffix
            or ".xlsx"
        )

        nome_artefato = (
            f"entrada_capstone_"
            f"{task_id}{extensao}"
        )

        maestro.post_artifact(
            task_id=task_id,
            artifact_name=nome_artefato,
            filepath=str(caminho_validado),
        )

        servico = (
            servico_orquestracao
            if servico_orquestracao is not None
            else _criar_servico_orquestracao(
                maestro
            )
        )

        fluxo = servico.iniciar_fluxo(
            predecessor_task_id=task_id,
            resultado_predecessor=(
                resultado.status.value
            ),
            execution_id=(
                resultado.execution_id
            ),
            correlation_id=(
                resultado.correlation_id
            ),
            entrada_task_id=task_id,
            entrada_artefato=nome_artefato,
        )

        logger.info(
            "bot_a_capstone_agendou_fluxo",
            extra={
                "evento": (
                    "bot_a_capstone_agendou_fluxo"
                ),
                "bot_id": "bot-a-entrada-capstone",
                "task_id": task_id,
                "task_id_bot_b": (
                    fluxo.coleta_desktop.task_id
                ),
                "task_id_bot_c": (
                    fluxo.coleta_web.task_id
                ),
                "task_id_bot_d": (
                    fluxo.consolidacao.task_id
                ),
                "execution_id": (
                    resultado.execution_id
                ),
                "correlation_id": (
                    resultado.correlation_id
                ),
                "entrada_artefato": (
                    nome_artefato
                ),
            },
        )

        maestro.finish_task(
            task_id=task_id,
            status=(
                AutomationTaskFinishStatus.SUCCESS
            ),
            message=(
                "Bot A concluído. "
                "Bots B e C e consolidação D "
                "foram agendados."
            ),
            total_items=1,
            processed_items=1,
            failed_items=0,
        )

        return 0

    except Exception as erro:
        logger.exception(
            "bot_a_capstone_falhou",
            extra={
                "evento": (
                    "bot_a_capstone_falhou"
                ),
                "bot_id": (
                    "bot-a-entrada-capstone"
                ),
                "task_id": task_id,
                "erro": str(erro),
            },
        )

        maestro.finish_task(
            task_id=task_id,
            status=(
                AutomationTaskFinishStatus.FAILED
            ),
            message=(
                f"Falha no Bot A Capstone: {erro}"
            ),
            total_items=1,
            processed_items=0,
            failed_items=1,
        )

        return 1


def main() -> int:
    """Executa o Bot A Capstone pelo Runner."""

    return executar_tarefa_bot_a_capstone()


if __name__ == "__main__":
    raise SystemExit(main())