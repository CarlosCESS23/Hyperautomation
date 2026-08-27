"""Testes unitários do canal SMTP de Email."""

from email.message import EmailMessage
from pathlib import Path

import pytest

from src.sistema_alertas import (
    AdaptadorEmail,
    Alerta,
    ConfiguracaoEmail,
    Severidade,
)


pytestmark = pytest.mark.unit


class SMTPControlado:
    """Simula um servidor SMTP sem utilizar internet."""

    instancias = []

    def __init__(
        self,
        host: str,
        port: int,
        *,
        timeout: float,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.ehlo_chamadas = 0
        self.tls_acionado = False
        self.login_recebido = None
        self.mensagem_recebida = None
        self.encerrado = False

        self.__class__.instancias.append(
            self
        )

    def ehlo(self):
        self.ehlo_chamadas += 1

    def starttls(self, *, context):
        assert context is not None
        self.tls_acionado = True

    def login(
        self,
        usuario: str,
        senha: str,
    ):
        self.login_recebido = (
            usuario,
            senha,
        )

    def send_message(
        self,
        mensagem: EmailMessage,
    ):
        self.mensagem_recebida = mensagem

    def quit(self):
        self.encerrado = True


def test_email_envia_mensagem_com_tls_e_anexo(
    tmp_path: Path,
):
    SMTPControlado.instancias.clear()

    anexo = tmp_path / "relatorio.xlsx"
    anexo.write_bytes(
        b"conteudo-controlado"
    )

    configuracao = ConfiguracaoEmail(
        enabled=True,
        smtp_host="smtp.exemplo.com",
        smtp_port=587,
        usuario="bot@exemplo.com",
        senha="senha-controlada",
        remetente="bot@exemplo.com",
        destinatarios=(
            "equipe@exemplo.com",
        ),
        use_tls=True,
        timeout_seconds=10,
    )

    adaptador = AdaptadorEmail(
        configuracao,
        fabrica_cliente=SMTPControlado,
    )

    resultado = adaptador.enviar(
        Alerta(
            severidade=Severidade.AVISO,
            mensagem=(
                "Pipeline operando 100% "
                "em modo fallback"
            ),
            contexto={
                "execution_id": "exec-email-001",
                "correlation_id": "corr-email-001",
            },
            anexo=anexo,
        )
    )

    assert resultado.sucesso is True
    assert resultado.canal == "email"
    assert resultado.erro is None

    assert len(
        SMTPControlado.instancias
    ) == 1

    cliente = (
        SMTPControlado.instancias[0]
    )

    assert cliente.host == (
        "smtp.exemplo.com"
    )
    assert cliente.port == 587
    assert cliente.timeout == 10

    assert cliente.tls_acionado is True
    assert cliente.ehlo_chamadas == 2

    assert cliente.login_recebido == (
        "bot@exemplo.com",
        "senha-controlada",
    )

    assert cliente.encerrado is True

    mensagem = cliente.mensagem_recebida

    assert mensagem is not None
    assert mensagem["From"] == (
        "bot@exemplo.com"
    )
    assert mensagem["To"] == (
        "equipe@exemplo.com"
    )
    assert mensagem["Subject"] == (
        "[AVISO] Alerta do pipeline"
    )

    corpo = mensagem.get_body(
        preferencelist=("plain",)
    ).get_content()

    assert "100% em modo fallback" in corpo
    assert "execution_id: exec-email-001" in corpo

    anexos = list(
        mensagem.iter_attachments()
    )

    assert len(anexos) == 1
    assert anexos[0].get_filename() == (
        "relatorio.xlsx"
    )
    assert anexos[0].get_payload(
        decode=True
    ) == b"conteudo-controlado"