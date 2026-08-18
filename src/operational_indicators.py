"""Fonte única dos indicadores operacionais do relatório executivo."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace

from src.validacao_lotes import RegistroValidado


DESCRICOES_REGRAS = {
    "RN01": "Lote obrigatório não informado",
    "RN02": "Produto obrigatório não informado",
    "RN03": "Linha obrigatória não informada",
    "RN04": "Status obrigatório não informado",
    "RN05": "Lote não encontrado na base de referência",
    "RN06": "Status OK é normalizado para APROVADO",
    "RN07": "Status NOK é normalizado para REPROVADO",
    "RN08": "Status padronizado é considerado válido",
    "RN09": "Status desconhecido e não normalizável",
    "RN10": "Lote reprovado sem observação",
    "RN11": "Lote duplicado dentro da mesma planilha ou dia",
    "RN12": "Data de inspeção ausente ou fora do formato DD/MM/AAAA",
}

# Catálogo completo da API histórica da branch main. Ele permanece separado de
# DESCRICOES_REGRAS porque o validador atual consolidou/renumerou algumas RNs.
NOMES_REGRAS = {
    "RN01": "Lote obrigatório não informado",
    "RN02": "Produto obrigatório não informado",
    "RN03": "Linha obrigatória não informada",
    "RN04": "Status obrigatório não informado",
    "RN05": "Lote não encontrado na base de referência",
    "RN06": "Status OK é normalizado para APROVADO",
    "RN07": "Status NOK é normalizado para REPROVADO",
    "RN08": "Status padronizado é considerado válido",
    "RN09": "Status desconhecido e não normalizável",
    "RN10": "Lote reprovado sem observação",
    "RN11": "Lote duplicado dentro da mesma planilha ou dia",
    "RN12": "Data de inspeção ausente ou fora do formato DD/MM/AAAA",
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
    minutos_poupados_por_registro_valido: float = 5
    tempo_manual_por_registro: float = 6.0
    tempo_automatizado_por_registro: float = 1.0

    @property
    def percentual_validos(self) -> float:
        return _percentual(self.validos, self.total_registros)

    @property
    def percentual_divergencias(self) -> float:
        return _percentual(self.divergencias, self.total_registros)

    @property
    def percentual_ambiguos(self) -> float:
        return _percentual(self.ambiguos, self.total_registros)

    @property
    def percentual_erros_entrada(self) -> float:
        return _percentual(self.erros_entrada, self.total_registros)

    @property
    def quantidade_regra_mais_acionada(self) -> int:
        return self.ranking_regras[0].quantidade if self.ranking_regras else 0

    @property
    def nome_regra_mais_acionada(self) -> str:
        return _nome_regra(self.regra_mais_acionada)

    @property
    def contagem_regras(self) -> dict[str, int]:
        return {regra.codigo: regra.quantidade for regra in self.ranking_regras}

    @property
    def ganho_estimado_tempo(self) -> float:
        """Economia total em minutos, conforme a API histórica da main."""
        return self.total_registros * (
            self.tempo_manual_por_registro
            - self.tempo_automatizado_por_registro
        )

    @property
    def descricao_regra_mais_acionada(self) -> str:
        return DESCRICOES_REGRAS.get(self.regra_mais_acionada, "Nenhuma regra acionada")


def _percentual(parte: int | float, total: int | float) -> float:
    """Retorna ``parte`` como percentual de ``total`` (escala de 0 a 100)."""
    return (parte / total) * 100 if total else 0.0


def _nome_regra(codigo: str) -> str:
    """Retorna a descrição pública de uma regra de negócio."""
    return NOMES_REGRAS.get(codigo, "")


def _contar_regras(registros: list[RegistroValidado]) -> Counter[str]:
    """Conta todos os acionamentos, inclusive mais de uma regra por registro."""
    return Counter(
        regra.strip()
        for registro in registros
        for regra in registro.regras_acionadas
        if regra.strip()
    )


def consolidar_indicadores(
    registros: list[RegistroValidado],
    minutos_poupados_por_registro_valido: float = 5,
) -> OperationalIndicators:
    """Consolida uma vez os dez indicadores e o ranking derivado das RNs."""
    classificacoes = Counter(registro.classificacao for registro in registros)
    regras = _contar_regras(registros)
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


def calcular_indicadores(
    registros: list[RegistroValidado],
    tempo_manual_por_registro: float = 5.0,
    tempo_automatizado_por_registro: float = 1.0,
) -> OperationalIndicators:
    """Compatibilidade com a API da main usando o consolidador atual.

    Os tempos recebidos estão em minutos. A diferença entre eles é usada como
    economia por registro válido, mantendo o ganho expresso em horas.
    """
    minutos_poupados = tempo_manual_por_registro - tempo_automatizado_por_registro
    indicadores = consolidar_indicadores(
        registros,
        minutos_poupados_por_registro_valido=minutos_poupados,
    )
    # A função histórica expõe taxas na escala percentual. O consolidador,
    # consumido pelo relatório atual, mantém taxas normalizadas entre 0 e 1.
    return replace(
        indicadores,
        taxa_retrabalho=_percentual(indicadores.divergencias, indicadores.total_registros),
        taxa_revisao_humana=_percentual(indicadores.ambiguos, indicadores.total_registros),
        taxa_qualidade_entrada=_percentual(
            indicadores.total_registros - indicadores.erros_entrada,
            indicadores.total_registros,
        ),
        tempo_manual_por_registro=tempo_manual_por_registro,
        tempo_automatizado_por_registro=tempo_automatizado_por_registro,
    )
