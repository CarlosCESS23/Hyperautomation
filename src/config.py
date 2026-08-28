"""Configurações locais para a integração com o BotCity Maestro."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]

# CAMINHOS PARA O PLAYWRIGHT


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_float(value: str | None, default: float, nome_variavel: str) -> float:
    """
    Converte uma variável de ambiente para o float
    """

    if value is None:
        return default
    try:
        return float(value.strip())
    except ValueError as erro:
        raise ValueError(f'{nome_variavel} deve possuir um valor numérico') from erro

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
    url_base: str
    interface_navegador: bool
    caminho_evidencia: str
    ml_enabled: bool

    # Configuração do novo pipeline híbrido.
    pipeline_hibrido_enabled: bool = False
    ml_api_url: str = "http://localhost:8000"
    ml_min_confidence: float = 0.75
    ml_timeout_seconds: float = 3.0



def obter_configuracao() -> Configuracao:
    carregar_ambiente()

    ml_min_confidence = _as_float(
        os.getenv("ML_MIN_CONFIDENCE"),
        default=0.75,
        nome_variavel="ML_MIN_CONFIDENCE",
    )

    ml_timeout_seconds = _as_float(
        os.getenv("ML_TIMEOUT_SECONDS"),
        default=3.0,
        nome_variavel="ML_TIMEOUT_SECONDS",
    )

    ml_enabled = _as_bool(os.getenv('ML_ENABLED'),default=False)

    if not 0 <= ml_min_confidence <= 1:
        raise ValueError(
            "ML_MIN_CONFIDENCE deve estar entre 0 e 1"
        )

    if ml_timeout_seconds <= 0:
        raise ValueError(
            "ML_TIMEOUT_SECONDS deve ser maior que zero"
        )

    return Configuracao(
        maestro_server=os.getenv("MAESTRO_SERVER", ""),
        maestro_login=os.getenv("MAESTRO_LOGIN", ""),
        maestro_key=os.getenv("MAESTRO_KEY", ""),
        maestro_enabled=_as_bool(
            os.getenv("MAESTRO_ENABLED"),
            default=True,
        ),
        vault_enabled=_as_bool(
            os.getenv("VAULT_ENABLED"),
            default=True,
        ),
        datapool_label=os.getenv(
            "AUDITORIA_DATAPOOL_LABEL",
            "FilaAuditoriaLotes_equipe1",
        ),
        credential_label=os.getenv(
            "CREDENTIAL_LABEL",
            "credencial_erp",
        ),
        credential_user_key=os.getenv(
            "CREDENTIAL_USER_KEY",
            "username",
        ),
        credential_password_key=os.getenv(
            "CREDENTIAL_PASSWORD_KEY",
            "password",
        ),
        interface_navegador=_as_bool(
            os.getenv("HEADLESS"),
            default=True,
        ),
        url_base=os.getenv(
            "URL_BASE",
            "http://localhost:8080",
        ),
        caminho_evidencia=os.getenv(
            "CAMINHO_EVIDENCIA",
            "screenshots/comprovante_lote_9999.png",
        ),
        pipeline_hibrido_enabled=_as_bool(
            os.getenv("PIPELINE_HIBRIDO_ENABLED"),
            default=False,
        ),
        ml_api_url=os.getenv(
            "ML_API_URL",
            "http://localhost:8000",
        ).rstrip("/"),
        ml_min_confidence=ml_min_confidence,
        ml_timeout_seconds=ml_timeout_seconds,
        ml_enabled = ml_enabled
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
