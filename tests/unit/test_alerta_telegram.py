"""Testes unitários do canal principal Telegram."""

from unittest.mock import Mock

from src.sistema_alertas import (
    AdaptadorTelegram,
    Alerta,
    ConfiguracaoTelegram,
    Severidade,
    SistemaAlertas,
)


def resposta_telegram(*, ok=True, message_id=123):
    resposta = Mock()
    resposta.json.return_value = {
        "ok": ok,
        "result": {"message_id": message_id},
    }
    return resposta


def test_alerta_e_enviado_pelo_telegram_sem_internet():
    cliente = Mock()
    cliente.post.return_value = resposta_telegram()
    adaptador = AdaptadorTelegram(
        ConfiguracaoTelegram(
            token="token-secreto",
            chat_id="chat-001",
            timeout_seconds=2,
        ),
        cliente=cliente,
    )

    resultado = adaptador.enviar(
        Alerta(
            severidade=Severidade.AVISO,
            mensagem="Pipeline operando sem ML",
        )
    )

    assert resultado.sucesso is True
    assert resultado.canal == "telegram"
    assert resultado.message_id == "123"
    cliente.post.assert_called_once_with(
        "https://api.telegram.org/bottoken-secreto/sendMessage",
        json={
            "chat_id": "chat-001",
            "text": "[AVISO] Pipeline operando sem ML",
        },
        timeout=2,
    )


def test_credenciais_sao_lidas_do_ambiente(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-ambiente")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-ambiente")
    monkeypatch.setenv("TELEGRAM_TIMEOUT_SECONDS", "3.5")

    configuracao = ConfiguracaoTelegram.de_ambiente()

    assert configuracao.token == "token-ambiente"
    assert configuracao.chat_id == "chat-ambiente"
    assert configuracao.timeout_seconds == 3.5


def test_erro_do_telegram_vira_resultado_controlado_e_oculta_token():
    token = "123456:token-ultrassecreto"
    cliente = Mock()
    cliente.post.side_effect = ConnectionError(
        f"falha em https://api.telegram.org/bot{token}/sendMessage"
    )
    logger = Mock()
    adaptador = AdaptadorTelegram(
        ConfiguracaoTelegram(token=token, chat_id="chat"),
        cliente=cliente,
        logger=logger,
    )

    resultado = adaptador.enviar(
        Alerta(Severidade.ERRO, "Falha crítica")
    )

    assert resultado.sucesso is False
    assert token not in resultado.erro
    dados_log = logger.error.call_args.kwargs["extra"]
    assert token not in str(dados_log)
    assert dados_log["evento"] == "alerta_telegram_falhou"


def test_resposta_negativa_do_telegram_e_controlada():
    cliente = Mock()
    cliente.post.return_value = resposta_telegram(ok=False)
    adaptador = AdaptadorTelegram(
        ConfiguracaoTelegram(token="token", chat_id="chat"),
        cliente=cliente,
    )

    resultado = adaptador.enviar(
        Alerta(Severidade.INFO, "Execução iniciada")
    )

    assert resultado.sucesso is False
    assert "não confirmada" in resultado.erro


def test_sistema_alertas_usa_canal_principal_simulado():
    canal = Mock()
    canal.nome = "telegram-simulado"
    canal.enviar.return_value = Mock(sucesso=True)
    sistema = SistemaAlertas(canal)

    resultado = sistema.enviar_alerta(
        severidade="CRITICO",
        mensagem="Canal principal em teste",
        contexto={"execution_id": "exec-001"},
    )

    assert resultado.sucesso is True
    alerta = canal.enviar.call_args.args[0]
    assert alerta.severidade is Severidade.CRITICO
    assert alerta.contexto == {"execution_id": "exec-001"}
