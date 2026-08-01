"""
Nesse modulo, será responsável por fazer as validações através de testes, então para cada mudança
que ocorrer, será obrigatório o uso desse pytest.
"""

#Importando as bibliotecas necessárias
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

# Importando para buscar as funções necessárias para verificar se os metódos estão funcionando
from src.validacao import verificar_estrutura_rn01
from src.relatorio import *

# Caminho da planilha para efetuar o teste:

CAMINHO_PLANINHA = 'data/samples/inspecao_lotes_dia_teste.xlsx'

@pytest.fixture
def mock_logger():
    """ Para criar um logger falso, e não tendo tanta sujeira no terminal durante o teste"""
    return MagicMock()

"""
Testes para a Regra R1
"""

def test_rn01_caminho_feliz(mock_logger):
    """Esse é o teste para verificar se a função ela passa de forma silenciamente quando as colunas
    estão presentes
    """
    colunas_corretas = [
        'lote_id', 'produto' ,'linha' , 'turno',
        'status','responsavel','data','observacao'
    ]
    # Se lançar exeção, o teste falha. Como não deve lançar, o teste passa
    verificar_estrutura_rn01(colunas_corretas, mock_logger)

def test_rn01_caminho_com_colunas_extras(mock_logger):
    """
    Teste para verificar se realmente está passando de forma aceitavel, se houver colunas a mais

    """
    colunas_corretas = [
        'lote_id', 'produto',
        'linha' , 'turno', 'status','responsavel',
        'data','observacao', 'coluna_nova'
    ]
    verificar_estrutura_rn01(colunas_corretas, mock_logger)

def test_rn01_falha_ao_faltar_colunas(mock_logger):
    """
    Testes para verificar se realmente está falhando corretamente para caso tiver coluna obrigatória
    faltando.
    """
    colunas_incorretas = [
        'lote_id','produto',
        'linha','turno',
        'responsavel','data'
    ]

    verificar_estrutura_rn01(colunas_incorretas, mock_logger)
