"""Testes do executor Maestro do Bot B."""

from types import SimpleNamespace
from unittest.mock import Mock

from botcity.maestro import (
    AutomationTaskFinishStatus,
)

from src.bots.bot_conferencia_maestro import (
    executar_tarefa_bot_b,
)


def criar_resultado_bot_b():
    return SimpleNamespace(
        sucesso=True,
        mensagem="Conferência concluída",
        status=SimpleNamespace(
            value="conferencia_concluida",
        ),
        execution_id="exec-001",
        correlation_id="corr-001",
        total_registros=2,
        registros=(
            SimpleNamespace(),
            SimpleNamespace(),
        ),
    )


def criar_baixador():
    def baixar(
        maestro,
        *,
        task_id_origem,
        nome_artefato,
        destino,
    ):
        destino.write_bytes(
            b"planilha"
        )

        return destino

    return Mock(
        side_effect=baixar,
    )


def test_bot_b_publica_artefato_e_cria_bot_c(
    tmp_path,
):
    maestro = Mock()

    maestro.get_execution.return_value = (
        SimpleNamespace(
            task_id=200,
            parameters={
                "entrada_task_id": "100",
                "entrada_artefato": (
                    "entrada_bot_a_100.xlsx"
                ),
                "predecessor_task_id": "100",
                "execution_id": "exec-001",
                "correlation_id": "corr-001",
            },
        )
    )

    espera_predecessor = Mock()
    baixador = criar_baixador()

    resultado = criar_resultado_bot_b()

    executor_bot_b = Mock(
        return_value=resultado,
    )

    def salvar(
        resultado_recebido,
        caminho,
    ):
        caminho.write_text(
            "{}",
            encoding="utf-8",
        )

        return caminho

    serializador = Mock(
        side_effect=salvar,
    )

    disparador_bot_c = Mock(
        return_value=SimpleNamespace(
            id=300,
        )
    )

    codigo = executar_tarefa_bot_b(
        maestro=maestro,
        executor_bot_b=executor_bot_b,
        espera_predecessor=(
            espera_predecessor
        ),
        baixador=baixador,
        serializador=serializador,
        disparador_bot_c=disparador_bot_c,
        diretorio_trabalho=tmp_path,
    )

    assert codigo == 0

    espera_predecessor.assert_called_once_with(
        maestro,
        "100",
    )

    caminho_entrada = (
        tmp_path
        / "entrada_bot_a_100.xlsx"
    )

    baixador.assert_called_once_with(
        maestro,
        task_id_origem="100",
        nome_artefato=(
            "entrada_bot_a_100.xlsx"
        ),
        destino=caminho_entrada,
    )

    executor_bot_b.assert_called_once_with(
        str(caminho_entrada),
        execution_id="exec-001",
        correlation_id="corr-001",
    )

    caminho_resultado = (
        tmp_path
        / "resultado_bot_b_200.json"
    )

    serializador.assert_called_once_with(
        resultado,
        caminho_resultado,
    )

    maestro.post_artifact.assert_called_once_with(
        task_id="200",
        artifact_name=(
            "resultado_bot_b_200.json"
        ),
        filepath=str(caminho_resultado),
    )

    disparador_bot_c.assert_called_once_with(
        maestro,
        predecessor_task_id="200",
        resultado_predecessor=(
            "conferencia_concluida"
        ),
        execution_id="exec-001",
        correlation_id="corr-001",
        parametros={
            "resultado_bot_b_task_id": "200",
            "resultado_bot_b_artefato": (
                "resultado_bot_b_200.json"
            ),
        },
    )

    maestro.finish_task.assert_called_once_with(
        task_id="200",
        status=(
            AutomationTaskFinishStatus.SUCCESS
        ),
        message=(
            "Bot B concluído. "
            "Artefato publicado e Bot C criado."
        ),
        total_items=2,
        processed_items=2,
        failed_items=0,
    )


def test_bot_b_com_falha_nao_cria_bot_c(
    tmp_path,
):
    maestro = Mock()

    maestro.get_execution.return_value = (
        SimpleNamespace(
            task_id=201,
            parameters={
                "entrada_task_id": "100",
                "entrada_artefato": (
                    "entrada_bot_a_100.xlsx"
                ),
                "predecessor_task_id": "100",
                "execution_id": "exec-002",
                "correlation_id": "corr-002",
            },
        )
    )

    espera_predecessor = Mock()
    baixador = criar_baixador()

    resultado = SimpleNamespace(
        sucesso=False,
        mensagem="Falha na conferência",
    )

    executor_bot_b = Mock(
        return_value=resultado,
    )

    serializador = Mock()
    disparador_bot_c = Mock()

    codigo = executar_tarefa_bot_b(
        maestro=maestro,
        executor_bot_b=executor_bot_b,
        espera_predecessor=(
            espera_predecessor
        ),
        baixador=baixador,
        serializador=serializador,
        disparador_bot_c=disparador_bot_c,
        diretorio_trabalho=tmp_path,
    )

    assert codigo == 1

    serializador.assert_not_called()
    maestro.post_artifact.assert_not_called()
    disparador_bot_c.assert_not_called()

    maestro.finish_task.assert_called_once_with(
        task_id="201",
        status=(
            AutomationTaskFinishStatus.FAILED
        ),
        message="Falha na conferência",
        total_items=1,
        processed_items=0,
        failed_items=1,
    )