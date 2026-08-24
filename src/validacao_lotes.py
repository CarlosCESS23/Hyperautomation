"""Serviço de validação de lotes conforme as regras RN01–RN12."""

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
    regra_aplicada: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.regra_aplicada, tuple):
            object.__setattr__(self, "regra_aplicada", ", ".join(self.regra_aplicada))

    @property
    def regras_acionadas(self) -> tuple[str, ...]:
        return tuple(
            regra.strip()
            for regra in self.regra_aplicada.split(",")
            if regra.strip()
        )

    def to_dict(self) -> dict[str, str]:
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
            "regra_aplicada": "Regra Aplicada",
        }
        return {nomes[chave]: valor for chave, valor in asdict(self).items()}


def validar_registro(
    registro: pd.Series,
    data_referencia: str,
    lotes_referencia: set[str],
    ocorrencia_no_dia: int,
) -> RegistroValidado:
    """Aplica RN01–RN12, retornando uma classificação exclusiva."""
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
    regra_aplicada = ''

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
    regras_acionadas: list[str] = []
    if campos_vazios or not data_valida(data_bruta):
        motivos = []
        regras = []
        if campos_vazios:
            motivos.append("Campo obrigatório vazio: " + ", ".join(campos_vazios))
            if not lote:
                regras_acionadas.append("RN01")
            if not produto:
                regras_acionadas.append("RN02")
            if not linha:
                regras_acionadas.append("RN03")
            if not status_original or not responsavel:
                regras_acionadas.append("RN04")
        if not data_valida(data_bruta):
            motivos.append("Data ausente ou fora do formato DD/MM/AAAA")
            regras_acionadas.append("RN12")
        classificacao = "Erro de Entrada"
        motivo = "; ".join(motivos)
        acao = "Corrigir os dados na planilha de origem"
        regra_aplicada = ', '.join(regras)
    else:
        divergencias = []
        regras_divergencia = [] # Criação de lista

        #RN05
        if lote not in lotes_referencia:
            divergencias.append("Lote não encontrado na base de referência")
            regras_acionadas.append("RN05")
        if status == "REPROVADO" and not observacao:
            divergencias.append("Lote reprovado sem observação")
            regras_acionadas.append("RN10")
        if ocorrencia_no_dia > 1:
            divergencias.append(
                f"Duplicidade no dia {data_referencia} (ocorrência {ocorrencia_no_dia})"
            )
            regras_acionadas.append("RN11")

        if divergencias:
            classificacao = "Divergência"
            motivo = "; ".join(divergencias)
            acao = "Conciliar com a base de referência ou com o processo"
            regra_aplicada = ', '.join(regras_divergencia)

        #RN09
        elif status not in {"APROVADO", "REPROVADO", "PENDENTE"}:
            classificacao = "Ambíguo"
            motivo = f"Status não reconhecido: {status_original}"
            acao = "Submeter à decisão da supervisão"
            regras_acionadas.append("RN09")
        else:
            classificacao = "Válido"
            motivo = "Registro em conformidade"
            acao = "Nenhuma ação necessária"
            regra_aplicada = ''

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
        regra_aplicada=", ".join(regras_acionadas),
    )
