"""Cliente HTTP resiliente para consumir a API de Machine Learning."""

from __future__ import annotations

import os
from typing import Any

import requests


class MLClient:
    """Realiza chamadas HTTP sem interromper o processamento."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 3.0,
        limite_falhas: int = 5,
        session: requests.Session | None = None,
    ):
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

    def _enviar_predicao(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Envia um payload ao endpoint de predição."""

        if self.circuito_aberto:
            return None

        try:
            resposta = self.session.post(
                f"{self.base_url}/predict",
                json=payload,
                timeout=self.timeout,
            )

            resposta.raise_for_status()

            predicao = resposta.json()

            self.falhas_consecutivas = 0

            return predicao

        except (
            requests.RequestException,
            ValueError,
        ):
            self.falhas_consecutivas += 1

            if (
                self.falhas_consecutivas
                >= self.limite_falhas
            ):
                self.circuito_aberto = True

            return None

    def classificar_observacao(
        self,
        *,
        observacao: str,
    ) -> dict[str, Any] | None:
        """Classifica uma observação pelo novo contrato textual."""

        return self._enviar_predicao(
            {
                "observacao": observacao,
            }
        )

    def classificar(
        self,
        *,
        status_raw: str,
        turno: str,
        tem_obs: bool,
    ) -> dict[str, Any] | None:
        """Contrato legado mantido temporariamente.

        O item_processor ainda utiliza este método. Sua remoção
        acontecerá depois que o fluxo antigo for migrado.
        """

        return self._enviar_predicao(
            {
                "status_raw": status_raw,
                "turno": turno,
                "tem_obs": tem_obs,
            }
        )

    def resetar_circuito(self) -> None:
        """Permite a recuperação manual do circuit breaker."""

        self.falhas_consecutivas = 0
        self.circuito_aberto = False