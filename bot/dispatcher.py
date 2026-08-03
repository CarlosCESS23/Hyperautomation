"""Publica no DataPool os lotes informados no CSV de entrada."""

import argparse
import csv
import logging
from pathlib import Path

from botcity.maestro.datapool.entry import DataPoolEntry

from config import ROOT_DIR, obter_configuracao
from maestro_client import criar_cliente


CAMINHO_PADRAO = ROOT_DIR / "bot" / "dados_entrada" / "lotes_auditoria.csv"


def publicar_csv(caminho_csv: Path, logger: logging.Logger) -> int:
    config = obter_configuracao()
    maestro = criar_cliente(config)
    datapool = maestro.get_datapool(config.datapool_label)

    with caminho_csv.open(newline="", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)
        if not leitor.fieldnames or "cpf" not in leitor.fieldnames:
            raise ValueError("O CSV precisa conter, ao menos, a coluna 'cpf'.")
        quantidade = 0
        for linha_numero, linha in enumerate(leitor, start=2):
            valores = {chave: (valor or "").strip() for chave, valor in linha.items()}
            if not any(valores.values()):
                continue
            entrada = DataPoolEntry(values=valores)
            datapool.create_entry(entrada)
            quantidade += 1
            logger.info("Item da linha %s publicado no DataPool.", linha_numero)
    logger.info("Dispatcher finalizado: %s item(ns) publicado(s).", quantidade)
    return quantidade


def main() -> None:
    parser = argparse.ArgumentParser(description="Publica lotes de auditoria no DataPool.")
    parser.add_argument("--arquivo", type=Path, default=CAMINHO_PADRAO)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    publicar_csv(args.arquivo, logging.getLogger(__name__))


if __name__ == "__main__":
    main()
