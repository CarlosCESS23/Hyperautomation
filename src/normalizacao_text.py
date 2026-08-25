"""Normalização textual compartilhada pelo treinamento e pela API."""

import re
import unicodedata


def normalizar_observacao(
    observacao: str,
) -> str:
    """Normaliza uma observação antes da vetorização."""

    if not isinstance(observacao, str):
        raise TypeError(
            "A observação deve ser uma string"
        )

    texto_sem_acento = (
        unicodedata.normalize(
            "NFKD",
            observacao,
        )
        .encode("ascii", "ignore")
        .decode("ascii")
    )

    texto_minusculo = (
        texto_sem_acento.casefold()
    )

    texto_sem_pontuacao = re.sub(
        r"[^a-z0-9\s]",
        " ",
        texto_minusculo,
    )

    return " ".join(
        texto_sem_pontuacao.split()
    )