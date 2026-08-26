"""Executa localmente a cadeia Bot A -> Bot B -> Bot C.

Exemplo:
    python executar_pipeline_bots.py data/input/inspecao_lotes_10dias.xlsx
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import sys
from typing import Any

from gerar_relatorio import (
    gerar_excel,
    gerar_pdf_resumo,
    gerar_resumo_executivo,
    localizar_entrada,
    salvar_log,
)
from src.bots.bot_conferencia import (
    ResultadoBotConferencia,
    executar_bot_conferencia,
)
from src.bots.bot_entrada import executar_bot_entrada
from src.bots.bot_relatorio import executar_bot_relatorio
from src.config import carregar_ambiente
from src.operational_indicators import consolidar_indicadores
from src.sistema_alertas import (
    Alerta,
    ResultadoAlerta,
    SistemaAlertas,
)


LOGGER = logging.getLogger("botcity_permorfer")
CAMINHO_LOG = Path("logs/pipeline_bots.jsonl")


class FormatadorJSON(logging.Formatter):
    """Grava os eventos principais como uma linha JSON por evento."""

    CAMPOS_EXTRAS = (
        "evento",
        "bot_id",
        "execution_id",
        "correlation_id",
        "status",
        "total_registros",
        "classificacoes",
        "origens_decisao",
        "canal_entrega",
        "fallback_acionado",
        "tentativas",
        "erro",
    )

    def format(self, record: logging.LogRecord) -> str:
        dados: dict[str, Any] = {
            "data_hora": self.formatTime(
                record,
                "%Y-%m-%dT%H:%M:%S",
            ),
            "nivel": record.levelname,
            "mensagem": record.getMessage(),
        }
        for campo in self.CAMPOS_EXTRAS:
            if hasattr(record, campo):
                dados[campo] = getattr(record, campo)

        if record.exc_info:
            dados["excecao"] = self.formatException(record.exc_info)

        return json.dumps(
            dados,
            ensure_ascii=False,
            default=str,
        )


class CanalConsole:
    """Canal local para demonstrar os alertas sem usar a internet."""

    nome = "console"

    def enviar(self, alerta: Alerta) -> ResultadoAlerta:
        print("\n" + "=" * 70)
        print(f"ALERTA {alerta.severidade.value} — CANAL CONSOLE")
        print(alerta.mensagem)
        if alerta.contexto:
            print("Contexto:")
            for chave, valor in alerta.contexto.items():
                print(f"  {chave}: {valor}")
        if alerta.anexo is not None:
            print(f"Anexo: {alerta.anexo.resolve()}")
        print("=" * 70 + "\n")

        return ResultadoAlerta(
            sucesso=True,
            canal=self.nome,
            message_id=(
                f"console-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            ),
        )


@dataclass(frozen=True)
class ResultadoPipelineBots:
    sucesso: bool
    etapa_final: str
    mensagem: str
    execution_id: str
    correlation_id: str
    caminho_relatorio: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sucesso": self.sucesso,
            "etapa_final": self.etapa_final,
            "mensagem": self.mensagem,
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "caminho_relatorio": self.caminho_relatorio,
        }


def configurar_logger(caminho: Path = CAMINHO_LOG) -> logging.Logger:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    logger = LOGGER
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatador = FormatadorJSON()

    arquivo = logging.FileHandler(caminho, encoding="utf-8")
    arquivo.setFormatter(formatador)
    logger.addHandler(arquivo)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatador)
    logger.addHandler(console)
    return logger


def criar_sistema_alertas(
    modo: str,
    logger: logging.Logger,
) -> SistemaAlertas | None:
    """Seleciona alerta local, real ou desativado."""

    if modo == "nenhum":
        return None
    if modo == "console":
        return SistemaAlertas(
            canal_principal=CanalConsole(),
            logger=logger,
        )
    if modo == "reais":
        return SistemaAlertas.de_ambiente(logger=logger)
    raise ValueError(f"Modo de alerta desconhecido: {modo}")


def _alertar_falha(
    sistema_alertas: SistemaAlertas | None,
    *,
    severidade: str,
    mensagem: str,
    execution_id: str,
    correlation_id: str,
    etapa: str,
) -> None:
    if sistema_alertas is None:
        return

    # SistemaAlertas já converte falhas de canal em resultados controlados.
    sistema_alertas.enviar_alerta(
        severidade=severidade,
        mensagem=mensagem,
        contexto={
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            "bot_id": etapa,
        },
    )


def _gerador_completo(
    origem: Path,
    *,
    gerar_pdf: bool,
):
    """Cria o gerador injetado no Bot C sem repetir o processamento."""

    def gerar(registros, saida: Path, momento: datetime):
        indicadores = consolidar_indicadores(registros)
        dados = gerar_excel(
            registros,
            saida,
            momento,
            indicadores,
        )
        gerar_resumo_executivo(
            indicadores,
            saida.with_name("resumo_executivo.md"),
        )
        salvar_log(
            dados,
            saida.with_name("log_execucao.txt"),
            origem,
            momento,
        )
        if gerar_pdf:
            gerar_pdf_resumo(
                dados,
                saida.with_name("dashboard_resumo.pdf"),
            )
        return dados

    return gerar


def _mostrar_resumo_bot_b(resultado: ResultadoBotConferencia) -> None:
    print("\nResumo produzido pelo Bot B:")
    print(f"  Total: {resultado.total_registros}")
    for classificacao, quantidade in sorted(
        resultado.classificacoes.items()
    ):
        print(f"  {classificacao}: {quantidade}")
    print(f"  Decisões auditadas: {resultado.decisoes_auditadas}")
    print(f"  Origens: {resultado.origens_decisao}")


def executar_pipeline(
    origem: Path,
    saida: Path,
    *,
    modo_alertas: str = "console",
    gerar_pdf: bool = True,
    logger: logging.Logger | None = None,
) -> ResultadoPipelineBots:
    """Executa os três bots em sequência e preserva a rastreabilidade."""

    logger = logger or configurar_logger()
    sistema_alertas = criar_sistema_alertas(modo_alertas, logger)

    print("\n[1/3] BOT A — validação e preparação da entrada")
    resultado_a = executar_bot_entrada(origem, logger=logger)

    if not resultado_a.sucesso:
        _alertar_falha(
            sistema_alertas,
            severidade="ERRO",
            mensagem=f"Bot A rejeitou a entrada: {resultado_a.mensagem}",
            execution_id=resultado_a.execution_id,
            correlation_id=resultado_a.correlation_id,
            etapa="bot-a-entrada",
        )
        return ResultadoPipelineBots(
            sucesso=False,
            etapa_final="bot_a",
            mensagem=resultado_a.mensagem,
            execution_id=resultado_a.execution_id,
            correlation_id=resultado_a.correlation_id,
        )

    parametros_b = resultado_a.parametros_bot_b
    assert parametros_b is not None

    print("[2/3] BOT B — aplicação das RN01-RN12 e ML/fallback")
    resultado_b = executar_bot_conferencia(
        parametros_b.caminho_entrada,
        execution_id=parametros_b.execution_id,
        correlation_id=parametros_b.correlation_id,
        logger=logger,
    )

    if not resultado_b.sucesso:
        _alertar_falha(
            sistema_alertas,
            severidade="CRITICO",
            mensagem=f"Bot B falhou: {resultado_b.mensagem}",
            execution_id=resultado_b.execution_id,
            correlation_id=resultado_b.correlation_id,
            etapa="bot-b-conferencia",
        )
        return ResultadoPipelineBots(
            sucesso=False,
            etapa_final="bot_b",
            mensagem=resultado_b.mensagem,
            execution_id=resultado_b.execution_id,
            correlation_id=resultado_b.correlation_id,
        )

    _mostrar_resumo_bot_b(resultado_b)

    print("\n[3/3] BOT C — relatório, dashboard e alertas")
    resultado_c = executar_bot_relatorio(
        resultado_b.registros,
        saida,
        execution_id=resultado_b.execution_id,
        correlation_id=resultado_b.correlation_id,
        sistema_alertas=sistema_alertas,
        gerador_relatorio=_gerador_completo(
            origem,
            gerar_pdf=gerar_pdf,
        ),
        logger=logger,
    )

    if not resultado_c.sucesso:
        _alertar_falha(
            sistema_alertas,
            severidade="CRITICO",
            mensagem=f"Bot C falhou: {resultado_c.mensagem}",
            execution_id=resultado_b.execution_id,
            correlation_id=resultado_b.correlation_id,
            etapa="bot-c-relatorio",
        )
        return ResultadoPipelineBots(
            sucesso=False,
            etapa_final="bot_c",
            mensagem=resultado_c.mensagem,
            execution_id=resultado_b.execution_id,
            correlation_id=resultado_b.correlation_id,
        )

    return ResultadoPipelineBots(
        sucesso=True,
        etapa_final="concluido",
        mensagem=resultado_c.mensagem,
        execution_id=resultado_c.execution_id,
        correlation_id=resultado_c.correlation_id,
        caminho_relatorio=resultado_c.caminho_relatorio,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "entrada",
        nargs="?",
        help=(
            "Planilha de dez dias. Quando omitida, procura em data/input "
            "e em Downloads."
        ),
    )
    parser.add_argument(
        "--saida",
        default="reports/relatorio_conferencia_lotes.xlsx",
        help="Caminho do relatório final",
    )
    parser.add_argument(
        "--alertas",
        choices=("console", "reais", "nenhum"),
        default="console",
        help=(
            "console demonstra localmente; reais usa Telegram/Email do .env; "
            "nenhum desativa notificações"
        ),
    )
    parser.add_argument(
        "--sem-pdf",
        action="store_true",
        help="Não gera o dashboard em PDF",
    )
    args = parser.parse_args()

    carregar_ambiente()
    logger = configurar_logger()

    try:
        origem = localizar_entrada(args.entrada)
        resultado = executar_pipeline(
            origem,
            Path(args.saida),
            modo_alertas=args.alertas,
            gerar_pdf=not args.sem_pdf,
            logger=logger,
        )
    except (FileNotFoundError, ValueError) as erro:
        print(f"ERRO DE CONFIGURAÇÃO: {erro}", file=sys.stderr)
        return 2

    print("\nResultado final:")
    print(
        json.dumps(
            resultado.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )

    if resultado.sucesso:
        print("\nPIPELINE A -> B -> C CONCLUÍDO COM SUCESSO")
        print(f"Relatório: {resultado.caminho_relatorio}")
        print(f"Logs: {CAMINHO_LOG.resolve()}")
        return 0

    print("\nPIPELINE ENCERRADO COM FALHA CONTROLADA")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())