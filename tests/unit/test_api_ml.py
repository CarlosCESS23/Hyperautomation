import pytest

from fastapi.testclient import TestClient

from api_ml.main import app


pytestmark = pytest.mark.unit

#Vericiando se carrega
def test_predict_com_payload_valido():
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json={
                'status_raw': 'APROVADO',
                "turno": "MANHA",
                "tem_obs": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert "classe" in body
    assert "probabilidade" in body
    assert "nivel_confianca" in body

    assert isinstance(body["classe"], str)
    assert isinstance(body["probabilidade"], float)
    assert isinstance(body["nivel_confianca"], str)


#Testando a predição se realmente retorna invalida
def test_predict_com_turno_invalido_retorna_422():
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json={
                "status_raw": "APROVADO",
                "turno": "MADRUGADA",
                "tem_obs": True,
            },
        )

    assert response.status_code == 422

#Testando com modelo carregado
def test_health_com_modelo_carregado():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "healthy"
    assert body["modelo_carregado"] is True


import api_ml.main as api_main

# Testando modelo ausente
def test_predict_sem_modelo_retorna_503(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setattr(
            api_main,
            "modelo_ml",
            None,
        )

        response = client.post(
            "/predict",
            json={
                "status_raw": "APROVADO",
                "turno": "MANHA",
                "tem_obs": True,
            },
        )

    assert response.status_code == 503

    assert response.json() == {
        "detail": "Modelo de Machine Learning indisponível."
    }

# Testando health
def test_health_sem_modelo_retorna_unhealthy(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setattr(
            api_main,
            "modelo_ml",
            None,
        )

        response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "unhealthy"
    assert body["modelo_carregado"] is False

