import pandas as pd
import logging

def verificar_estrutura_rn01(lista: list, logging):
    # Colunas de Referência
    colunas_referencia = {"lote_id", "produto", "linha",
                          "turno", "status", "responsavel",
                          "data", "observacao"
                          }
    # Colunas da planilha recebida
    colunas_recebidas = set(lista)

    colunas_invalidas = colunas_referencia - colunas_recebidas

    if colunas_invalidas:
        msg = f"Falha na RN01: Identificou-se {colunas_invalidas} fora do padrão estipulado"
        logging.error(msg)
        raise ValueError(msg)

def validar_campos_obrigatorios_rn02(df,logger):
    #1. Ignoramos a coluna 'observação", pois ela pode ser que esteja vazia(ex: Lotes Aprovados)
    verificar_coluna = df.drop(columns=["observacao"], errors="ignore")

    #2. Aplicamos a máscara de nulos apenas nas colunas essenciais
    mascara_nulos = verificar_coluna.isna()

    if mascara_nulos.any():
        nulos_empilhados = mascara_nulos.stack()
        coordenadas = nulos_empilhados[nulos_empilhados].index.tolist()

        primeiro_erro = coordenadas[0]
        linha_erro, coluna_erro = primeiro_erro

        mensagem = f"Falha na RN02: Valor ausente ou nulo encontrado na linha {linha_erro}, coluna '{coluna_erro}."
        logging.error(mensagem)
        raise ValueError(mensagem)