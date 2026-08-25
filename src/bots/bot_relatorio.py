"""Bot C: consolida os resultados do Bot B e encerra a cadeia."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
import json
import logging
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from gerar_relatorio import gerar_excel
from src.alerta_pipeline_sem_ml import (
    avaliar_e_alertar_pipeline_sem_ml,
)
from src.validacao_lotes import RegistroValidado


LOGGER = logging.getLogger("botcity_permorfer")
BOT_ID = "bot-c-relatorio"


class SistemaAlertas(Protocol):
    """Contrato mínimo esperado do sistema multicanal de alertas."""

    def enviar_alerta(
        self,
        *,
        severidade: str,
        mensagem: str,
        anexo: Path,
        contexto: dict[str, Any],
    ) -> Any:
        """Envia uma notificação sobre o encerramento da cadeia."""


class StatusBotRelatorio(str, Enum):
    """Estados controlados do Bot C."""

    CONCLUIDO = "cadeia_concluida"
    CONCLUIDO_SEM_ALERTA = "cadeia_concluida_sem_alerta"
    ENTRADA_INVALIDA = "entrada_invalida"
    ERRO_RELATORIO = "erro_ao_gerar_relatorio"


@dataclass(frozen=True)
class ConsolidacaoDecisoes:
    """Contagens de rastreabilidade produzidas pelo Bot B."""

    quantidade_ml: int
    quantidade_fallback: int
    quantidade_sem_origem: int
    total_registros: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class ResultadoBotRelatorio:
    """Resultado serializável da última etapa do pipeline."""

    sucesso: bool
    status: StatusBotRelatorio
    mensagem: str
    execution_id: str
    correlation_id: str
    caminho_relatorio: str | None
    consolidacao: ConsolidacaoDecisoes
    alerta_enviado: bool
    erro_alerta: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sucesso": self.sucesso,
            "status": self.status.value,
            "mensagem": self.mensagem,
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "caminho_relatorio": self.caminho_relatorio,
            "consolidacao": self.consolidacao.to_dict(),
            "alerta_enviado": self.alerta_enviado,
            "erro_alerta": self.erro_alerta,
        }


GeradorRelatorio = Callable[
    [list[RegistroValidado], Path, datetime],
    Any,
]


def consolidar_decisoes(
    registros: Sequence[RegistroValidado],
) -> ConsolidacaoDecisoes:
    """Conta as origens decididas pelo Bot B sem recalculá-las."""

    contagens = Counter(
        (registro.origem_decisao or "").strip().lower()
        for registro in registros
    )

    return ConsolidacaoDecisoes(
        quantidade_ml=contagens["ml"],
        quantidade_fallback=contagens["fallback"],
        quantidade_sem_origem=sum(
            quantidade
            for origem, quantidade in contagens.items()
            if origem not in {"ml", "fallback"}
        ),
        total_registros=len(registros),
    )


def _gerar_relatorio_padrao(
    registros: list[RegistroValidado],
    caminho_saida: Path,
    momento: datetime,
) -> Any:
    """Utiliza o gerador real quando nenhum gerador é injetado."""

    return gerar_excel(registros, caminho_saida, momento)


def executar_bot_relatorio(
    resultados_bot_b: Sequence[RegistroValidado],
    caminho_saida: str | Path,
    *,
    execution_id: str,
    correlation_id: str,
    sistema_alertas: SistemaAlertas | None = None,
    gerador_relatorio: GeradorRelatorio | None = None,
    momento: datetime | None = None,
    logger: logging.Logger | None = None,
) -> ResultadoBotRelatorio:
    """Gera o relatório uma vez, tenta alertar e encerra a cadeia.

    Os registros recebidos já são os resultados finais do Bot B. Este bot
    não chama o classificador e não executa novamente as regras de negócio.

    Uma falha no sistema de alertas não interrompe a geração do relatório.
    """

    logger = logger or LOGGER
    gerador_relatorio = (
        gerador_relatorio or _gerar_relatorio_padrao
    )
    caminho = Path(caminho_saida)
    consolidacao = consolidar_decisoes(resultados_bot_b)

    logger.info(
        "bot_relatorio_iniciado",
        extra={
            "evento": "bot_relatorio_iniciado",
            "bot_id": BOT_ID,
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            **consolidacao.to_dict(),
        },
    )

    # Impede a execução do bot sem os identificadores de rastreabilidade.
    if not execution_id.strip() or not correlation_id.strip():
        resultado = ResultadoBotRelatorio(
            sucesso=False,
            status=StatusBotRelatorio.ENTRADA_INVALIDA,
            mensagem=(
                "execution_id e correlation_id são obrigatórios"
            ),
            execution_id=execution_id,
            correlation_id=correlation_id,
            caminho_relatorio=None,
            consolidacao=consolidacao,
            alerta_enviado=False,
        )

        logger.warning(
            "bot_relatorio_entrada_invalida",
            extra={
                "evento": "bot_relatorio_entrada_invalida",
                "bot_id": BOT_ID,
                **resultado.to_dict(),
            },
        )
        return resultado

    try:
        # Este é o único ponto em que o relatório é gerado.
        gerador_relatorio(
            list(resultados_bot_b),
            caminho,
            momento or datetime.now(),
        )
    except Exception as erro:
        resultado = ResultadoBotRelatorio(
            sucesso=False,
            status=StatusBotRelatorio.ERRO_RELATORIO,
            mensagem=f"Falha ao gerar relatório: {erro}",
            execution_id=execution_id,
            correlation_id=correlation_id,
            caminho_relatorio=None,
            consolidacao=consolidacao,
            alerta_enviado=False,
        )

        logger.exception(
            "bot_relatorio_falhou",
            extra={
                "evento": "bot_relatorio_falhou",
                "bot_id": BOT_ID,
                **resultado.to_dict(),
            },
        )
        return resultado

    alerta_enviado = False
    erro_alerta: str | None = None

    # O sistema de alertas é opcional. Quando ele não for informado,
    # o relatório continua sendo concluído normalmente.
    if sistema_alertas is not None:
        avaliar_e_alertar_pipeline_sem_ml(
            resultados_bot_b,
            sistema_alertas,
            execution_id=execution_id,
            correlation_id=correlation_id,
            logger=logger,
        )
        try:
            # Deve existir somente uma chamada a enviar_alerta.
            resultado_alerta = sistema_alertas.enviar_alerta(
                severidade="INFO",
                mensagem=(
                    "Pipeline concluído: "
                    f"{consolidacao.quantidade_ml} decisões por ML e "
                    f"{consolidacao.quantidade_fallback} por fallback."
                ),
                anexo=caminho,
                contexto={
                    "execution_id": execution_id,
                    "correlation_id": correlation_id,
                    "bot_id": BOT_ID,
                    **consolidacao.to_dict(),
                },
            )

            # ResultadoAlerta possui o atributo sucesso. O getattr também
            # mantém o Bot C compatível com canais simulados nos testes.
            alerta_enviado = bool(
                getattr(resultado_alerta, "sucesso", False)
            )

            if not alerta_enviado:
                erro_resultado = getattr(
                    resultado_alerta,
                    "erro",
                    None,
                )
                erro_alerta = (
                    str(erro_resultado)
                    if erro_resultado
                    else "O alerta não foi entregue"
                )

                logger.warning(
                    "bot_relatorio_alerta_nao_entregue",
                    extra={
                        "evento": (
                            "bot_relatorio_alerta_nao_entregue"
                        ),
                        "bot_id": BOT_ID,
                        "execution_id": execution_id,
                        "correlation_id": correlation_id,
                        "erro_alerta": erro_alerta,
                    },
                )
        except Exception as erro:
            # Uma exceção do canal não pode interromper o pipeline.
            alerta_enviado = False
            erro_alerta = str(erro)

            logger.exception(
                "bot_relatorio_alerta_falhou",
                extra={
                    "evento": "bot_relatorio_alerta_falhou",
                    "bot_id": BOT_ID,
                    "execution_id": execution_id,
                    "correlation_id": correlation_id,
                    "caminho_relatorio": str(
                        caminho.resolve()
                    ),
                },
            )

    status = (
        StatusBotRelatorio.CONCLUIDO
        if sistema_alertas is None or alerta_enviado
        else StatusBotRelatorio.CONCLUIDO_SEM_ALERTA
    )

    resultado = ResultadoBotRelatorio(
        sucesso=True,
        status=status,
        mensagem="Relatório gerado e cadeia encerrada",
        execution_id=execution_id,
        correlation_id=correlation_id,
        caminho_relatorio=str(caminho.resolve()),
        consolidacao=consolidacao,
        alerta_enviado=alerta_enviado,
        erro_alerta=erro_alerta,
    )

    logger.info(
        "cadeia_encerrada",
        extra={
            "evento": "cadeia_encerrada",
            "bot_id": BOT_ID,
            **resultado.to_dict(),
        },
    )
    return resultado


def main(argv: list[str] | None = None) -> int:
    """Exibe ajuda para a execução orquestrada do Bot C."""

    parser = argparse.ArgumentParser(
        description=(
            "Bot C: gera artefatos a partir dos resultados do Bot B"
        ),
    )
    parser.add_argument(
        "--contrato",
        action="store_true",
        help="Exibe o contrato esperado pelo Bot C em JSON",
    )
    args = parser.parse_args(argv)

    if args.contrato:
        print(
            json.dumps(
                {
                    "entrada": "Sequence[RegistroValidado]",
                    "identificadores": [
                        "execution_id",
                        "correlation_id",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())