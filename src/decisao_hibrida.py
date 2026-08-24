""" Contrato de Dados utilizado pelas decisoes do pipeline híbrido

Este módulo não executa a regra de negócio e além de chamar o modelo de ML, apenas define como resultado de uma tentativa de classificação
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Final


class OrigemDecisao(str,Enum):
    """Indica de onde veio a sugestão da causa"""
    ML = 'ml'
    FALLBACK : Final = 'fallback'

class MotivoFallback(str,Enum):
    """
    Motivo permitidos para não utilizar uma decisão
    """

    ML_DESATIVADO : Final = 'ml_desativado'
    SERVICO_INDISPONIVEL : Final = 'servico_indisponivel'
    TIMEOUT : Final = 'timeout'
    BAIXA_CONFIANCA : Final = 'baixa_confianca'
    RESPOSTA_INVALIDA : Final = 'resposta_invalida'

@dataclass(frozen = True)
class ResultadoDecisaoHibrida:
    """Resultado do enriquecimento realizado pelo pipline híbrido

    A classificação de negócio continua sendo responsabilidade das regras RN01-RN12. Este objeto representa somente a sugestão de causa provável pelo ML ou pelo fallback.
    """

    causa_provavel: str
    origem_decisao: OrigemDecisao
    confianca_ml: float | None = None
    motivo_fallback: MotivoFallback | None = None
    versao_modelo : str = ''

    def __post_init__(self):
        """Valida as combinações permitidas pelo contrato"""
        causa_normalizada = self.causa_provavel.strip()

        if not causa_normalizada:
            raise ValueError('causa_provavel não pode ser vazia')

        object.__setattr__(self,'causa_provavel',causa_normalizada)

        if not isinstance(self.origem_decisao, OrigemDecisao):
            raise ValueError("origem_decisao deve ser ml ou fallback")

        if self.origem_decisao == OrigemDecisao.ML:
            self._validar_resultado_ml()
        else:
            self._validar_resultado_fallback()

    def _validar_resultado_ml(self) -> None:
        """Valida um resultado originado pelo modelo."""

        if self.confianca_ml is None:
            raise ValueError(
                "confianca_ml é obrigatória quando a origem é ml"
            )

        if (
                isinstance(self.confianca_ml, bool)
                or not isinstance(self.confianca_ml, (int, float))
        ):
            raise ValueError("confianca_ml deve ser um número")

        if not 0 <= self.confianca_ml <= 1:
            raise ValueError(
                "confianca_ml deve estar entre 0 e 1"
            )

        if self.motivo_fallback is not None:
            raise ValueError(
                "uma decisão de ml não pode possuir motivo_fallback"
            )

        object.__setattr__(
            self,
            "confianca_ml",
            float(self.confianca_ml),
        )

    def _validar_resultado_fallback(self) -> None:
        """Valida um resultado produzido pelo fallback."""

        if self.motivo_fallback is None:
            raise ValueError(
                "motivo_fallback é obrigatório quando a origem é fallback"
            )

        if not isinstance(self.motivo_fallback, MotivoFallback):
            raise ValueError("motivo_fallback possui valor inválido")

        if self.confianca_ml is not None:
            raise ValueError(
                "uma decisão de fallback não pode possuir confianca_ml"
            )

    @classmethod
    def de_ml(
            cls,
            causa_provavel: str,
            confianca_ml: float,
            versao_modelo: str = "",
    ) -> "ResultadoDecisaoHibrida":
        """Cria um resultado válido produzido pelo modelo."""

        return cls(
            causa_provavel=causa_provavel,
            origem_decisao=OrigemDecisao.ML,
            confianca_ml=confianca_ml,
            versao_modelo=versao_modelo,
        )

    @classmethod
    def de_fallback(
            cls,
            motivo: MotivoFallback,
            causa_provavel: str = "nao_classificado",
    ) -> "ResultadoDecisaoHibrida":
        """Cria um resultado quando o ML não pôde ser utilizado."""

        return cls(
            causa_provavel=causa_provavel,
            origem_decisao=OrigemDecisao.FALLBACK,
            motivo_fallback=motivo,
        )

    def to_dict(self) -> dict[str, Any]:
        """Converte o resultado para um formato serializável."""

        return {
            "causa_provavel": self.causa_provavel,
            "confianca_ml": self.confianca_ml,
            "origem_decisao": self.origem_decisao.value,
            "motivo_fallback": (
                self.motivo_fallback.value
                if self.motivo_fallback is not None
                else None
            ),
            "versao_modelo": self.versao_modelo,
        }
