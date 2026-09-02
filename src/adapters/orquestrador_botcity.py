"""Adaptador BotCity da orquestração do Capstone."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
from typing import Any, Mapping, Protocol

from src.orquestracao_capstone import (
    TarefaAgendada,
)


LOGGER = logging.getLogger(
    "botcity_permorfer"
)


class ConflitoIdempotenciaError(
    RuntimeError
):
    """A mesma chave foi usada com dados diferentes."""


class MaestroComCreateTask(Protocol):
    """Operação do SDK utilizada pelo adaptador."""

    def create_task(
        self,
        activity_label: str,
        parameters: dict[str, object],
        test: bool = False,
        priority: int = 0,
        min_execution_date: Any = None,
    ) -> Any:
        """Cria uma tarefa no Maestro."""


class RepositorioIdempotencia(Protocol):
    """Armazena as tarefas criadas por chave."""

    def obter_ou_criar(
        self,
        *,
        idempotency_key: str,
        activity_label: str,
        parameters_json: str,
        priority: int,
        criador: Callable[[], str],
    ) -> tuple[str, bool]:
        """
        Retorna task_id e informa se uma
        nova tarefa foi criada.
        """


def _texto_obrigatorio(
    nome: str,
    valor: object,
) -> str:
    """Converte e valida um texto obrigatório."""

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


def _extrair_task_id(
    tarefa: Any,
) -> str:
    """Normaliza diferentes versões do SDK."""

    for atributo in (
        "task_id",
        "id",
    ):
        valor = getattr(
            tarefa,
            atributo,
            None,
        )

        if valor is not None:
            texto = str(valor).strip()

            if texto:
                return texto

    raise RuntimeError(
        "O Maestro criou a tarefa, "
        "mas não retornou task_id ou id"
    )


class RepositorioIdempotenciaSQLite:
    """Persistência local e transacional em SQLite."""

    def __init__(
        self,
        caminho: str | Path,
    ) -> None:
        self._caminho = Path(
            caminho
        )

        self._caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._inicializar()

    def _conectar(
        self,
    ) -> sqlite3.Connection:
        conexao = sqlite3.connect(
            str(self._caminho),
            timeout=30,
            isolation_level=None,
        )

        conexao.execute(
            "PRAGMA busy_timeout = 30000"
        )

        return conexao

    def _inicializar(self) -> None:
        """Cria a tabela quando necessário."""

        conexao = self._conectar()

        try:
            conexao.execute(
                """
                CREATE TABLE IF NOT EXISTS
                tarefas_idempotentes (
                    idempotency_key TEXT
                        PRIMARY KEY,
                    activity_label TEXT
                        NOT NULL,
                    parameters_json TEXT
                        NOT NULL,
                    priority INTEGER
                        NOT NULL,
                    task_id TEXT
                        NOT NULL,
                    registrado_em TEXT
                        NOT NULL
                )
                """
            )

        finally:
            conexao.close()

    def obter_ou_criar(
        self,
        *,
        idempotency_key: str,
        activity_label: str,
        parameters_json: str,
        priority: int,
        criador: Callable[[], str],
    ) -> tuple[str, bool]:
        """Executa consulta e criação em transação."""

        chave = _texto_obrigatorio(
            "idempotency_key",
            idempotency_key,
        )

        rotulo = _texto_obrigatorio(
            "activity_label",
            activity_label,
        )

        conexao = self._conectar()

        try:
            # Impede que dois processos utilizem
            # simultaneamente a mesma base.
            conexao.execute(
                "BEGIN IMMEDIATE"
            )

            registro = conexao.execute(
                """
                SELECT
                    activity_label,
                    parameters_json,
                    priority,
                    task_id
                FROM tarefas_idempotentes
                WHERE idempotency_key = ?
                """,
                (chave,),
            ).fetchone()

            if registro is not None:
                (
                    activity_registrada,
                    parametros_registrados,
                    prioridade_registrada,
                    task_id_registrado,
                ) = registro

                if (
                    activity_registrada
                    != rotulo
                    or parametros_registrados
                    != parameters_json
                    or prioridade_registrada
                    != priority
                ):
                    raise (
                        ConflitoIdempotenciaError(
                            "chave de idempotência "
                            "reutilizada com payload "
                            "diferente: "
                            f"{chave}"
                        )
                    )

                conexao.commit()

                return (
                    str(task_id_registrado),
                    False,
                )

            task_id = _texto_obrigatorio(
                "task_id",
                criador(),
            )

            conexao.execute(
                """
                INSERT INTO
                tarefas_idempotentes (
                    idempotency_key,
                    activity_label,
                    parameters_json,
                    priority,
                    task_id,
                    registrado_em
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    chave,
                    rotulo,
                    parameters_json,
                    priority,
                    task_id,
                    (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                ),
            )

            conexao.commit()

            return task_id, True

        except Exception:
            conexao.rollback()
            raise

        finally:
            conexao.close()


