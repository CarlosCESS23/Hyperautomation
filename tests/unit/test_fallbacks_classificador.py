from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from src import config

import src.classificador_divergencia as modulo_classificador

from src.classificador_divergencia import (
    ClassificadorDivergencia,
)
from src.decisao_hibrida import (
    MotivoFallback,
    OrigemDecisao,
)
from src.ml_client import (
    MLClient,
    MLInvalidResponseError,
    MLServiceUnavailableError,
    MLTimeoutError,
)


pytestmark = pytest.mark.unit

def test_configuracao_ml_enabled_false_impede_chamada_http(
    monkeypatch,
):
    clientes_criados = []

    class ClienteMLControlado:
        def __init__(
            self,
            *,
            base_url,
            timeout,
        ):
            self.base_url = base_url
            self.timeout = timeout
            self.chamadas = []
            clientes_criados.append(self)

        def classificar_observacao(
            self,
            *,
            observacao,
        ):
            self.chamadas.append(observacao)

            raise AssertionError(
                "O cliente HTTP não deveria ser chamado"
            )

    configuracao = SimpleNamespace(
        ml_enabled=False,
        ml_api_url="http://api_ml:8000",
        ml_timeout_seconds=3.0,
        ml_min_confidence=0.75,
    )

    monkeypatch.setattr(
        modulo_classificador,
        "MLClient",
        ClienteMLControlado,
    )

    classificador = (
        ClassificadorDivergencia.de_configuracao(
            configuracao
        )
    )

    resultado = classificador.classificar(
        "Produto sem uma peça."
    )

    assert len(clientes_criados) == 1
    assert clientes_criados[0].chamadas == []

    assert resultado.origem_decisao == (
        OrigemDecisao.FALLBACK
    )

    assert resultado.motivo_fallback == (
        MotivoFallback.ML_DESATIVADO
    )

def test_ml_enabled_desativa_pipeline(
    monkeypatch,
):
    monkeypatch.setattr(
        config,
        "carregar_ambiente",
        lambda: None,
    )

    monkeypatch.setenv(
        "ML_ENABLED",
        "false",
    )

    resultado = config.obter_configuracao()

    assert resultado.ml_enabled is False
class ClienteControlado:
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


def resposta_valida(
    confianca: float = 0.90,
):
    return {
        "causa_provavel": "falta_peca",
        "confianca_ml": confianca,
        "versao_modelo": "2.0.0-texto",
    }


def test_ml_desativado_nao_realiza_chamada():
    cliente = ClienteControlado(
        resposta=resposta_valida()
    )

    classificador = ClassificadorDivergencia(
        cliente_ml=cliente,
        ml_enabled=False,
        confianca_minima=0.75,
    )

    resultado = classificador.classificar(
        "Produto sem uma peça."
    )

    assert cliente.chamadas == []

    assert resultado.origem_decisao == (
        OrigemDecisao.FALLBACK
    )

    assert resultado.motivo_fallback == (
        MotivoFallback.ML_DESATIVADO
    )


def test_timeout_possui_fallback_especifico():
    cliente = ClienteControlado(
        erro=MLTimeoutError(
            "Tempo excedido"
        )
    )

    resultado = ClassificadorDivergencia(
        cliente_ml=cliente,
    ).classificar(
        "Código não localizado."
    )

    assert resultado.motivo_fallback == (
        MotivoFallback.TIMEOUT
    )


def test_servico_indisponivel_possui_fallback_especifico():
    cliente = ClienteControlado(
        erro=MLServiceUnavailableError(
            "API offline"
        )
    )

    resultado = ClassificadorDivergencia(
        cliente_ml=cliente,
    ).classificar(
        "Código não localizado."
    )

    assert resultado.motivo_fallback == (
        MotivoFallback.SERVICO_INDISPONIVEL
    )


def test_resposta_malformada_possui_fallback_especifico():
    cliente = ClienteControlado(
        erro=MLInvalidResponseError(
            "JSON inválido"
        )
    )

    resultado = ClassificadorDivergencia(
        cliente_ml=cliente,
    ).classificar(
        "Código não localizado."
    )

    assert resultado.motivo_fallback == (
        MotivoFallback.RESPOSTA_INVALIDA
    )


def test_baixa_confianca_descarta_sugestao():
    cliente = ClienteControlado(
        resposta=resposta_valida(
            confianca=0.74,
        )
    )

    resultado = ClassificadorDivergencia(
        cliente_ml=cliente,
        confianca_minima=0.75,
    ).classificar(
        "Produto sem uma peça."
    )

    assert resultado.origem_decisao == (
        OrigemDecisao.FALLBACK
    )

    assert resultado.motivo_fallback == (
        MotivoFallback.BAIXA_CONFIANCA
    )

    assert resultado.causa_provavel == (
        "nao_classificado"
    )

    assert resultado.confianca_ml is None


def test_confianca_igual_ao_limiar_e_aceita():
    cliente = ClienteControlado(
        resposta=resposta_valida(
            confianca=0.75,
        )
    )

    resultado = ClassificadorDivergencia(
        cliente_ml=cliente,
        confianca_minima=0.75,
    ).classificar(
        "Produto sem uma peça."
    )

    assert resultado.origem_decisao == (
        OrigemDecisao.ML
    )

    assert resultado.confianca_ml == 0.75
    assert resultado.motivo_fallback is None


def test_erro_inesperado_nao_propaga_excecao():
    cliente = ClienteControlado(
        erro=RuntimeError(
            "Falha inesperada"
        )
    )

    resultado = ClassificadorDivergencia(
        cliente_ml=cliente,
    ).classificar(
        "Código não localizado."
    )

    assert resultado.origem_decisao == (
        OrigemDecisao.FALLBACK
    )

    assert resultado.motivo_fallback == (
        MotivoFallback.SERVICO_INDISPONIVEL
    )


def test_ml_client_respeita_timeout_configurado():
    session = Mock()

    session.post.side_effect = (
        requests.Timeout(
            "Tempo excedido"
        )
    )

    cliente = MLClient(
        base_url="http://api-ml-teste:8000",
        timeout=1.25,
        session=session,
    )

    with pytest.raises(
        MLTimeoutError
    ):
        cliente.classificar_observacao(
            observacao="Produto sem peça."
        )

    session.post.assert_called_once_with(
        "http://api-ml-teste:8000/predict",
        json={
            "observacao": "Produto sem peça."
        },
        timeout=1.25,
    )


def test_fabrica_aplica_configuracao(
    monkeypatch,
):
    parametros_cliente = {}

    class ClienteCriado:
        def __init__(
            self,
            *,
            base_url,
            timeout,
        ):
            parametros_cliente["base_url"] = (
                base_url
            )

            parametros_cliente["timeout"] = (
                timeout
            )

    config = SimpleNamespace(
        ml_api_url="http://api-configurada:8000",
        ml_timeout_seconds=2.50,
        ml_min_confidence=0.82,
        ml_enabled=False,
    )

    monkeypatch.setattr(
        modulo_classificador,
        "MLClient",
        ClienteCriado,
    )

    classificador = (
        ClassificadorDivergencia
        .de_configuracao(config)
    )

    assert parametros_cliente == {
        "base_url": "http://api-configurada:8000",
        "timeout": 2.50,
    }

    resultado = classificador.classificar(
        "Produto sem uma peça."
    )

    assert resultado.motivo_fallback == (
        MotivoFallback.ML_DESATIVADO
    )

