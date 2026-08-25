"""Treinamento do classificador textual de causas prováveis."""

from __future__ import annotations

import json

from pathlib import Path

import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.pipeline import Pipeline

from src.causas_divergencia import CAUSAS_PROVAVEIS
from src.dataset_observacoes import validar_dataset
from src.normalizacao_text import normalizar_observacao


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "ml"
MODELS_DIR = BASE_DIR / "models"

DATASET_PATH = DATA_DIR / "dataset_observacoes.csv"
MODEL_PATH = MODELS_DIR / "classificador_causas.pkl"
METRICS_PATH = MODELS_DIR / "metricas_classificador_causas.json"

MODEL_VERSION = "2.0.0-texto"
SEMENTE_MODELO = 42


# Compatibilidade temporária com a API antiga.
# Estas constantes serão removidas quando a API for adaptada
# para receber somente a observação textual na Issue 05.
STATUS_MAP = {
    "APROVADO": 0,
    "REPROVADO": 1,
    "PENDENTE": 2,
    "EM_ANALISE": 3,
}

TURNO_MAP = {
    "MANHA": 0,
    "TARDE": 1,
    "NOITE": 2,
}

def carregar_dataset(
    caminho: Path = DATASET_PATH,
) -> pd.DataFrame:
    """Carrega e valida o dataset textual."""

    if not caminho.exists():
        raise FileNotFoundError(
            f"Dataset não encontrado: {caminho}. "
            "Execute: python -m src.dataset_observacoes"
        )

    dataset = pd.read_csv(caminho)

    validar_dataset(dataset)

    return dataset


def separar_dataset(
    dataset: pd.DataFrame,
) -> tuple[
    pd.Series,
    pd.Series,
    pd.Series,
    pd.Series,
]:
    """Separa observações e causas de treino e teste."""

    validar_dataset(dataset)

    registros_treino = dataset[
        dataset["particao"] == "treino"
    ]

    registros_teste = dataset[
        dataset["particao"] == "teste"
    ]

    if registros_treino.empty:
        raise ValueError(
            "O conjunto de treino não pode estar vazio"
        )

    if registros_teste.empty:
        raise ValueError(
            "O conjunto de teste não pode estar vazio"
        )

    x_treino = registros_treino["observacao"]
    y_treino = registros_treino["causa"]

    x_teste = registros_teste["observacao"]
    y_teste = registros_teste["causa"]

    return (
        x_treino,
        x_teste,
        y_treino,
        y_teste,
    )


def criar_pipeline() -> Pipeline:
    """Cria o pipeline completo de texto e classificação."""

    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    preprocessor=normalizar_observacao,
                    lowercase=False,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=3000,
                ),
            ),
            (
                "classificador",
                LogisticRegression(
                    max_iter=1000,
                    random_state=SEMENTE_MODELO,
                    class_weight="balanced",
                ),
            ),
        ]
    )


def treinar_modelo(
    dataset: pd.DataFrame,
) -> Pipeline:
    """Treina o classificador com a partição de treino."""

    (
        x_treino,
        _,
        y_treino,
        _,
    ) = separar_dataset(dataset)

    modelo = criar_pipeline()

    modelo.fit(
        x_treino,
        y_treino,
    )

    return modelo


def avaliar_modelo(
    modelo: Pipeline,
    dataset: pd.DataFrame,
) -> dict:
    """Avalia o modelo utilizando somente a partição de teste."""

    (
        x_treino,
        x_teste,
        _,
        y_teste,
    ) = separar_dataset(dataset)

    previsoes = modelo.predict(x_teste)

    classes = sorted(CAUSAS_PROVAVEIS)

    relatorio = classification_report(
        y_teste,
        previsoes,
        labels=classes,
        output_dict=True,
        zero_division=0,
    )

    matriz = confusion_matrix(
        y_teste,
        previsoes,
        labels=classes,
    )

    return {
        "versao_modelo": MODEL_VERSION,
        "acuracia": float(
            accuracy_score(
                y_teste,
                previsoes,
            )
        ),
        "quantidade_treino": int(len(x_treino)),
        "quantidade_teste": int(len(x_teste)),
        "classes": classes,
        "relatorio_classificacao": relatorio,
        "matriz_confusao": matriz.tolist(),
    }


def salvar_artefatos(
    modelo: Pipeline,
    metricas: dict,
    caminho_modelo: Path = MODEL_PATH,
    caminho_metricas: Path = METRICS_PATH,
) -> None:
    """Salva o pipeline treinado e suas métricas."""

    caminho_modelo.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho_metricas.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        modelo,
        caminho_modelo,
    )

    caminho_metricas.write_text(
        json.dumps(
            metricas,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    """Executa treinamento, avaliação e persistência."""

    dataset = carregar_dataset()

    modelo = treinar_modelo(dataset)

    metricas = avaliar_modelo(
        modelo,
        dataset,
    )

    salvar_artefatos(
        modelo,
        metricas,
    )

    print(
        json.dumps(
            metricas,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print(f"Modelo salvo em: {MODEL_PATH}")
    print(f"Métricas salvas em: {METRICS_PATH}")


if __name__ == "__main__":
    main()