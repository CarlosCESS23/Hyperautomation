"""Executor Maestro do Bot D: consolidação das fontes desktop e web."""

from __future__ import annotations

from dataclasses import dataclass
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
from src.bots.bot_consolidacao import (
    ConfiguracaoConsolidacao,
    ResultadoConsolidacao,
    executar_bot_consolidacao,
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
    DependenciaFalhouError,
    TimeoutDependenciaError,
    wait_for_predecessor,
)


LOGGER = logging.getLogger("botcity_permorfer")

NOME_ARTEFATO_ESTOQUE = (
    "estoque_desktop.json"
)

NOME_ARTEFATO_PEDIDOS = (
    "pedidos_fornecedores.json"
)

NOME_ARTEFATO_CONSOLIDACAO = (
    "registros_consolidados.json"
)


@dataclass(frozen=True)
class ResultadoDownloadFonte:
    """Resultado da espera e download de uma fonte."""

    task_id: str
    nome_artefato: str
    caminho: Path | None
    erro: str | None = None


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


def _texto_opcional(
    parametros: dict[str, object],
    nome: str,
    padrao: str,
) -> str:
    """Lê um parâmetro opcional com valor padrão."""

    valor = parametros.get(nome)

    if valor is None:
        return padrao

    texto = str(valor).strip()

    return texto or padrao


def _decimal_ambiente(
    nome: str,
    padrao: float,
) -> float:
    """Lê uma configuração decimal do ambiente."""

    valor = os.getenv(nome)

    if valor is None or not valor.strip():
        return padrao

    try:
        return float(valor)
    except ValueError as erro:
        raise ValueError(
            f"{nome} deve possuir um valor numérico"
        ) from erro


def criar_configuracao_consolidacao(
    task_id: str,
) -> ConfiguracaoConsolidacao:
    """Cria uma saída isolada para a tarefa atual."""

    diretorio_saida = Path(
        os.getenv(
            "CONSOLIDACAO_OUTPUT_DIR",
            "data/output",
        )
    )

    return ConfiguracaoConsolidacao(
        caminho_artefato=(
            diretorio_saida
            / f"registros_consolidados_{task_id}.json"
        )
    )


def _criar_servico_orquestracao(
    maestro: Any,
) -> ServicoOrquestracaoCapstone:
    """Cria o serviço que agenda o Bot E."""

    porta = (
        AdaptadorOrquestradorBotCity
        .de_ambiente(
            maestro=maestro,
        )
    )

    return ServicoOrquestracaoCapstone(
        porta,
    )


