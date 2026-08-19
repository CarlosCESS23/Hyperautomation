"""Verifica os artefatos do Exercício 22 usando apenas a biblioteca padrão.

Uso: python scripts/verificar_exercicio22.py
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


RAIZ = Path(__file__).resolve().parents[1]
RELATORIO = RAIZ / "reports" / "relatorio_conferencia_lotes.xlsx"
LOG = RAIZ / "reports" / "log_execucao.txt"
PDF = RAIZ / "reports" / "dashboard_resumo.pdf"
ABAS = [
    "Resumo", "Todos", "Válidos", "Divergências", "Ambíguos",
    "Erros de Entrada", "Ranking de Regras", "Dicionário",
    "Decisões de ML",
]
LINHAS = {"Todos": 251, "Válidos": 151, "Divergências": 51, "Ambíguos": 21, "Erros de Entrada": 31}

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
NS_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def exigir(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise AssertionError(mensagem)
    print(f"OK — {mensagem}")


def verificar_excel() -> None:
    exigir(RELATORIO.is_file(), "relatório Excel existe")
    with zipfile.ZipFile(RELATORIO) as arquivo:
        workbook = ET.fromstring(arquivo.read("xl/workbook.xml"))
        folhas = [
            (item.attrib["name"], item.attrib[f"{{{NS['r']}}}id"])
            for item in workbook.find("m:sheets", NS)
        ]
        exigir([nome for nome, _ in folhas] == ABAS, "as nove abas têm os nomes e a ordem esperados")

        relacionamentos = ET.fromstring(arquivo.read("xl/_rels/workbook.xml.rels"))
        destinos = {item.attrib["Id"]: item.attrib["Target"].lstrip("/") for item in relacionamentos}
        for nome, rel_id in folhas:
            if nome not in LINHAS:
                continue
            destino = destinos[rel_id]
            destino = destino if destino.startswith("xl/") else f"xl/{destino}"
            folha = ET.fromstring(arquivo.read(destino))
            quantidade = len(folha.findall(".//m:sheetData/m:row", NS))
            exigir(quantidade == LINHAS[nome], f"aba {nome}: {quantidade - 1} registros")

        graficos = [n for n in arquivo.namelist() if re.fullmatch(r"xl/charts/chart\d+\.xml", n)]
        imagens = [n for n in arquivo.namelist() if n.startswith("xl/media/")]
        exigir(len(graficos) == 2, "Resumo contém dois gráficos nativos")
        exigir(not imagens, "o Excel não usa imagens coladas como gráficos")


def verificar_evidencias() -> None:
    exigir(LOG.is_file(), "log de execução existe")
    conteudo = LOG.read_text(encoding="utf-8-sig")
    for trecho in (
        "Total processado: 250",
        "Válido: 150",
        "Divergência: 50",
        "Ambíguo: 20",
        "Erro de Entrada: 30",
        "Validação de aceite: APROVADA",
    ):
        exigir(trecho in conteudo, f"log registra “{trecho}”")
    exigir(PDF.is_file() and PDF.read_bytes()[:4] == b"%PDF", "dashboard em PDF existe e é válido")


def main() -> int:
    try:
        verificar_excel()
        verificar_evidencias()
    except (AssertionError, KeyError, OSError, zipfile.BadZipFile) as erro:
        print(f"FALHA — {erro}", file=sys.stderr)
        return 1
    print("\nACEITE DO EXERCÍCIO 22: APROVADO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
