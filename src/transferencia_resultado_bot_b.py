"""Serialização do resultado produzido pelo Bot B."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from src.bots.bot_conferencia import (
    ResultadoBotConferencia,
    StatusBotConferencia,
)
from src.validacao_lotes import (
    RegistroValidado,
)


NOME_CONTRATO = "resultado_bot_b"
VERSAO_CONTRATO = 1


def salvar_resultado_bot_b(
    resultado: ResultadoBotConferencia,
    caminho: str | Path,
) -> Path:
    """Salva o resultado completo para o Bot C."""

    destino = Path(caminho)

    destino.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "contrato": NOME_CONTRATO,
        "versao": VERSAO_CONTRATO,
        "resumo": resultado.to_dict(),
        "registros": [
            asdict(registro)
            for registro in resultado.registros
        ],
    }

    destino.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=_converter_json,
        ),
        encoding="utf-8",
    )

    return destino


def carregar_resultado_bot_b(
    caminho: str | Path,
) -> ResultadoBotConferencia:
    """Reconstrói o resultado recebido pelo Bot C."""

    origem = Path(caminho)

    dados = json.loads(
        origem.read_text(
            encoding="utf-8",
        )
    )

    if dados.get("contrato") != NOME_CONTRATO:
        raise ValueError(
            "Contrato do resultado do Bot B "
            "é inválido"
        )

    if dados.get("versao") != VERSAO_CONTRATO:
        raise ValueError(
            "Versão de contrato do Bot B "
            "não suportada"
        )

    resumo = dados.get("resumo")

    if not isinstance(resumo, dict):
        raise ValueError(
            "Resumo do Bot B é inválido"
        )

    registros_brutos = dados.get(
        "registros",
    )

    if not isinstance(
        registros_brutos,
        list,
    ):
        raise ValueError(
            "Registros do Bot B são inválidos"
        )

    registros = tuple(
        RegistroValidado(**registro)
        for registro in registros_brutos
    )

    return ResultadoBotConferencia(
        sucesso=bool(
            resumo["sucesso"]
        ),
        status=StatusBotConferencia(
            resumo["status"]
        ),
        mensagem=str(
            resumo["mensagem"]
        ),
        execution_id=str(
            resumo["execution_id"]
        ),
        correlation_id=str(
            resumo["correlation_id"]
        ),
        caminho_entrada=str(
            resumo["caminho_entrada"]
        ),
        registros=registros,
        classificacoes=dict(
            resumo.get(
                "classificacoes",
                {},
            )
        ),
        origens_decisao=dict(
            resumo.get(
                "origens_decisao",
                {},
            )
        ),
        decisoes_auditadas=int(
            resumo.get(
                "decisoes_auditadas",
                0,
            )
        ),
        erro=resumo.get("erro"),
    )


def _converter_json(
    valor: Any,
) -> Any:
    """
    Converte números produzidos por bibliotecas
    como NumPy para valores nativos.
    """

    item = getattr(
        valor,
        "item",
        None,
    )

    if callable(item):
        return item()

    raise TypeError(
        f"Valor não serializável: "
        f"{type(valor).__name__}"
    )