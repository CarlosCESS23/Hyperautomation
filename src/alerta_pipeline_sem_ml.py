"""Política do alerta de execução operando integralmente sem ML."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Protocol, Sequence

from src.validacao_lotes import RegistroValidado


LOGGER = logging.getLogger("botcity_permorfer")


class EmissorAlertas(Protocol):
    """Fachada multicanal; a política não conhece Telegram ou fallback."""

    def enviar_alerta(
        self,
        *,
        severidade: str,
        mensagem: str,
        contexto: dict[str, Any],
    ) -> Any:
        """Envia pelo canal principal e aplica seu fallback interno."""


@dataclass(frozen=True)
class AvaliacaoPipelineSemML:
    total_divergencias: int
    total_fallback: int
    proporcao_fallback: float
    alerta_disparado: bool
    resultado_alerta: Any = None
    erro_alerta: str | None = None


def avaliar_e_alertar_pipeline_sem_ml(
    registros: Sequence[RegistroValidado],
    sistema_alertas: EmissorAlertas,
    *,
    execution_id: str,
    correlation_id: str,
    logger: logging.Logger | None = None,
) -> AvaliacaoPipelineSemML:
    """Emite AVISO somente quando toda divergência usou fallback.

    Uma execução sem divergências possui proporção zero e não gera alerta.
    O envio é delegado à fachada para preservar o fallback de canal.
    """

    divergencias = tuple(
        registro
        for registro in registros
        if _eh_divergencia(registro.classificacao)
    )
    total_divergencias = len(divergencias)
    total_fallback = sum(
        1
        for registro in divergencias
        if (registro.origem_decisao or "").strip().lower()
        == "fallback"
    )
    proporcao = (
        total_fallback / total_divergencias
        if total_divergencias
        else 0.0
    )

    if total_divergencias == 0 or total_fallback != total_divergencias:
        return AvaliacaoPipelineSemML(
            total_divergencias=total_divergencias,
            total_fallback=total_fallback,
            proporcao_fallback=proporcao,
            alerta_disparado=False,
        )

    contexto = {
        "evento": "pipeline_operando_sem_ml",
        "execution_id": execution_id,
        "correlation_id": correlation_id,
        "total_divergencias": total_divergencias,
        "total_fallback": total_fallback,
        "proporcao_fallback": proporcao,
    }
    try:
        resultado = sistema_alertas.enviar_alerta(
            severidade="AVISO",
            mensagem=(
                "Pipeline operando sem ML: 100% das divergências "
                "utilizaram fallback."
            ),
            contexto=contexto,
        )
    except Exception as erro:
        # Uma falha em todos os canais de alerta não pode desfazer a
        # conclusão do lote ou a geração de seus artefatos.
        (logger or LOGGER).exception(
            "alerta_pipeline_sem_ml_falhou",
            extra={
                **contexto,
                "evento": "alerta_pipeline_sem_ml_falhou",
                "erro": str(erro),
            },
        )
        return AvaliacaoPipelineSemML(
            total_divergencias=total_divergencias,
            total_fallback=total_fallback,
            proporcao_fallback=proporcao,
            alerta_disparado=True,
            erro_alerta=str(erro),
        )

    (logger or LOGGER).warning(
        "pipeline_operando_sem_ml",
        extra=contexto,
    )
    return AvaliacaoPipelineSemML(
        total_divergencias=total_divergencias,
        total_fallback=total_fallback,
        proporcao_fallback=proporcao,
        alerta_disparado=True,
        resultado_alerta=resultado,
    )


def _eh_divergencia(classificacao: str) -> bool:
    normalizada = classificacao.strip().casefold()
    return normalizada in {"divergência", "divergencia"}
