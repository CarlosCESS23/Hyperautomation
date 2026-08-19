"""Registro auditável das decisões já produzidas pelo classificador de ML."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
from time import perf_counter
from typing import Any, Callable, Mapping


LOGGER = logging.getLogger("botcity_permorfer")


@dataclass(frozen=True)
class DecisaoML:
    """Retrato imutável de uma chamada concluída ao classificador."""

    lote_id: str
    classe_prevista: str
    probabilidade: float
    nivel_confianca: str
    latencia_ms: float
    registrado_em: str
    modelo_versao: str = ""

    def __post_init__(self) -> None:
        if not self.lote_id.strip():
            raise ValueError("lote_id é obrigatório na decisão de ML")
        if not self.classe_prevista.strip():
            raise ValueError("classe prevista é obrigatória na decisão de ML")
        if not 0 <= self.probabilidade <= 1:
            raise ValueError("probabilidade deve estar entre 0 e 1")
        if not self.nivel_confianca.strip():
            raise ValueError("nível de confiança é obrigatório na decisão de ML")
        if self.latencia_ms < 0:
            raise ValueError("latência não pode ser negativa")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_excel_dict(self) -> dict[str, Any]:
        return {
            "Lote ID": self.lote_id,
            "Classe Prevista": self.classe_prevista,
            "Probabilidade": self.probabilidade,
            "Nível de Confiança": self.nivel_confianca,
            "Latência (ms)": self.latencia_ms,
            "Registrado em (UTC)": self.registrado_em,
            "Versão do Modelo": self.modelo_versao,
        }


def _campo(resposta: Any, *nomes: str, padrao: Any = None) -> Any:
    for nome in nomes:
        if isinstance(resposta, Mapping) and nome in resposta:
            return resposta[nome]
        if hasattr(resposta, nome):
            return getattr(resposta, nome)
    return padrao


class AuditoriaDecisoesML:
    """Acumula e registra, sem deduplicação, uma decisão por chamada ao ML."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or LOGGER
        self._decisoes: list[DecisaoML] = []

    @property
    def decisoes(self) -> tuple[DecisaoML, ...]:
        return tuple(self._decisoes)

    def registrar(
        self,
        lote_id: str,
        resposta: Any,
        latencia_ms: float,
    ) -> DecisaoML:
        """Persiste em memória e em log os valores retornados pelo MLClient."""
        decisao = DecisaoML(
            lote_id=str(lote_id),
            classe_prevista=str(
                _campo(resposta, "classe_prevista", "classe", "predicted_class", padrao="")
            ),
            probabilidade=float(
                _campo(resposta, "probabilidade", "probability", "score", padrao=-1)
            ),
            nivel_confianca=str(
                _campo(resposta, "nivel_confianca", "confianca", "confidence_level", padrao="")
            ),
            latencia_ms=round(float(latencia_ms), 3),
            registrado_em=datetime.now(timezone.utc).isoformat(),
            modelo_versao=str(
                _campo(resposta, "modelo_versao", "model_version", padrao="")
            ),
        )
        # Primeiro mantém o registro que alimentará o relatório; depois emite o
        # mesmo conteúdo no logger JSON já configurado pela aplicação.
        self._decisoes.append(decisao)
        self._logger.info(
            "decisao_ml",
            extra={"evento": "decisao_ml", **decisao.to_dict()},
        )
        return decisao

    def classificar(
        self,
        lote_id: str,
        classificador: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Executa o cliente uma vez e audita sua resposta sem recalculá-la."""
        inicio = perf_counter()
        resposta = classificador(*args, **kwargs)
        latencia_ms = (perf_counter() - inicio) * 1_000
        self.registrar(lote_id, resposta, latencia_ms)
        return resposta
