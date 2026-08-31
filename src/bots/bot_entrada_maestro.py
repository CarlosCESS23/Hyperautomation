"""Ponto de entrada do Bot A para o BotCity Maestro."""

from __future__ import annotations
from dotenv import load_dotenv
import logging
from pathlib import Path
from typing import Any, Callable
import os

from botcity.maestro import (
    AutomationTaskFinishStatus,
)

from src.bots.bot_entrada import (
    executar_bot_entrada,
)
from src.maestro_client import (
    criar_cliente_maestro_runner,
)
from src.orchestrator import (
    disparar_bot_b,
)


LOGGER = logging.getLogger(
    "botcity_permorfer"
)


CAMINHO_PROJETO = Path('/home/carloscess/Documentos/projetoAX/Atividades/Hyperautomation')

CAMINHO_ARQUIVO_ENV = (CAMINHO_PROJETO/ '.env')

load_dotenv(dotenv_path=CAMINHO_ARQUIVO_ENV)



def _texto_opcional(
    valor: object,
) -> str | None:
    """Converte um parâmetro opcional em texto."""

    if valor is None:
        return None

    texto = str(valor).strip()

    return texto or None


def executar_tarefa_bot_a(
    *,
    maestro: Any = None,
    executor_bot_a: Callable[..., Any] | None = None,
    disparador_bot_b: Callable[..., Any] | None = None,
    logger: logging.Logger | None = None,
) -> int:
    """Executa o Bot A e agenda o Bot B."""

    logger = logger or LOGGER

    if maestro is None:
        maestro = criar_cliente_maestro_runner()

    executor = (
        executor_bot_a
        if executor_bot_a is not None
        else executar_bot_entrada
    )

    disparador = (
        disparador_bot_b
        if disparador_bot_b is not None
        else disparar_bot_b
    )

    execucao = maestro.get_execution()

    task_id = str(
        execucao.task_id
    )

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
            status=(
                AutomationTaskFinishStatus
                .FAILED
            ),
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
        parametros.get(
            "execution_id"
        )
    )

    correlation_id = _texto_opcional(
        parametros.get(
            "correlation_id"
        )
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
                    AutomationTaskFinishStatus
                    .FAILED
                ),
                message=resultado.mensagem,
                total_items=1,
                processed_items=0,
                failed_items=1,
            )

            return 1

        parametros_bot_b = (
            resultado.parametros_bot_b
        )

        if parametros_bot_b is None:
            raise RuntimeError(
                "Bot A foi concluído sem os "
                "parâmetros do Bot B"
            )

        caminho_validado = Path(
            parametros_bot_b
            .caminho_entrada
        )

        extensao = (
            caminho_validado.suffix
            or ".xlsx"
        )

        nome_artefato_entrada = (
            f"entrada_bot_a_{task_id}"
            f"{extensao}"
        )

        maestro.post_artifact(
            task_id=task_id,
            artifact_name=(
                nome_artefato_entrada
            ),
            filepath=str(
                caminho_validado
            ),
        )

        tarefa_bot_b = disparador(
            maestro,
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
            parametros={
                "entrada_task_id": task_id,
                "entrada_artefato": (
                    nome_artefato_entrada
                ),
            },
        )

        task_id_sucessor = getattr(
            tarefa_bot_b,
            "id",
            getattr(
                tarefa_bot_b,
                "task_id",
                None,
            ),
        )

        logger.info(
            "bot_a_agendou_bot_b",
            extra={
                "evento": (
                    "bot_a_agendou_bot_b"
                ),
                "bot_id": "bot-a-entrada",
                "task_id": task_id,
                "task_id_sucessor": (
                    task_id_sucessor
                ),
                "execution_id": (
                    resultado.execution_id
                ),
                "correlation_id": (
                    resultado.correlation_id
                ),
                "caminho_artefato": str(
                    caminho_validado
                ),
            },
        )

        maestro.finish_task(
            task_id=task_id,
            status=(
                AutomationTaskFinishStatus
                .SUCCESS
            ),
            message=(
                "Bot A concluído. "
                "Tarefa do Bot B criada."
            ),
            total_items=1,
            processed_items=1,
            failed_items=0,
        )

        return 0

    except Exception as erro:
        logger.exception(
            "bot_a_maestro_falhou",
            extra={
                "evento": (
                    "bot_a_maestro_falhou"
                ),
                "bot_id": "bot-a-entrada",
                "task_id": task_id,
                "erro": str(erro),
                       },
        )

        maestro.finish_task(
            task_id=task_id,
            status=(
                AutomationTaskFinishStatus
                .FAILED
            ),
            message=(
                f"Falha no Bot A: {erro}"
            ),
            total_items=1,
            processed_items=0,
            failed_items=1,
        )

        return 1


def main() -> int:
    """Executa o Bot A pelo Runner."""

    return executar_tarefa_bot_a()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )