"""Fonte única dos indicadores operacionais do relatório executivo."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from src.validacao_lotes import CLASSIFICACOES, RegistroValidado


DESCRICOES_REGRAS = {
    "RN01": "Preenchimento dos campos obrigatórios",
    "RN08": "Status de inspeção não reconhecido",
    "RN09": "Lote ausente da base de referência",
    "RN10": "Reprovação sem observação",
    "RN11": "Duplicidade de lote no mesmo dia",
    "RN12": "Data ausente ou em formato inválido",
}


@dataclass(frozen=True)
class RegraRanking:
    codigo: str
    descricao: str
    quantidade: int
    percentual: float


@dataclass(frozen=True)
class OperationalIndicators:
    total_registros: int
    validos: int
    divergencias: int
    ambiguos: int
    erros_entrada: int
    regra_mais_acionada: str
    taxa_retrabalho: float
    taxa_revisao_humana: float
    taxa_qualidade_entrada: float
    ganho_estimado_horas: float
    ranking_regras: tuple[RegraRanking, ...]
    minutos_poupados_por_registro_valido: int = 5

    @property
    def descricao_regra_mais_acionada(self) -> str:
        return DESCRICOES_REGRAS.get(self.regra_mais_acionada, "Nenhuma regra acionada")


def consolidar_indicadores(
    registros: list[RegistroValidado],
    minutos_poupados_por_registro_valido: int = 5,
) -> OperationalIndicators:
    """Consolida uma vez os dez indicadores e o ranking derivado das RNs."""
    classificacoes = Counter(registro.classificacao for registro in registros)
    regras = Counter(
        regra
        for registro in registros
        for regra in registro.regras_acionadas
    )
    total = len(registros)
    total_acionamentos = sum(regras.values())
    ranking = tuple(
        RegraRanking(
            codigo=codigo,
            descricao=DESCRICOES_REGRAS.get(codigo, "Regra de negócio"),
            quantidade=quantidade,
            percentual=quantidade / total_acionamentos if total_acionamentos else 0.0,
        )
        for codigo, quantidade in sorted(
            regras.items(), key=lambda item: (-item[1], item[0])
        )
    )
    validos = classificacoes["Válido"]
    divergencias = classificacoes["Divergência"]
    ambiguos = classificacoes["Ambíguo"]
    erros = classificacoes["Erro de Entrada"]
    return OperationalIndicators(
        total_registros=total,
        validos=validos,
        divergencias=divergencias,
        ambiguos=ambiguos,
        erros_entrada=erros,
        regra_mais_acionada=ranking[0].codigo if ranking else "Nenhuma",
        taxa_retrabalho=(divergencias + erros) / total if total else 0.0,
        taxa_revisao_humana=ambiguos / total if total else 0.0,
        taxa_qualidade_entrada=(total - erros) / total if total else 0.0,
        ganho_estimado_horas=(validos * minutos_poupados_por_registro_valido) / 60,
        ranking_regras=ranking,
        minutos_poupados_por_registro_valido=minutos_poupados_por_registro_valido,
    )
