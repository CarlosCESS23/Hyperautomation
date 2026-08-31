import pytest

from src import config


pytestmark = pytest.mark.unit


def test_converte_flags_booleanas():
    assert config._as_bool(None, default=True) is True
    assert config._as_bool(" YES ") is True
    assert config._as_bool("não") is False


def test_obtem_configuracao_com_defaults(monkeypatch):
    monkeypatch.setattr(config, "carregar_ambiente", lambda: None)
    for nome in (
        "MAESTRO_SERVER", "MAESTRO_LOGIN", "MAESTRO_KEY", "MAESTRO_ENABLED",
        "VAULT_ENABLED", "AUDITORIA_DATAPOOL_LABEL", "CREDENTIAL_LABEL",
        "CREDENTIAL_USER_KEY", "CREDENTIAL_PASSWORD_KEY", "HEADLESS", "URL_BASE",
        "CAMINHO_EVIDENCIA",
    ):
        monkeypatch.delenv(nome, raising=False)

    resultado = config.obter_configuracao()
    assert resultado.maestro_enabled is True
    assert resultado.vault_enabled is True
    assert resultado.url_base == "http://localhost:8080"
    assert resultado.interface_navegador is True


def test_valida_conexao_e_informa_campos_ausentes():
    base = config.Configuracao(
        "", "", "", True, True, "fila", "cred", "user", "pass",
        "http://localhost", True, "evidencia.png",ml_enabled=True
    )
    with pytest.raises(RuntimeError, match="MAESTRO_SERVER, MAESTRO_LOGIN, MAESTRO_KEY"):
        config.validar_conexao(base)

    desabilitada = config.Configuracao(
        "server", "login", "key", False, True, "fila", "cred", "user", "pass",
        "http://localhost", True, "evidencia.png",ml_enabled=True
    )
    with pytest.raises(RuntimeError, match="MAESTRO_ENABLED"):
        config.validar_conexao(desabilitada)
