"""Acesso resiliente à base de referência, infraestrutura crítica."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
import os
from time import sleep
from typing import Callable, Collection


LOGGER = logging.getLogger("botcity_permorfer")


class StatusBaseReferencia(str, Enum):
    """Resultado seguro da consulta à infraestrutura crítica."""

    DISPONIVEL = "DISPONIVEL"
    PENDENTE_REVISAO = "PENDENTE_REVISAO"


@dataclass(frozen=True)
class ConfiguracaoRetryBase:
    """Parâmetros do retry linear da base de referência."""

    max_tentativas: int = 3
    backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.max_tentativas < 1:
            raise ValueError("max_tentativas deve ser maior ou igual a 1")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds não pode ser negativo")

    @classmethod
    def de_ambiente(cls) -> "ConfiguracaoRetryBase":
        """Carrega a configuração sem compartilhar flags do componente ML."""

        try:
            max_tentativas = int(
                os.getenv("BASE_REFERENCIA_MAX_TENTATIVAS", "3")
            )
        except ValueError as erro:
            raise ValueError(
                "BASE_REFERENCIA_MAX_TENTATIVAS deve ser um inteiro"
            ) from erro
        try:
            backoff = float(
                os.getenv("BASE_REFERENCIA_BACKOFF_SECONDS", "1")
            )
        except ValueError as erro:
            raise ValueError(
                "BASE_REFERENCIA_BACKOFF_SECONDS deve ser numérico"
            ) from erro
        return cls(
            max_tentativas=max_tentativas,
            backoff_seconds=backoff,
        )


@dataclass(frozen=True)
class ResultadoConsultaBase:
    """Resultado controlado que nunca confunde infraestrutura com ML."""

    status: StatusBaseReferencia
    lotes: frozenset[str]
    tentativas: int
    erro: str | None = None

    @property
    def sucesso(self) -> bool:
        return self.status is StatusBaseReferencia.DISPONIVEL


def consultar_base_com_retry(
    consulta: Callable[[], Collection[str]],
    *,
    configuracao: ConfiguracaoRetryBase | None = None,
    sleeper: Callable[[float], None] = sleep,
    logger: logging.Logger | None = None,
) -> ResultadoConsultaBase:
    """Consulta a base com backoff linear e degrada sem lançar exceção.

    O intervalo antes da tentativa N é ``backoff_seconds * (N - 1)``.
    Falhas persistentes retornam ``PENDENTE_REVISAO``; não são tratadas
    pelo classificador nem pelo fallback opcional de ML.
    """

    configuracao = configuracao or ConfiguracaoRetryBase.de_ambiente()
    logger = logger or LOGGER
    ultimo_erro: Exception | None = None

    for tentativa in range(1, configuracao.max_tentativas + 1):
        try:
            lotes = frozenset(consulta())
            logger.info(
                "base_referencia_consulta_sucesso",
                extra={
                    "evento": "base_referencia_consulta_sucesso",
                    "tentativa": tentativa,
                    "max_tentativas": configuracao.max_tentativas,
                },
            )
            return ResultadoConsultaBase(
                status=StatusBaseReferencia.DISPONIVEL,
                lotes=lotes,
                tentativas=tentativa,
            )
        except Exception as erro:
            ultimo_erro = erro
            logger.warning(
                "base_referencia_tentativa_falhou",
                extra={
                    "evento": "base_referencia_tentativa_falhou",
                    "tentativa": tentativa,
                    "max_tentativas": configuracao.max_tentativas,
                    "erro": str(erro),
                },
            )
            if tentativa < configuracao.max_tentativas:
                atraso = configuracao.backoff_seconds * tentativa
                logger.info(
                    "base_referencia_retry_agendado",
                    extra={
                        "evento": "base_referencia_retry_agendado",
                        "tentativa_atual": tentativa,
                        "proxima_tentativa": tentativa + 1,
                        "backoff_seconds": atraso,
                    },
                )
                sleeper(atraso)

    erro_final = str(ultimo_erro) if ultimo_erro else "erro desconhecido"
    logger.error(
        "infraestrutura_degradada",
        extra={
            "evento": "infraestrutura_degradada",
            "componente": "base_referencia",
            "tentativas": configuracao.max_tentativas,
            "status_fallback": StatusBaseReferencia.PENDENTE_REVISAO.value,
            "erro": erro_final,
        },
    )
    return ResultadoConsultaBase(
        status=StatusBaseReferencia.PENDENTE_REVISAO,
        lotes=frozenset(),
        tentativas=configuracao.max_tentativas,
        erro=erro_final,
    )
