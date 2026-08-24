"""Cliente resiliente para consumir a API de Machine Learning"""
from __future__ import annotations

import os

from typing import Any

import requests

class MLClient():
    """Consome a API ML sem interromper o processamento"""

    def __init__(self,base_url: str | None = None, timeout: float = 3.0, limite_falhas : int = 5, session: requests.Session | None = None):
        self.base_url = (
                base_url
                or os.getenv("ML_API_URL", "http://api_ml:8000")
        ).rstrip("/")
        self.timeout = timeout
        self.limite_falhas = limite_falhas
        self.session = session or requests.Session()
        self.falhas_consecutivas = 0
        self.circuito_aberto = False

    def classificar(
            self,
            *,
            status_raw: str,
            turno: str,
            tem_obs: bool,
    ) -> dict[str, Any] | None:
        """Retorna a predição ou None em caso de indisponibilidade."""

        if self.circuito_aberto:
            return None

        payload = {
            "status_raw": status_raw,
            "turno": turno,
            "tem_obs": tem_obs,
        }

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

        except (requests.RequestException, ValueError):
            self.falhas_consecutivas += 1

            if self.falhas_consecutivas >= self.limite_falhas:
                self.circuito_aberto = True

            return None

    def resetar_circuito(self) -> None:
        """Permite recuperação manual após a API voltar."""

        self.falhas_consecutivas = 0
        self.circuito_aberto = False

