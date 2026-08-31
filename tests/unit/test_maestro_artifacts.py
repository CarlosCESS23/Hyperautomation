"""Testes dos artefatos compartilhados no Maestro."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.maestro_artifacts import (
    baixar_artefato,
    localizar_artefato,
)


def test_localiza_artefato_por_tarefa_e_nome():
    maestro = Mock()

    incorreto = SimpleNamespace(
        id=10,
        task_id=999,
        name="entrada.xlsx",
        filename="entrada.xlsx",
    )

    correto = SimpleNamespace(
        id=20,
        task_id=100,
        name="entrada.xlsx",
        filename="entrada.xlsx",
    )

    maestro.list_artifacts.return_value = [
        incorreto,
        correto,
    ]

    encontrado = localizar_artefato(
        maestro,
        task_id_origem="100",
        nome_artefato="entrada.xlsx",
    )

    assert encontrado is correto

    maestro.list_artifacts.assert_called_once_with(
        days=7,
    )


def test_baixa_artefato_para_destino(
    tmp_path,
):
    maestro = Mock()

    artefato = SimpleNamespace(
        id=20,
        task_id=100,
        name="entrada.xlsx",
        filename="entrada.xlsx",
    )

    maestro.list_artifacts.return_value = [
        artefato,
    ]

    maestro.get_artifact.return_value = (
        "entrada.xlsx",
        b"conteudo-da-planilha",
    )

    destino = (
        tmp_path / "entrada.xlsx"
    )

    resultado = baixar_artefato(
        maestro,
        task_id_origem="100",
        nome_artefato="entrada.xlsx",
        destino=destino,
    )

    assert resultado == destino

    assert (
        destino.read_bytes()
        == b"conteudo-da-planilha"
    )

    maestro.get_artifact.assert_called_once_with(
        artifact_id=20,
    )


def test_falha_quando_artefato_nao_existe():
    maestro = Mock()

    maestro.list_artifacts.return_value = []

    with pytest.raises(
        FileNotFoundError,
        match="não encontrado",
    ):
        localizar_artefato(
            maestro,
            task_id_origem="100",
            nome_artefato="entrada.xlsx",
        )