"""Publicação, localização e download de artefatos do Maestro."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def localizar_artefato(
    maestro: Any,
    *,
    task_id_origem: str,
    nome_artefato: str,
    dias: int = 7,
) -> Any:
    """
    Localiza um artefato pelo ID da tarefa e nome.

    O filtro pelo task_id impede que um bot carregue
    um arquivo pertencente a outra execução.
    """

    if not str(task_id_origem).strip():
        raise ValueError(
            "task_id_origem é obrigatório"
        )

    if not nome_artefato.strip():
        raise ValueError(
            "nome_artefato é obrigatório"
        )

    if dias <= 0:
        raise ValueError(
            "dias deve ser maior que zero"
        )

    artefatos = maestro.list_artifacts(
        days=dias,
    )

    encontrados = [
        artefato
        for artefato in artefatos
        if (
            str(
                getattr(
                    artefato,
                    "task_id",
                    "",
                )
            )
            == str(task_id_origem)
            and nome_artefato
            in {
                str(
                    getattr(
                        artefato,
                        "name",
                        "",
                    )
                ),
                str(
                    getattr(
                        artefato,
                        "filename",
                        "",
                    )
                ),
            }
        )
    ]

    if not encontrados:
        raise FileNotFoundError(
            "Artefato não encontrado: "
            f"tarefa={task_id_origem}, "
            f"nome={nome_artefato}"
        )

    # Caso existam versões repetidas, utiliza
    # o artefato de maior ID, que é o mais recente.
    return max(
        encontrados,
        key=lambda artefato: int(
            getattr(
                artefato,
                "id",
                0,
            )
        ),
    )


def baixar_artefato(
    maestro: Any,
    *,
    task_id_origem: str,
    nome_artefato: str,
    destino: str | Path,
    dias: int = 7,
) -> Path:
    """
    Baixa um artefato do Maestro para o ambiente atual.

    Retorna o caminho em que o arquivo foi gravado.
    """

    artefato = localizar_artefato(
        maestro,
        task_id_origem=task_id_origem,
        nome_artefato=nome_artefato,
        dias=dias,
    )

    _, conteudo = maestro.get_artifact(
        artifact_id=artefato.id,
    )

    if not isinstance(
        conteudo,
        bytes,
    ):
        raise TypeError(
            "Conteúdo do artefato deve ser bytes"
        )

    caminho = Path(destino)

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho.write_bytes(
        conteudo
    )

    return caminho


def publicar_artefato(
    maestro: Any,
    *,
    task_id: str,
    caminho: str | Path,
    nome_artefato: str | None = None,
) -> Path:
    """
    Publica um arquivo como resultado de uma tarefa.

    Quando o nome não é informado, utiliza o nome
    original do arquivo.
    """

    if not str(task_id).strip():
        raise ValueError(
            "task_id é obrigatório"
        )

    arquivo = Path(caminho)

    if not arquivo.is_file():
        raise FileNotFoundError(
            "Arquivo para publicação "
            f"não encontrado: {arquivo}"
        )

    nome = (
        nome_artefato.strip()
        if nome_artefato
        else arquivo.name
    )

    if not nome:
        raise ValueError(
            "nome_artefato é obrigatório"
        )

    maestro.post_artifact(
        task_id=str(task_id),
        artifact_name=nome,
        filepath=str(arquivo),
    )

    return arquivo