"""Ponto de entrada do Bot C para o BotCity Maestro."""

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Callable, Mapping

from botcity.maestro import (
    AutomationTaskFinishStatus,
)

from src.bots.bot_relatorio import (
    executar_bot_relatorio,
)
from src.maestro_client import (
    criar_cliente_maestro_runner,
)
from src.sistema_alertas import (
    SistemaAlertas,
)
from src.transferencia_resultado_bot_b import (
    carregar_resultado_bot_b,
)
from src.wait_for_predecessor import (
    wait_for_predecessor,
)

from src.maestro_artifacts import (
    baixar_artefato,
)


LOGGER = logging.getLogger(
    "botcity_permorfer"
)


def _parametro_obrigatorio(
    parametros: Mapping[str, object],
    nome: str,
) -> str:
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

def executar_tarefa_bot_c(
    *,
    maestro: Any = None,
    espera_predecessor: Callable[..., Any] | None = None,
    carregador: Callable[..., Any] | None = None,
    executor_bot_c: Callable[..., Any] | None = None,
    sistema_alertas: SistemaAlertas | Any = None,
    diretorio_trabalho: str | Path | None = None,
    logger: logging.Logger | None = None,
) -> int:
    """Executa o Bot C e encerra a cadeia."""

    logger = logger or LOGGER

    if maestro is None:
        maestro = criar_cliente_maestro_runner()

    esperar = (
        espera_predecessor
        if espera_predecessor is not None
        else wait_for_predecessor
    )

    carregar = (
        carregador
        if carregador is not None
        else carregar_resultado_bot_b
    )

    executor = (
        executor_bot_c
        if executor_bot_c is not None
        else executar_bot_relatorio
    )

    alertas = (
        sistema_alertas
        if sistema_alertas is not None
        else SistemaAlertas.de_ambiente(
            logger=logger,
        )
    )

    execucao = maestro.get_execution()
    task_id = str(execucao.task_id)

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

        task_id_resultado = (
            _parametro_obrigatorio(
                parametros,
                "resultado_bot_b_task_id",
            )
        )

        nome_resultado = (
            _parametro_obrigatorio(
                parametros,
                "resultado_bot_b_artefato",
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

        esperar(
            maestro,
            predecessor_task_id,
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

        caminho_resultado = baixar_artefato(
            maestro,
            task_id_origem=task_id_resultado,
            nome_artefato=nome_resultado,
            destino=(
                    diretorio / nome_resultado
            ),
        )

        resultado_bot_b = carregar(
            caminho_resultado,
        )

        if not resultado_bot_b.sucesso:
            raise RuntimeError(
                "Bot C recebeu um resultado "
                "malsucedido do Bot B"
            )

        if (
            resultado_bot_b.execution_id
            != execution_id
        ):
            raise ValueError(
                "execution_id do artefato "
                "não corresponde à tarefa"
            )

        if (
            resultado_bot_b.correlation_id
            != correlation_id
        ):
            raise ValueError(
                "correlation_id do artefato "
                "não corresponde à tarefa"
            )

        caminho_relatorio = (
            diretorio
            / "relatorio_conferencia_lotes.xlsx"
        )

        resultado_bot_c = executor(
            resultado_bot_b.registros,
            caminho_relatorio,
            execution_id=execution_id,
            correlation_id=correlation_id,
            sistema_alertas=alertas,
        )

        if not resultado_bot_c.sucesso:
            maestro.finish_task(
                task_id=task_id,
                status=(
                    AutomationTaskFinishStatus
                    .FAILED
                ),
                message=(
                    resultado_bot_c.mensagem
                ),
                total_items=(
                    resultado_bot_b
                    .total_registros
                ),
                processed_items=0,
                failed_items=(
                    resultado_bot_b
                    .total_registros
                ),
            )
            return 1

        caminho_gerado = Path(
            resultado_bot_c
            .caminho_relatorio
        )

        if not caminho_gerado.is_file():
            raise FileNotFoundError(
                "Bot C informou sucesso, mas "
                "o relatório não foi encontrado"
            )

        maestro.post_artifact(
            task_id=task_id,
            artifact_name=(
                caminho_gerado.name
            ),
            filepath=str(caminho_gerado),
        )

        total = (
            resultado_bot_b.total_registros
        )

        maestro.finish_task(
            task_id=task_id,
            status=(
                AutomationTaskFinishStatus
                .SUCCESS
            ),
            message=(
                "Bot C concluído. "
                "Relatório publicado."
            ),
            total_items=total,
            processed_items=total,
            failed_items=0,
        )

        logger.info(
            "cadeia_maestro_encerrada",
            extra={
                "evento": (
                    "cadeia_maestro_encerrada"
                ),
                "bot_id": "bot-c-relatorio",
                "task_id": task_id,
                "predecessor_task_id": (
                    predecessor_task_id
                ),
                "execution_id": execution_id,
                "correlation_id": (
                    correlation_id
                ),
                "caminho_relatorio": str(
                    caminho_gerado
                ),
            },
        )

        return 0

    except Exception as erro:
        logger.exception(
            "bot_c_maestro_falhou",
            extra={
                "evento": (
                    "bot_c_maestro_falhou"
                ),
                "bot_id": "bot-c-relatorio",
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
                f"Falha no Bot C: {erro}"
            ),
            total_items=1,
            processed_items=0,
            failed_items=1,
        )

        return 1


def main() -> int:
    return executar_tarefa_bot_c()


if __name__ == "__main__":
    raise SystemExit(main())