def _aguardar_e_baixar_fonte(
    *,
    maestro: Any,
    task_id_origem: str,
    nome_artefato: str,
    destino: Path,
    timeout_seconds: float,
    poll_interval_seconds: float,
    esperar_predecessor: Callable[..., Any],
    baixar: Callable[..., Path],
    logger: logging.Logger,
) -> ResultadoDownloadFonte:
    """
    Aguarda uma fonte e tenta baixar seu artefato.

    Mesmo quando a tarefa termina com falha, tentamos baixar
    o JSON de falha produzido pelo Bot B ou pelo Bot C.
    """

    erro_dependencia: str | None = None

    try:
        esperar_predecessor(
            maestro,
            task_id_origem,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=(
                poll_interval_seconds
            ),
            logger=logger,
        )

    except DependenciaFalhouError as erro:
        erro_dependencia = str(erro)

        logger.warning(
            "fonte_capstone_falhou",
            extra={
                "evento": (
                    "fonte_capstone_falhou"
                ),
                "predecessor_task_id": (
                    task_id_origem
                ),
                "nome_artefato": (
                    nome_artefato
                ),
                "erro": erro_dependencia,
            },
        )

    except TimeoutDependenciaError as erro:
        erro_dependencia = str(erro)

        logger.warning(
            "fonte_capstone_timeout",
            extra={
                "evento": (
                    "fonte_capstone_timeout"
                ),
                "predecessor_task_id": (
                    task_id_origem
                ),
                "nome_artefato": (
                    nome_artefato
                ),
                "erro": erro_dependencia,
            },
        )

    try:
        caminho = baixar(
            maestro,
            task_id_origem=task_id_origem,
            nome_artefato=nome_artefato,
            destino=destino,
        )

        logger.info(
            "fonte_capstone_baixada",
            extra={
                "evento": (
                    "fonte_capstone_baixada"
                ),
                "predecessor_task_id": (
                    task_id_origem
                ),
                "nome_artefato": (
                    nome_artefato
                ),
                "caminho": str(caminho),
                "dependencia_com_erro": (
                    erro_dependencia is not None
                ),
            },
        )

        return ResultadoDownloadFonte(
            task_id=task_id_origem,
            nome_artefato=nome_artefato,
            caminho=caminho,
            erro=erro_dependencia,
        )

    except Exception as erro_download:
        mensagens = [
            mensagem
            for mensagem in (
                erro_dependencia,
                str(erro_download),
            )
            if mensagem
        ]

        erro_final = " | ".join(
            mensagens
        )

        logger.warning(
            "fonte_capstone_indisponivel",
            extra={
                "evento": (
                    "fonte_capstone_indisponivel"
                ),
                "predecessor_task_id": (
                    task_id_origem
                ),
                "nome_artefato": (
                    nome_artefato
                ),
                "erro": erro_final,
            },
        )

        return ResultadoDownloadFonte(
            task_id=task_id_origem,
            nome_artefato=nome_artefato,
            caminho=None,
            erro=erro_final,
        )


