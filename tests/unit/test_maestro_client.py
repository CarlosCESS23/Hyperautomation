"""Testes da criação do cliente BotCity Maestro."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.maestro_client import (
    criar_cliente_maestro_local,
    criar_cliente_maestro_runner,
)


def criar_configuracao_maestro(
    *,
    habilitado: bool = True,
):
    return SimpleNamespace(
        maestro_enabled=habilitado,
        maestro_server=(
            "https://developers.botcity.dev"
        ),
        maestro_login="login-teste",
        maestro_key="chave-teste",
    )


def test_cria_cliente_local_com_credenciais():
    sdk = Mock()
    cliente = Mock()
    sdk.return_value = cliente

    configuracao = criar_configuracao_maestro()

    resultado = criar_cliente_maestro_local(
        configuracao=configuracao,
        sdk_factory=sdk,
    )

    assert resultado is cliente

    sdk.assert_called_once_with()

    cliente.login.assert_called_once_with(
        server=(
            "https://developers.botcity.dev"
        ),
        login="login-teste",
        key="chave-teste",
    )


def test_cliente_local_rejeita_maestro_desativado():
    sdk = Mock()

    configuracao = criar_configuracao_maestro(
        habilitado=False,
    )

    with pytest.raises(
        RuntimeError,
        match="MAESTRO_ENABLED",
    ):
        criar_cliente_maestro_local(
            configuracao=configuracao,
            sdk_factory=sdk,
        )

    sdk.assert_not_called()


def test_cria_cliente_pelos_argumentos_do_runner():
    sdk = Mock()
    cliente = Mock()

    sdk.from_sys_args.return_value = cliente

    resultado = criar_cliente_maestro_runner(
        sdk_factory=sdk,
    )

    assert resultado is cliente

    sdk.from_sys_args.assert_called_once_with()