"""Integração do Bot D com artefatos, consolidação e Maestro."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from botcity.maestro import (
    AutomationTaskFinishStatus,
)

from src.bots.bot_consolidacao import (
    ConfiguracaoConsolidacao,
)
from src.bots.bot_consolidacao_maestro import (
    NOME_ARTEFATO_CONSOLIDACAO,
    NOME_ARTEFATO_ESTOQUE,
    NOME_ARTEFATO_PEDIDOS,
    executar_tarefa_bot_d_capstone,
)
from src.contratos_capstone import (
    ArtefatoConsolidacao,
    ArtefatoEstoqueDesktop,
    ArtefatoPedidosFornecedor,
    EnvelopeAuditoria,
    EstadoExecucao,
    PedidoFornecedor,
    RegistroEstoqueDesktop,
)


EXECUTION_ID = "exec-capstone-001"
CORRELATION_ID = "corr-capstone-001"

TASK_ID_B = "task-desktop-200"
TASK_ID_C = "task-web-300"
TASK_ID_D = "task-consolidacao-400"


def criar_maestro() -> Mock:
    """Cria um Maestro simulado para o Bot D."""

    maestro = Mock()

    maestro.get_execution.return_value = (
        SimpleNamespace(
            task_id=TASK_ID_D,
            parameters={
                "execution_id": EXECUTION_ID,
                "correlation_id": (
                    CORRELATION_ID
                ),
                "desktop_task_id": TASK_ID_B,
                "desktop_artefato": (
                    NOME_ARTEFATO_ESTOQUE
                ),
                "web_task_id": TASK_ID_C,
                "web_artefato": (
                    NOME_ARTEFATO_PEDIDOS
                ),
            },
        )
    )

    return maestro


def criar_artefato_estoque(
    caminho: Path,
    *,
    estado: EstadoExecucao = (
        EstadoExecucao.CONCLUIDO
    ),
) -> Path:
    """Cria o JSON que seria produzido pelo Bot B."""

    artefato = ArtefatoEstoqueDesktop(
        auditoria=EnvelopeAuditoria(
            execution_id=EXECUTION_ID,
            correlation_id=CORRELATION_ID,
            bot_id="bot-b-coleta-desktop",
            task_id=TASK_ID_B,
            estado=estado,
            predecessor="bot-a-entrada-capstone",
            predecessor_task_id="task-entrada-100",
            resultado_predecessor=(
                "pronto_para_processamento"
            ),
        ),
        registros=(
            RegistroEstoqueDesktop(
                lote_id="LOTE-001",
                produto="Sensor de temperatura",
                quantidade_disponivel=10,
                localizacao="A-01",
                status_estoque="DISPONIVEL",
            ),
            RegistroEstoqueDesktop(
                lote_id="LOTE-002",
                produto="Válvula de controle",
                quantidade_disponivel=0,
                localizacao="A-02",
                status_estoque="INDISPONIVEL",
            ),
        )
        if estado == EstadoExecucao.CONCLUIDO
        else (),
    )

    caminho.write_text(
        artefato.para_json(),
        encoding="utf-8",
    )

    return caminho


def criar_artefato_pedidos(
    caminho: Path,
    *,
    estado: EstadoExecucao = (
        EstadoExecucao.CONCLUIDO
    ),
) -> Path:
    """Cria o JSON que seria produzido pelo Bot C."""

    artefato = ArtefatoPedidosFornecedor(
        auditoria=EnvelopeAuditoria(
            execution_id=EXECUTION_ID,
            correlation_id=CORRELATION_ID,
            bot_id="bot-c-coleta-web",
            task_id=TASK_ID_C,
            estado=estado,
            predecessor="bot-a-entrada-capstone",
            predecessor_task_id="task-entrada-100",
            resultado_predecessor=(
                "pronto_para_processamento"
            ),
        ),
        registros=(
            PedidoFornecedor(
                pedido_id="PED-001",
                lote_id="LOTE-001",
                fornecedor="Fornecedor Norte",
                produto="Sensor de temperatura",
                quantidade_pedida=6,
                status_pedido="PENDENTE",
            ),
            PedidoFornecedor(
                pedido_id="PED-002",
                lote_id="LOTE-002",
                fornecedor="Fornecedor Amazonas",
                produto="Válvula de controle",
                quantidade_pedida=2,
                status_pedido="PENDENTE",
            ),
        )
        if estado == EstadoExecucao.CONCLUIDO
        else (),
    )

    caminho.write_text(
        artefato.para_json(),
        encoding="utf-8",
    )

    return caminho


def criar_baixador(
    fontes: dict[
        tuple[str, str],
        Path,
    ],
):
    """Simula o download de artefatos do Maestro."""

    def baixar(
        maestro,
        *,
        task_id_origem: str,
        nome_artefato: str,
        destino: str | Path,
        dias: int = 7,
    ) -> Path:
        del maestro
        del dias

        chave = (
            task_id_origem,
            nome_artefato,
        )

        origem = fontes.get(chave)

        if origem is None:
            raise FileNotFoundError(
                "Artefato simulado não encontrado: "
                f"{chave}"
            )

        destino = Path(destino)

        destino.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destino.write_bytes(
            origem.read_bytes()
        )

        return destino

    return baixar


def ler_consolidacao(
    caminho: Path,
) -> ArtefatoConsolidacao:
    """Lê o artefato final do Bot D."""

    return ArtefatoConsolidacao.de_json(
        caminho.read_text(
            encoding="utf-8"
        )
    )


def test_bot_d_consolida_duas_fontes_e_agenda_bot_e(
    tmp_path,
):
    """B e C concluídos geram uma consolidação normal."""

    caminho_estoque = criar_artefato_estoque(
        tmp_path / "estoque.json"
    )

    caminho_pedidos = criar_artefato_pedidos(
        tmp_path / "pedidos.json"
    )

    caminho_saida = (
        tmp_path
        / "registros_consolidados.json"
    )

    fontes = {
        (
            TASK_ID_B,
            NOME_ARTEFATO_ESTOQUE,
        ): caminho_estoque,
        (
            TASK_ID_C,
            NOME_ARTEFATO_PEDIDOS,
        ): caminho_pedidos,
    }

    maestro = criar_maestro()

    maestro.get_task.return_value = (
        SimpleNamespace(
            status="FINISHED"
        )
    )

    servico = Mock()

    servico.agendar_classificacao_ml.return_value = (
        SimpleNamespace(
            task_id="task-ml-500"
        )
    )

    codigo = executar_tarefa_bot_d_capstone(
        maestro=maestro,
        servico_orquestracao=servico,
        baixar=criar_baixador(fontes),
        configuracao=(
            ConfiguracaoConsolidacao(
                caminho_artefato=(
                    caminho_saida
                )
            )
        ),
    )

    assert codigo == 0
    assert caminho_saida.is_file()

    consolidacao = ler_consolidacao(
        caminho_saida
    )

    assert (
        consolidacao.auditoria.estado
        == EstadoExecucao.CONCLUIDO
    )

    assert consolidacao.total_registros == 2

    registros = {
        registro.lote_id: registro
        for registro
        in consolidacao.registros
    }

    assert (
        registros["LOTE-001"]
        .classificacao_deterministica
        == "REGULAR"
    )

    assert (
        registros["LOTE-002"]
        .classificacao_deterministica
        == "ESTOQUE_INDISPONIVEL"
    )

    maestro.post_artifact.assert_called_once_with(
        task_id=TASK_ID_D,
        artifact_name=(
            NOME_ARTEFATO_CONSOLIDACAO
        ),
        filepath=str(caminho_saida),
    )

    servico.agendar_classificacao_ml.assert_called_once_with(
        predecessor_task_id=TASK_ID_D,
        resultado_predecessor="CONCLUIDO",
        execution_id=EXECUTION_ID,
        correlation_id=CORRELATION_ID,
        consolidacao_task_id=TASK_ID_D,
        consolidacao_artefato=(
            NOME_ARTEFATO_CONSOLIDACAO
        ),
    )

    maestro.finish_task.assert_called_once_with(
        task_id=TASK_ID_D,
        status=(
            AutomationTaskFinishStatus.SUCCESS
        ),
        message=(
            "Bot D concluído. "
            "2 registro(s) consolidado(s). "
            "Bot E agendado."
        ),
        total_items=2,
        processed_items=2,
        failed_items=0,
    )


def test_bot_d_continua_quando_desktop_falha(
    tmp_path,
):
    """Falha do Bot B permite consolidação degradada com o Bot C."""

    caminho_pedidos = criar_artefato_pedidos(
        tmp_path / "pedidos.json"
    )

    caminho_saida = (
        tmp_path
        / "consolidacao_degradada.json"
    )

    fontes = {
        (
            TASK_ID_C,
            NOME_ARTEFATO_PEDIDOS,
        ): caminho_pedidos,
    }

    maestro = criar_maestro()

    def obter_tarefa(
        task_id: str,
    ):
        if task_id == TASK_ID_B:
            return SimpleNamespace(
                status="FAILED"
            )

        return SimpleNamespace(
            status="FINISHED"
        )

    maestro.get_task.side_effect = (
        obter_tarefa
    )

    servico = Mock()

    servico.agendar_classificacao_ml.return_value = (
        SimpleNamespace(
            task_id="task-ml-501"
        )
    )

    codigo = executar_tarefa_bot_d_capstone(
        maestro=maestro,
        servico_orquestracao=servico,
        baixar=criar_baixador(fontes),
        configuracao=(
            ConfiguracaoConsolidacao(
                caminho_artefato=(
                    caminho_saida
                )
            )
        ),
    )

    assert codigo == 0

    consolidacao = ler_consolidacao(
        caminho_saida
    )

    assert (
        consolidacao.auditoria.estado
        == EstadoExecucao.CONCLUIDO_DEGRADADO
    )

    assert consolidacao.total_registros == 2

    assert all(
        registro.modo_degradado
        for registro
        in consolidacao.registros
    )

    assert all(
        registro.classificacao_deterministica
        == "SEM_REGISTRO_ESTOQUE"
        for registro
        in consolidacao.registros
    )

    servico.agendar_classificacao_ml.assert_called_once()

    finalizacao = (
        maestro.finish_task
        .call_args
        .kwargs
    )

    assert (
        finalizacao["status"]
        == AutomationTaskFinishStatus.SUCCESS
    )

    assert (
        "modo degradado"
        in finalizacao["message"]
    )


def test_bot_d_falha_quando_as_duas_fontes_falham(
    tmp_path,
):
    """Sem B e C válidos, o Bot E não deve ser agendado."""

    caminho_saida = (
        tmp_path
        / "consolidacao_falhou.json"
    )

    maestro = criar_maestro()

    maestro.get_task.return_value = (
        SimpleNamespace(
            status="FAILED"
        )
    )

    servico = Mock()

    codigo = executar_tarefa_bot_d_capstone(
        maestro=maestro,
        servico_orquestracao=servico,
        baixar=criar_baixador({}),
        configuracao=(
            ConfiguracaoConsolidacao(
                caminho_artefato=(
                    caminho_saida
                )
            )
        ),
    )

    assert codigo == 1
    assert caminho_saida.is_file()

    consolidacao = ler_consolidacao(
        caminho_saida
    )

    assert (
        consolidacao.auditoria.estado
        == EstadoExecucao.FALHOU
    )

    assert consolidacao.total_registros == 0

    servico.agendar_classificacao_ml.assert_not_called()

    maestro.post_artifact.assert_called_once_with(
        task_id=TASK_ID_D,
        artifact_name=(
            NOME_ARTEFATO_CONSOLIDACAO
        ),
        filepath=str(caminho_saida),
    )

    maestro.finish_task.assert_called_once_with(
        task_id=TASK_ID_D,
        status=(
            AutomationTaskFinishStatus.FAILED
        ),
        message=(
            "Bot D não encontrou uma "
            "fonte válida para consolidação."
        ),
        total_items=1,
        processed_items=0,
        failed_items=1,
    )