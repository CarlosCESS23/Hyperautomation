"""Categorias de causa provável utilizadas pelo modelo textual."""

from enum import Enum


class CausaProvavel(str, Enum):
    """Causas que o modelo poderá sugerir.

    Essas categorias não representam status de negócio.
    As regras RN01–RN12 continuam responsáveis pelo status.
    """

    ERRO_CODIGO = "erro_codigo"
    FALTA_PECA = "falta_peca"
    DUPLICIDADE = "duplicidade"
    ERRO_CADASTRO = "erro_cadastro"


CAUSAS_PROVAVEIS = frozenset(
    causa.value for causa in CausaProvavel
)