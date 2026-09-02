"""Executor Maestro do Bot E: classificação híbrida com ML e fallback."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable

from botcity.maestro import (
    AutomationTaskFinishStatus,
)
from dotenv import load_dotenv

from src.adapters.orquestrador_botcity import (
    AdaptadorOrquestradorBotCity,
)
from src.bots.bot_classificacao_ml import (
    ConfiguracaoClassificacaoML,
    ResultadoClassificacaoML,
    executar_bot_classificacao_ml,
)
from src.maestro_artifacts import (
    baixar_artefato,
    publicar_artefato,
)
from src.maestro_client import (
    criar_cliente_maestro_runner,
)
from src.orquestracao_capstone import (
    ServicoOrquestracaoCapstone,
)
from src.wait_for_predecessor import (
    wait_for_predecessor,
)


LOGGER = logging.getLogger("botcity_permorfer")

NOME_ARTEFATO_CONSOLIDACAO = (
    "registros_consolidados.json"
)

NOME_ARTEFATO_CLASSIFICACAO = (
    "registros_classificados.json"
)


def _texto_obrigatorio(
    parametros: dict[str, object],
    nome: str,
) -> str:
    """Lê um parâmetro obrigatório do Maestro."""

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


def _texto_opcional(
    parametros: dict[str, object],
    nome: str,
    padrao: str,
) -> str:
    """Lê um parâmetro opcional."""

    valor = parametros.get(nome)

    if valor is None:
        return padrao

    texto = str(valor).strip()

    return texto or padrao


def _decimal_ambiente(
    nome: str,
    padrao: float,
) -> float:
    """Lê um valor decimal do ambiente."""

    valor = os.getenv(nome)

    if valor is None or not valor.strip():
        return padrao

    try:
        return float(valor)
    except ValueError as erro:
        raise ValueError(
            f"{nome} deve possuir um valor numérico"
        ) from erro


def criar_configuracao_classificacao(
    task_id: str,
) -> ConfiguracaoClassificacaoML:
    """Cria a saída isolada da tarefa atual."""

    diretorio_saida = Path(
        os.getenv(
            "CLASSIFICACAO_OUTPUT_DIR",
            "data/output",
        )
    )

    return ConfiguracaoClassificacaoML(
        caminho_artefato=(
            diretorio_saida
            / f"registros_classificados_{task_id}.json"
        )
    )


def _criar_servico_orquestracao(
    maestro: Any,
) -> ServicoOrquestracaoCapstone:
    """Cria o serviço responsável por agendar o Bot F."""

    porta = (
        AdaptadorOrquestradorBotCity
        .de_ambiente(
            maestro=maestro,
        )
    )

    return ServicoOrquestracaoCapstone(
        porta,
    )


def executar_tarefa_bot_e_capstone(
    *,
    maestro: Any = None,
    executor_classificacao: (
        Callable[..., ResultadoClassificacaoML]
        | None
    ) = None,
    classificador: Any = None,
    servico_orquestracao: Any = None,
    esperar_predecessor: (
        Callable[..., Any] | None
    ) = None,
    baixar: Callable[..., Path] | None = None,
    configuracao: (
        ConfiguracaoClassificacaoML | None
    ) = None,
    logger: logging.Logger | None = None,
) -> int:
    """Executa o Bot E e agenda o Bot F."""

    load_dotenv()

    logger = logger or LOGGER

    if maestro is None:
        maestro = criar_cliente_maestro_runner()

    execucao = maestro.get_execution()

    task_id = str(execucao.task_id)

    parametros = dict(
        execucao.parameters or {}
    )

    executor = (
        executor_classificacao
        if executor_classificacao is not None
        else executar_bot_classificacao_ml
    )

    esperar = (
        esperar_predecessor
        if esperar_predecessor is not None
        else wait_for_predecessor
    )

    funcao_download = (
        baixar
        if baixar is not None
        else baixar_artefato
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

        predecessor_task_id = (
            _texto_obrigatorio(
                parametros,
                "predecessor_task_id",
            )
        )

        consolidacao_task_id = (
            _texto_obrigatorio(
                parametros,
                "consolidacao_task_id",
            )
        )

        consolidacao_artefato = (
            _texto_opcional(
                parametros,
                "consolidacao_artefato",
                NOME_ARTEFATO_CONSOLIDACAO,
            )
        )

        timeout_seconds = (
            _decimal_ambiente(
                "CAPSTONE_DEPENDENCY_TIMEOUT_SECONDS",
                300.0,
            )
        )

        poll_seconds = (
            _decimal_ambiente(
                "CAPSTONE_DEPENDENCY_POLL_SECONDS",
                5.0,
            )
        )

        logger.info(
            "bot_e_maestro_iniciado",
            extra={
                "evento": (
                    "bot_e_maestro_iniciado"
                ),
                "bot_id": (
                    "bot-e-classificacao-ml"
                ),
                "task_id": task_id,
                "execution_id": execution_id,
                "correlation_id": (
                    correlation_id
                ),
                "predecessor_task_id": (
                    predecessor_task_id
                ),
                "consolidacao_task_id": (
                    consolidacao_task_id
                ),
            },
        )

        esperar(
            maestro,
            predecessor_task_id,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=(
                poll_seconds
            ),
            logger=logger,
        )

        diretorio_download = (
            Path(
                os.getenv(
                    "CAPSTONE_DOWNLOAD_DIR",
                    "data/downloads",
                )
            )
            / task_id
        )

        caminho_consolidacao = (
            funcao_download(
                maestro,
                task_id_origem=(
                    consolidacao_task_id
                ),
                nome_artefato=(
                    consolidacao_artefato
                ),
                destino=(
                    diretorio_download
                    / NOME_ARTEFATO_CONSOLIDACAO
                ),
            )
        )

        configuracao_execucao = (
            configuracao
            if configuracao is not None
            else criar_configuracao_classificacao(
                task_id
            )
        )

        resultado = executor(
            caminho_consolidacao=(
                caminho_consolidacao
            ),
            execution_id=execution_id,
            correlation_id=correlation_id,
            task_id=task_id,
            predecessor_task_id=(
                predecessor_task_id
            ),
            configuracao=(
                configuracao_execucao
            ),
            classificador=classificador,
            logger=logger,
        )

        publicar_artefato(
            maestro,
            task_id=task_id,
            caminho=(
                resultado.caminho_artefato
            ),
            nome_artefato=(
                NOME_ARTEFATO_CLASSIFICACAO
            ),
        )

        if not resultado.sucesso:
            maestro.finish_task(
                task_id=task_id,
                status=(
                    AutomationTaskFinishStatus
                    .FAILED
                ),
                message=(
                    "Bot E não conseguiu "
                    "classificar os registros: "
                    f"{resultado.erro}"
                ),
                total_items=1,
                processed_items=0,
                failed_items=1,
            )

            return 1

        servico = (
            servico_orquestracao
            if servico_orquestracao is not None
            else _criar_servico_orquestracao(
                maestro
            )
        )

        tarefa_bot_f = (
            servico.agendar_relatorio(
                predecessor_task_id=task_id,
                resultado_predecessor=(
                    resultado.estado.value
                ),
                execution_id=execution_id,
                correlation_id=(
                    correlation_id
                ),
                classificacao_task_id=task_id,
                classificacao_artefato=(
                    NOME_ARTEFATO_CLASSIFICACAO
                ),
            )
        )

        task_id_bot_f = str(
            tarefa_bot_f.task_id
        )

        logger.info(
            "bot_e_agendou_bot_f",
            extra={
                "evento": (
                    "bot_e_agendou_bot_f"
                ),
                "bot_id": (
                    "bot-e-classificacao-ml"
                ),
                "task_id": task_id,
                "task_id_sucessor": (
                    task_id_bot_f
                ),
                "execution_id": execution_id,
                "correlation_id": (
                    correlation_id
                ),
                "estado": (
                    resultado.estado.value
                ),
                "total_registros": (
                    resultado.total_registros
                ),
                "total_ml": (
                    resultado.total_ml
                ),
                "total_fallback": (
                    resultado.total_fallback
                ),
            },
        )

        mensagem = (
            "Bot E concluído. "
            f"{resultado.total_registros} "
            "registro(s) classificado(s). "
            f"ML: {resultado.total_ml}. "
            f"Fallback: {resultado.total_fallback}. "
            "Bot F agendado."
        )

        maestro.finish_task(
            task_id=task_id,
            status=(
                AutomationTaskFinishStatus.SUCCESS
            ),
            message=mensagem,
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
            "bot_e_maestro_falhou",
            extra={
                "evento": (
                    "bot_e_maestro_falhou"
                ),
                "bot_id": (
                    "bot-e-classificacao-ml"
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
                f"Falha no Bot E: {erro}"
            ),
            total_items=1,
            processed_items=0,
            failed_items=1,
        )

        return 1


def main() -> int:
    """Executa o Bot E pelo Runner do Maestro."""

    return executar_tarefa_bot_e_capstone()


if __name__ == "__main__":
    raise SystemExit(main())