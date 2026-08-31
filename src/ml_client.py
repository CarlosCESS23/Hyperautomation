"""Cliente HTTP resiliente da API de Machine Learning."""

from __future__ import annotations

import os
from typing import Any

import requests


class MLClientError(RuntimeError):
    """Erro base do cliente ML."""


class MLTimeoutError(MLClientError):
    """A API ultrapassou o timeout configurado."""


class MLServiceUnavailableError(MLClientError):
    """A API está indisponível ou o circuito está aberto."""


class MLInvalidResponseError(MLClientError):
    """A API retornou um JSON inválido."""


class MLClient:
    """Realiza chamadas HTTP e controla falhas consecutivas."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 3.0,
        limite_falhas: int = 5,
        session: requests.Session | None = None,
    ):
        if timeout <= 0:
            raise ValueError(
                "timeout deve ser maior que zero"
            )

        if limite_falhas <= 0:
            raise ValueError(
                "limite_falhas deve ser maior que zero"
            )

        self.base_url = (
            base_url
            or os.getenv(
                "ML_API_URL",
                "http://api_ml:8000",
            )
        ).rstrip("/")

        self.timeout = timeout
        self.limite_falhas = limite_falhas
        self.session = (
            session
            or requests.Session()
        )

        self.falhas_consecutivas = 0
        self.circuito_aberto = False

    def _registrar_falha(self) -> None:
        """Incrementa falhas e abre o circuito no limite."""

        self.falhas_consecutivas += 1

        if (
            self.falhas_consecutivas
            >= self.limite_falhas
        ):
            self.circuito_aberto = True

    def _registrar_sucesso(self) -> None:
        """Limpa as falhas depois de uma resposta válida."""

        self.falhas_consecutivas = 0
        self.circuito_aberto = False

    def _enviar_predicao(
        self,
        payload: dict[str, Any],
        *,
        detalhar_erros: bool,
    ) -> dict[str, Any] | None:
        """Envia o payload e opcionalmente diferencia as falhas."""

        if self.circuito_aberto:
            if detalhar_erros:
                raise MLServiceUnavailableError(
                    "Circuit breaker aberto"
                )

            return None

        try:
            resposta = self.session.post(
                f"{self.base_url}/predict",
                json=payload,
                timeout=self.timeout,
            )

            resposta.raise_for_status()

        except requests.Timeout as erro:
            self._registrar_falha()

            if detalhar_erros:
                raise MLTimeoutError(
                    "A API ML ultrapassou o timeout"
                ) from erro

            return None

        except requests.RequestException as erro:
            self._registrar_falha()

            if detalhar_erros:
                raise MLServiceUnavailableError(
                    "A API ML está indisponível"
                ) from erro

            return None

        try:
            predicao = resposta.json()
        except ValueError as erro:
            self._registrar_falha()

            if detalhar_erros:
                raise MLInvalidResponseError(
                    "A API retornou JSON inválido"
                ) from erro

            return None

        if not isinstance(predicao, dict):
            self._registrar_falha()

            if detalhar_erros:
                raise MLInvalidResponseError(
                    "A resposta da API não é um objeto JSON"
                )

            return None

        self._registrar_sucesso()

        return predicao

    def classificar_observacao(
        self,
        *,
        observacao: str,
    ) -> dict[str, Any]:
        """Chama o novo endpoint textual com erros detalhados."""

        resultado = self._enviar_predicao(
            {
                "observacao": observacao,
            },
            detalhar_erros=True,
        )

        if resultado is None:
            # Proteção defensiva: no modo detalhado,
            # uma falha deveria gerar uma exceção específica.
            raise MLServiceUnavailableError(
                "A API ML está indisponível"
            )

        return resultado

    def classificar(
        self,
        *,
        status_raw: str,
        turno: str,
        tem_obs: bool,
    ) -> dict[str, Any] | None:
        """Contrato legado mantido até a migração do item_processor."""

        return self._enviar_predicao(
            {
                "status_raw": status_raw,
                "turno": turno,
                "tem_obs": tem_obs,
            },
            detalhar_erros=False,
        )

    def resetar_circuito(self) -> None:
        """Reinicia manualmente o circuit breaker."""

        self.falhas_consecutivas = 0
        self.circuito_aberto = False