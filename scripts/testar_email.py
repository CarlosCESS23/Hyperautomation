"""Envia um Email real usando as configurações do arquivo .env."""


from __future__ import annotations

import os
import sys
# Adiciona a pasta raiz (Hyperautomation) ao caminho de busca do Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import carregar_ambiente
from src.sistema_alertas import (
    AdaptadorEmail,
    Alerta,
    Severidade,
)

import argparse
import json
from pathlib import Path

from uuid import uuid4





def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Testa isoladamente o canal SMTP de Email"
        )
    )

    parser.add_argument(
        "--anexo",
        type=Path,
        help="Arquivo opcional que será anexado ao Email",
    )

    parser.add_argument(
        "--mensagem",
        default=(
            "Teste real do canal secundário "
            "do pipeline Hyperautomation"
        ),
    )

    args = parser.parse_args()

    if (
        args.anexo is not None
        and not args.anexo.is_file()
    ):
        print(
            f"Anexo não encontrado: {args.anexo}",
            file=sys.stderr,
        )
        return 2

    carregar_ambiente()

    try:
        adaptador = (
            AdaptadorEmail.de_ambiente()
        )
    except ValueError as erro:
        print(
            f"Configuração inválida: {erro}",
            file=sys.stderr,
        )
        return 2

    execution_id = (
        f"exec-email-{uuid4()}"
    )

    alerta = Alerta(
        severidade=Severidade.AVISO,
        mensagem=args.mensagem,
        anexo=args.anexo,
        contexto={
            "execution_id": execution_id,
            "bot_id": "teste-email-manual",
            "tipo_teste": "smtp_real",
        },
    )

    resultado = adaptador.enviar(
        alerta
    )

    print(
        json.dumps(
            resultado.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )

    if resultado.sucesso:
        print(
            "\nEmail enviado com sucesso."
        )
        return 0

    print(
        "\nO Email não foi entregue.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())