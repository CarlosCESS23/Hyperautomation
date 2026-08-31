"""Cria uma planilha demonstrativa com 250 registros e dez abas."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd


DIAS = (15, 16, 17, 18, 19, 22, 23, 24, 25, 26)


def _registro(
    *,
    lote_id: str,
    data: str,
    status: str = "APROVADO",
    produto: str = "Produto demonstrativo",
    observacao: str = "Inspeção executada",
) -> dict[str, str]:
    return {
        "lote_id": lote_id,
        "produto": produto,
        "linha": "Linha 1",
        "turno": "Manhã",
        "status": status,
        "responsavel": "Equipe demonstrativa",
        "data": data,
        "observacao": observacao,
    }


def criar_planilha(caminho: Path) -> None:
    """Gera o gabarito: 150 válidos, 50 divergências, 20 ambíguos e 30 erros."""

    caminho.parent.mkdir(parents=True, exist_ok=True)
    lotes_referencia: set[str] = set()

    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        for dia in DIAS:
            data = f"{dia:02d}/06/2026"
            sufixo_dia = f"{dia:02d}"
            registros: list[dict[str, str]] = []

            # 15 registros válidos por dia: 150 no total.
            for numero in range(1, 16):
                lote = f"LOTE-VAL-{sufixo_dia}-{numero:02d}"
                lotes_referencia.add(lote)
                registros.append(
                    _registro(lote_id=lote, data=data)
                )

            # 5 lotes ausentes da referência por dia: 50 divergências.
            for numero in range(1, 6):
                lote = f"LOTE-DIV-{sufixo_dia}-{numero:02d}"
                registros.append(
                    _registro(
                        lote_id=lote,
                        data=data,
                        observacao=(
                            "Código do lote não localizado na base"
                        ),
                    )
                )

            # 2 status desconhecidos por dia: 20 ambíguos.
            for numero in range(1, 3):
                lote = f"LOTE-AMB-{sufixo_dia}-{numero:02d}"
                lotes_referencia.add(lote)
                registros.append(
                    _registro(
                        lote_id=lote,
                        data=data,
                        status="EM ANÁLISE",
                        observacao="Aguardando definição da supervisão",
                    )
                )

            # 3 produtos vazios por dia: 30 erros de entrada.
            for numero in range(1, 4):
                lote = f"LOTE-ERR-{sufixo_dia}-{numero:02d}"
                lotes_referencia.add(lote)
                registros.append(
                    _registro(
                        lote_id=lote,
                        data=data,
                        produto="",
                        observacao="Produto não informado na origem",
                    )
                )

            pd.DataFrame(registros).to_excel(
                writer,
                sheet_name=f"Insp_{dia:02d}_06_2026",
                index=False,
                startrow=2,
            )

        pd.DataFrame(
            {"lote_id": sorted(lotes_referencia)}
        ).to_excel(
            writer,
            sheet_name="Base_Referencia",
            index=False,
            startrow=1,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--saida",
        default="data/input/inspecao_lotes_10dias.xlsx",
        help="Caminho da planilha que será criada",
    )
    parser.add_argument(
        "--sobrescrever",
        action="store_true",
        help="Permite substituir uma planilha demonstrativa existente",
    )
    args = parser.parse_args()

    caminho = Path(args.saida)
    if caminho.exists() and not args.sobrescrever:
        print(
            f"O arquivo já existe: {caminho.resolve()}\n"
            "Use --sobrescrever somente se quiser substituí-lo."
        )
        return 2

    criar_planilha(caminho)
    print(f"Planilha criada: {caminho.resolve()}")
    print("Total esperado: 250 registros")
    print(
        "Distribuição esperada: 150 válidos, 50 divergências, "
        "20 ambíguos e 30 erros de entrada"
    )
    print(
        "Gerada em: "
        + datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
