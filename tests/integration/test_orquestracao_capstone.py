"""Testes da orquestração dos seis bots do Capstone."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pytest

from src.orquestracao_capstone import (
    BOTS_CAPSTONE,
    BOT_A_ENTRADA,
    BOT_B_COLETA_DESKTOP,
    BOT_C_COLETA_WEB,
    BOT_D_CONSOLIDACAO,
    BOT_E_CLASSIFICACAO_ML,
    BOT_F_RELATORIO,
    ServicoOrquestracaoCapstone,
    TarefaAgendada,
)


@dataclass(frozen=True)
class ChamadaCriacao:
    """Registra uma chamada feita ao orquestrador."""

    task_id: str
    activity_label: str
    parameters: dict[str, object]
    idempotency_key: str
    priority: int


class OrquestradorFalso:
    """Orquestrador em memória para os testes."""

    def __init__(self) -> None:
        self._contador = 0

        self._tarefas_por_chave: dict[
            str,
            TarefaAgendada,
        ] = {}

        self._chamadas_por_chave: dict[
            str,
            ChamadaCriacao,
        ] = {}

        self.chamadas: list[
            ChamadaCriacao
        ] = []

    def criar_tarefa_idempotente(
        self,
        *,
        activity_label: str,
        parameters: Mapping[
            str,
            object,
        ],
        idempotency_key: str,
        priority: int = 0,
    ) -> TarefaAgendada:
        """Cria ou reutiliza uma tarefa."""

        parametros = dict(parameters)

        tarefa_existente = (
            self._tarefas_por_chave.get(
                idempotency_key
            )
        )

        if tarefa_existente is not None:
            chamada_original = (
                self._chamadas_por_chave[
                    idempotency_key
                ]
            )

            if (
                chamada_original.activity_label
                != activity_label
                or chamada_original.parameters
                != parametros
                or chamada_original.priority
                != priority
            ):
                raise ValueError(
                    "chave de idempotência "
                    "reutilizada com dados "
                    "diferentes: "
                    f"{idempotency_key}"
                )

            return TarefaAgendada(
                task_id=(
                    tarefa_existente.task_id
                ),
                activity_label=(
                    tarefa_existente
                    .activity_label
                ),
                idempotency_key=(
                    idempotency_key
                ),
                criada=False,
            )

        self._contador += 1

        task_id = (
            f"task-{self._contador:03d}"
        )

        tarefa = TarefaAgendada(
            task_id=task_id,
            activity_label=activity_label,
            idempotency_key=(
                idempotency_key
            ),
            criada=True,
        )

        chamada = ChamadaCriacao(
            task_id=task_id,
            activity_label=activity_label,
            parameters=parametros,
            idempotency_key=(
                idempotency_key
            ),
            priority=priority,
        )

        self._tarefas_por_chave[
            idempotency_key
        ] = tarefa

        self._chamadas_por_chave[
            idempotency_key
        ] = chamada

        self.chamadas.append(chamada)

        return tarefa

    def obter_chamada(
        self,
        activity_label: str,
    ) -> ChamadaCriacao:
        """Localiza a chamada de criação de um bot."""

        encontradas = [
            chamada
            for chamada in self.chamadas
            if (
                chamada.activity_label
                == activity_label
            )
        ]

        if len(encontradas) != 1:
            raise AssertionError(
                "esperada uma chamada para "
                f"{activity_label}; "
                f"encontradas: "
                f"{len(encontradas)}"
            )

        return encontradas[0]


def criar_servico(
) -> tuple[
    OrquestradorFalso,
    ServicoOrquestracaoCapstone,
]:
    """Cria os objetos utilizados nos testes."""

    orquestrador = OrquestradorFalso()

    servico = (
        ServicoOrquestracaoCapstone(
            orquestrador
        )
    )

    return orquestrador, servico


def test_seis_bots_possuem_nomes_unicos():
    """Confirma os nomes oficiais dos bots."""

    nomes = [
        bot.activity_label
        for bot in BOTS_CAPSTONE
    ]

    assert len(nomes) == 6
    assert len(set(nomes)) == 6

    assert nomes == [
        "carlos_souza-entrada-v2",
        (
            "carlos_souza-"
            "coleta-desktop-v1"
        ),
        (
            "carlos_souza-"
            "coleta-web-v1"
        ),
        (
            "carlos_souza-"
            "conferencia-v2"
        ),
        (
            "carlos_souza-"
            "classificacao-ml-v1"
        ),
        (
            "carlos_souza-"
            "relatorio-v2"
        ),
    ]


def test_bot_a_realiza_fanout_para_b_e_c():
    """O Bot A cria as duas coletas independentes."""

    (
        orquestrador,
        servico,
    ) = criar_servico()

    fluxo = servico.iniciar_fluxo(
        task_id_bot_a="task-a-001",
        execution_id="exec-001",
        correlation_id="corr-001",
        parametros_desktop={
            "janela_estoque": (
                "Hyperautomation - "
                "Estoque Interno"
            ),
        },
        parametros_web={
            "portal_url": (
                "http://127.0.0.1:8010"
            ),
        },
    )

    assert (
        fluxo
        .coleta_desktop
        .activity_label
        == (
            BOT_B_COLETA_DESKTOP
            .activity_label
        )
    )

    assert (
        fluxo
        .coleta_web
        .activity_label
        == (
            BOT_C_COLETA_WEB
            .activity_label
        )
    )

    assert (
        fluxo.coleta_desktop.task_id
        != fluxo.coleta_web.task_id
    )

    chamada_desktop = (
        orquestrador.obter_chamada(
            BOT_B_COLETA_DESKTOP
            .activity_label
        )
    )

    chamada_web = (
        orquestrador.obter_chamada(
            BOT_C_COLETA_WEB
            .activity_label
        )
    )

    for chamada in (
        chamada_desktop,
        chamada_web,
    ):
        assert (
            chamada.parameters[
                "predecessor"
            ]
            == BOT_A_ENTRADA.activity_label
        )

        assert (
            chamada.parameters[
                "predecessor_task_id"
            ]
            == "task-a-001"
        )

        assert (
            chamada.parameters[
                "execution_id"
            ]
            == "exec-001"
        )

        assert (
            chamada.parameters[
                "correlation_id"
            ]
            == "corr-001"
        )

    assert (
        chamada_desktop.parameters[
            "janela_estoque"
        ]
        == (
            "Hyperautomation - "
            "Estoque Interno"
        )
    )

    assert (
        chamada_web.parameters[
            "portal_url"
        ]
        == "http://127.0.0.1:8010"
    )


def test_bot_d_recebe_referencias_de_b_e_c():
    """O Bot D recebe os IDs dos dois predecessores."""

    (
        orquestrador,
        servico,
    ) = criar_servico()

    fluxo = servico.iniciar_fluxo(
        task_id_bot_a="task-a-002",
        execution_id="exec-002",
        correlation_id="corr-002",
    )

    chamada_bot_d = (
        orquestrador.obter_chamada(
            BOT_D_CONSOLIDACAO
            .activity_label
        )
    )

    predecessores = (
        chamada_bot_d.parameters[
            "predecessores"
        ]
    )

    assert isinstance(
        predecessores,
        dict,
    )

    coleta_desktop = (
        predecessores[
            "coleta_desktop"
        ]
    )

    coleta_web = (
        predecessores[
            "coleta_web"
        ]
    )

    assert isinstance(
        coleta_desktop,
        dict,
    )

    assert isinstance(
        coleta_web,
        dict,
    )

    assert (
        coleta_desktop["task_id"]
        == fluxo
        .coleta_desktop
        .task_id
    )

    assert (
        coleta_web["task_id"]
        == fluxo.coleta_web.task_id
    )

    assert (
        coleta_desktop[
            "activity_label"
        ]
        == (
            BOT_B_COLETA_DESKTOP
            .activity_label
        )
    )

    assert (
        coleta_web[
            "activity_label"
        ]
        == (
            BOT_C_COLETA_WEB
            .activity_label
        )
    )

    assert (
        coleta_desktop[
            "artifact_name"
        ]
        == "estoque_desktop.json"
    )

    assert (
        coleta_web[
            "artifact_name"
        ]
        == "pedidos_fornecedores.json"
    )

    assert (
        chamada_bot_d.parameters[
            "execution_id"
        ]
        == "exec-002"
    )

    assert (
        chamada_bot_d.parameters[
            "correlation_id"
        ]
        == "corr-002"
    )


def test_fluxo_d_e_f_preserva_rastreabilidade():
    """D cria E e E cria F com os mesmos IDs."""

    (
        orquestrador,
        servico,
    ) = criar_servico()

    fluxo = servico.iniciar_fluxo(
        task_id_bot_a="task-a-003",
        execution_id="exec-003",
        correlation_id="corr-003",
    )

    tarefa_bot_e = (
        servico.agendar_classificacao_ml(
            task_id_bot_d=(
                fluxo.consolidacao.task_id
            ),
            resultado_bot_d=(
                "CONCLUIDO"
            ),
            nome_artefato=(
                "registros_consolidados.json"
            ),
            execution_id="exec-003",
            correlation_id="corr-003",
        )
    )

    tarefa_bot_f = (
        servico.agendar_relatorio(
            task_id_bot_e=(
                tarefa_bot_e.task_id
            ),
            resultado_bot_e=(
                "CONCLUIDO"
            ),
            nome_artefato=(
                "registros_classificados.json"
            ),
            execution_id="exec-003",
            correlation_id="corr-003",
        )
    )

    assert (
        tarefa_bot_e.activity_label
        == (
            BOT_E_CLASSIFICACAO_ML
            .activity_label
        )
    )

    assert (
        tarefa_bot_f.activity_label
        == (
            BOT_F_RELATORIO
            .activity_label
        )
    )

    chamada_bot_e = (
        orquestrador.obter_chamada(
            BOT_E_CLASSIFICACAO_ML
            .activity_label
        )
    )

    chamada_bot_f = (
        orquestrador.obter_chamada(
            BOT_F_RELATORIO
            .activity_label
        )
    )

    for chamada in (
        chamada_bot_e,
        chamada_bot_f,
    ):
        assert (
            chamada.parameters[
                "execution_id"
            ]
            == "exec-003"
        )

        assert (
            chamada.parameters[
                "correlation_id"
            ]
            == "corr-003"
        )

    assert (
        chamada_bot_e.parameters[
            "predecessor_task_id"
        ]
        == fluxo.consolidacao.task_id
    )

    assert (
        chamada_bot_e.parameters[
            "artefato_entrada"
        ]
        == (
            "registros_consolidados.json"
        )
    )

    assert (
        chamada_bot_f.parameters[
            "predecessor_task_id"
        ]
        == tarefa_bot_e.task_id
    )

    assert (
        chamada_bot_f.parameters[
            "artefato_entrada"
        ]
        == (
            "registros_classificados.json"
        )
    )

    # B, C, D, E e F.
    assert len(
        orquestrador.chamadas
    ) == 5


def test_reprocessamento_nao_cria_duplicados():
    """Executar novamente reutiliza as tarefas."""

    (
        orquestrador,
        servico,
    ) = criar_servico()

    primeiro = servico.iniciar_fluxo(
        task_id_bot_a="task-a-004",
        execution_id="exec-004",
        correlation_id="corr-004",
    )

    segundo = servico.iniciar_fluxo(
        task_id_bot_a="task-a-004",
        execution_id="exec-004",
        correlation_id="corr-004",
    )

    # Somente B, C e D foram realmente criados.
    assert len(
        orquestrador.chamadas
    ) == 3

    assert (
        primeiro
        .coleta_desktop
        .task_id
        == segundo
        .coleta_desktop
        .task_id
    )

    assert (
        primeiro.coleta_web.task_id
        == segundo.coleta_web.task_id
    )

    assert (
        primeiro.consolidacao.task_id
        == segundo.consolidacao.task_id
    )

    assert (
        primeiro.coleta_desktop.criada
        is True
    )

    assert (
        primeiro.coleta_web.criada
        is True
    )

    assert (
        primeiro.consolidacao.criada
        is True
    )

    assert (
        segundo.coleta_desktop.criada
        is False
    )

    assert (
        segundo.coleta_web.criada
        is False
    )

    assert (
        segundo.consolidacao.criada
        is False
    )


def test_mesma_chave_rejeita_payload_diferente():
    """A mesma chave não aceita parâmetros diferentes."""

    (
        _,
        servico,
    ) = criar_servico()

    servico.iniciar_fluxo(
        task_id_bot_a="task-a-005",
        execution_id="exec-005",
        correlation_id="corr-005",
        parametros_web={
            "portal_url": (
                "http://127.0.0.1:8010"
            ),
        },
    )

    with pytest.raises(
        ValueError,
        match=(
            "chave de idempotência "
            "reutilizada com dados diferentes"
        ),
    ):
        servico.iniciar_fluxo(
            task_id_bot_a="task-a-005",
            execution_id="exec-005",
            correlation_id="corr-005",
            parametros_web={
                "portal_url": (
                    "http://127.0.0.1:9000"
                ),
            },
        )


def test_execucoes_diferentes_sao_independentes():
    """Execuções diferentes criam tarefas novas."""

    (
        orquestrador,
        servico,
    ) = criar_servico()

    fluxo_um = servico.iniciar_fluxo(
        task_id_bot_a="task-a-006",
        execution_id="exec-006",
        correlation_id="corr-006",
    )

    fluxo_dois = servico.iniciar_fluxo(
        task_id_bot_a="task-a-007",
        execution_id="exec-007",
        correlation_id="corr-007",
    )

    assert (
        fluxo_um
        .coleta_desktop
        .task_id
        != fluxo_dois
        .coleta_desktop
        .task_id
    )

    assert (
        fluxo_um.coleta_web.task_id
        != fluxo_dois.coleta_web.task_id
    )

    assert (
        fluxo_um.consolidacao.task_id
        != fluxo_dois
        .consolidacao
        .task_id
    )

    # Três tarefas em cada execução.
    assert len(
        orquestrador.chamadas
    ) == 6