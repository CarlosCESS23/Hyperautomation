"""Abstração segura para classificação de causas prováveis."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from src.causas_divergencia import (
    CausaProvavel,
)
from src.decisao_hibrida import (
    MotivoFallback,
    ResultadoDecisaoHibrida,
)
from src.ml_client import MLClient


class ClienteClassificacaoML(Protocol):
    """Contrato mínimo exigido do cliente HTTP."""

    def classificar_observacao(
        self,
        *,
        observacao: str,
    ) -> dict[str, Any] | None:
        """Envia a observação para o serviço ML."""


class ClassificadorDivergencia:
    """Única abstração do novo pipeline autorizada a chamar o ML.

    Independentemente do comportamento da API, este componente
    sempre retorna um ResultadoDecisaoHibrida válido.
    """

    def __init__(
        self,
        cliente_ml: ClienteClassificacaoML | None = None,
    ):
        self._cliente_ml = (
            cliente_ml
            if cliente_ml is not None
            else MLClient()
        )

    def classificar(
        self,
        observacao: str,
    ) -> ResultadoDecisaoHibrida:
        """Sugere a causa provável de uma observação."""

        observacao_normalizada = self._preparar_observacao(
            observacao
        )

        if observacao_normalizada is None:
            return ResultadoDecisaoHibrida.de_fallback(
                motivo=MotivoFallback.RESPOSTA_INVALIDA,
            )

        try:
            resposta = (
                self._cliente_ml
                .classificar_observacao(
                    observacao=observacao_normalizada,
                )
            )
        except Exception:
            # Nenhuma exceção da API pode chegar ao bot.
            return ResultadoDecisaoHibrida.de_fallback(
                motivo=(
                    MotivoFallback
                    .SERVICO_INDISPONIVEL
                ),
            )

        if resposta is None:
            return ResultadoDecisaoHibrida.de_fallback(
                motivo=(
                    MotivoFallback
                    .SERVICO_INDISPONIVEL
                ),
            )

        return self._converter_resposta(
            resposta
        )

    @staticmethod
    def _preparar_observacao(
        observacao: str,
    ) -> str | None:
        """Valida e remove espaços repetidos."""

        if not isinstance(observacao, str):
            return None

        texto = " ".join(
            observacao.split()
        )

        if len(texto) < 3:
            return None

        return texto

    @staticmethod
    def _converter_resposta(
        resposta: object,
    ) -> ResultadoDecisaoHibrida:
        """Converte o JSON da API para o contrato seguro."""

        if not isinstance(resposta, Mapping):
            return ResultadoDecisaoHibrida.de_fallback(
                motivo=MotivoFallback.RESPOSTA_INVALIDA,
            )

        try:
            causa_texto = resposta[
                "causa_provavel"
            ]

            confianca = resposta[
                "confianca_ml"
            ]

            versao_modelo = resposta[
                "versao_modelo"
            ]

            if not isinstance(
                causa_texto,
                str,
            ):
                raise ValueError(
                    "causa_provavel inválida"
                )

            causa = CausaProvavel(
                causa_texto
            )

            if (
                isinstance(confianca, bool)
                or not isinstance(
                    confianca,
                    (int, float),
                )
            ):
                raise ValueError(
                    "confianca_ml inválida"
                )

            if not isinstance(
                versao_modelo,
                str,
            ):
                raise ValueError(
                    "versao_modelo inválida"
                )

            versao_modelo = (
                versao_modelo.strip()
            )

            if not versao_modelo:
                raise ValueError(
                    "versao_modelo vazia"
                )

            return ResultadoDecisaoHibrida.de_ml(
                causa_provavel=causa.value,
                confianca_ml=float(confianca),
                versao_modelo=versao_modelo,
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            return ResultadoDecisaoHibrida.de_fallback(
                motivo=MotivoFallback.RESPOSTA_INVALIDA,
            )