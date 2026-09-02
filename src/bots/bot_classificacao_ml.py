"""Bot E: enriquecimento híbrido dos registros consolidados."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from src.auditoria_hibrida import (
    AuditoriaPipelineHibrido,
)
from src.classificador_divergencia import (
    ClassificadorDivergencia,
)
from src.contratos_capstone import (
    ArtefatoClassificacaoML,
    ArtefatoConsolidacao,
    EnvelopeAuditoria,
    EstadoExecucao,
    RegistroClassificado,
    RegistroConsolidado,
)
from src.decisao_hibrida import (
    MotivoFallback,
    OrigemDecisao,
    ResultadoDecisaoHibrida,
)


LOGGER = logging.getLogger("botcity_permorfer")

BOT_ID = "bot-e-classificacao-ml"

ESTADOS_ACEITOS = frozenset(
    {
        EstadoExecucao.CONCLUIDO,
        EstadoExecucao.CONCLUIDO_DEGRADADO,
    }
)


class FalhaClassificacaoMLError(RuntimeError):
    """Representa uma falha controlada no Bot E."""


@dataclass(frozen=True)
class ConfiguracaoClassificacaoML:
    """Configuração do Bot E."""

    caminho_artefato: Path = Path(
        "data/output/registros_classificados.json"
    )


@dataclass(frozen=True)
class ResultadoClassificacaoML:
    """Resultado controlado produzido pelo Bot E."""

    sucesso: bool
    estado: EstadoExecucao
    total_registros: int
    total_ml: int
    total_fallback: int
    caminho_artefato: Path
    erro: str | None = None


def carregar_consolidacao(
    caminho: Path,
    *,
    execution_id: str,
    correlation_id: str,
) -> ArtefatoConsolidacao:
    """Carrega e valida o resultado produzido pelo Bot D."""

    caminho = Path(caminho)

    if not caminho.is_file():
        raise FileNotFoundError(
            "Artefato de consolidação "
            f"não encontrado: {caminho}"
        )

    artefato = ArtefatoConsolidacao.de_json(
        caminho.read_text(
            encoding="utf-8"
        )
    )

    if (
        artefato.auditoria.execution_id
        != execution_id
    ):
        raise FalhaClassificacaoMLError(
            "execution_id da consolidação "
            "não pertence à execução atual"
        )

    if (
        artefato.auditoria.correlation_id
        != correlation_id
    ):
        raise FalhaClassificacaoMLError(
            "correlation_id da consolidação "
            "não pertence à execução atual"
        )

    if (
        artefato.auditoria.estado
        not in ESTADOS_ACEITOS
    ):
        raise FalhaClassificacaoMLError(
            "A consolidação terminou com "
            f"estado {artefato.auditoria.estado.value}"
        )

    return artefato


def criar_observacao_ml(
    registro: RegistroConsolidado,
) -> str:
    """Transforma o registro consolidado em texto para o ML."""

    partes = [
        f"Lote {registro.lote_id}",
        f"produto {registro.produto}",
        (
            "classificação determinística "
            f"{registro.classificacao_deterministica}"
        ),
        f"motivo {registro.motivo}",
    ]

    if registro.quantidade_estoque is not None:
        partes.append(
            "quantidade em estoque "
            f"{registro.quantidade_estoque}"
        )

    if registro.quantidade_pedida is not None:
        partes.append(
            "quantidade pedida "
            f"{registro.quantidade_pedida}"
        )

    if registro.status_estoque is not None:
        partes.append(
            "status do estoque "
            f"{registro.status_estoque}"
        )

    if registro.status_pedido is not None:
        partes.append(
            "status do pedido "
            f"{registro.status_pedido}"
        )

    if registro.modo_degradado:
        partes.append(
            "processamento em modo degradado"
        )

    return ". ".join(partes) + "."


def _converter_decisao(
    registro: RegistroConsolidado,
    decisao: ResultadoDecisaoHibrida,
) -> RegistroClassificado:
    """Combina a regra determinística com a sugestão híbrida."""

    motivo_fallback = (
        decisao.motivo_fallback.value
        if decisao.motivo_fallback is not None
        else None
    )

    return RegistroClassificado(
        registro=registro,
        causa_provavel=(
            decisao.causa_provavel
        ),
        origem_decisao=(
            decisao.origem_decisao.value
        ),
        confianca_ml=(
            decisao.confianca_ml
        ),
        motivo_fallback=(
            motivo_fallback
        ),
        versao_modelo=(
            decisao.versao_modelo
        ),
    )


def classificar_registros(
    registros: tuple[
        RegistroConsolidado,
        ...,
    ],
    *,
    classificador: ClassificadorDivergencia,
    auditoria: AuditoriaPipelineHibrido,
    logger: logging.Logger,
) -> tuple[
    tuple[RegistroClassificado, ...],
    int,
    int,
]:
    """Classifica cada registro sem interromper o lote."""

    classificados: list[
        RegistroClassificado
    ] = []

    total_ml = 0
    total_fallback = 0

    for registro in registros:
        observacao = criar_observacao_ml(
            registro
        )

        try:
            decisao = auditoria.classificar(
                lote_id=registro.lote_id,
                classificador=(
                    classificador.classificar
                ),
                observacao=observacao,
            )

        except Exception as erro:
            logger.exception(
                "classificacao_ml_item_falhou",
                extra={
                    "evento": (
                        "classificacao_ml_item_falhou"
                    ),
                    "bot_id": BOT_ID,
                    "lote_id": registro.lote_id,
                    "erro": str(erro),
                },
            )

            decisao = (
                ResultadoDecisaoHibrida
                .de_fallback(
                    motivo=(
                        MotivoFallback
                        .SERVICO_INDISPONIVEL
                    )
                )
            )

            auditoria.registrar(
                lote_id=registro.lote_id,
                decisao=decisao,
                latencia_ms=0,
            )

        if (
            decisao.origem_decisao
            == OrigemDecisao.ML
        ):
            total_ml += 1
        else:
            total_fallback += 1

        classificados.append(
            _converter_decisao(
                registro,
                decisao,
            )
        )

    return (
        tuple(classificados),
        total_ml,
        total_fallback,
    )


def salvar_artefato(
    artefato: ArtefatoClassificacaoML,
    caminho: Path,
) -> Path:
    """Salva o artefato JSON de forma atômica."""

    caminho = Path(caminho)

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporario = caminho.with_suffix(
        caminho.suffix + ".tmp"
    )

    temporario.write_text(
        artefato.para_json(),
        encoding="utf-8",
    )

    temporario.replace(caminho)

    return caminho


def executar_bot_classificacao_ml(
    *,
    caminho_consolidacao: Path,
    execution_id: str,
    correlation_id: str,
    task_id: str,
    predecessor_task_id: str,
    configuracao: (
        ConfiguracaoClassificacaoML | None
    ) = None,
    classificador: (
        ClassificadorDivergencia | None
    ) = None,
    auditoria: (
        AuditoriaPipelineHibrido | None
    ) = None,
    logger: logging.Logger | None = None,
) -> ResultadoClassificacaoML:
    """Executa o enriquecimento híbrido do Bot E."""

    configuracao = (
        configuracao
        or ConfiguracaoClassificacaoML()
    )

    logger = logger or LOGGER

    classificador_execucao = (
        classificador
        if classificador is not None
        else (
            ClassificadorDivergencia
            .de_configuracao()
        )
    )

    auditoria_execucao = (
        auditoria
        if auditoria is not None
        else AuditoriaPipelineHibrido(
            execution_id=execution_id,
            logger=logger,
        )
    )

    try:
        consolidacao = carregar_consolidacao(
            caminho_consolidacao,
            execution_id=execution_id,
            correlation_id=correlation_id,
        )

        (
            registros_classificados,
            total_ml,
            total_fallback,
        ) = classificar_registros(
            consolidacao.registros,
            classificador=(
                classificador_execucao
            ),
            auditoria=auditoria_execucao,
            logger=logger,
        )

        possui_degradacao = (
            consolidacao.auditoria.estado
            == EstadoExecucao.CONCLUIDO_DEGRADADO
            or total_fallback > 0
        )

        estado = (
            EstadoExecucao.CONCLUIDO_DEGRADADO
            if possui_degradacao
            else EstadoExecucao.CONCLUIDO
        )

        artefato = ArtefatoClassificacaoML(
            auditoria=EnvelopeAuditoria(
                execution_id=execution_id,
                correlation_id=correlation_id,
                bot_id=BOT_ID,
                task_id=task_id,
                estado=estado,
                predecessor=(
                    "bot-d-consolidacao"
                ),
                predecessor_task_id=(
                    predecessor_task_id
                ),
                resultado_predecessor=(
                    consolidacao
                    .auditoria
                    .estado
                    .value
                ),
            ),
            registros=(
                registros_classificados
            ),
        )

        caminho = salvar_artefato(
            artefato,
            configuracao.caminho_artefato,
        )

        logger.info(
            "classificacao_ml_concluida",
            extra={
                "evento": (
                    "classificacao_ml_concluida"
                ),
                "bot_id": BOT_ID,
                "execution_id": execution_id,
                "correlation_id": (
                    correlation_id
                ),
                "task_id": task_id,
                "estado": estado.value,
                "total_registros": (
                    len(registros_classificados)
                ),
                "total_ml": total_ml,
                "total_fallback": (
                    total_fallback
                ),
                "caminho_artefato": (
                    str(caminho)
                ),
            },
        )

        return ResultadoClassificacaoML(
            sucesso=True,
            estado=estado,
            total_registros=(
                len(registros_classificados)
            ),
            total_ml=total_ml,
            total_fallback=total_fallback,
            caminho_artefato=caminho,
        )

    except Exception as erro:
        artefato_falha = (
            ArtefatoClassificacaoML(
                auditoria=EnvelopeAuditoria(
                    execution_id=execution_id,
                    correlation_id=(
                        correlation_id
                    ),
                    bot_id=BOT_ID,
                    task_id=task_id,
                    estado=(
                        EstadoExecucao.FALHOU
                    ),
                    predecessor=(
                        "bot-d-consolidacao"
                    ),
                    predecessor_task_id=(
                        predecessor_task_id
                    ),
                    resultado_predecessor=(
                        "classificacao_nao_realizada"
                    ),
                ),
                registros=(),
            )
        )

        caminho = salvar_artefato(
            artefato_falha,
            configuracao.caminho_artefato,
        )

        logger.exception(
            "classificacao_ml_falhou",
            extra={
                "evento": (
                    "classificacao_ml_falhou"
                ),
                "bot_id": BOT_ID,
                "execution_id": execution_id,
                "correlation_id": (
                    correlation_id
                ),
                "task_id": task_id,
                "erro": str(erro),
                "caminho_artefato": (
                    str(caminho)
                ),
            },
        )

        return ResultadoClassificacaoML(
            sucesso=False,
            estado=EstadoExecucao.FALHOU,
            total_registros=0,
            total_ml=0,
            total_fallback=0,
            caminho_artefato=caminho,
            erro=str(erro),
        )