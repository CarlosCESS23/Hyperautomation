"""Testes unitários das regras RN09–RN12 da validação de lotes."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.validacao_lotes import validar_registro


@pytest.mark.unit
class TestValidarRegistroRN09RN12(unittest.TestCase):
    """Valida cenários críticos sem acessar planilhas ou serviços externos."""

    def setUp(self):
        """Prepara um registro válido e dependências compartilhadas."""
        self.registro_base = pd.Series(
            {
                "lote_id": "LOTE-001",
                "produto": "Produto A",
                "linha": "Linha 1",
                "turno": "Manhã",
                "status": "APROVADO",
                "responsavel": "Ana",
                "data": "15/08/2026",
                "observacao": "Inspeção concluída",
            },
            dtype=object,
        )
        self.data_referencia = "15/08/2026"
        self.base_referencia = MagicMock(name="base_referencia")
        self.base_referencia.__contains__.return_value = True
        self.primeira_ocorrencia = 1

    def test_rn09_classifica_status_reconhecido_e_ambiguo(self):
        cenarios = (
            ("status aprovado é válido", "APROVADO", "Válido", "Registro em conformidade"),
            ("status pendente é válido", "PENDENTE", "Válido", "Registro em conformidade"),
            (
                "status desconhecido é ambíguo",
                "EM ANÁLISE",
                "Ambíguo",
                "Status não reconhecido: EM ANÁLISE",
            ),
        )

        for descricao, status, classificacao, motivo in cenarios:
            with self.subTest(cenario=descricao):
                # Arrange
                registro = self.registro_base.copy()
                registro["status"] = status
                self.base_referencia.reset_mock()

                # Act
                resultado = validar_registro(
                    registro,
                    self.data_referencia,
                    self.base_referencia,
                    self.primeira_ocorrencia,
                )

                # Assert
                self.assertEqual(classificacao, resultado.classificacao)
                self.assertEqual(motivo, resultado.motivo)
                self.base_referencia.__contains__.assert_called_once_with("LOTE-001")

    def test_rn10_exige_observacao_para_lote_reprovado(self):
        cenarios = (
            (
                "reprovado com observação é válido",
                "Falha dimensional identificada",
                "Válido",
                "Registro em conformidade",
            ),
            (
                "reprovado sem observação diverge",
                "",
                "Divergência",
                "Lote reprovado sem observação",
            ),
            (
                "reprovado com somente espaços diverge",
                "   ",
                "Divergência",
                "Lote reprovado sem observação",
            ),
        )

        for descricao, observacao, classificacao, motivo in cenarios:
            with self.subTest(cenario=descricao):
                # Arrange
                registro = self.registro_base.copy()
                registro["status"] = "REPROVADO"
                registro["observacao"] = observacao
                self.base_referencia.reset_mock()

                # Act
                resultado = validar_registro(
                    registro,
                    self.data_referencia,
                    self.base_referencia,
                    self.primeira_ocorrencia,
                )

                # Assert
                self.assertEqual(classificacao, resultado.classificacao)
                self.assertEqual(motivo, resultado.motivo)
                self.base_referencia.__contains__.assert_called_once_with("LOTE-001")

    @pytest.mark.regression
    def test_regressao_rn10_reprovado_sem_observacao(self):
        """Protegendo o bug que corrige de registros REPROVADO sem observação válida"""

        observacoes_invalidas = (None, "", "   ")

        for observacao in observacoes_invalidas:
            with self.subTest(observacao=repr(observacao)):
                # Arrange

                registro = self.registro_base.copy()
                registro["status"] = "REPROVADO"
                registro["observacao"] = observacao

                self.base_referencia.reset_mock()

                # Act
                resultado = validar_registro(registro,self.data_referencia,self.base_referencia,self.primeira_ocorrencia)

                #Assert
                self.assertEqual('Divergência',resultado.classificacao)
                self.assertIn('Lote reprovado sem observação',resultado.motivo)
                self.assertNotEqual('Válido',resultado.classificacao)
                self.base_referencia.__contains__.assert_called_once_with('LOTE-001')

    def test_rn11_classifica_duplicidades_a_partir_da_segunda_ocorrencia(self):
        cenarios = (
            ("primeira ocorrência é válida", 1, "Válido", "Registro em conformidade"),
            (
                "segunda ocorrência é duplicidade",
                2,
                "Divergência",
                "Duplicidade no dia 15/08/2026 (ocorrência 2)",
            ),
            (
                "terceira ocorrência continua duplicada",
                3,
                "Divergência",
                "Duplicidade no dia 15/08/2026 (ocorrência 3)",
            ),
        )

        for descricao, ocorrencia, classificacao, motivo in cenarios:
            with self.subTest(cenario=descricao):
                # Arrange
                registro = self.registro_base.copy()
                self.base_referencia.reset_mock()

                # Act
                resultado = validar_registro(
                    registro,
                    self.data_referencia,
                    self.base_referencia,
                    ocorrencia,
                )

                # Assert
                self.assertEqual(classificacao, resultado.classificacao)
                self.assertEqual(motivo, resultado.motivo)
                self.base_referencia.__contains__.assert_called_once_with("LOTE-001")

    def test_rn12_classifica_datas_validas_e_erros_de_entrada(self):
        cenarios = (
            (
                "data textual válida",
                "15/08/2026",
                "Válido",
                "Registro em conformidade",
            ),
            (
                "objeto datetime válido",
                datetime(2026, 8, 15),
                "Válido",
                "Registro em conformidade",
            ),
            (
                "data em formato inválido",
                "2026-08-15",
                "Erro de Entrada",
                "Data ausente ou fora do formato DD/MM/AAAA",
            ),
            (
                "data de calendário inexistente",
                "31/02/2026",
                "Erro de Entrada",
                "Data ausente ou fora do formato DD/MM/AAAA",
            ),
            (
                "data ausente",
                None,
                "Erro de Entrada",
                "Data ausente ou fora do formato DD/MM/AAAA",
            ),
        )

        for descricao, data, classificacao, motivo in cenarios:
            with self.subTest(cenario=descricao):
                # Arrange
                registro = self.registro_base.copy()
                registro["data"] = data
                self.base_referencia.reset_mock()

                # Act
                resultado = validar_registro(
                    registro,
                    self.data_referencia,
                    self.base_referencia,
                    self.primeira_ocorrencia,
                )

                # Assert
                self.assertEqual(classificacao, resultado.classificacao)
                self.assertEqual(motivo, resultado.motivo)
                if classificacao == "Erro de Entrada":
                    self.base_referencia.__contains__.assert_not_called()
                else:
                    self.base_referencia.__contains__.assert_called_once_with("LOTE-001")


if __name__ == "__main__":
    unittest.main()
