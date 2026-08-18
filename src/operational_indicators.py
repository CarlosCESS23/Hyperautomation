from collections import Counter
from dataclasses import dataclass

from src.validacao_lotes import RegistroValidado

#Implementando nome_regras

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
class OperationalIndicators:
    total_registros: int

    validos: int
    percentual_validos: float

    divergencias: int
    percentual_divergencias: float

    ambiguos: int
    percentual_ambiguos: float

    erros_entrada: int
    percentual_erros_entrada: float

    regra_mais_acionada: str
    quantidade_regra_mais_acionada: int
    nome_regra_mais_acionada : str

    taxa_qualidade_entrada: float
    taxa_revisao_humana: float
    taxa_retrabalho: float

    ganho_estimado_tempo: float

    tempo_manual_por_registro: float
    tempo_automatizado_por_registro: float

    contagem_regras: dict[str, int]


def _percentual(
    parte: int | float,
    total: int | float,) -> float:
    """Faz o calculo para porcentagem"""
    if total == 0:
        return 0.0

    return (parte / total) * 100



def _nome_regra(codigo : str) -> str:
    """Retorna o nome da regra"""
    return NOMES_REGRAS.get(codigo , '')

def _contar_regras(
    registros: list[RegistroValidado],
) -> Counter:
    """Conta quantas divergencias e regras são aplicadas"""
    regras = []

    for registro in registros:
        if not registro.regra_aplicada:
            continue

        regras_registro = registro.regra_aplicada.split(",")

        for regra in regras_registro:
            regra = regra.strip()

            if regra:
                regras.append(regra)

    return Counter(regras)


def calcular_indicadores(
    registros: list[RegistroValidado],
    tempo_manual_por_registro: float = 5.0,
    tempo_automatizado_por_registro: float = 1.0,
) -> OperationalIndicators:
    """Faz as buscas e traz os resultados (Como porcentagens)"""

    total = len(registros)

    validos = sum(
        1
        for registro in registros
        if registro.classificacao == "Válido"
    )

    divergencias = sum(
        1
        for registro in registros
        if registro.classificacao == "Divergência"
    )

    ambiguos = sum(
        1
        for registro in registros
        if registro.classificacao == "Ambíguo"
    )

    erros_entrada = sum(
        1
        for registro in registros
        if registro.classificacao == "Erro de Entrada"
    )

    contagem_regras = _contar_regras(registros)

    if contagem_regras:
        regra_mais_acionada, quantidade_regra_mais_acionada = (
            contagem_regras.most_common(1)[0]
        )
        nome_regra_mais_acionada = _nome_regra(regra_mais_acionada)
    else:
        regra_mais_acionada = ''
        nome_regra_mais_acionada = ''
        quantidade_regra_mais_acionada = 0

    percentual_validos = _percentual(validos, total)
    percentual_divergencias = _percentual(
        divergencias,
        total,
    )
    percentual_ambiguos = _percentual(
        ambiguos,
        total,
    )
    percentual_erros_entrada = _percentual(
        erros_entrada,
        total,
    )

    taxa_qualidade_entrada = _percentual(
        total - erros_entrada,
        total,
    )

    taxa_revisao_humana = _percentual(
        ambiguos,
        total,
    )

    taxa_retrabalho = _percentual(
        divergencias,
        total,
    )

    ganho_estimado_tempo = (
        total
        * (
            tempo_manual_por_registro
            - tempo_automatizado_por_registro
        )
    )

    return OperationalIndicators(
        total_registros=total,

        validos=validos,
        percentual_validos=percentual_validos,

        divergencias=divergencias,
        percentual_divergencias=percentual_divergencias,

        ambiguos=ambiguos,
        percentual_ambiguos=percentual_ambiguos,

        erros_entrada=erros_entrada,
        percentual_erros_entrada=percentual_erros_entrada,

        regra_mais_acionada=regra_mais_acionada,
        nome_regra_mais_acionada = nome_regra_mais_acionada,
        quantidade_regra_mais_acionada=(
            quantidade_regra_mais_acionada
        ),

        taxa_qualidade_entrada=taxa_qualidade_entrada,
        taxa_revisao_humana=taxa_revisao_humana,
        taxa_retrabalho=taxa_retrabalho,

        ganho_estimado_tempo=ganho_estimado_tempo,

        tempo_manual_por_registro=(
            tempo_manual_por_registro
        ),
        tempo_automatizado_por_registro=(
            tempo_automatizado_por_registro
        ),

        contagem_regras=dict(contagem_regras),
    )