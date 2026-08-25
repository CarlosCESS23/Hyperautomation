"""Testes da dead letter de falhas definitivas de dados."""

from datetime import datetime, timezone
import json
from unittest.mock import Mock

from src.dead_letter import (
    ErroDadoIrrecuperavel,
    RepositorioDeadLetter,
    processar_lote_com_dead_letter,
    reprocessar_pendentes,
)


def test_somente_erro_de_dado_repetido_entra_na_dead_letter(
    tmp_path,
):
    repositorio = RepositorioDeadLetter(tmp_path / "dead_letter.jsonl")
    processador = Mock(
        side_effect=ErroDadoIrrecuperavel("formato inválido")
    )

    resultado = processar_lote_com_dead_letter(
        [{"lote_id": "LOTE-ERRO", "valor": "inválido"}],
        processador,
        repositorio=repositorio,
        execution_id="exec-001",
        max_tentativas_dado=3,
        clock=lambda: datetime(
            2026, 8, 25, 12, 0, tzinfo=timezone.utc
        ),
    )

    assert processador.call_count == 3
    assert len(resultado.dead_letters) == 1
    registro = resultado.dead_letters[0]
    assert registro.lote == "LOTE-ERRO"
    assert registro.execution_id == "exec-001"
    assert registro.erro == "formato inválido"
    assert registro.tentativas == 3
    assert registro.horario == "2026-08-25T12:00:00+00:00"


def test_falha_de_rede_nao_e_tratada_como_erro_de_dado(tmp_path):
    repositorio = RepositorioDeadLetter(tmp_path / "dead_letter.jsonl")
    processador = Mock(side_effect=ConnectionError("rede instável"))

    resultado = processar_lote_com_dead_letter(
        [{"lote_id": "LOTE-REDE"}],
        processador,
        repositorio=repositorio,
        execution_id="exec-002",
    )

    assert processador.call_count == 1
    assert resultado.dead_letters == ()
    assert len(resultado.falhas_infraestrutura) == 1
    assert repositorio.listar_pendentes() == ()


def test_falha_de_um_item_nao_interrompe_os_demais(tmp_path):
    repositorio = RepositorioDeadLetter(tmp_path / "dead_letter.jsonl")

    def processar(item):
        if item["lote_id"] == "LOTE-RUIM":
            raise ErroDadoIrrecuperavel("dado corrompido")
        return item["lote_id"]

    resultado = processar_lote_com_dead_letter(
        [
            {"lote_id": "LOTE-001"},
            {"lote_id": "LOTE-RUIM"},
            {"lote_id": "LOTE-002"},
        ],
        processar,
        repositorio=repositorio,
        execution_id="exec-003",
        max_tentativas_dado=2,
    )

    assert resultado.processados == ("LOTE-001", "LOTE-002")
    assert [item.lote for item in resultado.dead_letters] == [
        "LOTE-RUIM"
    ]


def test_dead_letter_persistida_e_auditavel(tmp_path):
    caminho = tmp_path / "dead_letter.jsonl"
    repositorio = RepositorioDeadLetter(caminho)

    processar_lote_com_dead_letter(
        [{"lote_id": "LOTE-AUDITAVEL", "campo": "valor"}],
        Mock(side_effect=ErroDadoIrrecuperavel("erro definitivo")),
        repositorio=repositorio,
        execution_id="exec-auditoria",
        max_tentativas_dado=2,
    )

    evento = json.loads(caminho.read_text(encoding="utf-8").splitlines()[0])
    assert evento["tipo_evento"] == "dead_letter_criada"
    assert evento["lote"] == "LOTE-AUDITAVEL"
    assert evento["execution_id"] == "exec-auditoria"
    assert evento["tentativas"] == 2
    assert evento["erro"] == "erro definitivo"
    assert evento["horario"]
    assert evento["item"] == {
        "lote_id": "LOTE-AUDITAVEL",
        "campo": "valor",
    }


def test_dead_letter_pode_ser_reprocessada_posteriormente(tmp_path):
    repositorio = RepositorioDeadLetter(tmp_path / "dead_letter.jsonl")
    processar_lote_com_dead_letter(
        [{"lote_id": "LOTE-CORRIGIDO"}],
        Mock(side_effect=ErroDadoIrrecuperavel("campo ausente")),
        repositorio=repositorio,
        execution_id="exec-original",
        max_tentativas_dado=1,
    )

    resultados = reprocessar_pendentes(
        repositorio,
        lambda item: f"processado:{item['lote_id']}",
        execution_id="exec-reprocessamento",
    )

    assert resultados == ("processado:LOTE-CORRIGIDO",)
    assert repositorio.listar_pendentes() == ()
    eventos = repositorio.caminho.read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(eventos) == 2
    assert json.loads(eventos[1])["tipo_evento"] == (
        "dead_letter_reprocessada"
    )
