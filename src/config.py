"""Configurações locais para a integração com o BotCity Maestro."""

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]

# CAMINHOS PARA O PLAYWRIGHT
CAMINHO_EVIDENCIA = 'screenshots/comprovante_lote_9999.png'
INTERFACE_NAVEGADOR = os.getenv("HEADLESS",'true').lower() == 'true'
URL_BASE = os.getenv("URL_BASE", "http://localhost:8080")

def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def carregar_ambiente() -> None:
    """Carrega o .env da raiz; mantém compatibilidade com o antigo src/.env."""
    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(Path(__file__).with_name(".env"), override=False)


@dataclass(frozen=True)
class Configuracao:
    maestro_server: str
    maestro_login: str
    maestro_key: str
    maestro_enabled: bool
    vault_enabled: bool
    datapool_label: str
    credential_label: str
    credential_user_key: str
    credential_password_key: str


def obter_configuracao() -> Configuracao:
    carregar_ambiente()
    return Configuracao(
        maestro_server=os.getenv("MAESTRO_SERVER", ""),
        maestro_login=os.getenv("MAESTRO_LOGIN", ""),
        maestro_key=os.getenv("MAESTRO_KEY", ""),
        # O modelo anterior de .env não tinha estas flags; true mantém compatibilidade.
        maestro_enabled=_as_bool(os.getenv("MAESTRO_ENABLED"), default=True),
        vault_enabled=_as_bool(os.getenv("VAULT_ENABLED"), default=True),
        # Nome específico para não reutilizar por acidente a fila de outro robô.
        datapool_label=os.getenv("AUDITORIA_DATAPOOL_LABEL", "FilaAuditoriaLotes_equipe1"),
        credential_label=os.getenv("CREDENTIAL_LABEL", "credencial_erp"),
        credential_user_key=os.getenv("CREDENTIAL_USER_KEY", "username"),
        credential_password_key=os.getenv("CREDENTIAL_PASSWORD_KEY", "password"),
    )


def validar_conexao(config: Configuracao) -> None:
    if not config.maestro_enabled:
        raise RuntimeError("MAESTRO_ENABLED deve estar definido como true no .env.")
    campos_ausentes = [
        nome
        for nome, valor in {
            "MAESTRO_SERVER": config.maestro_server,
            "MAESTRO_LOGIN": config.maestro_login,
            "MAESTRO_KEY": config.maestro_key,
        }.items()
        if not valor
    ]
    if campos_ausentes:
        raise RuntimeError(f"Configure no .env: {', '.join(campos_ausentes)}.")
