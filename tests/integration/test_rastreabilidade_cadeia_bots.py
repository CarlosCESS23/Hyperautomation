"""Valida a rastreabilidade da cadeia Bot A -> Bot B -> Bot C."""

from __future__ import annotations

import logging
from pathlib import Path

from executar_pipeline_bots import executar_pipeline


class CapturadorRegistros(logging.Handler):
    """Armazena os registros de log produzidos pelo pipeline."""

    def __init__(self) -> None:
        super().__init__()
        self.registros: list[logging.LogRecord] = []

    def emit(self, registro: logging.LogRecord) -> None:
        self.registros.append(registro)


def criar_logger_teste() -> tuple[
    logging.Logger,
    CapturadorRegistros,
]:
    logger = logging.getLogger(
        "teste_rastreabilidade_cadeia",
    )
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    capturador = CapturadorRegistros()
    logger.addHandler(capturador)

    return logger, capturador


def test_pipeline_registra_transicoes_entre_os_tres_bots(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ML_ENABLED", "false")

    entrada = Path(
        "data/input/inspecao_lotes_10dias.xlsx",
    )
    saida = tmp_path / "relatorio_cadeia.xlsx"

    logger, capturador = criar_logger_teste()

    resultado = executar_pipeline(
        entrada,
        saida,
        modo_alertas="nenhum",
        gerar_pdf=False,
        logger=logger,
    )

    assert resultado.sucesso is True
    assert saida.is_file()

    transicoes = [
        registro
        for registro in capturador.registros
        if getattr(
            registro,
            "evento",
            None,
        ) == "transicao_pipeline"
    ]

    assert len(transicoes) == 2

    assert [
        (
            registro.bot_origem,
            registro.bot_destino,
        )
        for registro in transicoes
    ] == [
        (
            "bot-a-entrada",
            "bot-b-conferencia",
        ),
        (
            "bot-b-conferencia",
            "bot-c-relatorio",
        ),
    ]

    assert all(
        registro.execution_id == resultado.execution_id
        for registro in transicoes
    )

    assert all(
        registro.correlation_id
        == resultado.correlation_id
        for registro in transicoes
    )

    assert transicoes[0].resultado_predecessor
    assert transicoes[1].resultado_predecessor