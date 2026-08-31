"""Testes dos modos de alerta da execução manual."""

from unittest.mock import Mock

import pytest

import executar_pipeline_bots as modulo_pipeline

from src.sistema_alertas import (
    ResultadoAlerta,
)


pytestmark = pytest.mark.unit


def test_modo_email_usa_email_como_canal_principal(
    monkeypatch,
):
    canal_email = Mock()
    canal_email.nome = "email"

    canal_email.enviar.return_value = (
        ResultadoAlerta(
            sucesso=True,
            canal="email",
        )
    )

    monkeypatch.setattr(
        modulo_pipeline.AdaptadorEmail,
        "de_ambiente",
        lambda **_kwargs: canal_email,
    )

    sistema = (
        modulo_pipeline.criar_sistema_alertas(
            "email",
            Mock(),
        )
    )

    assert sistema is not None

    resultado = sistema.enviar_alerta(
        severidade="INFO",
        mensagem="Pipeline concluído",
        contexto={
            "execution_id": "exec-email-001",
        },
    )

    assert resultado.sucesso is True
    assert resultado.canal == "email"
    canal_email.enviar.assert_called_once()