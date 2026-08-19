from unittest.mock import Mock

import pytest
import requests

from src.ml_client import MLClient

@pytest.mark.unit
def test_retorna_predicao_e_reinicia_contador_de_falhas():
    session = Mock()
    resposta = Mock()
    resposta.raise_for_status.return_value = None
    resposta.json.return_value = {
        "classe": "válido_automático",
        "probabilidade": 0.91,
        "nivel_confianca": "acao_automatica",
    }
    session.post.return_value = resposta

    client = MLClient(session=session)
    client.falhas_consecutivas = 2

    predicao = client.classificar(
        status_raw="APROVADO",
        turno="MANHA",
        tem_obs=True,
    )

    assert predicao["classe"] == "válido_automático"
    assert client.falhas_consecutivas == 0
    assert client.circuito_aberto is False


@pytest.mark.unit
def test_abre_circuito_apos_cinco_falhas_e_para_chamadas_de_rede():
    session = Mock()
    session.post.side_effect = requests.Timeout()

    client = MLClient(session=session)

    for _ in range(5):
        assert client.classificar(
            status_raw="APROVADO",
            turno="MANHA",
            tem_obs=False,
        ) is None

    assert client.falhas_consecutivas == 5
    assert client.circuito_aberto is True
    assert session.post.call_count == 5

    # A sexta chamada não acessa a rede.
    assert client.classificar(
        status_raw="APROVADO",
        turno="MANHA",
        tem_obs=False,
    ) is None

    assert session.post.call_count == 5

@pytest.mark.unit
def test_ml_client_retorna_predicao_com_sucesso():
    session_mock = Mock()

    resposta_mock = Mock()

    resposta_mock.json.return_value = {
        "classe": "valido_automatico",
        "probabilidade": 0.95,
        "nivel_confianca": "acao_automatica",
    }

    session_mock.post.return_value = resposta_mock

    client = MLClient(
        base_url="http://api-ml-teste:8000",
        session=session_mock,
    )

    resultado = client.classificar(
        status_raw="APROVADO",
        turno="MANHA",
        tem_obs=True,
    )

    assert resultado == {
        "classe": "valido_automatico",
        "probabilidade": 0.95,
        "nivel_confianca": "acao_automatica",
    }

    assert client.falhas_consecutivas == 0
    assert client.circuito_aberto is False

@pytest.mark.unit
def test_ml_client_api_offline_retorna_none():
    session_mock = Mock()

    session_mock.post.side_effect = (
        requests.ConnectionError(
            "API indisponível"
        )
    )

    client = MLClient(
        base_url="http://api-ml-teste:8000",
        session=session_mock,
    )

    resultado = client.classificar(
        status_raw="APROVADO",
        turno="MANHA",
        tem_obs=True,
    )

    assert resultado is None
    assert client.falhas_consecutivas == 1
    assert client.circuito_aberto is False

@pytest.mark.unit
def test_circuit_breaker_abre_apos_cinco_falhas():
    session_mock = Mock()

    session_mock.post.side_effect = (
        requests.ConnectionError(
            "API indisponível"
        )
    )

    client = MLClient(
        base_url="http://api-ml-teste:8000",
        limite_falhas=5,
        session=session_mock,
    )

    for _ in range(5):
        resultado = client.classificar(
            status_raw="APROVADO",
            turno="MANHA",
            tem_obs=True,
        )

        assert resultado is None

    assert client.falhas_consecutivas == 5
    assert client.circuito_aberto is True

@pytest.mark.unit
def test_circuit_breaker_aberto_nao_tenta_nova_chamada():
    session_mock = Mock()

    session_mock.post.side_effect = (
        requests.ConnectionError(
            "API indisponível"
        )
    )

    client = MLClient(
        base_url="http://api-ml-teste:8000",
        limite_falhas=5,
        session=session_mock,
    )

    for _ in range(5):
        client.classificar(
            status_raw="APROVADO",
            turno="MANHA",
            tem_obs=True,
        )

    assert client.circuito_aberto is True

    quantidade_chamadas_antes = (
        session_mock.post.call_count
    )

    resultado = client.classificar(
        status_raw="APROVADO",
        turno="MANHA",
        tem_obs=True,
    )

    quantidade_chamadas_depois = (
        session_mock.post.call_count
    )

    assert resultado is None

    assert quantidade_chamadas_antes == 5
    assert quantidade_chamadas_depois == 5

@pytest.mark.unit
def test_resetar_circuito():
    session_mock = Mock()

    session_mock.post.side_effect = (
        requests.ConnectionError(
            "API indisponível"
        )
    )

    client = MLClient(
        limite_falhas=5,
        session=session_mock,
    )

    for _ in range(5):
        client.classificar(
            status_raw="APROVADO",
            turno="MANHA",
            tem_obs=True,
        )

    assert client.circuito_aberto is True
    assert client.falhas_consecutivas == 5

    client.resetar_circuito()

    assert client.circuito_aberto is False
    assert client.falhas_consecutivas == 0