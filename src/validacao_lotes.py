"""Serviço de validação de lotes conforme as regras RN01–RN12 da Aula 22.

Este módulo concentra a lógica de negócio. Consumidores como relatórios, bots e
testes devem chamar :func:`validar_registro`, sem reproduzir as regras.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import pandas as pd


CLASSIFICACOES = ("Válido", "Divergência", "Ambíguo", "Erro de Entrada")


def texto(valor: Any) -> str:
    """Converte célula vazia/NaN em texto vazio e remove espaços externos."""
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def data_valida(valor: Any) -> bool:
    """RN12: aceita somente data real ou texto estritamente DD/MM/AAAA."""
    if isinstance(valor, (pd.Timestamp, datetime)):
        return True
    bruto = texto(valor)
    if len(bruto) != 10:
        return False
    try:
        return datetime.strptime(bruto, "%d/%m/%Y").strftime("%d/%m/%Y") == bruto
    except ValueError:
        return False


def normalizar_status(status: Any) -> str:
    """Padroniza o status de inspeção usado pelas regras de negócio."""
    status_tratado = texto(status).upper()
    return {"OK": "APROVADO", "NOK": "REPROVADO"}.get(
        status_tratado, status_tratado
    )


@dataclass(frozen=True)
class RegistroValidado:
    """Resultado de negócio de uma linha, incluindo a data do dashboard."""

    data_referencia: str
    lote: str
    produto: str
    linha: str
    turno: str
    status: str
    responsavel: str
    data_inspecao: str
    observacao: str
    classificacao: str
    motivo: str
    acao_recomendada: str

    def to_dict(self) -> dict[str, str]:
        """Converte o resultado para as colunas públicas usadas pelo pandas."""
        nomes = {
            "data_referencia": "Data de Referência",
            "lote": "Lote",
            "produto": "Produto",
            "linha": "Linha",
            "turno": "Turno",
            "status": "Status",
            "responsavel": "Responsável",
            "data_inspecao": "Data da Inspeção",
            "observacao": "Observação",
            "classificacao": "Classificação",
            "motivo": "Motivo",
            "acao_recomendada": "Ação Recomendada",
        }
        return {nomes[chave]: valor for chave, valor in asdict(self).items()}


def validar_registro(
    registro: pd.Series,
    data_referencia: str,
    lotes_referencia: set[str],
    ocorrencia_no_dia: int,
) -> RegistroValidado:
    """Aplica RN01–RN12, retornando uma classificação exclusiva.

    A precedência é: erros estruturais, divergências de conciliação, estados
    ambíguos e, por fim, registros válidos. RN11 recebe a ocorrência calculada
    pelo consumidor dentro do dia; apenas a segunda ocorrência em diante é
    divergente.
    """
    lote = texto(registro.get("lote_id"))
    produto = texto(registro.get("produto"))
    linha = texto(registro.get("linha"))
    status_original = texto(registro.get("status")).upper()
    status = normalizar_status(registro.get("status"))
    responsavel = texto(registro.get("responsavel"))
    observacao = texto(registro.get("observacao"))
    data_bruta = registro.get("data")
    data_inspecao = (
        data_bruta.strftime("%d/%m/%Y")
        if isinstance(data_bruta, (pd.Timestamp, datetime))
        else texto(data_bruta)
    )

    campos_vazios = [
        rotulo
        for rotulo, valor in (
            ("lote", lote),
            ("produto", produto),
            ("linha", linha),
            ("status", status_original),
            ("responsável", responsavel),
        )
        if not valor
    ]
    if campos_vazios or not data_valida(data_bruta):
        motivos = []
        if campos_vazios:
            motivos.append("Campo obrigatório vazio: " + ", ".join(campos_vazios))
        if not data_valida(data_bruta):
            motivos.append("Data ausente ou fora do formato DD/MM/AAAA")
        classificacao = "Erro de Entrada"
        motivo = "; ".join(motivos)
        acao = "Corrigir os dados na planilha de origem"
    else:
        divergencias = []
        if lote not in lotes_referencia:
            divergencias.append("Lote não encontrado na base de referência")
        if status == "REPROVADO" and not observacao:
            divergencias.append("Lote reprovado sem observação")
        if ocorrencia_no_dia > 1:
            divergencias.append(
                f"Duplicidade no dia {data_referencia} (ocorrência {ocorrencia_no_dia})"
            )

        if divergencias:
            classificacao = "Divergência"
            motivo = "; ".join(divergencias)
            acao = "Conciliar com a base de referência ou com o processo"
        elif status not in {"APROVADO", "REPROVADO", "PENDENTE"}:
            classificacao = "Ambíguo"
            motivo = f"Status não reconhecido: {status_original}"
            acao = "Submeter à decisão da supervisão"
        else:
            classificacao = "Válido"
            motivo = "Registro em conformidade"
            acao = "Nenhuma ação necessária"

    return RegistroValidado(
        data_referencia=data_referencia,
        lote=lote,
        produto=produto,
        linha=linha,
        turno=texto(registro.get("turno")),
        status=status,
        responsavel=responsavel,
        data_inspecao=data_inspecao,
        observacao=observacao,
        classificacao=classificacao,
        motivo=motivo,
        acao_recomendada=acao,
    )
