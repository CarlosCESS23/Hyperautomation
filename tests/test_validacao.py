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
from src.validacao import verificar_estrutura_rn01,validar_campos_obrigatorios_rn02
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

"""
Testes para regra de negócio: RN02
"""

def test_rn02_caminho_feliz(mock_logger):
    """
    Verifica se o DataFrame que estão sem valores nulos, passa na validação
    """
    dados = {
        'lote_id' : [1,2],
        'produto': ["Produto A", "Produto B"],
        'observacao' : ['Lote Aprovado', 'Lote ok']
    }
    #Transformando em um dataframe
    df = pd.DataFrame(data=dados)

    validar_campos_obrigatorios_rn02(df, mock_logger)

def test_rn02_caminho_feliz_com_observao_vazia(mock_logger):
    """
    Verifica se os valores nulos nas colunas observação são ignorados
    """
    dados = {
        'lote_id': [1, 2],
        'produto': ["Produto A", "Produto B"],
        'observacao': [None, pd.NA]
    }
    df = pd.DataFrame(data=dados)
    validar_campos_obrigatorios_rn02(df, mock_logger)


def test_rn02_falha_em_campo_obrigatorio(mock_logger):
    """
    Verificando se realmente ele vai resultar em falha, pois, iremos inserir os valores nulos nos campos obrigatórios
    """
    dados = {
        'lote_id': [1, None],
        'produto': ["Produto A", None],
        'observacao': [None, pd.NA]
    }
    df = pd.DataFrame(data=dados)
    validar_campos_obrigatorios_rn02(df, mock_logger)