class AdaptadorOrquestradorBotCity:
    """Implementa PortaOrquestrador usando Maestro."""

    def __init__(
        self,
        *,
        maestro: MaestroComCreateTask,
        repositorio: (
            RepositorioIdempotencia
        ),
        test: bool = False,
        logger: (
            logging.Logger | None
        ) = None,
    ) -> None:
        self._maestro = maestro
        self._repositorio = repositorio
        self._test = test
        self._logger = (
            logger or LOGGER
        )

    @classmethod
    def de_ambiente(
        cls,
        *,
        maestro: MaestroComCreateTask,
        test: bool = False,
        logger: (
            logging.Logger | None
        ) = None,
    ) -> "AdaptadorOrquestradorBotCity":
        """Cria o adaptador com configuração local."""

        caminho = Path(
            os.getenv(
                "CAPSTONE_IDEMPOTENCIA_DB",
                (
                    "data/state/"
                    "capstone_idempotencia.sqlite3"
                ),
            )
        )

        return cls(
            maestro=maestro,
            repositorio=(
                RepositorioIdempotenciaSQLite(
                    caminho
                )
            ),
            test=test,
            logger=logger,
        )

    @staticmethod
    def _serializar_parametros(
        parametros: Mapping[
            str,
            object,
        ],
    ) -> str:
        """Gera representação canônica do payload."""

        try:
            return json.dumps(
                dict(parametros),
                ensure_ascii=False,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
            )

        except TypeError as erro:
            raise ValueError(
                "parameters deve conter "
                "somente valores serializáveis "
                "em JSON"
            ) from erro

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
        """Cria ou recupera uma tarefa do Maestro."""

        rotulo = _texto_obrigatorio(
            "activity_label",
            activity_label,
        )

        chave = _texto_obrigatorio(
            "idempotency_key",
            idempotency_key,
        )

        if (
            not isinstance(priority, int)
            or priority < 0
        ):
            raise ValueError(
                "priority deve ser um "
                "inteiro não negativo"
            )

        payload = dict(parameters)

        # Garante que a chave também fique
        # visível nos parâmetros do Maestro.
        payload["idempotency_key"] = (
            chave
        )

        parametros_json = (
            self._serializar_parametros(
                payload
            )
        )

        def criar_no_maestro() -> str:
            tarefa = (
                self._maestro.create_task(
                    activity_label=rotulo,
                    parameters=payload,
                    test=self._test,
                    priority=priority,
                )
            )

            return _extrair_task_id(
                tarefa
            )

        task_id, criada = (
            self._repositorio
            .obter_ou_criar(
                idempotency_key=chave,
                activity_label=rotulo,
                parameters_json=(
                    parametros_json
                ),
                priority=priority,
                criador=criar_no_maestro,
            )
        )

        evento = (
            "tarefa_capstone_criada"
            if criada
            else (
                "tarefa_capstone_"
                "reutilizada"
            )
        )

        self._logger.info(
            evento,
            extra={
                "evento": evento,
                "bot_destino": rotulo,
                "task_id": task_id,
                "idempotency_key": chave,
                "tarefa_criada": criada,
                "execution_id": (
                    payload.get(
                        "execution_id"
                    )
                ),
                "correlation_id": (
                    payload.get(
                        "correlation_id"
                    )
                ),
            },
        )

        return TarefaAgendada(
            task_id=task_id,
            activity_label=rotulo,
            idempotency_key=chave,
            criada=criada,
        )