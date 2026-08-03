from pathlib import Path

import pandas as pd


CAMINHO_SAIDA = Path(__file__).resolve().parents[1] / "data" / "output" / "relatorio_divergencias.xlsx"

def gerar_relatorio_divergencias(dados: list, caminho_saida: str | Path) -> bool:
    """
    Gera relatório .xlsx contendo os registros de divergência
    """
    try:
        if not dados:
            df = pd.DataFrame(columns=["lote_id","status","observacao","motivo_divergencia"])
        else:
            df = pd.DataFrame(dados)

        caminho_saida = Path(caminho_saida)
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)

        df.to_excel(caminho_saida,index=False,engine='openpyxl')
        return True

    except Exception as e:
        raise IOError(f"Erro ao gerar relatório: \nMotivo:{e}")
