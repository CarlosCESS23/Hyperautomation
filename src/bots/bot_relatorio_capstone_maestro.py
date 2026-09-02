"""Executor Maestro do Bot F: relatório e encerramento do Capstone."""

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

from src.bots.bot_relatorio_capstone import (
    ConfiguracaoRelatorioCapstone,
    ResultadoRelatorioCapstone,
    executar_bot_relatorio_capstone,
)
from src.maestro_artifacts import (
    baixar_artefato,
    publicar_artefato,
)
from src.maestro_client import (
    criar_cliente_maestro_runner,
)
from src.sistema_alertas import (
    SistemaAlertas,
)
from src.wait_for_predecessor import (
    wait_for_predecessor,
)


LOGGER = logging.getLogger("botcity_permorfer")

NOME_ARTEFATO_CLASSIFICACAO = (
    "registros_classificados.json"
)

NOME_ARTEFATO_EXCEL = (
    "relatorio_capstone.xlsx"
)

NOME_ARTEFATO_MARKDOWN = (
    "resumo_capstone.md"
)


@dataclass(frozen=True)
class ResultadoAlertaIndisponivel:
    """Resultado usado quando os canais não podem ser configurados."""

    sucesso: bool = False
    canal: str = "nenhum"
    erro: str = (
        "sistema de alertas não configurado"
    )


