import pytest

from src.operational_indicators import consolidar_indicadores
from src.validacao_lotes import RegistroValidado


pytestmark = pytest.mark.unit


def registro(classificacao, regras=()):
    return RegistroValidado(
        "15/06/2026", "L1", "P", "1", "M", "APROVADO", "Ana",
        "15/06/2026", "", classificacao, "motivo", "ação", regras,
    )


def test_consolida_dez_indicadores_e_ordena_ranking():
    indicadores = consolidar_indicadores([
        registro("Válido"),
        registro("Válido"),
        registro("Divergência", ("RN11",)),
        registro("Divergência", ("RN09", "RN11")),
        registro("Ambíguo", ("RN08",)),
        registro("Erro de Entrada", ("RN12",)),
    ])

    assert (indicadores.total_registros, indicadores.validos) == (6, 2)
    assert indicadores.regra_mais_acionada == "RN11"
    assert indicadores.ranking_regras[0].quantidade == 2
    assert indicadores.taxa_retrabalho == pytest.approx(0.5)
    assert indicadores.taxa_revisao_humana == pytest.approx(1 / 6)
    assert indicadores.taxa_qualidade_entrada == pytest.approx(5 / 6)
    assert indicadores.ganho_estimado_horas == pytest.approx(10 / 60)


def test_base_vazia_tem_percentuais_e_ranking_neutros():
    indicadores = consolidar_indicadores([])
    assert indicadores.total_registros == 0
    assert indicadores.regra_mais_acionada == "Nenhuma"
    assert indicadores.descricao_regra_mais_acionada == "Nenhuma regra acionada"
    assert indicadores.ranking_regras == ()
    assert indicadores.taxa_retrabalho == 0
