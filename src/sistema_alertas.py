"""Sistema de alertas com Telegram principal e Email como fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from email.message import EmailMessage
from enum import Enum
import logging
import mimetypes
import os
from pathlib import Path
import smtplib
import socket
import ssl
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
class TentativaAlerta:
    """Registro seguro de uma tentativa de entrega."""

    canal: str
    sucesso: bool
    erro: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "canal": self.canal,
            "sucesso": self.sucesso,
            "erro": self.erro,
        }


@dataclass(frozen=True)
class ResultadoAlerta:
    sucesso: bool
    canal: str
    erro: str | None = None
    message_id: str | None = None
    fallback_acionado: bool = False
    tentativas: tuple[TentativaAlerta, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "sucesso": self.sucesso,
            "canal": self.canal,
            "erro": self.erro,
            "message_id": self.message_id,
            "fallback_acionado": self.fallback_acionado,
            "tentativas": [
                tentativa.to_dict()
                for tentativa in self.tentativas
            ],
        }


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
            timeout = float(
                os.getenv("TELEGRAM_TIMEOUT_SECONDS", "5")
            )
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

            if (
                not isinstance(corpo, Mapping)
                or corpo.get("ok") is not True
            ):
                raise RuntimeError(
                    "resposta não confirmada pelo Telegram"
                )

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


class ClienteSMTP(Protocol):
    def ehlo(self) -> Any:
        ...

    def starttls(self, *, context: ssl.SSLContext) -> Any:
        ...

    def login(self, usuario: str, senha: str) -> Any:
        ...

    def send_message(self, mensagem: EmailMessage) -> Any:
        ...

    def quit(self) -> Any:
        ...


class FabricaSMTP(Protocol):
    def __call__(
        self,
        host: str,
        port: int,
        *,
        timeout: float,
    ) -> ClienteSMTP:
        ...


def _variavel_booleana(nome: str, padrao: bool) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao

    valor_normalizado = valor.strip().lower()
    if valor_normalizado in {"1", "true", "yes", "sim", "on"}:
        return True
    if valor_normalizado in {"0", "false", "no", "nao", "não", "off"}:
        return False

    raise ValueError(f"{nome} deve possuir um valor booleano")


@dataclass(frozen=True)
class ConfiguracaoEmail:
    enabled: bool
    smtp_host: str
    smtp_port: int
    usuario: str
    senha: str
    remetente: str
    destinatarios: tuple[str, ...]
    use_tls: bool = True
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.smtp_port <= 0:
            raise ValueError("EMAIL_SMTP_PORT deve ser positivo")
        if self.timeout_seconds <= 0:
            raise ValueError("EMAIL_TIMEOUT_SECONDS deve ser positivo")

        # As credenciais só são obrigatórias se o canal estiver habilitado.
        if not self.enabled:
            return

        campos_obrigatorios = {
            "EMAIL_SMTP_HOST": self.smtp_host,
            "EMAIL_SMTP_USER": self.usuario,
            "EMAIL_SMTP_PASSWORD": self.senha,
            "EMAIL_FROM": self.remetente,
        }
        for nome, valor in campos_obrigatorios.items():
            if not valor.strip():
                raise ValueError(f"{nome} não configurado")

        if not self.destinatarios:
            raise ValueError("EMAIL_TO não configurado")

    @classmethod
    def de_ambiente(cls) -> "ConfiguracaoEmail":
        try:
            smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        except ValueError as erro:
            raise ValueError(
                "EMAIL_SMTP_PORT deve ser numérico"
            ) from erro

        try:
            timeout = float(os.getenv("EMAIL_TIMEOUT_SECONDS", "10"))
        except ValueError as erro:
            raise ValueError(
                "EMAIL_TIMEOUT_SECONDS deve ser numérico"
            ) from erro

        destinatarios = tuple(
            email.strip()
            for email in os.getenv("EMAIL_TO", "").split(",")
            if email.strip()
        )

        return cls(
            enabled=_variavel_booleana("EMAIL_ENABLED", False),
            smtp_host=os.getenv("EMAIL_SMTP_HOST", ""),
            smtp_port=smtp_port,
            usuario=os.getenv("EMAIL_SMTP_USER", ""),
            senha=os.getenv("EMAIL_SMTP_PASSWORD", ""),
            remetente=os.getenv("EMAIL_FROM", ""),
            destinatarios=destinatarios,
            use_tls=_variavel_booleana("EMAIL_USE_TLS", True),
            timeout_seconds=timeout,
        )


class AdaptadorEmail:
    """Canal secundário de alertas usando SMTP."""

    nome = "email"

    def __init__(
        self,
        configuracao: ConfiguracaoEmail,
        *,
        fabrica_cliente: FabricaSMTP | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._configuracao = configuracao
        self._fabrica_cliente = fabrica_cliente or smtplib.SMTP
        self._logger = logger or LOGGER

    @classmethod
    def de_ambiente(
        cls,
        *,
        fabrica_cliente: FabricaSMTP | None = None,
        logger: logging.Logger | None = None,
    ) -> "AdaptadorEmail":
        return cls(
            ConfiguracaoEmail.de_ambiente(),
            fabrica_cliente=fabrica_cliente,
            logger=logger,
        )

    def _criar_mensagem(self, alerta: Alerta) -> EmailMessage:
        mensagem = EmailMessage()
        mensagem["Subject"] = (
            f"[{alerta.severidade.value}] Alerta do pipeline"
        )
        mensagem["From"] = self._configuracao.remetente
        mensagem["To"] = ", ".join(
            self._configuracao.destinatarios
        )

        linhas_contexto = [
            f"{chave}: {valor}"
            for chave, valor in alerta.contexto.items()
        ]
        corpo = [
            f"Severidade: {alerta.severidade.value}",
            f"Mensagem: {alerta.mensagem}",
        ]
        if linhas_contexto:
            corpo.extend(["", "Contexto:", *linhas_contexto])

        mensagem.set_content("\n".join(corpo))

        if alerta.anexo is not None and alerta.anexo.is_file():
            tipo, _ = mimetypes.guess_type(str(alerta.anexo))
            tipo_principal, subtipo = (
                tipo.split("/", 1)
                if tipo is not None
                else ("application", "octet-stream")
            )
            mensagem.add_attachment(
                alerta.anexo.read_bytes(),
                maintype=tipo_principal,
                subtype=subtipo,
                filename=alerta.anexo.name,
            )

        return mensagem

    def enviar(self, alerta: Alerta) -> ResultadoAlerta:
        if not self._configuracao.enabled:
            return ResultadoAlerta(
                sucesso=False,
                canal=self.nome,
                erro="canal_desativado",
            )

        cliente: ClienteSMTP | None = None

        try:
            mensagem = self._criar_mensagem(alerta)
            cliente = self._fabrica_cliente(
                self._configuracao.smtp_host,
                self._configuracao.smtp_port,
                timeout=self._configuracao.timeout_seconds,
            )
            cliente.ehlo()

            if self._configuracao.use_tls:
                cliente.starttls(context=ssl.create_default_context())
                cliente.ehlo()

            cliente.login(
                self._configuracao.usuario,
                self._configuracao.senha,
            )
            cliente.send_message(mensagem)
        except smtplib.SMTPAuthenticationError:
            return self._falha(alerta, "falha_autenticacao")
        except (TimeoutError, socket.timeout):
            return self._falha(alerta, "timeout")
        except (smtplib.SMTPException, OSError):
            return self._falha(alerta, "falha_transporte")
        except Exception:
            return self._falha(alerta, "erro_inesperado")
        finally:
            if cliente is not None:
                try:
                    cliente.quit()
                except Exception:
                    pass

        self._logger.info(
            "alerta_email_enviado",
            extra={
                "evento": "alerta_email_enviado",
                "canal": self.nome,
                "severidade": alerta.severidade.value,
            },
        )
        return ResultadoAlerta(
            sucesso=True,
            canal=self.nome,
        )

    def _falha(
        self,
        alerta: Alerta,
        codigo_erro: str,
    ) -> ResultadoAlerta:
        self._logger.error(
            "alerta_email_falhou",
            extra={
                "evento": "alerta_email_falhou",
                "canal": self.nome,
                "severidade": alerta.severidade.value,
                "erro": codigo_erro,
            },
        )
        return ResultadoAlerta(
            sucesso=False,
            canal=self.nome,
            erro=codigo_erro,
        )


SEVERIDADES_COM_FALLBACK = frozenset(
    {
        Severidade.ERRO,
        Severidade.CRITICO,
    }
)


class SistemaAlertas:
    """Telegram como principal e Email como canal secundário."""

    def __init__(
        self,
        canal_principal: CanalAlerta,
        canal_secundario: CanalAlerta | None = None,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._canal_principal = canal_principal
        self._canal_secundario = canal_secundario
        self._logger = logger or LOGGER

    @classmethod
    def de_ambiente(
        cls,
        *,
        cliente_telegram: ClienteHTTP | None = None,
        fabrica_email: FabricaSMTP | None = None,
        logger: logging.Logger | None = None,
    ) -> "SistemaAlertas":
        canal_principal = AdaptadorTelegram.de_ambiente(
            cliente=cliente_telegram,
            logger=logger,
        )
        canal_secundario = AdaptadorEmail.de_ambiente(
            fabrica_cliente=fabrica_email,
            logger=logger,
        )
        return cls(
            canal_principal=canal_principal,
            canal_secundario=canal_secundario,
            logger=logger,
        )

    def _enviar_seguro(
        self,
        canal: CanalAlerta,
        alerta: Alerta,
    ) -> ResultadoAlerta:
        try:
            return canal.enviar(alerta)
        except Exception:
            return ResultadoAlerta(
                sucesso=False,
                canal=canal.nome,
                erro="falha_nao_controlada_do_canal",
            )

    @staticmethod
    def _criar_tentativa(
        resultado: ResultadoAlerta,
    ) -> TentativaAlerta:
        return TentativaAlerta(
            canal=resultado.canal,
            sucesso=resultado.sucesso,
            erro=resultado.erro,
        )

    def _auditar(
        self,
        alerta: Alerta,
        resultado: ResultadoAlerta,
    ) -> None:
        contexto_auditavel = {
            chave: valor
            for chave, valor in alerta.contexto.items()
            if chave in {
                "execution_id",
                "correlation_id",
                "bot_id",
            }
        }
        extra = {
            "evento": (
                "alerta_entregue"
                if resultado.sucesso
                else "alerta_nao_entregue"
            ),
            "severidade": alerta.severidade.value,
            "canal_entrega": (
                resultado.canal
                if resultado.sucesso
                else None
            ),
            "fallback_acionado": resultado.fallback_acionado,
            "tentativas": [
                tentativa.to_dict()
                for tentativa in resultado.tentativas
            ],
            **contexto_auditavel,
        }

        if resultado.sucesso:
            self._logger.info("alerta_entregue", extra=extra)
            return

        if alerta.severidade in SEVERIDADES_COM_FALLBACK:
            self._logger.critical(
                "ALERTA_NAO_ENTREGUE",
                extra=extra,
            )
            return

        self._logger.warning(
            "alerta_nao_entregue",
            extra=extra,
        )

    def enviar(self, alerta: Alerta) -> ResultadoAlerta:
        resultado_principal = self._enviar_seguro(
            self._canal_principal,
            alerta,
        )
        tentativas = [
            self._criar_tentativa(resultado_principal)
        ]

        if resultado_principal.sucesso:
            resultado = ResultadoAlerta(
                sucesso=True,
                canal=resultado_principal.canal,
                message_id=resultado_principal.message_id,
                fallback_acionado=False,
                tentativas=tuple(tentativas),
            )
            self._auditar(alerta, resultado)
            return resultado

        deve_tentar_secundario = (
            alerta.severidade in SEVERIDADES_COM_FALLBACK
            and self._canal_secundario is not None
        )

        if deve_tentar_secundario:
            # A verificação acima garante que o canal não é None.
            assert self._canal_secundario is not None
            resultado_secundario = self._enviar_seguro(
                self._canal_secundario,
                alerta,
            )
            tentativas.append(
                self._criar_tentativa(resultado_secundario)
            )

            if resultado_secundario.sucesso:
                resultado = ResultadoAlerta(
                    sucesso=True,
                    canal=resultado_secundario.canal,
                    message_id=resultado_secundario.message_id,
                    fallback_acionado=True,
                    tentativas=tuple(tentativas),
                )
                self._auditar(alerta, resultado)
                return resultado

        resultado = ResultadoAlerta(
            sucesso=False,
            canal=resultado_principal.canal,
            erro=(
                "todos_os_canais_falharam"
                if deve_tentar_secundario
                else resultado_principal.erro
            ),
            fallback_acionado=deve_tentar_secundario,
            tentativas=tuple(tentativas),
        )
        self._auditar(alerta, resultado)
        return resultado

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
                severidade = Severidade(
                    severidade.strip().upper()
                )
            except ValueError:
                return ResultadoAlerta(
                    sucesso=False,
                    canal=self._canal_principal.nome,
                    erro=f"severidade inválida: {severidade}",
                )

        alerta = Alerta(
            severidade=severidade,
            mensagem=mensagem,
            anexo=anexo,
            contexto=contexto or {},
        )
        return self.enviar(alerta)


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