class SistemaAlertasIndisponivel:
    """Mantém a falha de configuração controlada."""

    def __init__(
        self,
        erro: str,
    ) -> None:
        self._erro = erro

    def enviar_alerta(
        self,
        *,
        severidade: str,
        mensagem: str,
        anexo: Path | None = None,
        contexto: dict[str, Any] | None = None,
    ) -> ResultadoAlertaIndisponivel:
        del severidade
        del mensagem
        del anexo
        del contexto

        return ResultadoAlertaIndisponivel(
            erro=self._erro,
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


def criar_configuracao_relatorio(
    task_id: str,
) -> ConfiguracaoRelatorioCapstone:
    """Cria os caminhos de saída do Bot F."""

    diretorio_relatorios = Path(
        os.getenv(
            "CAPSTONE_REPORTS_DIR",
            "reports",
        )
    )

    return ConfiguracaoRelatorioCapstone(
        caminho_excel=(
            diretorio_relatorios
            / f"relatorio_capstone_{task_id}.xlsx"
        ),
        caminho_markdown=(
            diretorio_relatorios
            / f"resumo_capstone_{task_id}.md"
        ),
    )


def criar_sistema_alertas_seguro(
    *,
    logger: logging.Logger,
):
    """Cria Telegram/Email sem deixar configuração inválida derrubar o bot."""

    alertas_habilitados = (
        _booleano_ambiente(
            "CAPSTONE_ALERTAS_ENABLED",
            True,
        )
    )

    if not alertas_habilitados:
        logger.info(
            "alertas_capstone_desativados",
            extra={
                "evento": (
                    "alertas_capstone_desativados"
                ),
                "bot_id": (
                    "bot-f-relatorio"
                ),
            },
        )

        return None

    try:
        return SistemaAlertas.de_ambiente(
            logger=logger,
        )

    except Exception as erro:
        logger.exception(
            "configuracao_alertas_capstone_falhou",
            extra={
                "evento": (
                    "configuracao_alertas_capstone_falhou"
                ),
                "bot_id": (
                    "bot-f-relatorio"
                ),
                "erro": str(erro),
            },
        )

        return SistemaAlertasIndisponivel(
            str(erro)
        )


def executar_tarefa_bot_f_capstone(
    *,
    maestro: Any = None,
    executor_relatorio: (
        Callable[..., ResultadoRelatorioCapstone]
        | None
    ) = None,
    sistema_alertas: Any = None,
    esperar_predecessor: (
        Callable[..., Any] | None
    ) = None,
    baixar: Callable[..., Path] | None = None,
    configuracao: (
        ConfiguracaoRelatorioCapstone | None
    ) = None,
    logger: logging.Logger | None = None,
) -> int:
    """Executa o relatório e encerra a cadeia de seis bots."""

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
        executor_relatorio
        if executor_relatorio is not None
        else executar_bot_relatorio_capstone
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

        classificacao_task_id = (
            _texto_obrigatorio(
                parametros,
                "classificacao_task_id",
            )
        )

        classificacao_artefato = (
            _texto_opcional(
                parametros,
                "classificacao_artefato",
                NOME_ARTEFATO_CLASSIFICACAO,
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
            "bot_f_maestro_iniciado",
            extra={
                "evento": (
                    "bot_f_maestro_iniciado"
                ),
                "bot_id": (
                    "bot-f-relatorio"
                ),
                "task_id": task_id,
                "execution_id": execution_id,
                "correlation_id": (
                    correlation_id
                ),
                "predecessor_task_id": (
                    predecessor_task_id
                ),
                "classificacao_task_id": (
                    classificacao_task_id
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

        caminho_classificacao = (
            funcao_download(
                maestro,
                task_id_origem=(
                    classificacao_task_id
                ),
                nome_artefato=(
                    classificacao_artefato
                ),
                destino=(
                    diretorio_download
                    / NOME_ARTEFATO_CLASSIFICACAO
                ),
            )
        )

        configuracao_execucao = (
            configuracao
            if configuracao is not None
            else criar_configuracao_relatorio(
                task_id
            )
        )

        alertas_execucao = (
            sistema_alertas
            if sistema_alertas is not None
            else criar_sistema_alertas_seguro(
                logger=logger
            )
        )

        resultado = executor(
            caminho_classificacao=(
                caminho_classificacao
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
            sistema_alertas=(
                alertas_execucao
            ),
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
                    "Bot F não conseguiu gerar "
                    f"o relatório: {resultado.erro}"
                ),
                total_items=1,
                processed_items=0,
                failed_items=1,
            )

            return 1

        if resultado.caminho_excel is None:
            raise RuntimeError(
                "Bot F terminou sem o "
                "relatório Excel"
            )

        if resultado.caminho_markdown is None:
            raise RuntimeError(
                "Bot F terminou sem o "
                "resumo Markdown"
            )

        publicar_artefato(
            maestro,
            task_id=task_id,
            caminho=(
                resultado.caminho_excel
            ),
            nome_artefato=(
                NOME_ARTEFATO_EXCEL
            ),
        )

        publicar_artefato(
            maestro,
            task_id=task_id,
            caminho=(
                resultado.caminho_markdown
            ),
            nome_artefato=(
                NOME_ARTEFATO_MARKDOWN
            ),
        )

        logger.info(
            "pipeline_capstone_finalizado",
            extra={
                "evento": (
                    "pipeline_capstone_finalizado"
                ),
                "bot_id": (
                    "bot-f-relatorio"
                ),
                "task_id": task_id,
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
                "alerta_enviado": (
                    resultado.alerta_enviado
                ),
                "severidade_alerta": (
                    resultado.severidade_alerta
                ),
                "erro_alerta": (
                    resultado.erro_alerta
                ),
                "relatorio_excel": (
                    str(
                        resultado
                        .caminho_excel
                    )
                ),
                "resumo_markdown": (
                    str(
                        resultado
                        .caminho_markdown
                    )
                ),
            },
        )

        mensagem = (
            "Pipeline Capstone concluído. "
            f"{resultado.total_registros} "
            "registro(s) incluído(s) no relatório."
        )

        if resultado.alerta_enviado:
            mensagem += (
                " Alerta entregue."
            )

        elif alertas_execucao is None:
            mensagem += (
                " Alertas desativados."
            )

        else:
            mensagem += (
                " Relatório concluído, mas o "
                "alerta não foi entregue."
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
            "bot_f_maestro_falhou",
            extra={
                "evento": (
                    "bot_f_maestro_falhou"
                ),
                "bot_id": (
                    "bot-f-relatorio"
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
                f"Falha no Bot F: {erro}"
            ),
            total_items=1,
            processed_items=0,
            failed_items=1,
        )

        return 1


def main() -> int:
    """Executa o Bot F pelo Runner do Maestro."""

    return executar_tarefa_bot_f_capstone()


if __name__ == "__main__":
    raise SystemExit(main())