from pathlib import Path

import pandas as pd
import pytest

from src.causas_divergencia import (
    CAUSAS_PROVAVEIS,
)
from src.dataset_observacoes import (
    COLUNAS_DATASET,
    MINIMO_AMOSTRAS_POR_CLASSE,
    gerar_dataset,
    salvar_dataset,
    validar_dataset,
)


pytestmark = pytest.mark.unit


def test_dataset_possui_colunas_esperadas():
    dataset = gerar_dataset()

    assert tuple(dataset.columns) == COLUNAS_DATASET


def test_geracao_do_dataset_e_reproduzivel():
    primeiro = gerar_dataset(semente=42)
    segundo = gerar_dataset(semente=42)

    pd.testing.assert_frame_equal(
        primeiro,
        segundo,
    )


def test_dataset_nao_possui_observacoes_vazias():
    dataset = gerar_dataset()

    assert not dataset["observacao"].isna().any()

    assert not (
        dataset["observacao"]
        .astype(str)
        .str.strip()
        .eq("")
        .any()
    )


def test_dataset_nao_possui_observacoes_duplicadas():
    dataset = gerar_dataset()

    assert not dataset["observacao"].duplicated().any()


def test_dataset_possui_somente_causas_permitidas():
    dataset = gerar_dataset()

    assert set(dataset["causa"].unique()) == CAUSAS_PROVAVEIS


def test_todas_as_causas_possuem_quantidade_minima():
    dataset = gerar_dataset()

    quantidade_por_causa = dataset.groupby(
        "causa"
    ).size()

    assert (
        quantidade_por_causa
        >= MINIMO_AMOSTRAS_POR_CLASSE
    ).all()


def test_todas_as_causas_aparecem_no_treino_e_teste():
    dataset = gerar_dataset()

    distribuicao = dataset.groupby(
        ["causa", "particao"]
    ).size()

    for causa in CAUSAS_PROVAVEIS:
        assert (causa, "treino") in distribuicao
        assert (causa, "teste") in distribuicao


def test_salva_dataset_em_csv(tmp_path: Path):
    caminho = (
        tmp_path
        / "dataset_observacoes.csv"
    )

    dataset_salvo = salvar_dataset(
        caminho=caminho,
        semente=42,
    )

    assert caminho.exists()

    dataset_lido = pd.read_csv(caminho)

    pd.testing.assert_frame_equal(
        dataset_salvo,
        dataset_lido,
    )


def test_rejeita_identificador_do_lote_oculto():
    dataset = gerar_dataset()

    dataset.loc[
        0,
        "observacao",
    ] = "Falha encontrada no lote LT-OCULTO-999."

    with pytest.raises(
        ValueError,
        match="Dataset contém identificador proibido",
    ):
        validar_dataset(
            dataset,
            identificadores_proibidos={
                "LT-OCULTO-999",
            },
        )


def test_rejeita_proporcao_de_teste_invalida():
    with pytest.raises(
        ValueError,
        match="proporcao_teste deve estar entre 0 e 1",
    ):
        gerar_dataset(proporcao_teste=1.0)