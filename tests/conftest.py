"""Fixtures compartilhadas pela suíte de testes."""

from pathlib import Path
import sys

import pytest
from datetime import datetime
from unittest.mock import MagicMock
import pandas as pd
import pytest

# Permite executar ``pytest tests/e2e/`` de qualquer diretório ou configuração
# de importação do pytest, sem exigir que o projeto esteja instalado como pacote.
RAIZ_PROJETO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from src.pages.formulario_lotes_page import PlaywrightFormularioLotesPage

DIAS_INSPECAO = [
    ("Insp_15_06_2026", "15/06/2026"),
    ("Insp_16_06_2026", "16/06/2026"),
    ("Insp_17_06_2026", "17/06/2026"),
    ("Insp_18_06_2026", "18/06/2026"),
    ("Insp_19_06_2026", "19/06/2026"),
    ("Insp_22_06_2026", "22/06/2026"),
    ("Insp_23_06_2026", "23/06/2026"),
    ("Insp_24_06_2026", "24/06/2026"),
    ("Insp_25_06_2026", "25/06/2026"),
    ("Insp_26_06_2026", "26/06/2026"),
]

@pytest.fixture
def mock_base_referencia(base_referencia_controlada):
    """
    Simula a consulta à Base de Referência.

    O retorno pode ser sobrescrito diretamente pelo teste.
    """

    mock = MagicMock(name="consulta_base_referencia")

    mock.return_value = set(base_referencia_controlada)

    return mock


@pytest.fixture
def registro_valido_factory():
    """
    Cria registros válidos independentes.

    Cada chamada retorna um novo objeto mutável.
    """

    def criar(
        lote_id="LOTE-VALIDO",
        produto="Produto A",
        linha="Linha 1",
        turno="Manhã",
        status="APROVADO",
        responsavel="Ana",
        data="15/06/2026",
        observacao="Inspeção concluída",
        **alteracoes,
    ):
        registro = {
            "lote_id": lote_id,
            "produto": produto,
            "linha": linha,
            "turno": turno,
            "status": status,
            "responsavel": responsavel,
            "data": data,
            "observacao": observacao,
        }

        registro.update(alteracoes)

        return pd.Series(
            registro,
            dtype=object,
        )

    return criar


@pytest.fixture
def registro_dict_factory():
    """
    Cria registros em formato dict para geração de planilhas.
    """

    def criar(
        lote_id="LOTE-VALIDO",
        produto="Produto A",
        linha="Linha 1",
        turno="Manhã",
        status="APROVADO",
        responsavel="Ana",
        data="15/06/2026",
        observacao="Inspeção concluída",
        **alteracoes,
    ):
        registro = {
            "lote_id": lote_id,
            "produto": produto,
            "linha": linha,
            "turno": turno,
            "status": status,
            "responsavel": responsavel,
            "data": data,
            "observacao": observacao,
        }

        registro.update(alteracoes)

        return registro

    return criar


@pytest.fixture
def cenarios_classificacao(registro_dict_factory):
    """
    Fornece registros representativos das classificações da suíte.
    """

    return {
        "valido": registro_dict_factory(
            lote_id="LOTE-VALIDO",
        ),

        "divergente": registro_dict_factory(
            lote_id="LOTE-DIVERGENTE",
            status="REPROVADO",
            observacao=None,
        ),

        "ambiguo": registro_dict_factory(
            lote_id="LOTE-AMBIGUO",
            status="EM ANÁLISE",
        ),

        "invalido": registro_dict_factory(
            lote_id="LOTE-INVALIDO",
            data="2026-06-15",
        ),

        "duplicado": registro_dict_factory(
            lote_id="LOTE-DUPLICADO",
        ),
    }


@pytest.fixture
def caminho_relatorio(tmp_path):
    """
    Retorna um caminho temporário para o relatório gerado.
    """

    return tmp_path / "relatorio_conferencia_lotes.xlsx"


@pytest.fixture
def planilha_controlada_factory(
    tmp_path,
    registro_dict_factory,
):
    """
    Cria planilhas temporárias compatíveis com o pipeline de relatório.
    """

    def criar(
        nome="inspecao_lotes_10dias.xlsx",
        registros_por_dia=None,
        lotes_referencia=None,
    ):
        caminho = tmp_path / nome

        if registros_por_dia is None:
            registros_por_dia = {}

            for indice, (nome_aba, data) in enumerate(
                DIAS_INSPECAO,
                start=1,
            ):
                registro_1 = registro_dict_factory(
                    lote_id=f"LOTE-{indice:03d}-A",
                    data=data,
                )

                registro_2 = registro_dict_factory(
                    lote_id=f"LOTE-{indice:03d}-B",
                    data=data,
                )

                registros_por_dia[nome_aba] = [
                    registro_1,
                    registro_2,
                ]

        if lotes_referencia is None:
            lotes_referencia = {
                registro["lote_id"]
                for registros in registros_por_dia.values()
                for registro in registros
                if registro.get("lote_id")
            }

        with pd.ExcelWriter(
            caminho,
            engine="openpyxl",
        ) as writer:

            for nome_aba, _ in DIAS_INSPECAO:
                registros = registros_por_dia.get(
                    nome_aba,
                    [],
                )

                df = pd.DataFrame(registros)

                if df.empty:
                    df = pd.DataFrame(
                        columns=[
                            "lote_id",
                            "produto",
                            "linha",
                            "turno",
                            "status",
                            "responsavel",
                            "data",
                            "observacao",
                        ]
                    )

                df.to_excel(
                    writer,
                    sheet_name=nome_aba,
                    index=False,
                    startrow=2,
                )

            pd.DataFrame(
                {
                    "lote_id": sorted(lotes_referencia),
                }
            ).to_excel(
                writer,
                sheet_name="Base_Referencia",
                index=False,
                startrow=1,
            )

        return caminho

    return criar


@pytest.fixture
def data_hora_fixa(monkeypatch):
    """
    Fixa datetime.now() no namespace de gerar_relatorio.

    O monkeypatch restaura automaticamente a implementação original
    após o término do teste.
    """

    import gerar_relatorio

    momento_fixo = datetime(
        2026,
        8,
        17,
        10,
        30,
        0,
    )

    datetime_real = datetime

    class DatetimeFixo(datetime_real):

        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return momento_fixo.replace(
                    tzinfo=tz,
                )

            return momento_fixo

        @classmethod
        def strptime(cls, data_string, formato):
            return datetime_real.strptime(
                data_string,
                formato,
            )

    monkeypatch.setattr(
        gerar_relatorio,
        "datetime",
        DatetimeFixo,
    )

    return momento_fixo


@pytest.fixture
def pagina_html() -> str:
    """Retorna o caminho absoluto do formulário alvo dos testes E2E."""
    caminho = RAIZ_PROJETO / "web" / "lote-teste.html"
    if not caminho.exists():
        pytest.skip(f"Arquivo {caminho} não encontrado — teste E2E ignorado")
    return str(caminho)


@pytest.fixture
def formulario_page(page, pagina_html) -> PlaywrightFormularioLotesPage:
    """Fornece o Page Object com o formulário aberto em uma aba limpa."""
    formulario = PlaywrightFormularioLotesPage(page=page, pagina_html=pagina_html)
    formulario.abrir()
    return formulario