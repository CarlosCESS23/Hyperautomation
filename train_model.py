"""Definição de configuração de treinamento do modelo"""

#Importação de bibliotecas necessárias
from pathlib import Path
import random

import jotlib
import pandas as pd

# Importação de Modelo RandomForest
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / 'data'
MODELS_DIR = BASE_DIR / 'models'

DATASET_PATH = DATA_DIR / 'dataset_lotes.csv'
MODELS_PATH = MODELS_DIR / 'classificador_lotes.pkl'

STATUS_MAP =  {
    'APROVADO' : 0,
    'REPROVADO' : 1,
    'PENDENTE' : 2,
    'EM_ANALISE' : 3,
}

TURNO_MAP = {
    'MANHA': 0,
    'TARDE': 1,
    'NOITE': 2
}


def gerar_amostra():
    """Gerar para cada unidades para o dataframe"""
    status_raw = random.choice(list(STATUS_MAP.keys()))
    turno = random.choice(list(TURNO_MAP.keys()))

    tem_obs = random.choice([0,1])

    if status_raw == 'APROVADO':
        classe = 'válido_automatico'
    elif status_raw == 'REPROVADO':
        if tem_obs:
            classe = 'recusar_automático'
        else:
            classe = 'revisar'
    elif status_raw == 'PENDENTE':
        classe = 'revisar'
    else:
        classe = 'revisar'

    return {
        'status_raw' : STATUS_MAP[status_raw],
        'turno': TURNO_MAP[turno],
        'tem_obs': tem_obs,
        'classe': classe
    }


def gerar_dataset(quantidade: int = 300)-> pd.DataFrame:
    """Gerando dataframe com as amostras"""
    registros = [gerar_amostra() for _ in range(quantidade)]

    return pd.DataFrame(registros)

def treinar_modelo(df: pd.DataFrame):
    X = df[
        'status_raw',
        'turno',
        'tem_obs'
    ]

    y = df['classe']

    # Separando as amostras para o treino e para validação, sendo 80% para treino
    X_train, X_test,y_train,y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y)

    # Criação do modelo
    modelo = RandomForestClassifier(
        n_estimators=100,
        random_state=42
    )

    modelo.fit(X_train, y_train)

    previsoes = modelo.predict(X_test)

    print(classification_report(y_test,previsoes))

    return modelo

def main():

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    dataset = gerar_dataset()

    dataset.to_csv(
        DATASET_PATH,
        index=False
    )

    modelo = treinar_modelo(dataset)

    joblib.dump(modelo, MODELS_PATH)
if __name__ == '__main__':
    main()