"""Auditoria das decisões de enriquecimento do pipeline híbrido."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from src.decisao_hibrida import ResultadoDecisaoHibrida


LOGGER = logging.getLogger("botcity_permorfer")


@dataclass(frozen=True)
class RegistroAuditoriaHibrida:
    """
    Representa uma decisão auditada do pipeline híbrido.

    Esse registro não contém a decisão das RN01–RN12.
    Ele registra somente o enriquecimento produzido pelo ML ou fallback.
    """

    execution_id: str
    lote_id: str
    causa_provavel: str
    origem_decisao: str
    confianca_ml: float | None
    motivo_fallback: str
    versao_modelo: str
    latencia_ms: float
    registrado_em: str

    def __post_init__(self) -> None:
        if not self.execution_id.strip():
            raise ValueError("execution_id é obrigatório")

        if not self.lote_id.strip():
            raise ValueError("lote_id é obrigatório")

        if not self.causa_provavel.strip():
            raise ValueError("causa_provavel é obrigatória")

        if self.origem_decisao not in {"ml", "fallback"}:
            raise ValueError(
                "origem_decisao deve ser 'ml' ou 'fallback'"
            )

        if (
            self.confianca_ml is not None
            and not 0 <= self.confianca_ml <= 1
        ):
            raise ValueError(
                "confianca_ml deve estar entre 0 e 1"
            )

        if self.origem_decisao == "ml" and self.confianca_ml is None:
            raise ValueError(
                "decisão de origem ML deve possuir confiança"
            )

        if self.origem_decisao == "fallback" and not self.motivo_fallback:
            raise ValueError(
                "decisão de fallback deve possuir um motivo"
            )

        if self.latencia_ms < 0:
            raise ValueError("latencia_ms não pode ser negativa")

    def to_dict(self) -> dict[str, Any]:
        """Converte o registro para log estruturado."""

        return asdict(self)


class AuditoriaPipelineHibrido:
    """
    Registra uma decisão de enriquecimento por divergência processada.

    Registros repetidos não são descartados porque cada chamada representa
    um evento independente da execução.
    """

    def __init__(
        self,
        execution_id: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._execution_id = (
            execution_id or f"exec-{uuid4()}"
        ).strip()

        if not self._execution_id:
            raise ValueError("execution_id é obrigatório")

        self._logger = logger or LOGGER
        self._decisoes: list[RegistroAuditoriaHibrida] = []

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def decisoes(self) -> tuple[RegistroAuditoriaHibrida, ...]:
        """
        Retorna uma cópia imutável das decisões.

        Assim, quem recebe a auditoria não consegue modificar a lista interna.
        """

        return tuple(self._decisoes)

    def registrar(
        self,
        lote_id: str,
        decisao: ResultadoDecisaoHibrida,
        latencia_ms: float,
    ) -> RegistroAuditoriaHibrida:
        """Registra a decisão em memória e no log estruturado."""

        origem_decisao = decisao.origem_decisao.value

        motivo_fallback = (
            decisao.motivo_fallback.value
            if decisao.motivo_fallback is not None
            else ""
        )

        registro = RegistroAuditoriaHibrida(
            execution_id=self._execution_id,
            lote_id=str(lote_id),
            causa_provavel=decisao.causa_provavel,
            origem_decisao=origem_decisao,
            confianca_ml=decisao.confianca_ml,
            motivo_fallback=motivo_fallback,
            versao_modelo=decisao.versao_modelo,
            latencia_ms=round(float(latencia_ms), 3),
            registrado_em=datetime.now(timezone.utc).isoformat(),
        )

        # Não existe verificação de duplicidade.
        # Duas chamadas para o mesmo lote representam dois eventos.
        self._decisoes.append(registro)

        self._logger.info(
            "decisao_pipeline_hibrido",
            extra={
                "evento": "decisao_pipeline_hibrido",
                **registro.to_dict(),
            },
        )

        return registro

    def classificar(
        self,
        lote_id: str,
        classificador: Callable[..., ResultadoDecisaoHibrida],
        *args: Any,
        **kwargs: Any,
    ) -> ResultadoDecisaoHibrida:
        """
        Executa o classificador uma única vez e registra sua resposta.

        perf_counter é utilizado para medir duração porque não sofre alterações
        do relógio do sistema durante a execução.
        """

        inicio = perf_counter()

        decisao = classificador(*args, **kwargs)

        latencia_ms = (perf_counter() - inicio) * 1_000

        self.registrar(
            lote_id=lote_id,
            decisao=decisao,
            latencia_ms=latencia_ms,
        )

        return decisao