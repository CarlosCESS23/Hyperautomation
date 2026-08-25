import pytest

from src.decisao_hibrida import (
    MotivoFallback,
    OrigemDecisao,
    ResultadoDecisaoHibrida,
)


pytestmark = pytest.mark.unit


def test_cria_resultado_produzido_pelo_ml():
    resultado = ResultadoDecisaoHibrida.de_ml(
        causa_provavel="falha_operacional",
        confianca_ml=0.91,
        versao_modelo="1.0.0",
    )

    assert resultado.causa_provavel == "falha_operacional"
    assert resultado.origem_decisao == OrigemDecisao.ML
    assert resultado.confianca_ml == 0.91
    assert resultado.motivo_fallback is None
    assert resultado.versao_modelo == "1.0.0"


def test_cria_resultado_produzido_pelo_fallback():
    resultado = ResultadoDecisaoHibrida.de_fallback(
        motivo=MotivoFallback.TIMEOUT,
    )

    assert resultado.causa_provavel == "nao_classificado"
    assert resultado.origem_decisao == OrigemDecisao.FALLBACK
    assert resultado.confianca_ml is None
    assert resultado.motivo_fallback == MotivoFallback.TIMEOUT


def test_resultado_ml_exige_confianca():
    with pytest.raises(
        ValueError,
        match="confianca_ml é obrigatória",
    ):
        ResultadoDecisaoHibrida(
            causa_provavel="falha_operacional",
            origem_decisao=OrigemDecisao.ML,
        )


@pytest.mark.parametrize(
    "confianca_invalida",
    [-0.01, 1.01],
)
def test_rejeita_confianca_fora_do_intervalo(
    confianca_invalida,
):
    with pytest.raises(
        ValueError,
        match="deve estar entre 0 e 1",
    ):
        ResultadoDecisaoHibrida.de_ml(
            causa_provavel="falha_operacional",
            confianca_ml=confianca_invalida,
        )


def test_resultado_ml_nao_aceita_motivo_fallback():
    with pytest.raises(
        ValueError,
        match="não pode possuir motivo_fallback",
    ):
        ResultadoDecisaoHibrida(
            causa_provavel="falha_operacional",
            origem_decisao=OrigemDecisao.ML,
            confianca_ml=0.85,
            motivo_fallback=MotivoFallback.TIMEOUT,
        )


def test_resultado_fallback_exige_motivo():
    with pytest.raises(
        ValueError,
        match="motivo_fallback é obrigatório",
    ):
        ResultadoDecisaoHibrida(
            causa_provavel="nao_classificado",
            origem_decisao=OrigemDecisao.FALLBACK,
        )


def test_resultado_fallback_nao_aceita_confianca_ml():
    with pytest.raises(
        ValueError,
        match="não pode possuir confianca_ml",
    ):
        ResultadoDecisaoHibrida(
            causa_provavel="nao_classificado",
            origem_decisao=OrigemDecisao.FALLBACK,
            confianca_ml=0.50,
            motivo_fallback=MotivoFallback.TIMEOUT,
        )


def test_rejeita_causa_provavel_vazia():
    with pytest.raises(
        ValueError,
        match="causa_provavel não pode ser vazia",
    ):
        ResultadoDecisaoHibrida.de_ml(
            causa_provavel="   ",
            confianca_ml=0.90,
        )


def test_converte_resultado_para_dicionario():
    resultado = ResultadoDecisaoHibrida.de_fallback(
        motivo=MotivoFallback.ML_DESATIVADO,
    )

    assert resultado.to_dict() == {
        "causa_provavel": "nao_classificado",
        "confianca_ml": None,
        "origem_decisao": "fallback",
        "motivo_fallback": "ml_desativado",
        "versao_modelo": "",
    }