"""Integração da dead letter com o processamento real do Bot B."""

import gerar_relatorio

from src.bots.bot_conferencia import executar_bot_conferencia
from pathlib import Path
from unittest.mock import Mock

from src.dead_letter import (
    ErroDadoIrrecuperavel,
    RepositorioDeadLetter,
    processar_lote_com_dead_letter,
)

def test_bot_b_envia_erro_de_dado_para_dead_letter_e_continua_lote(tmp_path,monkeypatch,planilha_controlada_factory):
    entrada = planilha_controlada_factory()

    caminho_dead_letter = (
        tmp_path / 'data' / 'output' / 'dead_letter.jsonl'
    )

    repositorio = RepositorioDeadLetter(caminho_dead_letter)

    processador_real = gerar_relatorio.processar_item

    tentativas_lote_corrompido = 0

    def processador_controlado(*args,**kwargs):
        nonlocal tentativas_lote_corrompido

        registro= kwargs['registro']
        lote= str(registro.get('lote_id'))

        if lote == 'LOTE-001-B':
            tentativas_lote_corrompido += 1

            raise ErroDadoIrrecuperavel('Estrutura interna do registro inválida')

        return processador_real(*args, **kwargs)

    monkeypatch.setattr(gerar_relatorio,'processar_item',processador_controlado)

    resultado = executar_bot_conferencia(entrada,execution_id='exec-dead-letter-001',correlation_id='corr-dead-letter-001', repositorio_dead_letter=repositorio)

    #Planilha controlada possui 20 registro, sendo que somente 1 registro falha, mas outro 19 continuam

    assert resultado.sucesso is True
    assert resultado.total_registros == 19

    assert tentativas_lote_corrompido == 3
    assert caminho_dead_letter.exists()

    pendentes = repositorio.listar_pendentes()

    assert len(pendentes) == 1
    assert pendentes[0].lote == 'LOTE-001-B'
    assert pendentes[0].execution_id == ('exec-dead-letter-001')
    assert pendentes[0].tentativas == 3

def test_item_com_erro_repetido_vai_para_dead_letter_sem_parar_lote(
    tmp_path: Path,
):
    caminho_dead_letter = (
        tmp_path / "data" / "output" / "dead_letter.jsonl"
    )

    repositorio = RepositorioDeadLetter(
        caminho_dead_letter
    )

    itens = [
        {
            "lote_id": "LOTE-001",
            "observacao": "Item válido",
        },
        {
            "lote_id": "LOTE-CORROMPIDO",
            "observacao": "Dado impossível de processar",
        },
        {
            "lote_id": "LOTE-002",
            "observacao": "Outro item válido",
        },
    ]

    def processar_item_controlado(item):
        if item["lote_id"] == "LOTE-CORROMPIDO":
            raise ErroDadoIrrecuperavel(
                "estrutura interna do registro inválida"
            )

        return item["lote_id"]

    resultado = processar_lote_com_dead_letter(
        itens,
        processar_item_controlado,
        repositorio=repositorio,
        execution_id="exec-integracao-001",
        max_tentativas_dado=3,
    )

    assert resultado.processados == (
        "LOTE-001",
        "LOTE-002",
    )

    assert len(resultado.dead_letters) == 1

    registro_dead_letter = resultado.dead_letters[0]

    assert registro_dead_letter.lote == (
        "LOTE-CORROMPIDO"
    )

    assert registro_dead_letter.tentativas == 3
    assert caminho_dead_letter.exists()