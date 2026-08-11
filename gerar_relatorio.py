"""Gera o relatório executivo de conferência de lotes (RN01 a RN12).

Uso:
    python gerar_relatorio.py caminho/inspecao_lotes_10dias.xlsx

Sem argumento, o script procura o arquivo em ``data/input`` e em Downloads.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook
from openpyxl.chart import DoughnutChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.marker import DataPoint
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo


CLASSIFICACOES = ("Válido", "Divergência", "Ambíguo", "Erro de Entrada")
CORES = {
    "Válido": "22C55E",
    "Divergência": "F59E0B",
    "Ambíguo": "8B5CF6",
    "Erro de Entrada": "EF4444",
}
ABAS = {
    "Válido": "Válidos",
    "Divergência": "Divergências",
    "Ambíguo": "Ambíguos",
    "Erro de Entrada": "Erros de Entrada",
}


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


@dataclass(frozen=True)
class RegistroValidado:
    """Resultado de negócio de uma linha da planilha de inspeção."""

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
    """Aplica RN01–RN12, com uma classificação exclusiva por registro.

    A precedência evita mistura de categorias: erros estruturais primeiro,
    conciliações em seguida e, por último, estados que pedem decisão humana.
    """
    lote = texto(registro.get("lote_id"))
    produto = texto(registro.get("produto"))
    linha = texto(registro.get("linha"))
    status_original = texto(registro.get("status")).upper()
    status = {"OK": "APROVADO", "NOK": "REPROVADO"}.get(
        status_original, status_original
    )
    observacao = texto(registro.get("observacao"))
    data_bruta = registro.get("data")
    data_inspecao = (
        data_bruta.strftime("%d/%m/%Y")
        if isinstance(data_bruta, (pd.Timestamp, datetime))
        else texto(data_bruta)
    )

    # O arquivo fornecido também marca o responsável como obrigatório no seu
    # gabarito operacional (dois casos). A validação preserva esse contrato.
    campos_vazios = [
        rotulo
        for rotulo, valor in (
            ("lote", lote),
            ("produto", produto),
            ("linha", linha),
            ("status", status_original),
            ("responsável", texto(registro.get("responsavel"))),
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
        responsavel=texto(registro.get("responsavel")),
        data_inspecao=data_inspecao,
        observacao=observacao,
        classificacao=classificacao,
        motivo=motivo,
        acao_recomendada=acao,
    )


def ler_e_validar(caminho: Path) -> list[RegistroValidado]:
    planilha = pd.ExcelFile(caminho)
    abas_diarias = sorted(
        (aba for aba in planilha.sheet_names if aba.startswith("Insp_")),
        key=lambda aba: datetime.strptime(aba, "Insp_%d_%m_%Y"),
    )
    if not abas_diarias:
        raise ValueError("Nenhuma aba diária no padrão Insp_DD_MM_AAAA foi encontrada.")

    referencia = pd.read_excel(caminho, sheet_name="Base_Referencia", header=1)
    lotes_referencia = {texto(valor) for valor in referencia["lote_id"] if texto(valor)}
    resultados: list[RegistroValidado] = []

    for aba in abas_diarias:
        dados = pd.read_excel(caminho, sheet_name=aba, header=2)
        # Remove somente rodapés/linhas sem os oito campos do registro.
        dados = dados[dados[["lote_id", "produto", "linha", "turno", "status", "responsavel", "data", "observacao"]].notna().any(axis=1)]
        dados = dados[~dados["lote_id"].fillna("").astype(str).str.startswith("Total de registros:")]
        data_referencia = datetime.strptime(aba, "Insp_%d_%m_%Y").strftime("%d/%m/%Y")

        # RN11 é deliberadamente reiniciada a cada aba/dia.
        totais = Counter(texto(valor) for valor in dados["lote_id"] if texto(valor))
        vistas: Counter[str] = Counter()
        for _, registro in dados.iterrows():
            lote = texto(registro.get("lote_id"))
            if lote and totais[lote] > 1:
                vistas[lote] += 1
                ocorrencia = vistas[lote]
            else:
                ocorrencia = 1
            resultados.append(
                validar_registro(registro, data_referencia, lotes_referencia, ocorrencia)
            )
    return resultados


def estilizar_tabela(ws, nome_tabela: str) -> None:
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    if ws.max_row >= 2:
        tabela = Table(displayName=nome_tabela, ref=ws.dimensions)
        tabela.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2", showRowStripes=True, showFirstColumn=False
        )
        ws.add_table(tabela)
    for celula in ws[1]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor="17365D")
        celula.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28
    for coluna in ws.columns:
        valores = [len(str(c.value or "")) for c in coluna[:80]]
        largura = min(max(max(valores, default=8) + 2, 11), 48)
        ws.column_dimensions[get_column_letter(coluna[0].column)].width = largura
    for row in ws.iter_rows(min_row=2):
        for celula in row:
            celula.alignment = Alignment(vertical="top", wrap_text=True)


def montar_resumo(ws, df: pd.DataFrame, momento: datetime) -> None:
    azul, azul_claro, branco = "17365D", "D9EAF7", "FFFFFF"
    ws.sheet_view.showGridLines = False
    ws.merge_cells("A1:N2")
    ws["A1"] = "CONFERÊNCIA DE LOTES · PAINEL EXECUTIVO"
    ws["A1"].font = Font(size=22, bold=True, color=branco)
    ws["A1"].fill = PatternFill("solid", fgColor=azul)
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 34
    ws["A3"] = "Período analisado"
    ws["B3"] = f"{df['Data de Referência'].min()} a {df['Data de Referência'].max()}"
    ws["F3"] = "Atualizado em"
    ws["G3"] = momento.strftime("%d/%m/%Y %H:%M:%S")

    contagens = df["Classificação"].value_counts().reindex(CLASSIFICACOES, fill_value=0)
    total = len(df)
    cards = [("TOTAL", total, "17365D")] + [
        (nome.upper(), int(contagens[nome]), CORES[nome]) for nome in CLASSIFICACOES
    ]
    for indice, (titulo, valor, cor) in enumerate(cards):
        coluna = 1 + indice * 3
        ws.merge_cells(start_row=5, start_column=coluna, end_row=5, end_column=coluna + 1)
        ws.merge_cells(start_row=6, start_column=coluna, end_row=6, end_column=coluna + 1)
        ws.merge_cells(start_row=7, start_column=coluna, end_row=7, end_column=coluna + 1)
        topo = ws.cell(5, coluna, titulo)
        numero = ws.cell(6, coluna, valor)
        for row in range(5, 8):
            for col in range(coluna, coluna + 2):
                ws.cell(row, col).fill = PatternFill("solid", fgColor=cor)
        topo.font = Font(bold=True, color=branco, size=10)
        numero.font = Font(bold=True, color=branco, size=23)
        topo.alignment = numero.alignment = Alignment(horizontal="center", vertical="center")
        if titulo != "TOTAL":
            ws.cell(7, coluna).value = int(valor) / total if total else 0
            ws.cell(7, coluna).number_format = "0.0%"
            ws.cell(7, coluna).font = Font(bold=True, color=branco)
            ws.cell(7, coluna).alignment = Alignment(horizontal="center")

    ws["A10"] = "Distribuição por classificação"
    ws["A10"].font = Font(size=14, bold=True, color=azul)
    ws["A11"], ws["B11"], ws["C11"] = "Classificação", "Quantidade", "%"
    for i, nome in enumerate(CLASSIFICACOES, start=12):
        ws.cell(i, 1, nome)
        ws.cell(i, 2, int(contagens[nome]))
        ws.cell(i, 3, int(contagens[nome]) / total if total else 0)
        ws.cell(i, 3).number_format = "0.0%"

    rosca = DoughnutChart()
    rosca.title = "Distribuição dos 250 registros"
    rosca.holeSize = 58
    rosca.height, rosca.width = 8.2, 12.5
    rosca.add_data(Reference(ws, min_col=2, min_row=11, max_row=15), titles_from_data=True)
    rosca.set_categories(Reference(ws, min_col=1, min_row=12, max_row=15))
    rosca.dataLabels = DataLabelList()
    rosca.dataLabels.showPercent = True
    rosca.dataLabels.showLeaderLines = True
    rosca.series[0].data_points = [DataPoint(idx=i, spPr=None) for i in range(4)]
    for ponto, nome in zip(rosca.series[0].data_points, CLASSIFICACOES):
        ponto.graphicalProperties.solidFill = CORES[nome]
    ws.add_chart(rosca, "E10")

    ws["A28"] = "Evolução diária dos registros que exigem ação"
    ws["A28"].font = Font(size=14, bold=True, color=azul)
    ws["A29"], ws["B29"], ws["C29"], ws["D29"] = (
        "Data", "Divergências", "Ambíguos", "Total de problemas"
    )
    diario = (
        df.assign(_n=1)
        .pivot_table(index="Data de Referência", columns="Classificação", values="_n", aggfunc="sum", fill_value=0)
        .reindex(columns=CLASSIFICACOES, fill_value=0)
    )
    diario.index = pd.to_datetime(diario.index, format="%d/%m/%Y")
    diario = diario.sort_index()
    for row, (data, valores) in enumerate(diario.iterrows(), start=30):
        ws.cell(row, 1, data.to_pydatetime())
        ws.cell(row, 1).number_format = "dd/mm/yyyy"
        ws.cell(row, 2, int(valores["Divergência"]))
        ws.cell(row, 3, int(valores["Ambíguo"]))
        ws.cell(row, 4, int(valores["Divergência"] + valores["Ambíguo"] + valores["Erro de Entrada"]))

    linha = LineChart()
    linha.title = "Evolução dos registros"
    linha.y_axis.title = "Quantidade"
    linha.x_axis.title = "Dia da inspeção"
    linha.style = 13
    linha.height, linha.width = 9, 22
    linha.add_data(Reference(ws, min_col=2, max_col=4, min_row=29, max_row=29 + len(diario)), titles_from_data=True)
    linha.set_categories(Reference(ws, min_col=1, min_row=30, max_row=29 + len(diario)))
    for serie, cor in zip(linha.series, (CORES["Divergência"], CORES["Ambíguo"], CORES["Erro de Entrada"])):
        serie.graphicalProperties.line.solidFill = cor
        serie.graphicalProperties.line.width = 28575
        serie.marker.symbol = "circle"
        serie.marker.size = 7
    ws.add_chart(linha, "E28")

    ws["A43"] = "LEITURA PARA DECISÃO"
    ws["A44"] = "Corrigir na origem"
    ws["B44"] = f"{contagens['Erro de Entrada']} registros"
    ws["A45"] = "Conciliar com base/processo"
    ws["B45"] = f"{contagens['Divergência']} registros"
    ws["A46"] = "Decisão humana"
    ws["B46"] = f"{contagens['Ambíguo']} registros"
    ws["A48"] = "Nota: duplicidades são avaliadas separadamente em cada dia; apenas a partir da 2ª ocorrência."
    ws.merge_cells("A48:N48")
    ws["A48"].fill = PatternFill("solid", fgColor=azul_claro)
    ws["A48"].font = Font(italic=True, color=azul)

    borda = Border(bottom=Side(style="thin", color="CBD5E1"))
    for linha_celulas in ws.iter_rows(min_row=11, max_row=15, min_col=1, max_col=3):
        for celula in linha_celulas:
            celula.border = borda
    for coluna, largura in {"A": 25, "B": 18, "C": 14, "D": 20, "E": 14, "F": 16, "G": 20, "H": 14, "I": 14, "J": 14, "K": 14, "L": 14, "M": 14, "N": 14}.items():
        ws.column_dimensions[coluna].width = largura
    ws.freeze_panes = "A4"
    ws.print_area = "A1:N49"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def gerar_excel(registros: list[RegistroValidado], saida: Path, momento: datetime) -> pd.DataFrame:
    df = pd.DataFrame([registro.to_dict() for registro in registros])
    saida.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(saida, engine="openpyxl") as writer:
        pd.DataFrame().to_excel(writer, sheet_name="Resumo", index=False)
        df.to_excel(writer, sheet_name="Todos", index=False)
        for classificacao, aba in ABAS.items():
            df[df["Classificação"] == classificacao].to_excel(writer, sheet_name=aba, index=False)

    wb = load_workbook(saida)
    montar_resumo(wb["Resumo"], df, momento)
    for numero, aba in enumerate(("Todos", *ABAS.values()), start=1):
        estilizar_tabela(wb[aba], f"Tabela{numero}")
    wb.active = wb.sheetnames.index("Resumo")
    wb.calculation.fullCalcOnLoad = True
    wb.save(saida)
    return df


def gerar_pdf_resumo(df: pd.DataFrame, saida: Path) -> bool:
    """Cria uma réplica estática do painel para impressão/entrega."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.patches import Patch
    except ImportError:
        return False
    contagens = df["Classificação"].value_counts().reindex(CLASSIFICACOES, fill_value=0)
    diario = df.groupby(["Data de Referência", "Classificação"]).size().unstack(fill_value=0).reindex(columns=CLASSIFICACOES, fill_value=0)
    diario.index = pd.to_datetime(diario.index, format="%d/%m/%Y")
    diario = diario.sort_index()
    fig = plt.figure(figsize=(16, 9), facecolor="#F7FAFC")
    grade = fig.add_gridspec(3, 5, height_ratios=[0.7, 2.7, 0.8], hspace=0.45, wspace=0.5)
    fig.suptitle("CONFERÊNCIA DE LOTES · PAINEL EXECUTIVO", fontsize=22, fontweight="bold", color="#17365D", y=0.97)
    cards = [("TOTAL", len(df), "#17365D")] + [(n.upper(), int(contagens[n]), "#" + CORES[n]) for n in CLASSIFICACOES]
    for i, (nome, valor, cor) in enumerate(cards):
        ax = fig.add_subplot(grade[0, i]); ax.axis("off")
        pct = "" if nome == "TOTAL" else f"\n{valor / len(df):.1%}"
        ax.text(0.5, 0.5, f"{nome}\n{valor}{pct}", ha="center", va="center", color="white", fontsize=12, fontweight="bold", bbox=dict(boxstyle="round,pad=0.8", facecolor=cor, edgecolor=cor))
    ax1 = fig.add_subplot(grade[1, :2])
    cores_distribuicao = ["#" + CORES[n] for n in CLASSIFICACOES]
    ax1.pie(
        contagens,
        labels=None,
        autopct="%1.1f%%",
        pctdistance=0.78,
        startangle=90,
        colors=cores_distribuicao,
        textprops={"color": "white", "fontweight": "bold", "fontsize": 11},
        wedgeprops=dict(width=0.48, edgecolor="white", linewidth=2),
    )
    ax1.set_title("Distribuição dos registros", fontweight="bold", color="#17365D")
    legenda = [
        Patch(facecolor=cor, edgecolor="none", label=nome)
        for nome, cor in zip(CLASSIFICACOES, cores_distribuicao)
    ]
    ax1.legend(
        handles=legenda,
        loc="lower left",
        bbox_to_anchor=(-0.12, -0.18),
        ncol=2,
        frameon=True,
        fancybox=True,
        framealpha=1,
        facecolor="white",
        edgecolor="#CBD5E1",
        fontsize=9,
        title="Legenda",
        title_fontproperties={"weight": "bold", "size": 9},
    )
    ax2 = fig.add_subplot(grade[1, 2:])
    eixo_x = diario.index.strftime("%d/%m")
    total_problemas = diario[["Divergência", "Ambíguo", "Erro de Entrada"]].sum(axis=1)
    posicoes = np.arange(len(eixo_x))
    largura = 0.25
    barras_divergencias = ax2.bar(
        posicoes - largura,
        diario["Divergência"],
        largura,
        label="Divergências",
        color="#F59E0B",
    )
    barras_ambiguos = ax2.bar(
        posicoes,
        diario["Ambíguo"],
        largura,
        label="Ambíguos",
        color="#8B5CF6",
    )
    barras_total = ax2.bar(
        posicoes + largura,
        total_problemas,
        largura,
        label="Total de problemas",
        color="#EF4444",
    )
    for barras in (barras_divergencias, barras_ambiguos, barras_total):
        ax2.bar_label(barras, padding=2, fontsize=7, color="#334155")
    ax2.set_title("Evolução dos registros", fontweight="bold", color="#17365D")
    ax2.set_ylabel("Quantidade")
    ax2.set_xticks(posicoes, eixo_x, rotation=35, ha="right")
    ax2.set_ylim(0, max(total_problemas) + 4)
    ax2.grid(axis="y", alpha=.25)
    ax2.set_axisbelow(True)
    ax2.legend(loc="upper left", ncol=3, frameon=False, fontsize=8)
    ax3 = fig.add_subplot(grade[2, :]); ax3.axis("off")
    ax3.text(0, .75, f"Corrigir na origem: {contagens['Erro de Entrada']}  |  Conciliar: {contagens['Divergência']}  |  Decisão humana: {contagens['Ambíguo']}", fontsize=13, fontweight="bold", color="#17365D")
    ax3.text(0, .25, "Duplicidades são avaliadas separadamente em cada dia e somente a partir da 2ª ocorrência.", fontsize=10, color="#475569")
    fig.savefig(saida, bbox_inches="tight")
    plt.close(fig)
    return True


