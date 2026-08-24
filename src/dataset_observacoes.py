"""Geração reproduzível do dataset textual de causas prováveis."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.causas_divergencia import (
    CAUSAS_PROVAVEIS,
    CausaProvavel,
)


ROOT_DIR = Path(__file__).resolve().parents[1]

DATASET_PATH = (
    ROOT_DIR
    / "data"
    / "ml"
    / "dataset_observacoes.csv"
)

SEMENTE_PADRAO = 42
PROPORCAO_TESTE = 0.20
MINIMO_AMOSTRAS_POR_CLASSE = 20

COLUNAS_DATASET = (
    "observacao",
    "causa",
    "particao",
)

PARTICOES_PERMITIDAS = {
    "treino",
    "teste",
}


OBSERVACOES_BASE = {
    CausaProvavel.ERRO_CODIGO: (
        "Código do produto não foi reconhecido",
        "Sistema informa que o código não existe",
        "Código de barras está ilegível",
        "Identificador do item está incorreto",
        "Código digitado não pertence ao produto",
        "Não foi possível localizar o código no cadastro",
        "Etiqueta apresenta um código inválido",
        "Leitura retornou código diferente do esperado",
    ),
    CausaProvavel.FALTA_PECA: (
        "Produto está sem uma das peças necessárias",
        "Componente obrigatório não foi encontrado",
        "Material necessário está em falta",
        "Item chegou com uma peça ausente",
        "Montagem não pode continuar por falta de componente",
        "Quantidade de peças está abaixo do esperado",
        "Embalagem não contém todos os componentes",
        "Foi identificada ausência de material no produto",
    ),
    CausaProvavel.DUPLICIDADE: (
        "Registro já havia sido processado anteriormente",
        "Mesmo item aparece duas vezes na relação",
        "Lote foi informado mais de uma vez",
        "Sistema encontrou um registro duplicado",
        "Inspeção repetida para o mesmo item",
        "Entrada já existe na base de conferência",
        "Produto foi cadastrado novamente por engano",
        "Foi encontrada outra ocorrência do mesmo registro",
    ),
    CausaProvavel.ERRO_CADASTRO: (
        "Responsável foi informado incorretamente",
        "Data de inspeção foi cadastrada errada",
        "Nome do produto não corresponde ao registro",
        "Turno informado está incorreto",
        "Dados preenchidos não correspondem ao item",
        "Cadastro possui informações inconsistentes",
        "Operador preencheu o campo errado",
        "Registro contém dados inválidos do responsável",
    ),
}


CONTEXTOS = (
    "durante a conferência",
    "ao processar a inspeção",
    "na validação do registro",
)


def _gerar_observacoes_por_causa(
    causa: CausaProvavel,
) -> list[str]:
    """Combina textos-base e contextos de forma determinística."""

    return [
        f"{texto} {contexto}."
        for texto in OBSERVACOES_BASE[causa]
        for contexto in CONTEXTOS
    ]


def gerar_dataset(
    semente: int = SEMENTE_PADRAO,
    proporcao_teste: float = PROPORCAO_TESTE,
) -> pd.DataFrame:
    """Gera o dataset com divisão reproduzível entre treino e teste."""

    if not 0 < proporcao_teste < 1:
        raise ValueError(
            "proporcao_teste deve estar entre 0 e 1"
        )

    gerador_aleatorio = random.Random(semente)
    registros: list[dict[str, str]] = []

    for causa in CausaProvavel:
        observacoes = _gerar_observacoes_por_causa(causa)

        # A cópia é embaralhada sem modificar a constante original.
        observacoes_embaralhadas = observacoes.copy()
        gerador_aleatorio.shuffle(observacoes_embaralhadas)

        quantidade_teste = max(
            1,
            round(
                len(observacoes_embaralhadas)
                * proporcao_teste
            ),
        )

        for indice, observacao in enumerate(
            observacoes_embaralhadas
        ):
            particao = (
                "teste"
                if indice < quantidade_teste
                else "treino"
            )

            registros.append(
                {
                    "observacao": observacao,
                    "causa": causa.value,
                    "particao": particao,
                }
            )

    dataset = pd.DataFrame(
        registros,
        columns=COLUNAS_DATASET,
    )

    validar_dataset(dataset)

    return dataset


def validar_dataset(
    dataset: pd.DataFrame,
    identificadores_proibidos: Iterable[str] = (),
) -> None:
    """Valida a qualidade e impede vazamento de dados ocultos."""

    colunas_ausentes = (
        set(COLUNAS_DATASET)
        - set(dataset.columns)
    )

    if colunas_ausentes:
        raise ValueError(
            "Dataset não possui as colunas obrigatórias: "
            f"{sorted(colunas_ausentes)}"
        )

    if dataset.empty:
        raise ValueError("Dataset não pode estar vazio")

    if dataset["observacao"].isna().any():
        raise ValueError(
            "Dataset possui observações nulas"
        )

    observacoes = dataset["observacao"].astype(str).str.strip()

    if observacoes.eq("").any():
        raise ValueError(
            "Dataset possui observações vazias"
        )

    if observacoes.duplicated().any():
        raise ValueError(
            "Dataset possui observações duplicadas"
        )

    causas_encontradas = set(dataset["causa"].unique())

    if causas_encontradas != CAUSAS_PROVAVEIS:
        raise ValueError(
            "As causas do dataset são diferentes "
            "das causas permitidas"
        )

    particoes_encontradas = set(
        dataset["particao"].unique()
    )

    if not particoes_encontradas.issubset(
        PARTICOES_PERMITIDAS
    ):
        raise ValueError(
            "Dataset possui partição inválida"
        )

    quantidade_por_causa = dataset.groupby(
        "causa"
    ).size()

    classes_insuficientes = quantidade_por_causa[
        quantidade_por_causa
        < MINIMO_AMOSTRAS_POR_CLASSE
    ]

    if not classes_insuficientes.empty:
        raise ValueError(
            "Existem causas com poucas amostras: "
            f"{classes_insuficientes.to_dict()}"
        )

    # Cada classe deve aparecer tanto no treino quanto no teste.
    distribuicao = dataset.groupby(
        ["causa", "particao"]
    ).size()

    for causa in CAUSAS_PROVAVEIS:
        for particao in PARTICOES_PERMITIDAS:
            if (causa, particao) not in distribuicao:
                raise ValueError(
                    f"A causa {causa} não aparece "
                    f"na partição {particao}"
                )

    # O identificador do lote oculto poderá ser fornecido
    # durante a apresentação ou durante um teste de sabotagem.
    for identificador in identificadores_proibidos:
        termo = identificador.strip().casefold()

        if not termo:
            continue

        encontrou_identificador = observacoes.str.casefold().str.contains(
            termo,
            regex=False,
        ).any()

        if encontrou_identificador:
            raise ValueError(
                "Dataset contém identificador proibido: "
                f"{identificador}"
            )


def salvar_dataset(
    caminho: Path = DATASET_PATH,
    semente: int = SEMENTE_PADRAO,
) -> pd.DataFrame:
    """Gera, valida e salva o dataset em CSV."""

    dataset = gerar_dataset(semente=semente)

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataset.to_csv(
        caminho,
        index=False,
        encoding="utf-8",
    )

    return dataset


def main() -> None:
    """Gera o dataset e apresenta sua distribuição."""

    dataset = salvar_dataset()

    print(f"Dataset salvo em: {DATASET_PATH}")
    print(f"Quantidade total: {len(dataset)}")
    print()
    print("Distribuição por causa e partição:")
    print(
        dataset.groupby(
            ["causa", "particao"]
        ).size()
    )


if __name__ == "__main__":
    main()