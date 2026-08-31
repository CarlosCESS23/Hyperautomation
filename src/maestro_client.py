"""Criação de clientes para o BotCity Maestro."""

from __future__ import annotations

from typing import Any

from botcity.maestro import BotMaestroSDK

from src.config import (
    Configuracao,
    obter_configuracao,
    validar_conexao,
)


def criar_cliente_maestro_local(
    *,
    configuracao: Configuracao | None = None,
    sdk_factory: Any = None,
) -> BotMaestroSDK:
    """
    Cria um cliente para testes locais.

    As credenciais são carregadas do arquivo .env.
    Esse modo não deve ser usado no Runner.
    """

    config = (
        configuracao
        if configuracao is not None
        else obter_configuracao()
    )

    validar_conexao(config)

    fabrica = (
        sdk_factory
        if sdk_factory is not None
        else BotMaestroSDK
    )

    cliente = fabrica()

    cliente.login(
        server=config.maestro_server,
        login=config.maestro_login,
        key=config.maestro_key,
    )

    return cliente


def criar_cliente_maestro_runner(
    *,
    sdk_factory: Any = None,
) -> BotMaestroSDK:
    """
    Cria o cliente usando os argumentos do Runner.

    O Runner fornece dinamicamente servidor, tarefa e
    autenticação, evitando credenciais fixas no código.
    """

    fabrica = (
        sdk_factory
        if sdk_factory is not None
        else BotMaestroSDK
    )

    return fabrica.from_sys_args()