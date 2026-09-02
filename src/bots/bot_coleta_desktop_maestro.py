"""Executor Maestro do Bot B: coleta visual do estoque desktop."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable

from botcity.maestro import (
    AutomationTaskFinishStatus,
)
from dotenv import load_dotenv

from src.bots.bot_coleta_desktop import (
    AdaptadorBotCityDesktop,
    ConfiguracaoColetaDesktop,
    ResultadoColetaDesktop,
    executar_bot_coleta_desktop,
)
from src.maestro_artifacts import (
    publicar_artefato,
)
from src.maestro_client import (
    criar_cliente_maestro_runner,
)


LOGGER = logging.getLogger("botcity_permorfer")

NOME_ARTEFATO_ESTOQUE = "estoque_desktop.json"


def _texto_obrigatorio(
    parametros: dict[str, object],
    nome: str,
) -> str:
    """Lê e valida um parâmetro obrigatório do Maestro."""

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


def _inteiro_ambiente(
    nome: str,
    padrao: int,
) -> int:
    """Obtém um número inteiro das variáveis de ambiente."""

    valor = os.getenv(nome)

    if valor is None or not valor.strip():
        return padrao

    try:
        return int(valor)
    except ValueError as erro:
        raise ValueError(
            f"{nome} deve possuir um valor inteiro"
        ) from erro


def _decimal_ambiente(
    nome: str,
    padrao: float,
) -> float:
    """Obtém um número decimal das variáveis de ambiente."""

    valor = os.getenv(nome)

    if valor is None or not valor.strip():
        return padrao

    try:
        return float(valor)
    except ValueError as erro:
        raise ValueError(
            f"{nome} deve possuir um valor numérico"
        ) from erro


def criar_configuracao_desktop(
    task_id: str,
) -> ConfiguracaoColetaDesktop:
    """Cria a configuração do Bot B usando o ambiente."""

    diretorio_saida = Path(
        os.getenv(
            "DESKTOP_OUTPUT_DIR",
            "data/output",
        )
    )

    diretorio_screenshots = Path(
        os.getenv(
            "DESKTOP_SCREENSHOTS_DIR",
            "screenshots/bot_desktop",
        )
    )

    return ConfiguracaoColetaDesktop(
        max_tentativas=_inteiro_ambiente(
            "DESKTOP_MAX_TENTATIVAS",
            3,
        ),
        timeout_seconds=_decimal_ambiente(
            "DESKTOP_TIMEOUT_SECONDS",
            30.0,
        ),
        backoff_seconds=_decimal_ambiente(
            "DESKTOP_BACKOFF_SECONDS",
            1.0,
        ),
        max_paginas=_inteiro_ambiente(
            "DESKTOP_MAX_PAGINAS",
            20,
        ),
        caminho_artefato=(
            diretorio_saida
            / f"estoque_desktop_{task_id}.json"
        ),
        diretorio_screenshots=(
            diretorio_screenshots
            / task_id
        ),
    )


def criar_automacao_desktop() -> AdaptadorBotCityDesktop:
    """Cria o adaptador visual utilizado no ambiente real."""

    diretorio_recursos = Path(
        os.getenv(
            "DESKTOP_RESOURCES_DIR",
            "resources/capstone_desktop",
        )
    )

    matching = _decimal_ambiente(
        "DESKTOP_IMAGE_MATCHING",
        0.90,
    )

    return AdaptadorBotCityDesktop(
        diretorio_recursos=diretorio_recursos,
        matching=matching,
    )


def _publicar_resultados(
    *,
    maestro: Any,
    task_id: str,
    resultado: ResultadoColetaDesktop,
    logger: logging.Logger,
) -> None:
    """Publica o JSON e, quando existir, o screenshot de falha."""

    publicar_artefato(
        maestro,
        task_id=task_id,
        caminho=resultado.caminho_artefato,
        nome_artefato=NOME_ARTEFATO_ESTOQUE,
    )

    if (
        resultado.caminho_screenshot is not None
        and resultado.caminho_screenshot.is_file()
    ):
        nome_screenshot = (
            f"falha_bot_b_{task_id}.png"
        )

        publicar_artefato(
            maestro,
            task_id=task_id,
            caminho=(
                resultado.caminho_screenshot
            ),
            nome_artefato=nome_screenshot,
        )

        logger.info(
            "bot_b_screenshot_publicado",
            extra={
                "evento": (
                    "bot_b_screenshot_publicado"
                ),
                "bot_id": (
                    "bot-b-coleta-desktop"
                ),
                "task_id": task_id,
                "nome_artefato": (
                    nome_screenshot
                ),
            },
        )


def executar_tarefa_bot_b_capstone(
    *,
    maestro: Any = None,
    executor_coleta: Callable[..., Any] | None = None,
    fabrica_automacao: Callable[[], Any] | None = None,
    configuracao: ConfiguracaoColetaDesktop | None = None,
    logger: logging.Logger | None = None,
) -> int:
    """Executa a coleta desktop como uma tarefa do Maestro."""

    load_dotenv()

    logger = logger or LOGGER

    if maestro is None:
        maestro = criar_cliente_maestro_runner()

    execucao = maestro.get_execution()

    task_id = str(execucao.task_id)

    parametros = dict(
        execucao.parameters or {}
    )

    try:
        execution_id = _texto_obrigatorio(
            parametros,
            "execution_id",
        )

        correlation_id = _texto_obrigatorio(
            parametros,
            "correlation_id",
        )

        predecessor = _texto_obrigatorio(
            parametros,
            "predecessor",
        )

        predecessor_task_id = (
            _texto_obrigatorio(
                parametros,
                "predecessor_task_id",
            )
        )

        resultado_predecessor = (
            _texto_obrigatorio(
                parametros,
                "resultado_predecessor",
            )
        )

        configuracao_execucao = (
            configuracao
            if configuracao is not None
            else criar_configuracao_desktop(
                task_id
            )
        )

        automacao = (
            fabrica_automacao()
            if fabrica_automacao is not None
            else criar_automacao_desktop()
        )

        executor = (
            executor_coleta
            if executor_coleta is not None
            else executar_bot_coleta_desktop
        )

        logger.info(
            "bot_b_maestro_iniciado",
            extra={
                "evento": (
                    "bot_b_maestro_iniciado"
                ),
                "bot_id": (
                    "bot-b-coleta-desktop"
                ),
                "task_id": task_id,
                "execution_id": execution_id,
                "correlation_id": (
                    correlation_id
                ),
                "predecessor": predecessor,
                "predecessor_task_id": (
                    predecessor_task_id
                ),
            },
        )

        resultado = executor(
            automacao,
            execution_id=execution_id,
            correlation_id=correlation_id,
            task_id=task_id,
            configuracao=(
                configuracao_execucao
            ),
            predecessor=predecessor,
            predecessor_task_id=(
                predecessor_task_id
            ),
            resultado_predecessor=(
                resultado_predecessor
            ),
            logger=logger,
        )

        _publicar_resultados(
            maestro=maestro,
            task_id=task_id,
            resultado=resultado,
            logger=logger,
        )

        if not resultado.sucesso:
            maestro.finish_task(
                task_id=task_id,
                status=(
                    AutomationTaskFinishStatus
                    .FAILED
                ),
                message=(
                    "Bot B falhou durante a "
                    f"coleta desktop: {resultado.erro}"
                ),
                total_items=1,
                processed_items=0,
                failed_items=1,
            )

            return 1

        logger.info(
            "bot_b_maestro_concluido",
            extra={
                "evento": (
                    "bot_b_maestro_concluido"
                ),
                "bot_id": (
                    "bot-b-coleta-desktop"
                ),
                "task_id": task_id,
                "execution_id": execution_id,
                "correlation_id": (
                    correlation_id
                ),
                "tentativas": (
                    resultado.tentativas
                ),
                "total_registros": (
                    resultado.total_registros
                ),
                "nome_artefato": (
                    NOME_ARTEFATO_ESTOQUE
                ),
            },
        )

        maestro.finish_task(
            task_id=task_id,
            status=(
                AutomationTaskFinishStatus.SUCCESS
            ),
            message=(
                "Bot B concluído. "
                f"{resultado.total_registros} "
                "registro(s) de estoque coletado(s)."
            ),
            total_items=(
                resultado.total_registros
            ),
            processed_items=(
                resultado.total_registros
            ),
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
                    "bot-b-coleta-desktop"
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
                f"Falha no Bot B: {erro}"
            ),
            total_items=1,
            processed_items=0,
            failed_items=1,
        )

        return 1


def main() -> int:
    """Executa o Bot B pelo Runner do Maestro."""

    return executar_tarefa_bot_b_capstone()


if __name__ == "__main__":
    raise SystemExit(main())