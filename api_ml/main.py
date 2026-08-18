"""API de Machine Learning para classificar os lotes"""

from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from train_model import STATUS_MAP,TURNO_MAP

# Configurando os caminhos

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR / 'models' / 'classificador_lotes.pkl'
)

#Variavel que será armazenado pelo modelo
modelo_ml = MODEL_PATH

modelo_ml = None

#Modelo Pydantic
class LoteInput(BaseModel):
    """Dados que serão recebdios pela API para realizar uma predição"""

    status_raw : str
    turno : str
    tem_obs: bool

    @field_validator('status_raw')
    @classmethod
    def validar_status(cls,valor: str) -> str:
        """Validando e normaliza os status que recebe"""
        status = valor.strip().upper()

        if status not in STATUS_MAP:
            raise ValueError(
                'Status inválido.\nValores permitido:\nAprovado, Reprovado, Pendente e em Análise '
            )
        return status


    @field_validator('turno')
    @classmethod
    def validar_turno(cls,valor: str) -> str:
        """Valida e normaliza o turno recebido."""

        turno = valor.strip().upper()

        if turno not in TURNO_MAP:
            raise ValueError(
                'Turno inválido.\nValores permitido: Manha, Tarde e noite'
            )

        return turno

class PredictionOutput(BaseModel):
    """Formato de resposta produzido pelo endpoint de predição"""

    classe : str
    probabilidade: float
    nivel_confianca: str

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    '''Carrega o moedlo quando a aplicação é iniciado'''

    global modelo_ml

    try:
        modelo_ml = joblib.load(MODEL_PATH)

        print(f'Modelo carregado com sucesso: {MODEL_PATH}')
    except Exception as erro:
        modelo_ml = None
        print(f'Erro ao carregar o modelo: {erro}')
    yield
    modelo_ml = None

#FastAPI

app = FastAPI(
    title='Hyperautomation ML API',
    description=(
        'API responsável pela classificação de lotes utilizando o RandomForestClassifier'
    ),
    version='1.0.0',
    lifespan = lifespan
)

@app.get('/health')
def health():
    """Informa se o modelo está disponível"""

    if modelo_ml is None:
        return{
            'status': 'unhealthy',
            'modelo_carregado' : False
        }

    return{
        'status' : 'healthy',
        'modelo_carregado' : True
    }

# Funções auxiliares

def definir_nivel_confianca(probabilidade: float) -> str:
    """Define o nível de confiança da predição."""

    if probabilidade >= 0.85:
        return 'acao_automatica'

    if probabilidade >= 0.65:
        return 'revisar'

    return 'revisar_prioritario'

def preparar_features(lote : LoteInput) -> pd.DataFrame:
    """Transforma os dados recebidos no formato esperado pelo modelo."""

    return pd.DataFrame(
        [
            {
                'status_raw' : STATUS_MAP[lote.status_raw],
                'turno': TURNO_MAP[lote.turno],
                'tem_obs': int(lote.tem_obs)
            }
        ]
    )

#Predicao

@app.post('/predict', response_model=PredictionOutput)
def predict(lote: LoteInput) -> PredictionOutput:

    if modelo_ml is None:
        raise HTTPException(
            status_code=503,
            detail='Modelo de Machine Learning indisponível.'
        )

    features = preparar_features(lote)

    classe = modelo_ml.predict(features)[0]
    probabilidades = modelo_ml.predict_proba(features)[0]

    maior_probabilidade = float(max(probabilidades))

    nivel_confianca = definir_nivel_confianca(maior_probabilidade)

    return PredictionOutput(
        classe=str(classe),
        probabilidade = maior_probabilidade,
        nivel_confianca= nivel_confianca
    )