def executar_tarefa_bot_d_capstone(
    *,
    maestro: Any = None,
    executor_consolidacao: (
        Callable[..., ResultadoConsolidacao]
        | None
    ) = None,
    servico_orquestracao: Any = None,
    esperar_predecessor: (
        Callable[..., Any] | None
    ) = None,
    baixar: Callable[..., Path] | None = None,
    configuracao: (
        ConfiguracaoConsolidacao | None
    ) = None,
    logger: logging.Logger | None = None,
) -> int:
    """Executa o fan-in dos Bots B e C dentro do Maestro."""

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
        executor_consolidacao
        if executor_consolidacao is not None
        else executar_bot_consolidacao
    )

    funcao_espera = (
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

        desktop_task_id = _texto_obrigatorio(
            parametros,
            "desktop_task_id",
        )

        web_task_id = _texto_obrigatorio(
            parametros,
            "web_task_id",
        )

        desktop_artefato = _texto_opcional(
            parametros,
            "desktop_artefato",
            NOME_ARTEFATO_ESTOQUE,
        )

        web_artefato = _texto_opcional(
            parametros,
            "web_artefato",
            NOME_ARTEFATO_PEDIDOS,
        )

        timeout_seconds = (
            _decimal_ambiente(
                "CAPSTONE_DEPENDENCY_TIMEOUT_SECONDS",
                300.0,
            )
        )

        poll_interval_seconds = (
            _decimal_ambiente(
                "CAPSTONE_DEPENDENCY_POLL_SECONDS",
                5.0,
            )
        )

        diretorio_download = Path(
            os.getenv(
                "CAPSTONE_DOWNLOAD_DIR",
                "data/downloads",
            )
        ) / task_id

        logger.info(
            "bot_d_maestro_iniciado",
            extra={
                "evento": (
                    "bot_d_maestro_iniciado"
                ),
                "bot_id": (
                    "bot-d-consolidacao"
                ),
                "task_id": task_id,
                "execution_id": execution_id,
                "correlation_id": (
                    correlation_id
                ),
                "desktop_task_id": (
                    desktop_task_id
                ),
                "web_task_id": web_task_id,
            },
        )

        fonte_desktop = (
            _aguardar_e_baixar_fonte(
                maestro=maestro,
                task_id_origem=(
                    desktop_task_id
                ),
                nome_artefato=(
                    desktop_artefato
                ),
                destino=(
                    diretorio_download
                    / NOME_ARTEFATO_ESTOQUE
                ),
                timeout_seconds=(
                    timeout_seconds
                ),
                poll_interval_seconds=(
                    poll_interval_seconds
                ),
                esperar_predecessor=(
                    funcao_espera
                ),
                baixar=funcao_download,
                logger=logger,
            )
        )

        fonte_web = (
            _aguardar_e_baixar_fonte(
                maestro=maestro,
                task_id_origem=(
                    web_task_id
                ),
                nome_artefato=(
                    web_artefato
                ),
                destino=(
                    diretorio_download
                    / NOME_ARTEFATO_PEDIDOS
                ),
                timeout_seconds=(
                    timeout_seconds
                ),
                poll_interval_seconds=(
                    poll_interval_seconds
                ),
                esperar_predecessor=(
                    funcao_espera
                ),
                baixar=funcao_download,
                logger=logger,
            )
        )

        configuracao_execucao = (
            configuracao
            if configuracao is not None
            else criar_configuracao_consolidacao(
                task_id
            )
        )

        resultado = executor(
            caminho_estoque=(
                fonte_desktop.caminho
            ),
            caminho_pedidos=(
                fonte_web.caminho
            ),
            execution_id=execution_id,
            correlation_id=correlation_id,
            task_id=task_id,
            predecessor_task_ids=(
                desktop_task_id,
                web_task_id,
            ),
            configuracao=(
                configuracao_execucao
            ),
            logger=logger,
        )

        publicar_artefato(
            maestro,
            task_id=task_id,
            caminho=(
                resultado.caminho_artefato
            ),
            nome_artefato=(
                NOME_ARTEFATO_CONSOLIDACAO
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
                    "Bot D não encontrou uma "
                    "fonte válida para consolidação."
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

        tarefa_bot_e = (
            servico.agendar_classificacao_ml(
                predecessor_task_id=task_id,
                resultado_predecessor=(
                    resultado.estado.value
                ),
                execution_id=execution_id,
                correlation_id=(
                    correlation_id
                ),
                consolidacao_task_id=task_id,
                consolidacao_artefato=(
                    NOME_ARTEFATO_CONSOLIDACAO
                ),
            )
        )

        task_id_bot_e = str(
            tarefa_bot_e.task_id
        )

        logger.info(
            "bot_d_agendou_bot_e",
            extra={
                "evento": (
                    "bot_d_agendou_bot_e"
                ),
                "bot_id": (
                    "bot-d-consolidacao"
                ),
                "task_id": task_id,
                "task_id_sucessor": (
                    task_id_bot_e
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
                "fontes_disponiveis": [
                    fonte.value
                    for fonte
                    in resultado.fontes_disponiveis
                ],
            },
        )

        mensagem = (
            "Bot D concluído. "
            f"{resultado.total_registros} "
            "registro(s) consolidado(s). "
            "Bot E agendado."
        )

        if (
            resultado.estado.value
            == "CONCLUIDO_DEGRADADO"
        ):
            mensagem = (
                "Bot D concluído em modo "
                "degradado. "
                f"{resultado.total_registros} "
                "registro(s) consolidado(s). "
                "Bot E agendado."
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
            "bot_d_maestro_falhou",
            extra={
                "evento": (
                    "bot_d_maestro_falhou"
                ),
                "bot_id": (
                    "bot-d-consolidacao"
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
                f"Falha no Bot D: {erro}"
            ),
            total_items=1,
            processed_items=0,
            failed_items=1,
        )

        return 1


def main() -> int:
    """Executa o Bot D pelo Runner do Maestro."""

    return executar_tarefa_bot_d_capstone()


if __name__ == "__main__":
    raise SystemExit(main())