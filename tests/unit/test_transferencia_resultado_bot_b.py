"""Testes da transferência Bot B -> Bot C."""

import json

import pytest

from src.bots.bot_conferencia import (
    ResultadoBotConferencia,
    StatusBotConferencia,
)
from src.transferencia_resultado_bot_b import (
    carregar_resultado_bot_b,
    salvar_resultado_bot_b,
)
from src.validacao_lotes import (
    RegistroValidado,
)


def criar_registro() -> RegistroValidado:
    return RegistroValidado(
        data_referencia="15/06/2026",
        lote="LOTE-001",
        produto="Produto A",
        linha="Linha 1",
        turno="Manhã",
        status="APROVADO",
        responsavel="Carlos",
        data_inspecao="15/06/2026",
        observacao="Registro válido",
        classificacao="Válido",
        motivo="Registro em conformidade",
        acao_recomendada=(
            "Nenhuma ação necessária"
        ),
        regra_aplicada="",
        causa_provavel="sem_divergencia",
        confianca_ml=0.91,
        origem_decisao="ml",
        motivo_fallback="",
        versao_modelo="1.0.0",
    )


def criar_resultado() -> ResultadoBotConferencia:
    registro = criar_registro()

    return ResultadoBotConferencia(
        sucesso=True,
        status=(
            StatusBotConferencia.CONCLUIDO
        ),
        mensagem=(
            "Conferência concluída"
        ),
        execution_id="exec-001",
        correlation_id="corr-001",
        caminho_entrada="/tmp/entrada.xlsx",
        registros=(registro,),
        classificacoes={
            "Válido": 1,
        },
        origens_decisao={
            "ml": 1,
        },
        decisoes_auditadas=1,
    )


def test_resultado_bot_b_preserva_dados_apos_json(
    tmp_path,
):
    caminho = (
        tmp_path
        / "resultado_bot_b.json"
    )

    resultado_original = criar_resultado()

    caminho_salvo = salvar_resultado_bot_b(
        resultado_original,
        caminho,
    )

    resultado_carregado = (
        carregar_resultado_bot_b(
            caminho_salvo,
        )
    )

    assert caminho_salvo.is_file()

    assert (
        resultado_carregado
        == resultado_original
    )


def test_arquivo_possui_versao_do_contrato(
    tmp_path,
):
    caminho = (
        tmp_path
        / "resultado_bot_b.json"
    )

    salvar_resultado_bot_b(
        criar_resultado(),
        caminho,
    )

    dados = json.loads(
        caminho.read_text(
            encoding="utf-8",
        )
    )

    assert (
        dados["contrato"]
        == "resultado_bot_b"
    )

    assert dados["versao"] == 1
    assert len(dados["registros"]) == 1


def test_rejeita_versao_desconhecida(
    tmp_path,
):
    caminho = (
        tmp_path
        / "resultado_invalido.json"
    )

    caminho.write_text(
        json.dumps(
            {
                "contrato": (
                    "resultado_bot_b"
                ),
                "versao": 999,
                "resumo": {},
                "registros": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Versão de contrato",
    ):
        carregar_resultado_bot_b(
            caminho,
        )