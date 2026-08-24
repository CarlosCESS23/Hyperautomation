"""API do classificador textual de causas prováveis."""

from __future__ import annotations

import logging
import math
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import joblib

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from src.causas_divergencia import CausaProvavel
from train_model import MODEL_VERSION


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "classificador_causas.pkl"
)

modelo_ml: Any | None = None


class ObservacaoInput(BaseModel):
    """Entrada textual recebida pelo classificador."""

    observacao: str = Field(
        ...,
        max_length=2000,
        description=(
            "Observação livre informada pelo operador"
        ),
        examples=[
            "O produto chegou sem uma peça necessária."
        ],
    )

    @field_validator("observacao")
    @classmethod
    def validar_observacao(
        cls,
        valor: str,
    ) -> str:
        """Remove espaços repetidos e rejeita texto vazio."""

        observacao_normalizada = " ".join(
            valor.split()
        )

        if not observacao_normalizada:
            raise ValueError(
                "A observação não pode ser vazia."
            )

        if len(observacao_normalizada) < 3:
            raise ValueError(
                "A observação deve possuir pelo menos "
                "três caracteres."
            )

        return observacao_normalizada


class PredictionOutput(BaseModel):
    """Resposta produzida pelo classificador textual."""

    causa_provavel: CausaProvavel

    confianca_ml: float = Field(
        ...,
        ge=0,
        le=1,
    )

    versao_modelo: str


class HealthOutput(BaseModel):
    """Estado atual do serviço e do modelo."""

    status: Literal[
        "healthy",
        "unhealthy",
    ]

    modelo_carregado: bool
    versao_modelo: str | None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carrega o modelo uma única vez durante a inicialização."""

    del app

    global modelo_ml

    try:
        modelo_ml = joblib.load(
            MODEL_PATH
        )

        logger.info(
            "Modelo textual carregado: %s",
            MODEL_PATH,
        )
    except Exception:
        modelo_ml = None

        logger.exception(
            "Não foi possível carregar o modelo: %s",
            MODEL_PATH,
        )

    yield

    modelo_ml = None


app = FastAPI(
    title="Hyperautomation ML API",
    description=(
        "API responsável por sugerir a causa provável "
        "a partir da observação textual do operador. "
        "O serviço não define status de negócio."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


@app.get(
    "/health",
    response_model=HealthOutput,
)
def health() -> HealthOutput:
    """Informa se o classificador está disponível."""

    modelo_carregado = modelo_ml is not None

    return HealthOutput(
        status=(
            "healthy"
            if modelo_carregado
            else "unhealthy"
        ),
        modelo_carregado=modelo_carregado,
        versao_modelo=(
            MODEL_VERSION
            if modelo_carregado
            else None
        ),
    )


def executar_predicao(
    observacao: str,
) -> tuple[CausaProvavel, float]:
    """Executa uma única predição e obtém sua confiança."""

    if modelo_ml is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Modelo de Machine Learning "
                "indisponível."
            ),
        )

    try:
        causas_previstas = modelo_ml.predict(
            [observacao]
        )

        probabilidades = modelo_ml.predict_proba(
            [observacao]
        )[0]

        causa_texto = str(
            causas_previstas[0]
        )

        classes_modelo = [
            str(classe)
            for classe in modelo_ml.classes_
        ]

        indice_causa = classes_modelo.index(
            causa_texto
        )

        confianca = float(
            probabilidades[indice_causa]
        )
    except Exception as erro:
        logger.exception(
            "Falha durante a predição textual."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Não foi possível executar "
                "a classificação."
            ),
        ) from erro

    try:
        causa = CausaProvavel(
            causa_texto
        )
    except ValueError as erro:
        logger.error(
            "Modelo retornou causa desconhecida: %s",
            causa_texto,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Modelo retornou uma causa "
                "não reconhecida."
            ),
        ) from erro

    if (
        not math.isfinite(confianca)
        or not 0 <= confianca <= 1
    ):
        raise HTTPException(
            status_code=500,
            detail=(
                "Modelo retornou uma confiança "
                "inválida."
            ),
        )

    return causa, confianca


@app.post(
    "/predict",
    response_model=PredictionOutput,
)
def predict(
    entrada: ObservacaoInput,
) -> PredictionOutput:
    """Sugere a causa provável da observação recebida."""

    causa, confianca = executar_predicao(
        entrada.observacao
    )

    return PredictionOutput(
        causa_provavel=causa,
        confianca_ml=confianca,
        versao_modelo=MODEL_VERSION,
    )