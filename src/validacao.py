def verificar_lote(id_lote : str, base_referencia: list) -> bool:
    """
    Regra de Negócio 3: Validação de existencia
    Verifica se o lote existe na base referência
    """

    if not id_lote or id_lote not in base_referencia:
        raise ValueError(f"""Divergência: Lote não existe\n
                         Lote de id: {id_lote} não foi encontrado na base de referência
                         """)
    return True

def verificar_observacao_reprovado_rn07(status: str, observacao: str, logging):
    # Vamos padronizar o texto para evitar erros de CamelSensitive
    status_normalizado = str(status).strip().upper if status else ""

    if status_normalizado == 'REPROVADO':
        if not observacao or str(observacao).strip() == "" or str(observacao).lower() == 'nan':
            msg = "Divergência: Falta de Justificativa no campo de observação em lote em REPROVADO"
            logging.error(msg)
            raise ValueError(msg)
    return True

def validar_estrutura_rn01(lista: list, logger):
    # Colunas de referencia
    colunas_referencia = {"lote_id", "produto", "linha", "turno", "status", "responsavel", "data", "observacao"}
    # Colunas da planilha recebida
    colunas_recebidas = set(lista)

    colunas_invalidas = colunas_referencia - colunas_recebidas

    if colunas_invalidas:
        msg = f"Falha na RN01: Identificou-se {colunas_invalidas} fora do padrão estipulado"
        logger.error(msg)
        raise ValueError(msg)


def validar_campos_obrigatorios_rn02(df, logger):
    # 1. Ignoramos a coluna 'observacao', pois ela PODE ser vazia (ex: Lotes Aprovados)
    colunas_para_verificar = df.drop(columns=['observacao'], errors='ignore')

    # 2. Aplicamos a máscara de nulos apenas nas colunas essenciais
    mascara_nulos = colunas_para_verificar.isna()

    if mascara_nulos.any().any():
        # Empilha PRIMEIRO, filtra DEPOIS — compatível com pandas >= 2.1,
        # onde stack() deixou de descartar NaN por padrão.
        nulos_empilhados = mascara_nulos.stack()
        coordenadas = nulos_empilhados[nulos_empilhados].index.tolist()

        primeiro_erro = coordenadas[0]
        linha_erro, coluna_erro = primeiro_erro

        msg = f"Falha na RN02: Valor ausente ou nulo encontrado na linha {linha_erro}, coluna '{coluna_erro}'."
        logger.error(msg)
        raise ValueError(msg)
    
def normalizar_status_rn05(status: str) -> str:
    """
    Normaliza os status específicos 'OK' e 'NOK' para o padrão do sistema.
    """
    mapeamento = {
        "OK": "APROVADO",
        "NOK": "REPROVADO"
    }
    # Retorna o valor mapeado; se não existir no dicionário, retorna o próprio status
    return mapeamento.get(status, status)

def verificar_status_rn04(status: str, logger) -> str:
    """
    Verifica se o status pertence ao escopo de regras de negócio.
    Aciona a normalização caso identifique entradas 'OK' ou 'NOK'.
    """
    # Tratamento defensivo da entrada
    status_tratado = str(status).strip().upper()

    # Validação e acionamento da normalização
    if status_tratado in {"OK", "NOK"}:
        status_tratado = normalizar_status_rn05(status_tratado)

    # Conjunto de referência (Operação O(1))
    status_permitidos = {"APROVADO", "REPROVADO", "PENDENTE"}

    if status_tratado not in status_permitidos:
        msg = f"Erro de validação: Status '{status}' não reconhecido."
        logger.error(msg)
        raise ValueError(msg)

    return status_tratado
