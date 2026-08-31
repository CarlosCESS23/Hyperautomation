"""Testes do fallback Telegram para Email."""

from unittest.mock import Mock

import pytest

from src.sistema_alertas import (
    Alerta,
    ResultadoAlerta,
    Severidade,
    SistemaAlertas,
)


pytestmark = pytest.mark.integration


class CanalControlado:
    def __init__(
        self,
        nome: str,
        *,
        sucesso: bool,
        erro: str | None = None,
        lancar_excecao: bool = False,
    ) -> None:
        self.nome = nome
        self.sucesso = sucesso
        self.erro = erro
        self.lancar_excecao = lancar_excecao
        self.chamadas: list[Alerta] = []

    def enviar(
        self,
        alerta: Alerta,
    ) -> ResultadoAlerta:
        self.chamadas.append(alerta)

        if self.lancar_excecao:
            raise RuntimeError(
                "falha simulada"
            )

        return ResultadoAlerta(
            sucesso=self.sucesso,
            canal=self.nome,
            erro=self.erro,
        )


def criar_alerta(
    severidade: Severidade,
) -> Alerta:
    return Alerta(
        severidade=severidade,
        mensagem="Evento controlado",
        contexto={
            "execution_id": "exec-001",
            "correlation_id": "corr-001",
            "bot_id": "bot-c-relatorio",
        },
    )


@pytest.mark.parametrize(
    "severidade",
    [
        Severidade.ERRO,
        Severidade.CRITICO,
        Severidade.AVISO
    ],
)
def test_falha_telegram_aciona_email(
    severidade,
):
    telegram = CanalControlado(
        "telegram",
        sucesso=False,
        erro="timeout",
    )

    email = CanalControlado(
        "email",
        sucesso=True,
    )

    sistema = SistemaAlertas(
        telegram,
        email,
    )

    resultado = sistema.enviar(
        criar_alerta(severidade)
    )

    assert resultado.sucesso is True
    assert resultado.canal == "email"
    assert resultado.fallback_acionado is True

    assert len(telegram.chamadas) == 1
    assert len(email.chamadas) == 1

    assert [
        tentativa.canal
        for tentativa in resultado.tentativas
    ] == [
        "telegram",
        "email",
    ]


def test_falha_dos_dois_canais_nao_interrompe_pipeline():
    logger = Mock()

    sistema = SistemaAlertas(
        CanalControlado(
            "telegram",
            sucesso=False,
            erro="timeout",
        ),
        CanalControlado(
            "email",
            sucesso=False,
            erro="falha_transporte",
        ),
        logger=logger,
    )

    resultado = sistema.enviar(
        criar_alerta(
            Severidade.CRITICO
        )
    )

    assert resultado.sucesso is False
    assert resultado.erro == (
        "todos_os_canais_falharam"
    )
    assert resultado.fallback_acionado is True
    assert len(resultado.tentativas) == 2

    logger.critical.assert_called_once()

    extra = logger.critical.call_args.kwargs[
        "extra"
    ]

    assert extra["canal_entrega"] is None
    assert len(extra["tentativas"]) == 2


def test_info_nao_utiliza_email():
    telegram = CanalControlado(
        "telegram",
        sucesso=False,
        erro="timeout",
    )

    email = CanalControlado(
        "email",
        sucesso=True,
    )

    sistema = SistemaAlertas(
        telegram,
        email,
    )

    resultado = sistema.enviar(
        criar_alerta(Severidade.INFO)
    )

    assert resultado.sucesso is False
    assert resultado.fallback_acionado is False
    assert email.chamadas == []


def test_sucesso_telegram_nao_utiliza_email():
    telegram = CanalControlado(
        "telegram",
        sucesso=True,
    )

    email = CanalControlado(
        "email",
        sucesso=True,
    )

    sistema = SistemaAlertas(
        telegram,
        email,
    )

    resultado = sistema.enviar(
        criar_alerta(Severidade.ERRO)
    )

    assert resultado.sucesso is True
    assert resultado.canal == "telegram"
    assert resultado.fallback_acionado is False
    assert email.chamadas == []


def test_excecao_do_telegram_tambem_aciona_email():
    telegram = CanalControlado(
        "telegram",
        sucesso=False,
        lancar_excecao=True,
    )

    email = CanalControlado(
        "email",
        sucesso=True,
    )

    sistema = SistemaAlertas(
        telegram,
        email,
    )

    resultado = sistema.enviar(
        criar_alerta(Severidade.ERRO)
    )

    assert resultado.sucesso is True
    assert resultado.canal == "email"

    assert (
        resultado.tentativas[0].erro
        == "falha_nao_controlada_do_canal"
    )