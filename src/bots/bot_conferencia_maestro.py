"""Ponto de entrada do Bot B para o BotCity Maestro."""

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Callable, Mapping

from botcity.maestro import (
    AutomationTaskFinishStatus,
)

from src.bots.bot_conferencia import (
    executar_bot_conferencia,
)
from src.maestro_artifacts import (
    baixar_artefato,
)
from src.maestro_client import (
    criar_cliente_maestro_runner,
)
from src.orchestrator import (
    disparar_bot_c,
)
from src.transferencia_resultado_bot_b import (
    salvar_resultado_bot_b,
)
from src.wait_for_predecessor import (
    wait_for_predecessor,
)


LOGGER = logging.getLogger(
    "botcity_permorfer"
)


def _parametro_obrigatorio(
    parametros: Mapping[str, object],
    nome: str,
) -> str:
    """Lê e valida um parâmetro da tarefa."""

    valor = parametros.get(nome)

    if valor is None:
        raise ValueError(
            f"Parâmetro {nome} não informado"
        )

    texto = str(valor).strip()

    if not texto:
        raise ValueError(
            f"Parâmetro {nome} não informado"
        )

    return texto


def executar_tarefa_bot_b(
    *,
    maestro: Any = None,
    executor_bot_b: Callable[..., Any] | None = None,
    espera_predecessor: Callable[..., Any] | None = None,
    baixador: Callable[..., Path] | None = None,
    serializador: Callable[..., Path] | None = None,
    disparador_bot_c: Callable[..., Any] | None = None,
    diretorio_trabalho: str | Path | None = None,
    logger: logging.Logger | None = None,
) -> int:
    """Executa o Bot B e agenda o Bot C."""

    logger = logger or LOGGER

    if maestro is None:
        maestro = criar_cliente_maestro_runner()

    executor = (
        executor_bot_b
        if executor_bot_b is not None
        else executar_bot_conferencia
    )

    esperar = (
        espera_predecessor
        if espera_predecessor is not None
        else wait_for_predecessor
    )

    baixar = (
        baixador
        if baixador is not None
        else baixar_artefato
    )

    salvar = (
        serializador
        if serializador is not None
        else salvar_resultado_bot_b
    )

    disparador = (
        disparador_bot_c
        if disparador_bot_c is not None
        else disparar_bot_c
    )

    execucao = maestro.get_execution()

    task_id = str(
        execucao.task_id
    )

    parametros = dict(
        execucao.parameters or {}
    )

    try:
        predecessor_task_id = (
            _parametro_obrigatorio(
                parametros,
                "predecessor_task_id",
            )
        )

        entrada_task_id = (
            _parametro_obrigatorio(
                parametros,
                "entrada_task_id",
            )
        )

        entrada_artefato = (
            _parametro_obrigatorio(
                parametros,
                "entrada_artefato",
            )
        )

        execution_id = (
            _parametro_obrigatorio(
                parametros,
                "execution_id",
            )
        )

        correlation_id = (
            _parametro_obrigatorio(
                parametros,
                "correlation_id",
            )
        )

        diretorio = (
            Path(diretorio_trabalho)
            if diretorio_trabalho is not None
            else (
                Path(gettempdir())
                / "hyperautomation-maestro"
            )
        )

        diretorio.mkdir(
            parents=True,
            exist_ok=True,
        )

        esperar(
            maestro,
            predecessor_task_id,
        )

        caminho_entrada = baixar(
            maestro,
            task_id_origem=entrada_task_id,
            nome_artefato=entrada_artefato,
            destino=(
                diretorio
                / entrada_artefato
            ),
        )

        resultado = executor(
            str(caminho_entrada),
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

        nome_resultado = (
            f"resultado_bot_b_"
            f"{task_id}.json"
        )

        caminho_resultado = (
            diretorio
            / nome_resultado
        )

        salvar(
            resultado,
            caminho_resultado,
        )

        maestro.post_artifact(
            task_id=task_id,
            artifact_name=nome_resultado,
            filepath=str(
                caminho_resultado
            ),
        )

        tarefa_bot_c = disparador(
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
                "resultado_bot_b_task_id": (
                    task_id
                ),
                "resultado_bot_b_artefato": (
                    nome_resultado
                ),
            },
        )

        task_id_sucessor = getattr(
            tarefa_bot_c,
            "id",
            getattr(
                tarefa_bot_c,
                "task_id",
                None,
            ),
        )

        logger.info(
            "bot_b_agendou_bot_c",
            extra={
                "evento": (
                    "bot_b_agendou_bot_c"
                ),
                "bot_id": (
                    "bot-b-conferencia"
                ),
                "task_id": task_id,
                "predecessor_task_id": (
                    predecessor_task_id
                ),
                "task_id_sucessor": (
                    task_id_sucessor
                ),
                "execution_id": execution_id,
                "correlation_id": (
                    correlation_id
                ),
                "caminho_artefato": str(
                    caminho_resultado
                ),
            },
        )

        total = resultado.total_registros

        maestro.finish_task(
            task_id=task_id,
            status=(
                AutomationTaskFinishStatus
                .SUCCESS
            ),
            message=(
                "Bot B concluído. "
                "Artefato publicado e Bot C criado."
            ),
            total_items=total,
            processed_items=total,
            failed_items=0,
        )

        return 0

    except Exception as erro:
        logger.exception(
            "bot_b_maestro_falhou",
            extra={
                "evento": (
                    "bot_b_maestro_falhou"
                ),
                "bot_id": (
                    "bot-b-conferencia"
                ),
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
                f"Falha no Bot B: {erro}"
            ),
            total_items=1,
            processed_items=0,
            failed_items=1,
        )

        return 1


def main() -> int:
    """Executa o Bot B pelo Runner."""

    return executar_tarefa_bot_b()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )