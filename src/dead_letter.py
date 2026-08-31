"""Dead letter auditável para falhas definitivas de dados."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4


LOGGER = logging.getLogger("botcity_permorfer")


class ErroDadoIrrecuperavel(ValueError):
    """Falha determinística no conteúdo de um item.

    Somente esta categoria pode seguir para a dead letter. Erros genéricos,
    timeouts e falhas de conexão são tratados como infraestrutura.
    """


@dataclass(frozen=True)
class RegistroDeadLetter:
    dead_letter_id: str
    lote: str
    execution_id: str
    erro: str
    tentativas: int
    horario: str
    item: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FalhaInfraestrutura:
    lote: str
    execution_id: str
    erro: str


@dataclass(frozen=True)
class ResultadoProcessamentoLote:
    processados: tuple[Any, ...]
    dead_letters: tuple[RegistroDeadLetter, ...]
    falhas_infraestrutura: tuple[FalhaInfraestrutura, ...]


class RepositorioDeadLetter:
    """Repositório JSONL append-only com histórico de auditoria."""

    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)

    def adicionar(self, registro: RegistroDeadLetter) -> None:
        self._adicionar_evento(
            {
                "tipo_evento": "dead_letter_criada",
                **registro.to_dict(),
            }
        )

    def registrar_reprocessamento(
        self,
        registro: RegistroDeadLetter,
        *,
        execution_id_reprocessamento: str,
        sucesso: bool,
        erro: str | None = None,
        horario: datetime | None = None,
    ) -> None:
        self._adicionar_evento(
            {
                "tipo_evento": "dead_letter_reprocessada",
                "dead_letter_id": registro.dead_letter_id,
                "lote": registro.lote,
                "execution_id_original": registro.execution_id,
                "execution_id_reprocessamento": execution_id_reprocessamento,
                "sucesso": sucesso,
                "erro": erro,
                "horario": _horario_iso(horario),
            }
        )

    def listar_pendentes(self) -> tuple[RegistroDeadLetter, ...]:
        eventos = self._ler_eventos()
        criados: dict[str, RegistroDeadLetter] = {}
        concluidos: set[str] = set()
        for evento in eventos:
            identificador = str(evento.get("dead_letter_id", ""))
            if evento.get("tipo_evento") == "dead_letter_criada":
                criados[identificador] = RegistroDeadLetter(
                    dead_letter_id=identificador,
                    lote=str(evento["lote"]),
                    execution_id=str(evento["execution_id"]),
                    erro=str(evento["erro"]),
                    tentativas=int(evento["tentativas"]),
                    horario=str(evento["horario"]),
                    item=dict(evento["item"]),
                )
            elif (
                evento.get("tipo_evento")
                == "dead_letter_reprocessada"
                and evento.get("sucesso") is True
            ):
                concluidos.add(identificador)
        return tuple(
            registro
            for identificador, registro in criados.items()
            if identificador not in concluidos
        )

    def _adicionar_evento(self, evento: Mapping[str, Any]) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        with self.caminho.open("a", encoding="utf-8") as arquivo:
            json.dump(evento, arquivo, ensure_ascii=False, default=str)
            arquivo.write("\n")

    def _ler_eventos(self) -> list[dict[str, Any]]:
        if not self.caminho.exists():
            return []
        eventos = []
        with self.caminho.open(encoding="utf-8") as arquivo:
            for numero_linha, linha in enumerate(arquivo, start=1):
                if not linha.strip():
                    continue
                try:
                    eventos.append(json.loads(linha))
                except json.JSONDecodeError as erro:
                    raise ValueError(
                        "Dead letter corrompida na linha "
                        f"{numero_linha}: {erro}"
                    ) from erro
        return eventos


def processar_lote_com_dead_letter(
    itens: Iterable[Mapping[str, Any]],
    processador: Callable[[Mapping[str, Any]], Any],
    *,
    repositorio: RepositorioDeadLetter,
    execution_id: str,
    max_tentativas_dado: int = 3,
    clock: Callable[[], datetime] | None = None,
    logger: logging.Logger | None = None,
) -> ResultadoProcessamentoLote:
    """Processa todos os itens e isola somente erros repetidos de dados."""

    if max_tentativas_dado < 1:
        raise ValueError("max_tentativas_dado deve ser maior ou igual a 1")
    if not execution_id.strip():
        raise ValueError("execution_id é obrigatório")

    logger = logger or LOGGER
    clock = clock or (lambda: datetime.now(timezone.utc))
    processados: list[Any] = []
    dead_letters: list[RegistroDeadLetter] = []
    falhas_infraestrutura: list[FalhaInfraestrutura] = []

    for item_original in itens:
        item = dict(item_original)
        lote = str(item.get("lote_id") or item.get("lote") or "")
        for tentativa in range(1, max_tentativas_dado + 1):
            try:
                processados.append(processador(item))
                break
            except ErroDadoIrrecuperavel as erro:
                logger.warning(
                    "item_dado_tentativa_falhou",
                    extra={
                        "evento": "item_dado_tentativa_falhou",
                        "lote": lote,
                        "execution_id": execution_id,
                        "tentativa": tentativa,
                        "max_tentativas": max_tentativas_dado,
                        "erro": str(erro),
                    },
                )
                if tentativa == max_tentativas_dado:
                    registro = RegistroDeadLetter(
                        dead_letter_id=f"dlq-{uuid4()}",
                        lote=lote,
                        execution_id=execution_id,
                        erro=str(erro),
                        tentativas=tentativa,
                        horario=_horario_iso(clock()),
                        item=item,
                    )
                    repositorio.adicionar(registro)
                    dead_letters.append(registro)
                    logger.error(
                        "item_enviado_dead_letter",
                        extra={
                            "evento": "item_enviado_dead_letter",
                            **registro.to_dict(),
                        },
                    )
            except Exception as erro:
                # Falha não tipada como dado é potencialmente temporária e
                # nunca pode contaminar a fila de itens irrecuperáveis.
                falha = FalhaInfraestrutura(
                    lote=lote,
                    execution_id=execution_id,
                    erro=str(erro),
                )
                falhas_infraestrutura.append(falha)
                logger.error(
                    "item_falha_infraestrutura",
                    extra={
                        "evento": "item_falha_infraestrutura",
                        **asdict(falha),
                    },
                )
                break

    return ResultadoProcessamentoLote(
        processados=tuple(processados),
        dead_letters=tuple(dead_letters),
        falhas_infraestrutura=tuple(falhas_infraestrutura),
    )


def reprocessar_pendentes(
    repositorio: RepositorioDeadLetter,
    processador: Callable[[Mapping[str, Any]], Any],
    *,
    execution_id: str,
    clock: Callable[[], datetime] | None = None,
) -> tuple[Any, ...]:
    """Tenta novamente as dead letters pendentes mantendo o histórico."""

    clock = clock or (lambda: datetime.now(timezone.utc))
    resultados = []
    for registro in repositorio.listar_pendentes():
        try:
            resultado = processador(registro.item)
        except Exception as erro:
            repositorio.registrar_reprocessamento(
                registro,
                execution_id_reprocessamento=execution_id,
                sucesso=False,
                erro=str(erro),
                horario=clock(),
            )
        else:
            resultados.append(resultado)
            repositorio.registrar_reprocessamento(
                registro,
                execution_id_reprocessamento=execution_id,
                sucesso=True,
                horario=clock(),
            )
    return tuple(resultados)


def _horario_iso(horario: datetime | None = None) -> str:
    horario = horario or datetime.now(timezone.utc)
    if horario.tzinfo is None:
        horario = horario.replace(tzinfo=timezone.utc)
    return horario.astimezone(timezone.utc).isoformat()
