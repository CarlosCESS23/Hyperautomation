"""Classificação segura das causas prováveis."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from src.causas_divergencia import (
    CausaProvavel,
)
from src.config import (
    Configuracao,
    obter_configuracao,
)
from src.decisao_hibrida import (
    MotivoFallback,
    OrigemDecisao,
    ResultadoDecisaoHibrida,
)
from src.ml_client import (
    MLClient,
    MLInvalidResponseError,
    MLServiceUnavailableError,
    MLTimeoutError,
)


class ClienteClassificacaoML(Protocol):
    """Contrato mínimo do cliente utilizado pelo classificador."""

    def classificar_observacao(
        self,
        *,
        observacao: str,
    ) -> dict[str, Any] | None:
        """Envia uma observação para o serviço ML."""


class ClassificadorDivergencia:
    """Aplica as políticas de segurança da classificação ML."""

    def __init__(
        self,
        cliente_ml: ClienteClassificacaoML | None = None,
        *,
        ml_enabled: bool = True,
        confianca_minima: float = 0.75,
    ):
        if not isinstance(ml_enabled, bool):
            raise ValueError(
                "ml_enabled deve ser booleano"
            )

        if (
            isinstance(confianca_minima, bool)
            or not isinstance(
                confianca_minima,
                (int, float),
            )
        ):
            raise ValueError(
                "confianca_minima deve ser numérica"
            )

        if not 0 <= confianca_minima <= 1:
            raise ValueError(
                "confianca_minima deve estar entre 0 e 1"
            )

        self._cliente_ml = (
            cliente_ml
            if cliente_ml is not None
            else MLClient()
        )

        self._ml_enabled = ml_enabled
        self._confianca_minima = float(
            confianca_minima
        )

    @classmethod
    def de_configuracao(
        cls,
        configuracao: Configuracao | None = None,
    ) -> "ClassificadorDivergencia":
        """Cria o classificador usando as variáveis de ambiente."""

        config = (
            configuracao
            if configuracao is not None
            else obter_configuracao()
        )

        cliente = MLClient(
            base_url=config.ml_api_url,
            timeout=config.ml_timeout_seconds,
        )

        return cls(cliente_ml=cliente,ml_enabled=config.ml_enabled,confianca_minima=config.ml_min_confidence)


    def classificar(
        self,
        observacao: str,
    ) -> ResultadoDecisaoHibrida:
        """Retorna uma decisão ML ou um fallback específico."""

        # A flag é verificada antes de qualquer validação
        # ou chamada ao cliente.
        if not self._ml_enabled:
            return self._fallback(
                MotivoFallback.ML_DESATIVADO
            )

        observacao_normalizada = (
            self._preparar_observacao(
                observacao
            )
        )

        if observacao_normalizada is None:
            return self._fallback(
                MotivoFallback.RESPOSTA_INVALIDA
            )

        try:
            resposta = (
                self._cliente_ml
                .classificar_observacao(
                    observacao=observacao_normalizada,
                )
            )

        except MLTimeoutError:
            return self._fallback(
                MotivoFallback.TIMEOUT
            )

        except MLInvalidResponseError:
            return self._fallback(
                MotivoFallback.RESPOSTA_INVALIDA
            )

        except MLServiceUnavailableError:
            return self._fallback(
                MotivoFallback.SERVICO_INDISPONIVEL
            )

        except Exception:
            # Uma exceção inesperada também não pode
            # interromper o bot.
            return self._fallback(
                MotivoFallback.SERVICO_INDISPONIVEL
            )

        if resposta is None:
            return self._fallback(
                MotivoFallback.SERVICO_INDISPONIVEL
            )

        resultado = self._converter_resposta(
            resposta
        )

        if resultado.origem_decisao != OrigemDecisao.ML:
            return resultado

        if (
            resultado.confianca_ml is not None
            and resultado.confianca_ml
            < self._confianca_minima
        ):
            return self._fallback(
                MotivoFallback.BAIXA_CONFIANCA
            )

        return resultado

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
    def _fallback(
        motivo: MotivoFallback,
    ) -> ResultadoDecisaoHibrida:
        """Cria um fallback sem causa ou confiança inventadas."""

        return ResultadoDecisaoHibrida.de_fallback(
            motivo=motivo,
        )

    @staticmethod
    def _converter_resposta(
        resposta: object,
    ) -> ResultadoDecisaoHibrida:
        """Converte e valida a resposta da FastAPI."""

        if not isinstance(resposta, Mapping):
            return ClassificadorDivergencia._fallback(
                MotivoFallback.RESPOSTA_INVALIDA
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
                raise ValueError

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
                raise ValueError

            if not isinstance(
                versao_modelo,
                str,
            ):
                raise ValueError

            versao_modelo = (
                versao_modelo.strip()
            )

            if not versao_modelo:
                raise ValueError

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
            return ClassificadorDivergencia._fallback(
                MotivoFallback.RESPOSTA_INVALIDA
            )