import pytest

from src import config


pytestmark = pytest.mark.unit


VARIAVEIS_PIPELINE = (
    "PIPELINE_HIBRIDO_ENABLED",
    "ML_API_URL",
    "ML_MIN_CONFIDENCE",
    "ML_TIMEOUT_SECONDS",
)


def limpar_variaveis(monkeypatch):
    for nome in VARIAVEIS_PIPELINE:
        monkeypatch.delenv(nome, raising=False)


def test_pipeline_hibrido_fica_desativado_por_padrao(
    monkeypatch,
):
    monkeypatch.setattr(
        config,
        "carregar_ambiente",
        lambda: None,
    )

    limpar_variaveis(monkeypatch)

    resultado = config.obter_configuracao()

    assert resultado.pipeline_hibrido_enabled is False
    assert resultado.ml_api_url == "http://localhost:8000"
    assert resultado.ml_min_confidence == 0.75
    assert resultado.ml_timeout_seconds == 3.0


def test_carrega_configuracao_do_pipeline_pelo_ambiente(
    monkeypatch,
):
    monkeypatch.setattr(
        config,
        "carregar_ambiente",
        lambda: None,
    )

    monkeypatch.setenv(
        "PIPELINE_HIBRIDO_ENABLED",
        "true",
    )
    monkeypatch.setenv(
        "ML_API_URL",
        "http://api_ml:8000/",
    )
    monkeypatch.setenv(
        "ML_MIN_CONFIDENCE",
        "0.85",
    )
    monkeypatch.setenv(
        "ML_TIMEOUT_SECONDS",
        "5",
    )

    resultado = config.obter_configuracao()

    assert resultado.pipeline_hibrido_enabled is True
    assert resultado.ml_api_url == "http://api_ml:8000"
    assert resultado.ml_min_confidence == 0.85
    assert resultado.ml_timeout_seconds == 5.0


@pytest.mark.parametrize(
    "valor",
    ["-0.01", "1.01"],
)
def test_rejeita_confianca_fora_do_intervalo(
    monkeypatch,
    valor,
):
    monkeypatch.setattr(
        config,
        "carregar_ambiente",
        lambda: None,
    )

    monkeypatch.setenv("ML_MIN_CONFIDENCE", valor)

    with pytest.raises(
        ValueError,
        match="deve estar entre 0 e 1",
    ):
        config.obter_configuracao()


@pytest.mark.parametrize(
    "valor",
    ["0", "-1"],
)
def test_rejeita_timeout_menor_ou_igual_a_zero(
    monkeypatch,
    valor,
):
    monkeypatch.setattr(
        config,
        "carregar_ambiente",
        lambda: None,
    )

    monkeypatch.setenv("ML_TIMEOUT_SECONDS", valor)

    with pytest.raises(
        ValueError,
        match="deve ser maior que zero",
    ):
        config.obter_configuracao()


def test_rejeita_valor_nao_numerico(
    monkeypatch,
):
    monkeypatch.setattr(
        config,
        "carregar_ambiente",
        lambda: None,
    )

    monkeypatch.setenv(
        "ML_MIN_CONFIDENCE",
        "oitenta",
    )

    with pytest.raises(
        ValueError,
        match="deve possuir um valor numérico",
    ):
        config.obter_configuracao()