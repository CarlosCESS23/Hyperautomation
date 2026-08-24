import pytest

from src.classificador_divergencia import (
    ClassificadorDivergencia,
)
from src.decisao_hibrida import (
    MotivoFallback,
    OrigemDecisao,
    ResultadoDecisaoHibrida,
)


pytestmark = pytest.mark.unit


class ClienteFake:
    """Cliente controlado usado nos testes."""

    def __init__(
        self,
        resposta=None,
        erro: Exception | None = None,
    ):
        self.resposta = resposta
        self.erro = erro
        self.chamadas = []

    def classificar_observacao(
        self,
        *,
        observacao: str,
    ):
        self.chamadas.append(
            observacao
        )

        if self.erro is not None:
            raise self.erro

        return self.resposta


def test_retorna_decisao_ml_com_resposta_valida():
    cliente = ClienteFake(
        resposta={
            "causa_provavel": "falta_peca",
            "confianca_ml": 0.87,
            "versao_modelo": "2.0.0-texto",
        }
    )

    classificador = ClassificadorDivergencia(
        cliente_ml=cliente
    )

    resultado = classificador.classificar(
        "Produto chegou sem uma peça."
    )

    assert isinstance(
        resultado,
        ResultadoDecisaoHibrida,
    )

    assert resultado.causa_provavel == "falta_peca"
    assert resultado.origem_decisao == OrigemDecisao.ML
    assert resultado.confianca_ml == 0.87
    assert resultado.motivo_fallback is None
    assert resultado.versao_modelo == "2.0.0-texto"

    assert cliente.chamadas == [
        "Produto chegou sem uma peça."
    ]


def test_envia_somente_observacao_necessaria():
    cliente = ClienteFake(
        resposta={
            "causa_provavel": "duplicidade",
            "confianca_ml": 0.91,
            "versao_modelo": "2.0.0-texto",
        }
    )

    classificador = ClassificadorDivergencia(
        cliente_ml=cliente
    )

    classificador.classificar(
        "  Registro   informado duas vezes.  "
    )

    assert cliente.chamadas == [
        "Registro informado duas vezes."
    ]


def test_api_indisponivel_retorna_fallback():
    cliente = ClienteFake(
        resposta=None
    )

    resultado = ClassificadorDivergencia(
        cliente_ml=cliente
    ).classificar(
        "Código não encontrado."
    )

    assert resultado.origem_decisao == (
        OrigemDecisao.FALLBACK
    )

    assert resultado.confianca_ml is None

    assert resultado.motivo_fallback == (
        MotivoFallback.SERVICO_INDISPONIVEL
    )


def test_excecao_do_cliente_nao_chega_ao_bot():
    cliente = ClienteFake(
        erro=ConnectionError(
            "API offline"
        )
    )

    resultado = ClassificadorDivergencia(
        cliente_ml=cliente
    ).classificar(
        "Código não encontrado."
    )

    assert isinstance(
        resultado,
        ResultadoDecisaoHibrida,
    )

    assert resultado.origem_decisao == (
        OrigemDecisao.FALLBACK
    )

    assert resultado.motivo_fallback == (
        MotivoFallback.SERVICO_INDISPONIVEL
    )


@pytest.mark.parametrize(
    "observacao",
    [
        "",
        "   ",
        "a",
        None,
        123,
    ],
)
def test_observacao_invalida_nao_chama_api(
    observacao,
):
    cliente = ClienteFake(
        resposta={
            "causa_provavel": "erro_codigo",
            "confianca_ml": 0.80,
            "versao_modelo": "2.0.0-texto",
        }
    )

    resultado = ClassificadorDivergencia(
        cliente_ml=cliente
    ).classificar(
        observacao
    )

    assert cliente.chamadas == []

    assert resultado.origem_decisao == (
        OrigemDecisao.FALLBACK
    )

    assert resultado.motivo_fallback == (
        MotivoFallback.RESPOSTA_INVALIDA
    )


@pytest.mark.parametrize(
    "resposta",
    [
        None,
        {},
        [],
        {
            "causa_provavel": "falta_peca",
        },
        {
            "causa_provavel": "causa_inexistente",
            "confianca_ml": 0.80,
            "versao_modelo": "2.0.0-texto",
        },
        {
            "causa_provavel": "falta_peca",
            "confianca_ml": "alta",
            "versao_modelo": "2.0.0-texto",
        },
        {
            "causa_provavel": "falta_peca",
            "confianca_ml": True,
            "versao_modelo": "2.0.0-texto",
        },
        {
            "causa_provavel": "falta_peca",
            "confianca_ml": 1.50,
            "versao_modelo": "2.0.0-texto",
        },
        {
            "causa_provavel": "falta_peca",
            "confianca_ml": 0.80,
            "versao_modelo": "",
        },
    ],
)
def test_resposta_invalida_retorna_fallback(
    resposta,
):
    cliente = ClienteFake(
        resposta=resposta
    )

    resultado = ClassificadorDivergencia(
        cliente_ml=cliente
    ).classificar(
        "Produto sem componente."
    )

    assert resultado.origem_decisao == (
        OrigemDecisao.FALLBACK
    )

    assert resultado.motivo_fallback in {
        MotivoFallback.SERVICO_INDISPONIVEL,
        MotivoFallback.RESPOSTA_INVALIDA,
    }

    assert resultado.confianca_ml is None