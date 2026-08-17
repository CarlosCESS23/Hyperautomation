import pytest

from src.operational_indicators import (
    _percentual,
    calcular_indicadores,
    _nome_regra,
    NOMES_REGRAS
)
from src.validacao_lotes import RegistroValidado


pytestmark = pytest.mark.unit


def criar_registro(
    classificacao="Válido",
    regra_aplicada="",
):
    return RegistroValidado(
        data_referencia="15/06/2026",
        lote="LOTE-001",
        produto="Produto A",
        linha="Linha 1",
        turno="Manhã",
        status="APROVADO",
        responsavel="Ana",
        data_inspecao="15/06/2026",
        observacao="Inspeção concluída",
        classificacao=classificacao,
        motivo="Motivo de teste",
        acao_recomendada="Nenhuma ação necessária",
        regra_aplicada=regra_aplicada,
    )


@pytest.mark.parametrize(
    ("parte", "total", "esperado"),
    [
        pytest.param(50, 100, 50.0, id="cinquenta-por-cento"),
        pytest.param(1, 4, 25.0, id="vinte-cinco-por-cento"),
        pytest.param(0, 10, 0.0, id="parte-zero"),
        pytest.param(10, 0, 0.0, id="divisao-por-zero"),
    ],
)
def test_percentual(parte, total, esperado):
    resultado = _percentual(parte, total)

    assert resultado == pytest.approx(esperado)


def test_calcula_total_de_registros():
    registros = [
        criar_registro(),
        criar_registro(),
        criar_registro(),
    ]

    indicadores = calcular_indicadores(registros)

    assert indicadores.total_registros == 3


def test_calcula_quantidade_e_percentual_por_classificacao():
    registros = [
        criar_registro("Válido"),
        criar_registro("Válido"),
        criar_registro("Divergência", "RN10"),
        criar_registro("Ambíguo", "RN09"),
        criar_registro("Erro de Entrada", "RN12"),
    ]

    indicadores = calcular_indicadores(registros)

    assert indicadores.validos == 2
    assert indicadores.percentual_validos == pytest.approx(40.0)

    assert indicadores.divergencias == 1
    assert indicadores.percentual_divergencias == pytest.approx(20.0)

    assert indicadores.ambiguos == 1
    assert indicadores.percentual_ambiguos == pytest.approx(20.0)

    assert indicadores.erros_entrada == 1
    assert indicadores.percentual_erros_entrada == pytest.approx(20.0)


def test_identifica_regra_mais_acionada():
    registros = [
        criar_registro("Divergência", "RN10"),
        criar_registro("Divergência", "RN10"),
        criar_registro("Divergência", "RN05"),
        criar_registro("Ambíguo", "RN09"),
    ]

    indicadores = calcular_indicadores(registros)

    assert indicadores.regra_mais_acionada == "RN10"
    assert indicadores.nome_regra_mais_acionada == 'Lote reprovado sem observação'
    assert indicadores.quantidade_regra_mais_acionada == 2


def test_contabiliza_multiplas_regras_no_mesmo_registro():
    registros = [
        criar_registro(
            "Divergência",
            "RN05, RN10",
        ),
        criar_registro(
            "Divergência",
            "RN10, RN11",
        ),
    ]

    indicadores = calcular_indicadores(registros)

    assert indicadores.contagem_regras == {
        "RN05": 1,
        "RN10": 2,
        "RN11": 1,
    }

    assert indicadores.regra_mais_acionada == "RN10"
    assert indicadores.quantidade_regra_mais_acionada == 2


def test_calcula_taxa_qualidade_entrada():
    registros = [
        criar_registro("Válido"),
        criar_registro("Válido"),
        criar_registro("Válido"),
        criar_registro("Erro de Entrada", "RN12"),
    ]

    indicadores = calcular_indicadores(registros)

    assert indicadores.taxa_qualidade_entrada == pytest.approx(
        75.0
    )


def test_calcula_taxa_revisao_humana():
    registros = [
        criar_registro("Válido"),
        criar_registro("Válido"),
        criar_registro("Válido"),
        criar_registro("Ambíguo", "RN09"),
    ]

    indicadores = calcular_indicadores(registros)

    assert indicadores.taxa_revisao_humana == pytest.approx(
        25.0
    )


def test_calcula_taxa_retrabalho():
    registros = [
        criar_registro("Válido"),
        criar_registro("Válido"),
        criar_registro("Divergência", "RN05"),
        criar_registro("Divergência", "RN10"),
    ]

    indicadores = calcular_indicadores(registros)

    assert indicadores.taxa_retrabalho == pytest.approx(
        50.0
    )


def test_calcula_ganho_estimado_tempo():
    registros = [
        criar_registro(),
        criar_registro(),
        criar_registro(),
    ]

    indicadores = calcular_indicadores(
        registros,
        tempo_manual_por_registro=5.0,
        tempo_automatizado_por_registro=1.0,
    )

    assert indicadores.ganho_estimado_tempo == pytest.approx(
        12.0
    )

    assert indicadores.tempo_manual_por_registro == 5.0
    assert indicadores.tempo_automatizado_por_registro == 1.0


def test_lista_vazia_retorna_indicadores_zerados():
    indicadores = calcular_indicadores([])

    assert indicadores.total_registros == 0

    assert indicadores.validos == 0
    assert indicadores.percentual_validos == 0.0

    assert indicadores.divergencias == 0
    assert indicadores.percentual_divergencias == 0.0

    assert indicadores.ambiguos == 0
    assert indicadores.percentual_ambiguos == 0.0

    assert indicadores.erros_entrada == 0
    assert indicadores.percentual_erros_entrada == 0.0

    assert indicadores.regra_mais_acionada == ""
    assert indicadores.nome_regra_mais_acionada == ''
    assert indicadores.quantidade_regra_mais_acionada == 0

    assert indicadores.taxa_qualidade_entrada == 0.0
    assert indicadores.taxa_revisao_humana == 0.0
    assert indicadores.taxa_retrabalho == 0.0

    assert indicadores.ganho_estimado_tempo == 0.0
    assert indicadores.contagem_regras == {}

def test_retorna_nome_da_regra():
    assert _nome_regra('RN10') == 'Lote reprovado sem observação'

def test_regra_desconhecida_retorna_texto_vazio():
    assert _nome_regra('RN99') == ''

@pytest.mark.parametrize(
    ("codigo", "nome"),
    [
        (
            "RN05",
            "Lote não encontrado na base de referência",
        ),
        (
            "RN09",
            "Status desconhecido e não normalizável",
        ),
        (
            "RN10",
            "Lote reprovado sem observação",
        ),
        (
            "RN11",
            "Lote duplicado dentro da mesma planilha ou dia",
        ),
        (
            "RN12",
            "Data de inspeção ausente ou fora do formato DD/MM/AAAA",
        ),
    ],
)
def test_nomes_das_regras(codigo, nome):
    assert _nome_regra(codigo) == nome