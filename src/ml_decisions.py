"""Registro auditável das decisões já produzidas pelo classificador de ML."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
from time import perf_counter
from typing import Any, Callable, Mapping, Final

LOGGER = logging.getLogger("botcity_permorfer")

# Variavel constante para ML
STATUS_SUCESSO : Final = 'sucesso'
STATUS_OFFLINE : Final = 'offline'

@dataclass(frozen=True)
class DecisaoML():
    """Representa uma chamada realizada no classificador de ML."""

    lote_id : str

    #Campos que podem ser None quando a API estiver indisponível.
    classe_prevista: str | None
    probabilidade : str | None
    nivel_confianca: str | None

    latencia_ms: float
    registrado_em : str
    modelo_versao : str = ''

    #Identificando se a chamada foi sucesso ou ficou em offline

    status_chamada: str = STATUS_SUCESSO
    detalhe_erro: str = ''

    def __post_init__(self):
        """Isso valida os dados que é conforme o resultado da chamada"""

        if not self.lote_id.strip():
            raise ValueError('lote_id é obrigatório na decisão de ML')

        if self.latencia_ms < 0:
            raise ValueError('Latência não pode ser negativa')

        status_permitidos = {
            STATUS_OFFLINE,
            STATUS_SUCESSO
        }

        if self.status_chamada not in status_permitidos:
            raise ValueError('status_chamada deve ser sucesso ou offline')

        # Caso em chamada bem sucedida, os dados da predição continuam sendo obrigatório

        if self.status_chamada == STATUS_SUCESSO:
            if (
                    self.classe_prevista is None
                    or not self.classe_prevista.strip()
            ):
                raise ValueError(
                    "classe prevista é obrigatória "
                    "em uma chamada bem-sucedida"
                )

            if self.probabilidade is None:
                raise ValueError(
                    "probabilidade é obrigatória "
                    "em uma chamada bem-sucedida"
                )

            if not 0 <= self.probabilidade <= 1:
                raise ValueError(
                    "probabilidade deve estar entre 0 e 1"
                )

            if (
                    self.nivel_confianca is None
                    or not self.nivel_confianca.strip()
            ):
                raise ValueError(
                    "nível de confiança é obrigatório "
                    "em uma chamada bem-sucedida"
                )
        # Caso estiver offline, deve existir o motivo:
        if self.status_chamada == STATUS_OFFLINE:
            if not self.detalhe_erro.strip():
                raise ValueError('detalhe do erro é obrigatório quando a chamada estiver offline')

    def to_dict(self) -> dict[str,Any]:
        """Converte a decisão para log estruturado"""

        return asdict(self)

    def to_excel_dict(self):
        """Convertendo a decisão para formato do relatório do Excel"""
        return {
            "Lote ID": self.lote_id,
            "Classe Prevista": (
                    self.classe_prevista
                    or "NÃO DISPONÍVEL"
            ),
            "Probabilidade": self.probabilidade,
            "Nível de Confiança": (
                    self.nivel_confianca
                    or "OFFLINE"
            ),
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
        """
        Registra uma chamada realizada ao ML.

        A chamada pode ter produzido uma predição ou ter
        terminado sem resposta por indisponibilidade da API.
        """

        if resposta is None:
            decisao = DecisaoML(
                lote_id=str(lote_id),
                classe_prevista=None,
                probabilidade=None,
                nivel_confianca=None,
                latencia_ms=round(
                    float(latencia_ms),
                    3,
                ),
                registrado_em=datetime.now(
                    timezone.utc
                ).isoformat(),
                modelo_versao="",
                status_chamada=STATUS_OFFLINE,
                detalhe_erro="API ML indisponível",
            )

        else:
            decisao = DecisaoML(
                lote_id=str(lote_id),
                classe_prevista=str(
                    _campo(
                        resposta,
                        "classe_prevista",
                        "classe",
                        "predicted_class",
                        padrao="",
                    )
                ),
                probabilidade=float(
                    _campo(
                        resposta,
                        "probabilidade",
                        "probability",
                        "score",
                        padrao=-1,
                    )
                ),
                nivel_confianca=str(
                    _campo(
                        resposta,
                        "nivel_confianca",
                        "confianca",
                        "confidence_level",
                        padrao="",
                    )
                ),
                latencia_ms=round(
                    float(latencia_ms),
                    3,
                ),
                registrado_em=datetime.now(
                    timezone.utc
                ).isoformat(),
                modelo_versao=str(
                    _campo(
                        resposta,
                        "modelo_versao",
                        "model_version",
                        padrao="",
                    )
                ),
                status_chamada=STATUS_SUCESSO,
                detalhe_erro="",
            )

        self._decisoes.append(decisao)

        self._logger.info(
            "decisao_ml",
            extra={
                "evento": "decisao_ml",
                **decisao.to_dict(),
            },
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
