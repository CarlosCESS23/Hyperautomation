"""Executor Maestro do Bot C: coleta web com Playwright."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable

from botcity.maestro import (
    AutomationTaskFinishStatus,
)
from dotenv import load_dotenv

from src.bots.bot_coleta_web import (
    ConfiguracaoColetaWeb,
    ResultadoColetaWeb,
    executar_bot_coleta_web,
)
from src.maestro_artifacts import (
    publicar_artefato,
)
from src.maestro_client import (
    criar_cliente_maestro_runner,
)


LOGGER = logging.getLogger("botcity_permorfer")

NOME_ARTEFATO_PEDIDOS = (
    "pedidos_fornecedores.json"
)


def _texto_obrigatorio(
    parametros: dict[str, object],
    nome: str,
) -> str:
    """Lê um parâmetro obrigatório recebido do Maestro."""

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
    """Lê um número inteiro do ambiente."""

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
    """Lê um número decimal do ambiente."""

    valor = os.getenv(nome)

    if valor is None or not valor.strip():
        return padrao

    try:
        return float(valor)
    except ValueError as erro:
        raise ValueError(
            f"{nome} deve possuir um valor numérico"
        ) from erro


def _booleano_ambiente(
    nome: str,
    padrao: bool,
) -> bool:
    """Lê uma configuração booleana do ambiente."""

    valor = os.getenv(nome)

    if valor is None or not valor.strip():
        return padrao

    normalizado = valor.strip().lower()

    if normalizado in {
        "true",
        "1",
        "yes",
        "sim",
        "on",
    }:
        return True

    if normalizado in {
        "false",
        "0",
        "no",
        "nao",
        "não",
        "off",
    }:
        return False

    raise ValueError(
        f"{nome} deve possuir true ou false"
    )


def criar_configuracao_web(
    task_id: str,
) -> ConfiguracaoColetaWeb:
    """Cria a configuração da coleta web."""

    diretorio_saida = Path(
        os.getenv(
            "WEB_OUTPUT_DIR",
            "data/output",
        )
    )

    diretorio_evidencias = Path(
        os.getenv(
            "WEB_EVIDENCE_DIR",
            "screenshots/bot_web",
        )
    )

    return ConfiguracaoColetaWeb(
        portal_url=os.getenv(
            "PORTAL_FORNECEDORES_URL",
            "http://127.0.0.1:8010",
        ),
        max_tentativas=_inteiro_ambiente(
            "WEB_MAX_TENTATIVAS",
            3,
        ),
        timeout_seconds=_decimal_ambiente(
            "WEB_TIMEOUT_SECONDS",
            20.0,
        ),
        backoff_seconds=_decimal_ambiente(
            "WEB_BACKOFF_SECONDS",
            1.0,
        ),
        max_paginas=_inteiro_ambiente(
            "WEB_MAX_PAGINAS",
            20,
        ),
        headless=_booleano_ambiente(
            "WEB_HEADLESS",
            True,
        ),
        intervalo_paginas_seconds=(
            _decimal_ambiente(
                "WEB_INTERVALO_PAGINAS_SECONDS",
                2.0,
            )
        ),
        caminho_artefato=(
            diretorio_saida
            / f"pedidos_fornecedores_{task_id}.json"
        ),
        diretorio_evidencias=(
            diretorio_evidencias
            / task_id
        ),
    )


def _publicar_resultados(
    *,
    maestro: Any,
    task_id: str,
    resultado: ResultadoColetaWeb,
    logger: logging.Logger,
) -> None:
    """Publica o JSON e as evidências produzidas pelo Bot C."""

    publicar_artefato(
        maestro,
        task_id=task_id,
        caminho=resultado.caminho_artefato,
        nome_artefato=NOME_ARTEFATO_PEDIDOS,
    )

    if (
        resultado.caminho_screenshot is not None
        and resultado.caminho_screenshot.is_file()
    ):
        nome_screenshot = (
            f"falha_bot_c_{task_id}.png"
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
            "bot_c_screenshot_publicado",
            extra={
                "evento": (
                    "bot_c_screenshot_publicado"
                ),
                "bot_id": "bot-c-coleta-web",
                "task_id": task_id,
                "nome_artefato": (
                    nome_screenshot
                ),
            },
        )

    if (
        resultado.caminho_html is not None
        and resultado.caminho_html.is_file()
    ):
        nome_html = (
            f"falha_bot_c_{task_id}.html"
        )

        publicar_artefato(
            maestro,
            task_id=task_id,
            caminho=resultado.caminho_html,
            nome_artefato=nome_html,
        )

        logger.info(
            "bot_c_html_publicado",
            extra={
                "evento": (
                    "bot_c_html_publicado"
                ),
                "bot_id": "bot-c-coleta-web",
                "task_id": task_id,
                "nome_artefato": nome_html,
            },
        )


def executar_tarefa_bot_c_capstone(
    *,
    maestro: Any = None,
    executor_coleta: Callable[..., Any] | None = None,
    fabrica_automacao: Callable[[], Any] | None = None,
    configuracao: ConfiguracaoColetaWeb | None = None,
    logger: logging.Logger | None = None,
) -> int:
    """Executa a coleta web como uma tarefa do Maestro."""

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
            else criar_configuracao_web(
                task_id
            )
        )

        executor = (
            executor_coleta
            if executor_coleta is not None
            else executar_bot_coleta_web
        )

        logger.info(
            "bot_c_maestro_iniciado",
            extra={
                "evento": (
                    "bot_c_maestro_iniciado"
                ),
                "bot_id": "bot-c-coleta-web",
                "task_id": task_id,
                "execution_id": execution_id,
                "correlation_id": (
                    correlation_id
                ),
                "predecessor": predecessor,
                "predecessor_task_id": (
                    predecessor_task_id
                ),
                "portal_url": (
                    configuracao_execucao
                    .portal_url
                ),
            },
        )

        resultado = executor(
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
            fabrica_automacao=(
                fabrica_automacao
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
                    "Bot C falhou durante a "
                    f"coleta web: {resultado.erro}"
                ),
                total_items=1,
                processed_items=0,
                failed_items=1,
            )

            return 1

        logger.info(
            "bot_c_maestro_concluido",
            extra={
                "evento": (
                    "bot_c_maestro_concluido"
                ),
                "bot_id": "bot-c-coleta-web",
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
                    NOME_ARTEFATO_PEDIDOS
                ),
            },
        )

        maestro.finish_task(
            task_id=task_id,
            status=(
                AutomationTaskFinishStatus.SUCCESS
            ),
            message=(
                "Bot C concluído. "
                f"{resultado.total_registros} "
                "pedido(s) coletado(s)."
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
            "bot_c_maestro_falhou",
            extra={
                "evento": (
                    "bot_c_maestro_falhou"
                ),
                "bot_id": "bot-c-coleta-web",
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
    """Executa o Bot C pelo Runner do Maestro."""

    return executar_tarefa_bot_c_capstone()


if __name__ == "__main__":
    raise SystemExit(main())