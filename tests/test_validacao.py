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
from src.validacao import verificar_estrutura_rn01,validar_campos_obrigatorios_rn02,verificar_status_rn04,normalizar_status_rn05
from src.base_referencia import verificar_lotes

# Caminho da planilha para efetuar o teste:

CAMINHO_PLANINHA = 'data/samples/inspecao_lotes_dia_teste.xlsx'

@pytest.fixture
def mock_logger():
    """ Para criar um logger falso, e não tendo tanta sujeira no terminal durante o teste"""
    return MagicMock()

"""
Testes para regra de negócio: RN01
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
    msg_esperada = 'Falha na RN01: Identificou-se '
    with pytest.raises(ValueError,match=msg_esperada):
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
    msg_esperada = 'Falha na RN02: Valor ausente ou nulo encontrado na linha'
    with pytest.raises(ValueError,match=msg_esperada):
        validar_campos_obrigatorios_rn02(df, mock_logger)

"""
Testes para regra de negócio: RN03
"""

def test_rn03_caminho_feliz(mock_logger):
    """
    Verifica se a função retorna True quando o lote existe na base de referência
    """
    base_referencia_existente = ['LOTE-001','LOTE-002','LOTE-003']
    id_lote_existente = 'LOTE-002'

    resultado = verificar_lotes(id_lote_existente, base_referencia_existente, mock_logger)
    assert resultado == True

def test_rn03_falha_lote_nao_existe(mock_logger):
    """
     Verificando se realmente o lote que não existe, ele resulta em falha
    """
    base_referencia_existente = ['LOTE-001','LOTE-002','LOTE-003']
    id_lote_nao_existente = 'LOTE-005'

    msg_esperada = 'Divergencia: Lote não existe'
    with pytest.raises(ValueError,match=msg_esperada):
        verificar_lotes(id_lote_nao_existente, base_referencia_existente, mock_logger)

def test_rn03_falha_lote_vazio(mock_logger):
    """
    Verificando se o Lote vazio  é levantando caso seja uma string vazia.
    """
    base_referencia_existente = ['LOTE-001','LOTE-002','LOTE-003']
    id_lote_vazia = ''
    msg_esperada = 'Divergencia: Lote não existe'
    with pytest.raises(ValueError,match=msg_esperada):
        verificar_lotes(id_lote_vazia, base_referencia_existente, mock_logger)

def test_rn03_falha_lote_null(mock_logger):
    """Verificando se o lote estiver null, ele tem que resulta como verdadeiro"""
    base_referencia_existente = ['LOTE-001','LOTE-002','LOTE-003']
    id_lote_null = None
    msg_esperada = 'Divergencia: Lote não existe'
    with pytest.raises(ValueError,match=msg_esperada):
        verificar_lotes(id_lote_null, base_referencia_existente, mock_logger)

"""
Testes para regra de negócio de RN04
"""

@pytest.mark.parametrize(
    "status_entrada, status_esperado",[
        ("APROVADO","APROVADO"),
        ("REPROVADO","REPROVADO"),
        ("PENDENTE","PENDENTE"),
        ("  aprovado","APROVADO"),
        ("ok","APROVADO"),
        ("Nok","REPROVADO")
    ]
)
def test_rn04_status_validos_normalizados(mock_logger, status_entrada, status_esperado):
    """
    Verifica se os status são aceitos e além que serão devidamente tratados e validados.
    """
    resultado = verificar_status_rn04(status_entrada,mock_logger)
    assert resultado == status_esperado # Caso realmente a saída esperada seja correta

def test_rn04_status_invalido(mock_logger):
    """
    Garante que um ValueError seja levantando ao receber um status fora do escopo.
    """

    status_invalido = 'EM ANDAMENTO'
    msg_esperada = f'Erro de validação:'

    with pytest.raises(ValueError,match=msg_esperada):
        verificar_status_rn04(status_invalido, mock_logger)

    # Verificando se o erro foi realmente registrado no log
    assert mock_logger.error.called


def test_rn04_falha_com_status_vazio(mock_logger):
    """
    Garante que uma string vazia ou apenas espaços também levante erro.
    """

    status_vazio = "   "
    # De acordo com a lógica, caso realmente esteja vazio, ele irá informar o erro:
    with pytest.raises(ValueError, match="Erro de validação: Status '   ' não reconhecido."):
        verificar_status_rn04(status_vazio, mock_logger)

def test_rn05_normaliza_ok_para_aprovado():
    """
    Verifica se o status 'OK' é mapeado corretamente.
    """
    assert normalizar_status_rn05("OK") == "APROVADO"

def test_rn05_normaliza_nok_para_reprovado():
    """
    Verifica se o status 'NOK' é mapeado corretamente.
    """
    assert normalizar_status_rn05("NOK") == "REPROVADO"

def test_rn05_ignora_status_nao_mapeados():
    """
    Garante que status que não são 'OK' ou 'NOK' retornem inalterados.
    """
    assert normalizar_status_rn05("PENDENTE") == "PENDENTE"
    assert normalizar_status_rn05("OUTRO_VALOR") == "OUTRO_VALOR"