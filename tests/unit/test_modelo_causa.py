from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from src.causas_divergencia import CAUSAS_PROVAVEIS
from src.dataset_observacoes import gerar_dataset
from train_model import (
    avaliar_modelo,
    carregar_dataset,
    criar_pipeline,
    normalizar_observacao,
    salvar_artefatos,
    separar_dataset,
    treinar_modelo,
)
from src.normalizacao_text import normalizar_observacao


pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def dataset():
    return gerar_dataset(semente=42)


@pytest.fixture(scope="module")
def modelo(dataset):
    return treinar_modelo(dataset)


def test_normaliza_observacao():
    resultado = normalizar_observacao(
        "  Código INVÁLIDO!!!  "
    )

    assert resultado == "codigo invalido"


def test_rejeita_observacao_que_nao_e_texto():
    with pytest.raises(
        TypeError,
        match="deve ser uma string",
    ):
        normalizar_observacao(123)


def test_carrega_dataset_do_csv(
    tmp_path: Path,
    dataset,
):
    caminho = (
        tmp_path
        / "dataset_observacoes.csv"
    )

    dataset.to_csv(
        caminho,
        index=False,
    )

    resultado = carregar_dataset(caminho)

    pd.testing.assert_frame_equal(
        resultado,
        dataset,
    )


def test_separa_treino_e_teste(dataset):
    (
        x_treino,
        x_teste,
        y_treino,
        y_teste,
    ) = separar_dataset(dataset)

    assert len(x_treino) == 76
    assert len(y_treino) == 76
    assert len(x_teste) == 20
    assert len(y_teste) == 20


def test_pipeline_possui_vetorizador_e_classificador():
    pipeline = criar_pipeline()

    assert "tfidf" in pipeline.named_steps
    assert "classificador" in pipeline.named_steps


def test_modelo_prediz_uma_causa_permitida(modelo):
    previsao = modelo.predict(
        [
            "O produto chegou sem uma peça "
            "necessária para montagem"
        ]
    )

    assert previsao[0] in CAUSAS_PROVAVEIS


def test_modelo_disponibiliza_probabilidades(modelo):
    probabilidades = modelo.predict_proba(
        [
            "O código informado não existe "
            "no sistema"
        ]
    )

    assert probabilidades.shape == (
        1,
        len(CAUSAS_PROVAVEIS),
    )

    assert np.isclose(
        probabilidades[0].sum(),
        1.0,
    )


def test_metricas_possuem_informacoes_esperadas(
    modelo,
    dataset,
):
    metricas = avaliar_modelo(
        modelo,
        dataset,
    )

    assert 0 <= metricas["acuracia"] <= 1
    assert metricas["quantidade_treino"] == 76
    assert metricas["quantidade_teste"] == 20
    assert set(metricas["classes"]) == CAUSAS_PROVAVEIS

    assert len(
        metricas["matriz_confusao"]
    ) == len(CAUSAS_PROVAVEIS)


def test_treinamento_e_reproduzivel(dataset):
    primeiro_modelo = treinar_modelo(dataset)
    segundo_modelo = treinar_modelo(dataset)

    observacoes = [
        "Código do produto está incorreto",
        "Está faltando uma peça no produto",
        "Registro foi cadastrado duas vezes",
    ]

    primeira_previsao = primeiro_modelo.predict(
        observacoes
    )

    segunda_previsao = segundo_modelo.predict(
        observacoes
    )

    assert np.array_equal(
        primeira_previsao,
        segunda_previsao,
    )


def test_salva_e_recarrega_pipeline_completo(
    tmp_path: Path,
    modelo,
    dataset,
):
    caminho_modelo = (
        tmp_path
        / "classificador_causas.pkl"
    )

    caminho_metricas = (
        tmp_path
        / "metricas.json"
    )

    metricas = avaliar_modelo(
        modelo,
        dataset,
    )

    salvar_artefatos(
        modelo=modelo,
        metricas=metricas,
        caminho_modelo=caminho_modelo,
        caminho_metricas=caminho_metricas,
    )

    assert caminho_modelo.exists()
    assert caminho_metricas.exists()

    modelo_recarregado = joblib.load(
        caminho_modelo
    )

    observacao = [
        "O registro já foi processado anteriormente"
    ]

    previsao_original = modelo.predict(
        observacao
    )

    previsao_recarregada = modelo_recarregado.predict(
        observacao
    )

    assert np.array_equal(
        previsao_original,
        previsao_recarregada,
    )
def test_normalizador_pertence_a_modulo_importavel():
    assert normalizar_observacao.__module__ == (
        "src.normalizacao_text"
    )