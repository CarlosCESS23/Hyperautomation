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