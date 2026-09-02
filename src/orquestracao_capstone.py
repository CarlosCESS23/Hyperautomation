"""Orquestração independente de plataforma do Capstone."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


VERSAO_SCHEMA = "1.0"


@dataclass(frozen=True)
class DefinicaoBotCapstone:
    """Identificação oficial de um bot."""

    etapa: str
    activity_label: str

    def __post_init__(self) -> None:
        if not self.etapa.strip():
            raise ValueError(
                "etapa não pode ser vazia"
            )

        if not self.activity_label.strip():
            raise ValueError(
                "activity_label não pode "
                "ser vazia"
            )


BOT_A_ENTRADA = DefinicaoBotCapstone(
    etapa="bot_a",
    activity_label=(
        "carlos_souza-entrada-v2"
    ),
)

BOT_B_COLETA_DESKTOP = (
    DefinicaoBotCapstone(
        etapa="bot_b",
        activity_label=(
            "carlos_souza-"
            "coleta-desktop-v1"
        ),
    )
)

BOT_C_COLETA_WEB = (
    DefinicaoBotCapstone(
        etapa="bot_c",
        activity_label=(
            "carlos_souza-"
            "coleta-web-v1"
        ),
    )
)

BOT_D_CONSOLIDACAO = (
    DefinicaoBotCapstone(
        etapa="bot_d",
        activity_label=(
            "carlos_souza-"
            "conferencia-v2"
        ),
    )
)

BOT_E_CLASSIFICACAO_ML = (
    DefinicaoBotCapstone(
        etapa="bot_e",
        activity_label=(
            "carlos_souza-"
            "classificacao-ml-v1"
        ),
    )
)

BOT_F_RELATORIO = (
    DefinicaoBotCapstone(
        etapa="bot_f",
        activity_label=(
            "carlos_souza-"
            "relatorio-v2"
        ),
    )
)


BOTS_CAPSTONE = (
    BOT_A_ENTRADA,
    BOT_B_COLETA_DESKTOP,
    BOT_C_COLETA_WEB,
    BOT_D_CONSOLIDACAO,
    BOT_E_CLASSIFICACAO_ML,
    BOT_F_RELATORIO,
)


@dataclass(frozen=True)
class TarefaAgendada:
    """Referência normalizada de uma tarefa."""

    task_id: str
    activity_label: str
    idempotency_key: str
    criada: bool = True

    def __post_init__(self) -> None:
        campos = {
            "task_id": self.task_id,
            "activity_label": (
                self.activity_label
            ),
            "idempotency_key": (
                self.idempotency_key
            ),
        }

        vazios = [
            nome
            for nome, valor
            in campos.items()
            if not valor.strip()
        ]

        if vazios:
            raise ValueError(
                "Campos obrigatórios vazios: "
                + ", ".join(vazios)
            )


@dataclass(frozen=True)
class FluxoInicialAgendado:
    """Tarefas criadas pelo fan-out e fan-in."""

    coleta_desktop: TarefaAgendada
    coleta_web: TarefaAgendada
    consolidacao: TarefaAgendada


class PortaOrquestrador(Protocol):
    """Interface independente do BotCity e Smart Office."""

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
        """
        Cria ou recupera uma tarefa utilizando
        a chave de idempotência.
        """


def _texto_obrigatorio(
    nome: str,
    valor: object,
) -> str:
    """Valida e converte um identificador."""

    if valor is None:
        raise ValueError(
            f"{nome} é obrigatório"
        )

    texto = str(valor).strip()

    if not texto:
        raise ValueError(
            f"{nome} é obrigatório"
        )

    return texto


class ServicoOrquestracaoCapstone:
    """Coordena a cadeia A → B/C → D → E → F."""

    def __init__(
        self,
        orquestrador: PortaOrquestrador,
    ) -> None:
        self._orquestrador = (
            orquestrador
        )

    @staticmethod
    def _chave_idempotencia(
        execution_id: str,
        bot: DefinicaoBotCapstone,
    ) -> str:
        """Produz uma chave única por execução e bot."""

        return (
            f"{execution_id}:"
            f"{bot.activity_label}"
        )

    @staticmethod
    def _payload_base(
        *,
        execution_id: str,
        correlation_id: str,
    ) -> dict[str, object]:
        """Cria os campos comuns de rastreabilidade."""

        return {
            "schema_version": (
                VERSAO_SCHEMA
            ),
            "execution_id": execution_id,
            "correlation_id": (
                correlation_id
            ),
        }

    def _criar_tarefa(
        self,
        *,
        bot: DefinicaoBotCapstone,
        execution_id: str,
        correlation_id: str,
        parametros: (
            Mapping[str, object] | None
        ) = None,
        priority: int = 0,
    ) -> TarefaAgendada:
        """Cria uma tarefa com rastreabilidade protegida."""

        execution_id = _texto_obrigatorio(
            "execution_id",
            execution_id,
        )

        correlation_id = (
            _texto_obrigatorio(
                "correlation_id",
                correlation_id,
            )
        )

        payload = dict(
            parametros or {}
        )

        # Os dados de rastreabilidade possuem
        # autoridade sobre parâmetros livres.
        payload.update(
            self._payload_base(
                execution_id=execution_id,
                correlation_id=(
                    correlation_id
                ),
            )
        )

        chave = (
            self._chave_idempotencia(
                execution_id,
                bot,
            )
        )

        payload["idempotency_key"] = (
            chave
        )

        return (
            self._orquestrador
            .criar_tarefa_idempotente(
                activity_label=(
                    bot.activity_label
                ),
                parameters=payload,
                idempotency_key=chave,
                priority=priority,
            )
        )

    def iniciar_fluxo(
        self,
        *,
        task_id_bot_a: str,
        execution_id: str,
        correlation_id: str,
        parametros_desktop: (
            Mapping[str, object] | None
        ) = None,
        parametros_web: (
            Mapping[str, object] | None
        ) = None,
        prioridade_desktop: int = 0,
        prioridade_web: int = 0,
    ) -> FluxoInicialAgendado:
        """
        Executa o fan-out B/C e agenda D com
        referências para as duas tarefas.
        """

        task_id_bot_a = (
            _texto_obrigatorio(
                "task_id_bot_a",
                task_id_bot_a,
            )
        )

        parametros_comuns = {
            "predecessor": (
                BOT_A_ENTRADA
                .activity_label
            ),
            "predecessor_task_id": (
                task_id_bot_a
            ),
            "resultado_predecessor": (
                "PRONTO_PARA_COLETA"
            ),
        }

        payload_desktop = dict(
            parametros_desktop or {}
        )

        payload_desktop.update(
            parametros_comuns
        )

        tarefa_desktop = (
            self._criar_tarefa(
                bot=(
                    BOT_B_COLETA_DESKTOP
                ),
                execution_id=execution_id,
                correlation_id=(
                    correlation_id
                ),
                parametros=(
                    payload_desktop
                ),
                priority=(
                    prioridade_desktop
                ),
            )
        )

        payload_web = dict(
            parametros_web or {}
        )

        payload_web.update(
            parametros_comuns
        )

        tarefa_web = (
            self._criar_tarefa(
                bot=BOT_C_COLETA_WEB,
                execution_id=execution_id,
                correlation_id=(
                    correlation_id
                ),
                parametros=payload_web,
                priority=prioridade_web,
            )
        )

        tarefa_consolidacao = (
            self._criar_tarefa(
                bot=BOT_D_CONSOLIDACAO,
                execution_id=execution_id,
                correlation_id=(
                    correlation_id
                ),
                parametros={
                    "predecessores": {
                        "coleta_desktop": {
                            "activity_label": (
                                tarefa_desktop
                                .activity_label
                            ),
                            "task_id": (
                                tarefa_desktop
                                .task_id
                            ),
                            "artifact_name": (
                                "estoque_desktop.json"
                            ),
                        },
                        "coleta_web": {
                            "activity_label": (
                                tarefa_web
                                .activity_label
                            ),
                            "task_id": (
                                tarefa_web
                                .task_id
                            ),
                            "artifact_name": (
                                "pedidos_fornecedores.json"
                            ),
                        },
                    },
                },
            )
        )

        return FluxoInicialAgendado(
            coleta_desktop=(
                tarefa_desktop
            ),
            coleta_web=tarefa_web,
            consolidacao=(
                tarefa_consolidacao
            ),
        )

    def agendar_classificacao_ml(
        self,
        *,
        task_id_bot_d: str,
        resultado_bot_d: str,
        nome_artefato: str,
        execution_id: str,
        correlation_id: str,
    ) -> TarefaAgendada:
        """Agenda o Bot E depois do Bot D."""

        return self._criar_tarefa(
            bot=BOT_E_CLASSIFICACAO_ML,
            execution_id=execution_id,
            correlation_id=correlation_id,
            parametros={
                "predecessor": (
                    BOT_D_CONSOLIDACAO
                    .activity_label
                ),
                "predecessor_task_id": (
                    _texto_obrigatorio(
                        "task_id_bot_d",
                        task_id_bot_d,
                    )
                ),
                "resultado_predecessor": (
                    _texto_obrigatorio(
                        "resultado_bot_d",
                        resultado_bot_d,
                    )
                ),
                "artefato_entrada": (
                    _texto_obrigatorio(
                        "nome_artefato",
                        nome_artefato,
                    )
                ),
            },
        )

    def agendar_relatorio(
        self,
        *,
        task_id_bot_e: str,
        resultado_bot_e: str,
        nome_artefato: str,
        execution_id: str,
        correlation_id: str,
    ) -> TarefaAgendada:
        """Agenda o Bot F depois do Bot E."""

        return self._criar_tarefa(
            bot=BOT_F_RELATORIO,
            execution_id=execution_id,
            correlation_id=correlation_id,
            parametros={
                "predecessor": (
                    BOT_E_CLASSIFICACAO_ML
                    .activity_label
                ),
                "predecessor_task_id": (
                    _texto_obrigatorio(
                        "task_id_bot_e",
                        task_id_bot_e,
                    )
                ),
                "resultado_predecessor": (
                    _texto_obrigatorio(
                        "resultado_bot_e",
                        resultado_bot_e,
                    )
                ),
                "artefato_entrada": (
                    _texto_obrigatorio(
                        "nome_artefato",
                        nome_artefato,
                    )
                ),
            },
        )