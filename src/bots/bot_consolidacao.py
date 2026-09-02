"""Bot D: consolidação dos dados coletados pelos Bots B e C."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Sequence

from src.contratos_capstone import (
    ArtefatoConsolidacao,
    ArtefatoEstoqueDesktop,
    ArtefatoPedidosFornecedor,
    EnvelopeAuditoria,
    EstadoExecucao,
    FonteDados,
    PedidoFornecedor,
    RegistroConsolidado,
    RegistroEstoqueDesktop,
)


LOGGER = logging.getLogger("botcity_permorfer")

BOT_ID = "bot-d-consolidacao"

ESTADOS_DISPONIVEIS = frozenset(
    {
        EstadoExecucao.CONCLUIDO,
        EstadoExecucao.CONCLUIDO_DEGRADADO,
    }
)


class FalhaConsolidacaoError(RuntimeError):
    """Representa uma falha controlada na consolidação."""


@dataclass(frozen=True)
class ConfiguracaoConsolidacao:
    """Configuração utilizada pelo Bot D."""

    caminho_artefato: Path = Path(
        "data/output/registros_consolidados.json"
    )


@dataclass(frozen=True)
class ResultadoConsolidacao:
    """Resultado controlado produzido pelo Bot D."""

    sucesso: bool
    estado: EstadoExecucao
    total_registros: int
    caminho_artefato: Path
    fontes_disponiveis: tuple[
        FonteDados,
        ...,
    ]
    erros_fontes: tuple[str, ...] = ()
    erro: str | None = None


def _normalizar_status(
    valor: str | None,
) -> str:
    """Normaliza um status para comparação."""

    if valor is None:
        return ""

    return (
        valor.strip()
        .upper()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _validar_rastreabilidade(
    *,
    execution_id_esperado: str,
    correlation_id_esperado: str,
    execution_id_recebido: str,
    correlation_id_recebido: str,
    fonte: str,
) -> None:
    """Impede a mistura de artefatos de execuções diferentes."""

    if (
        execution_id_recebido
        != execution_id_esperado
    ):
        raise FalhaConsolidacaoError(
            f"execution_id da fonte {fonte} "
            "não pertence à execução atual"
        )

    if (
        correlation_id_recebido
        != correlation_id_esperado
    ):
        raise FalhaConsolidacaoError(
            f"correlation_id da fonte {fonte} "
            "não pertence à execução atual"
        )


def carregar_estoque(
    caminho: Path,
    *,
    execution_id: str,
    correlation_id: str,
) -> ArtefatoEstoqueDesktop:
    """Carrega e valida o artefato produzido pelo Bot B."""

    caminho = Path(caminho)

    if not caminho.is_file():
        raise FileNotFoundError(
            "Artefato do Bot B não encontrado: "
            f"{caminho}"
        )

    artefato = ArtefatoEstoqueDesktop.de_json(
        caminho.read_text(
            encoding="utf-8"
        )
    )

    _validar_rastreabilidade(
        execution_id_esperado=execution_id,
        correlation_id_esperado=(
            correlation_id
        ),
        execution_id_recebido=(
            artefato.auditoria.execution_id
        ),
        correlation_id_recebido=(
            artefato.auditoria.correlation_id
        ),
        fonte="desktop",
    )

    return artefato


def carregar_pedidos(
    caminho: Path,
    *,
    execution_id: str,
    correlation_id: str,
) -> ArtefatoPedidosFornecedor:
    """Carrega e valida o artefato produzido pelo Bot C."""

    caminho = Path(caminho)

    if not caminho.is_file():
        raise FileNotFoundError(
            "Artefato do Bot C não encontrado: "
            f"{caminho}"
        )

    artefato = (
        ArtefatoPedidosFornecedor.de_json(
            caminho.read_text(
                encoding="utf-8"
            )
        )
    )

    _validar_rastreabilidade(
        execution_id_esperado=execution_id,
        correlation_id_esperado=(
            correlation_id
        ),
        execution_id_recebido=(
            artefato.auditoria.execution_id
        ),
        correlation_id_recebido=(
            artefato.auditoria.correlation_id
        ),
        fonte="web",
    )

    return artefato


def _agrupar_pedidos(
    pedidos: Sequence[PedidoFornecedor],
) -> dict[str, list[PedidoFornecedor]]:
    """Agrupa os pedidos pelo lote relacionado."""

    agrupados: dict[
        str,
        list[PedidoFornecedor],
    ] = {}

    for pedido in pedidos:
        agrupados.setdefault(
            pedido.lote_id,
            [],
        ).append(pedido)

    return agrupados


def _indexar_estoque(
    registros: Sequence[
        RegistroEstoqueDesktop
    ],
) -> dict[str, RegistroEstoqueDesktop]:
    """Indexa os registros de estoque pelo lote."""

    indexados: dict[
        str,
        RegistroEstoqueDesktop,
    ] = {}

    for registro in registros:
        anterior = indexados.get(
            registro.lote_id
        )

        if (
            anterior is not None
            and anterior != registro
        ):
            raise FalhaConsolidacaoError(
                "Lote duplicado com dados "
                "diferentes no estoque: "
                f"{registro.lote_id}"
            )

        indexados[registro.lote_id] = (
            registro
        )

    return indexados


def _status_pedido_principal(
    pedidos: Sequence[PedidoFornecedor],
) -> str | None:
    """Seleciona o status mais crítico entre os pedidos."""

    if not pedidos:
        return None

    prioridades = {
        "CANCELADO": 5,
        "ATRASADO": 4,
        "PENDENTE": 3,
        "EM_TRANSITO": 2,
        "EM_SEPARACAO": 2,
        "ENTREGUE": 1,
    }

    return max(
        (
            _normalizar_status(
                pedido.status_pedido
            )
            for pedido in pedidos
        ),
        key=lambda status: (
            prioridades.get(status, 0)
        ),
    )


def _classificar_registro(
    estoque: RegistroEstoqueDesktop | None,
    pedidos: Sequence[PedidoFornecedor],
) -> tuple[str, str, tuple[str, ...]]:
    """Aplica a classificação determinística do Bot D."""

    if estoque is None:
        return (
            "SEM_REGISTRO_ESTOQUE",
            (
                "O lote existe no portal de "
                "fornecedores, mas não foi "
                "encontrado no estoque interno."
            ),
            ("RD01",),
        )

    if not pedidos:
        return (
            "SEM_PEDIDO_FORNECEDOR",
            (
                "O lote existe no estoque, "
                "mas não possui pedido no portal."
            ),
            ("RD02",),
        )

    quantidade_pedida = sum(
        pedido.quantidade_pedida
        for pedido in pedidos
    )

    status_estoque = _normalizar_status(
        estoque.status_estoque
    )

    status_pedido = (
        _status_pedido_principal(
            pedidos
        )
    )

    if (
        estoque.quantidade_disponivel == 0
        or status_estoque
        in {
            "INDISPONIVEL",
            "SEM_ESTOQUE",
        }
    ):
        return (
            "ESTOQUE_INDISPONIVEL",
            (
                "O lote possui pedido, mas está "
                "indisponível no estoque."
            ),
            ("RD03",),
        )

    if (
        estoque.quantidade_disponivel
        < quantidade_pedida
    ):
        return (
            "ESTOQUE_INSUFICIENTE",
            (
                "A quantidade disponível é menor "
                "que a quantidade total pedida."
            ),
            ("RD04",),
        )

    if status_pedido == "ATRASADO":
        return (
            "ENTREGA_ATRASADA",
            (
                "O estoque é suficiente, mas existe "
                "pedido com entrega atrasada."
            ),
            ("RD05",),
        )

    if status_estoque == "ESTOQUE_BAIXO":
        return (
            "ATENCAO_ESTOQUE_BAIXO",
            (
                "O lote está disponível, mas seu "
                "status indica estoque baixo."
            ),
            ("RD06",),
        )

    return (
        "REGULAR",
        (
            "O estoque é suficiente e não foi "
            "encontrada divergência crítica."
        ),
        ("RD07",),
    )


def consolidar_registros(
    *,
    estoque: Sequence[
        RegistroEstoqueDesktop
    ],
    pedidos: Sequence[
        PedidoFornecedor
    ],
) -> tuple[RegistroConsolidado, ...]:
    """Realiza a junção completa dos lotes das duas fontes."""

    estoque_por_lote = _indexar_estoque(
        estoque
    )

    pedidos_por_lote = _agrupar_pedidos(
        pedidos
    )

    lotes = sorted(
        set(estoque_por_lote)
        | set(pedidos_por_lote)
    )

    consolidados: list[
        RegistroConsolidado
    ] = []

    for lote_id in lotes:
        registro_estoque = (
            estoque_por_lote.get(
                lote_id
            )
        )

        pedidos_lote = (
            pedidos_por_lote.get(
                lote_id,
                [],
            )
        )

        fontes: list[FonteDados] = []

        if registro_estoque is not None:
            fontes.append(
                FonteDados.DESKTOP
            )

        if pedidos_lote:
            fontes.append(
                FonteDados.WEB
            )

        classificacao, motivo, regras = (
            _classificar_registro(
                registro_estoque,
                pedidos_lote,
            )
        )

        quantidade_pedida = (
            sum(
                pedido.quantidade_pedida
                for pedido in pedidos_lote
            )
            if pedidos_lote
            else None
        )

        produto = (
            registro_estoque.produto
            if registro_estoque is not None
            else pedidos_lote[0].produto
        )

        possui_duas_fontes = (
            FonteDados.DESKTOP in fontes
            and FonteDados.WEB in fontes
        )

        consolidados.append(
            RegistroConsolidado(
                lote_id=lote_id,
                produto=produto,
                quantidade_estoque=(
                    registro_estoque
                    .quantidade_disponivel
                    if registro_estoque
                    is not None
                    else None
                ),
                quantidade_pedida=(
                    quantidade_pedida
                ),
                status_estoque=(
                    registro_estoque
                    .status_estoque
                    if registro_estoque
                    is not None
                    else None
                ),
                status_pedido=(
                    _status_pedido_principal(
                        pedidos_lote
                    )
                ),
                classificacao_deterministica=(
                    classificacao
                ),
                motivo=motivo,
                regras_aplicadas=regras,
                fontes_disponiveis=tuple(
                    fontes
                ),
                modo_degradado=(
                    not possui_duas_fontes
                ),
            )
        )

    return tuple(consolidados)


def salvar_artefato(
    artefato: ArtefatoConsolidacao,
    caminho: Path,
) -> Path:
    """Salva o resultado de forma atômica."""

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


def executar_bot_consolidacao(
    *,
    caminho_estoque: Path | None,
    caminho_pedidos: Path | None,
    execution_id: str,
    correlation_id: str,
    task_id: str,
    predecessor_task_ids: Sequence[str] = (),
    configuracao: (
        ConfiguracaoConsolidacao | None
    ) = None,
    logger: logging.Logger | None = None,
) -> ResultadoConsolidacao:
    """Executa a consolidação com suporte a modo degradado."""

    configuracao = (
        configuracao
        or ConfiguracaoConsolidacao()
    )

    logger = logger or LOGGER

    erros_fontes: list[str] = []

    artefato_estoque = None
    artefato_pedidos = None

    if caminho_estoque is not None:
        try:
            artefato_estoque = carregar_estoque(
                caminho_estoque,
                execution_id=execution_id,
                correlation_id=correlation_id,
            )
        except Exception as erro:
            erros_fontes.append(
                f"desktop: {erro}"
            )

    if caminho_pedidos is not None:
        try:
            artefato_pedidos = carregar_pedidos(
                caminho_pedidos,
                execution_id=execution_id,
                correlation_id=correlation_id,
            )
        except Exception as erro:
            erros_fontes.append(
                f"web: {erro}"
            )

    desktop_disponivel = (
        artefato_estoque is not None
        and artefato_estoque.auditoria.estado
        in ESTADOS_DISPONIVEIS
    )

    web_disponivel = (
        artefato_pedidos is not None
        and artefato_pedidos.auditoria.estado
        in ESTADOS_DISPONIVEIS
    )

    fontes_disponiveis: list[
        FonteDados
    ] = []

    if desktop_disponivel:
        fontes_disponiveis.append(
            FonteDados.DESKTOP
        )

    if web_disponivel:
        fontes_disponiveis.append(
            FonteDados.WEB
        )

    if desktop_disponivel and web_disponivel:
        estado = EstadoExecucao.CONCLUIDO
    elif desktop_disponivel or web_disponivel:
        estado = (
            EstadoExecucao
            .CONCLUIDO_DEGRADADO
        )
    else:
        estado = EstadoExecucao.FALHOU

    registros: tuple[
        RegistroConsolidado,
        ...,
    ] = ()

    erro_final = None

    if estado != EstadoExecucao.FALHOU:
        registros = consolidar_registros(
            estoque=(
                artefato_estoque.registros
                if desktop_disponivel
                and artefato_estoque is not None
                else ()
            ),
            pedidos=(
                artefato_pedidos.registros
                if web_disponivel
                and artefato_pedidos is not None
                else ()
            ),
        )
    else:
        erro_final = (
            "Nenhuma fonte válida ficou "
            "disponível para consolidação"
        )

    ids_predecessores = [
        str(valor).strip()
        for valor in predecessor_task_ids
        if str(valor).strip()
    ]

    possui_predecessores = bool(
        ids_predecessores
    )

    artefato = ArtefatoConsolidacao(
        auditoria=EnvelopeAuditoria(
            execution_id=execution_id,
            correlation_id=correlation_id,
            bot_id=BOT_ID,
            task_id=task_id,
            estado=estado,
            predecessor=(
                "bot-b-coleta-desktop"
                "+bot-c-coleta-web"
                if possui_predecessores
                else None
            ),
            predecessor_task_id=(
                ",".join(ids_predecessores)
                if possui_predecessores
                else None
            ),
            resultado_predecessor=(
                "fontes_avaliadas"
                if possui_predecessores
                else None
            ),
        ),
        registros=registros,
    )

    caminho = salvar_artefato(
        artefato,
        configuracao.caminho_artefato,
    )

    sucesso = (
        estado != EstadoExecucao.FALHOU
    )

    metodo_log = (
        logger.info
        if sucesso
        else logger.error
    )

    metodo_log(
        (
            "consolidacao_concluida"
            if sucesso
            else "consolidacao_falhou"
        ),
        extra={
            "evento": (
                "consolidacao_concluida"
                if sucesso
                else "consolidacao_falhou"
            ),
            "bot_id": BOT_ID,
            "execution_id": execution_id,
            "correlation_id": (
                correlation_id
            ),
            "task_id": task_id,
            "estado": estado.value,
            "total_registros": (
                len(registros)
            ),
            "fontes_disponiveis": [
                fonte.value
                for fonte
                in fontes_disponiveis
            ],
            "erros_fontes": erros_fontes,
            "caminho_artefato": (
                str(caminho)
            ),
        },
    )

    return ResultadoConsolidacao(
        sucesso=sucesso,
        estado=estado,
        total_registros=len(registros),
        caminho_artefato=caminho,
        fontes_disponiveis=tuple(
            fontes_disponiveis
        ),
        erros_fontes=tuple(
            erros_fontes
        ),
        erro=erro_final,
    )