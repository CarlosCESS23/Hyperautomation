"""Contratos e canal principal do sistema de alertas."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
import os
from pathlib import Path
from typing import Any, Mapping, Protocol


LOGGER = logging.getLogger("botcity_permorfer")


class Severidade(str, Enum):
    INFO = "INFO"
    AVISO = "AVISO"
    ERRO = "ERRO"
    CRITICO = "CRITICO"


@dataclass(frozen=True)
class Alerta:
    """Evento independente do canal usado para entregá-lo."""

    severidade: Severidade
    mensagem: str
    contexto: Mapping[str, Any] = field(default_factory=dict)
    anexo: Path | None = None

    def __post_init__(self) -> None:
        if not self.mensagem.strip():
            raise ValueError("mensagem do alerta é obrigatória")


@dataclass(frozen=True)
class ResultadoAlerta:
    sucesso: bool
    canal: str
    erro: str | None = None
    message_id: str | None = None


class CanalAlerta(Protocol):
    nome: str

    def enviar(self, alerta: Alerta) -> ResultadoAlerta:
        """Entrega um evento e sempre devolve resultado controlado."""


class ClienteHTTP(Protocol):
    def post(
        self,
        url: str,
        *,
        json: Mapping[str, Any],
        timeout: float,
    ) -> Any:
        """Contrato mínimo compatível com httpx e clientes simulados."""


@dataclass(frozen=True)
class ConfiguracaoTelegram:
    token: str
    chat_id: str
    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if not self.token.strip():
            raise ValueError("TELEGRAM_BOT_TOKEN não configurado")
        if not self.chat_id.strip():
            raise ValueError("TELEGRAM_CHAT_ID não configurado")
        if self.timeout_seconds <= 0:
            raise ValueError("TELEGRAM_TIMEOUT_SECONDS deve ser positivo")

    @classmethod
    def de_ambiente(cls) -> "ConfiguracaoTelegram":
        try:
            timeout = float(os.getenv("TELEGRAM_TIMEOUT_SECONDS", "5"))
        except ValueError as erro:
            raise ValueError(
                "TELEGRAM_TIMEOUT_SECONDS deve ser numérico"
            ) from erro
        return cls(
            token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            timeout_seconds=timeout,
        )


class AdaptadorTelegram:
    """Canal principal do pipeline usando a API Bot do Telegram."""

    nome = "telegram"

    def __init__(
        self,
        configuracao: ConfiguracaoTelegram,
        *,
        cliente: ClienteHTTP | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._configuracao = configuracao
        self._cliente = cliente or _cliente_http_padrao()
        self._logger = logger or LOGGER

    @classmethod
    def de_ambiente(
        cls,
        *,
        cliente: ClienteHTTP | None = None,
        logger: logging.Logger | None = None,
    ) -> "AdaptadorTelegram":
        return cls(
            ConfiguracaoTelegram.de_ambiente(),
            cliente=cliente,
            logger=logger,
        )

    def enviar(self, alerta: Alerta) -> ResultadoAlerta:
        texto = f"[{alerta.severidade.value}] {alerta.mensagem}"
        url = (
            "https://api.telegram.org/bot"
            f"{self._configuracao.token}/sendMessage"
        )
        try:
            resposta = self._cliente.post(
                url,
                json={
                    "chat_id": self._configuracao.chat_id,
                    "text": texto,
                },
                timeout=self._configuracao.timeout_seconds,
            )
            resposta.raise_for_status()
            corpo = resposta.json()
            if not isinstance(corpo, Mapping) or corpo.get("ok") is not True:
                raise RuntimeError("resposta não confirmada pelo Telegram")
            message_id = _message_id(corpo)
        except Exception as erro:
            erro_seguro = _ocultar_credencial(
                str(erro),
                self._configuracao.token,
            )
            self._logger.error(
                "alerta_telegram_falhou",
                extra={
                    "evento": "alerta_telegram_falhou",
                    "canal": self.nome,
                    "severidade": alerta.severidade.value,
                    "erro": erro_seguro,
                },
            )
            return ResultadoAlerta(
                sucesso=False,
                canal=self.nome,
                erro=erro_seguro,
            )

        self._logger.info(
            "alerta_telegram_enviado",
            extra={
                "evento": "alerta_telegram_enviado",
                "canal": self.nome,
                "severidade": alerta.severidade.value,
                "message_id": message_id,
            },
        )
        return ResultadoAlerta(
            sucesso=True,
            canal=self.nome,
            message_id=message_id,
        )


class SistemaAlertas:
    """Fachada de alertas com Telegram como canal principal."""

    def __init__(self, canal_principal: CanalAlerta) -> None:
        self._canal_principal = canal_principal

    @classmethod
    def de_ambiente(
        cls,
        *,
        cliente_telegram: ClienteHTTP | None = None,
        logger: logging.Logger | None = None,
    ) -> "SistemaAlertas":
        return cls(
            AdaptadorTelegram.de_ambiente(
                cliente=cliente_telegram,
                logger=logger,
            )
        )

    def enviar(self, alerta: Alerta) -> ResultadoAlerta:
        return self._canal_principal.enviar(alerta)

    def enviar_alerta(
        self,
        *,
        severidade: Severidade | str,
        mensagem: str,
        anexo: Path | None = None,
        contexto: Mapping[str, Any] | None = None,
    ) -> ResultadoAlerta:
        if isinstance(severidade, str):
            try:
                severidade = Severidade(severidade.strip().upper())
            except ValueError as erro:
                return ResultadoAlerta(
                    sucesso=False,
                    canal=self._canal_principal.nome,
                    erro=f"severidade inválida: {severidade}",
                )
        return self.enviar(
            Alerta(
                severidade=severidade,
                mensagem=mensagem,
                anexo=anexo,
                contexto=contexto or {},
            )
        )


def _cliente_http_padrao() -> ClienteHTTP:
    import httpx

    return httpx


def _message_id(corpo: Mapping[str, Any]) -> str | None:
    resultado = corpo.get("result")
    if not isinstance(resultado, Mapping):
        return None
    valor = resultado.get("message_id")
    return str(valor) if valor is not None else None


def _ocultar_credencial(mensagem: str, token: str) -> str:
    return mensagem.replace(token, "***") if token else mensagem
