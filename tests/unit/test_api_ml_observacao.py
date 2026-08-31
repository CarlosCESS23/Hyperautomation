from unittest.mock import Mock

import pytest

from fastapi.testclient import TestClient

import api_ml.main as api_main
from src.causas_divergencia import (
    CAUSAS_PROVAVEIS,
)
from train_model import MODEL_VERSION


pytestmark = pytest.mark.unit


class ModeloFake:
    """Modelo controlado para testar a API isoladamente."""

    classes_ = [
        "duplicidade",
        "erro_cadastro",
        "erro_codigo",
        "falta_peca",
    ]

    def __init__(self):
        self.ultima_entrada = None

    def predict(self, observacoes):
        self.ultima_entrada = observacoes

        return [
            "falta_peca"
        ]

    def predict_proba(self, observacoes):
        self.ultima_entrada = observacoes

        return [
            [
                0.05,
                0.05,
                0.10,
                0.80,
            ]
        ]


@pytest.fixture
def cliente_com_modelo(monkeypatch):
    modelo = ModeloFake()

    carregar_modelo = Mock(
        return_value=modelo
    )

    monkeypatch.setattr(
        api_main.joblib,
        "load",
        carregar_modelo,
    )

    with TestClient(api_main.app) as client:
        yield client, modelo, carregar_modelo


def test_predict_com_observacao_valida(
    cliente_com_modelo,
):
    client, _, _ = cliente_com_modelo

    response = client.post(
        "/predict",
        json={
            "observacao": (
                "O produto chegou sem uma "
                "peça necessária."
            )
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body == {
        "causa_provavel": "falta_peca",
        "confianca_ml": 0.80,
        "versao_modelo": MODEL_VERSION,
    }

    assert (
        body["causa_provavel"]
        in CAUSAS_PROVAVEIS
    )


def test_api_nao_retorna_status_de_negocio(
    cliente_com_modelo,
):
    client, _, _ = cliente_com_modelo

    response = client.post(
        "/predict",
        json={
            "observacao": (
                "Registro encontrado duas vezes."
            )
        },
    )

    body = response.json()

    assert "status" not in body
    assert "classe" not in body
    assert "acao_recomendada" not in body
    assert "nivel_confianca" not in body


def test_normaliza_espacos_da_observacao(
    cliente_com_modelo,
):
    client, modelo, _ = cliente_com_modelo

    response = client.post(
        "/predict",
        json={
            "observacao": (
                "  Produto   sem   uma peça  "
            )
        },
    )

    assert response.status_code == 200

    assert modelo.ultima_entrada == [
        "Produto sem uma peça"
    ]


@pytest.mark.parametrize(
    "observacao",
    [
        "",
        "   ",
        "\n\t",
        "a",
    ],
)
def test_rejeita_observacao_vazia_ou_curta(
    cliente_com_modelo,
    observacao,
):
    client, _, _ = cliente_com_modelo

    response = client.post(
        "/predict",
        json={
            "observacao": observacao
        },
    )

    assert response.status_code == 422


def test_rejeita_observacao_ausente(
    cliente_com_modelo,
):
    client, _, _ = cliente_com_modelo

    response = client.post(
        "/predict",
        json={},
    )

    assert response.status_code == 422


def test_rejeita_observacao_muito_grande(
    cliente_com_modelo,
):
    client, _, _ = cliente_com_modelo

    response = client.post(
        "/predict",
        json={
            "observacao": "a" * 2001
        },
    )

    assert response.status_code == 422


def test_health_com_modelo_carregado(
    cliente_com_modelo,
):
    client, _, carregar_modelo = (
        cliente_com_modelo
    )

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
        "modelo_carregado": True,
        "versao_modelo": MODEL_VERSION,
    }

    carregar_modelo.assert_called_once_with(
        api_main.MODEL_PATH
    )


def test_predict_sem_modelo_retorna_503(
    monkeypatch,
):
    def modelo_indisponivel(_):
        raise FileNotFoundError(
            "Modelo não encontrado"
        )

    monkeypatch.setattr(
        api_main.joblib,
        "load",
        modelo_indisponivel,
    )

    with TestClient(api_main.app) as client:
        response = client.post(
            "/predict",
            json={
                "observacao": (
                    "Código do produto inválido."
                )
            },
        )

    assert response.status_code == 503

    assert response.json() == {
        "detail": (
            "Modelo de Machine Learning "
            "indisponível."
        )
    }


def test_health_sem_modelo_retorna_unhealthy(
    monkeypatch,
):
    def modelo_indisponivel(_):
        raise FileNotFoundError(
            "Modelo não encontrado"
        )

    monkeypatch.setattr(
        api_main.joblib,
        "load",
        modelo_indisponivel,
    )

    with TestClient(api_main.app) as client:
        response = client.get(
            "/health"
        )

    assert response.status_code == 200

    assert response.json() == {
        "status": "unhealthy",
        "modelo_carregado": False,
        "versao_modelo": None,
    }