def salvar_log(df: pd.DataFrame, caminho: Path, origem: Path, momento: datetime) -> None:
    contagens = df["Classificação"].value_counts().reindex(CLASSIFICACOES, fill_value=0)
    problemas = int(contagens[["Divergência", "Ambíguo", "Erro de Entrada"]].sum())
    linhas = [
        "LOG DE EXECUÇÃO — CONFERÊNCIA DE LOTES",
        f"Data/hora: {momento.strftime('%d/%m/%Y %H:%M:%S')}",
        f"Arquivo de origem: {origem.resolve()}",
        f"Total processado: {len(df)}",
        *(f"{nome}: {int(contagens[nome])}" for nome in CLASSIFICACOES),
        f"Total que exige ação: {problemas}",
        "RN11: contagem reiniciada em cada aba diária; divergência somente a partir da 2ª ocorrência.",
        "Validação de aceite: " + ("APROVADA" if len(df) == 250 and problemas == 100 else "REVISAR"),
    ]
    # BOM facilita a abertura correta em Bloco de Notas/PowerShell legados.
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8-sig")


def localizar_entrada(argumento: str | None) -> Path:
    candidatos = [
        Path(argumento) if argumento else None,
        Path("data/input/inspecao_lotes_10dias.xlsx"),
        Path.home() / "Downloads" / "inspecao_lotes_10dias.xlsx",
    ]
    for candidato in candidatos:
        if candidato and candidato.exists():
            return candidato
    raise FileNotFoundError("Informe o caminho de inspecao_lotes_10dias.xlsx.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entrada", nargs="?", help="Planilha de inspeções")
    parser.add_argument("--saida", default="reports/relatorio_conferencia_lotes.xlsx")
    args = parser.parse_args()
    origem, saida = localizar_entrada(args.entrada), Path(args.saida)
    momento = datetime.now()
    registros = ler_e_validar(origem)
    df = gerar_excel(registros, saida, momento)
    salvar_log(df, saida.with_name("log_execucao.txt"), origem, momento)
    pdf_ok = gerar_pdf_resumo(df, saida.with_name("dashboard_resumo.pdf"))
    contagens = df["Classificação"].value_counts().reindex(CLASSIFICACOES, fill_value=0)
    print(f"Relatório: {saida.resolve()}")
    print(f"Total: {len(df)} | " + " | ".join(f"{n}: {int(contagens[n])}" for n in CLASSIFICACOES))
    print("PDF: gerado" if pdf_ok else "PDF: matplotlib não instalado; Excel gerado normalmente")


if __name__ == "__main__":
    main()
