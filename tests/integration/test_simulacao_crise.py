"""Testes reproduzíveis dos cinco cenários de crise da apresentação.

Nenhum teste acessa serviços reais. API ML, Telegram, Email, base de
referência e espera de retry são substituídos por objetos controlados.
"""

import logging
from unittest.mock import Mock

import pandas as pd
import pytest

from gerar_relatorio import ler_e_validar
from src.auditoria_hibrida import AuditoriaPipelineHibrido
from src.base_referencia import ConfiguracaoRetryBase
from src.classificador_divergencia import ClassificadorDivergencia
from src.decisao_hibrida import MotivoFallback, OrigemDecisao
from src.item_processor import processar_item
from src.ml_client import (
    MLServiceUnavailableError,
    MLTimeoutError,
)
from src.sistema_alertas import (
    Alerta,
    ResultadoAlerta,
    Severidade,
    SistemaAlertas,
)


pytestmark = pytest.mark.integration


class ClienteMLControlado:
    """Simula a API ML sem realizar chamadas HTTP."""

    def __init__(
        self,
        *,
        resposta: dict | None = None,
        erro: Exception | None = None,
    ) -> None:
        self.resposta = resposta
        self.erro = erro
        self.observacoes: list[str] = []

    def classificar_observacao(
        self,
        *,
        observacao: str,
    ) -> dict | None:
        self.observacoes.append(observacao)

        if self.erro is not None:
            raise self.erro

        return self.resposta


class CanalControlado:
    """Simula Telegram ou Email e registra todas as tentativas."""

    def __init__(
        self,
        nome: str,
        *,
        sucesso: bool,
        erro: str | None = None,
        lancar_excecao: bool = False,
    ) -> None:
        self.nome = nome
        self.sucesso = sucesso
        self.erro = erro
        self.lancar_excecao = lancar_excecao
        self.alertas: list[Alerta] = []

    def enviar(self, alerta: Alerta) -> ResultadoAlerta:
        self.alertas.append(alerta)

        if self.lancar_excecao:
            raise RuntimeError(
                self.erro or f"Falha inesperada no canal {self.nome}"
            )

        return ResultadoAlerta(
            sucesso=self.sucesso,
            canal=self.nome,
            erro=None if self.sucesso else self.erro,
        )


def criar_registro_divergente(numero: int) -> pd.Series:
    """Cria um lote ausente da base para acionar a RN05 e o ML."""

    return pd.Series(
        {
            "lote_id": f"LOTE-CRISE-{numero:03d}",
            "produto": "Produto de teste",
            "linha": "Linha 1",
            "turno": "Manhã",
            "status": "APROVADO",
            "responsavel": "Equipe de teste",
            "data": "15/06/2026",
            "observacao": "Código não localizado na base de referência",
        },
        dtype=object,
    )


def processar_lote_divergente(
    classificador: ClassificadorDivergencia,
    auditoria: AuditoriaPipelineHibrido,
    *,
    quantidade: int = 2,
):
    """Processa vários itens para provar que uma falha não para o lote."""

    return [
        processar_item(
            registro=criar_registro_divergente(numero),
            data_referencia="15/06/2026",
            lotes_referencia={"LOTE-REFERENCIA"},
            ocorrencia_no_dia=1,
            classificador=classificador,
            auditoria_ml=auditoria,
        )
        for numero in range(1, quantidade + 1)
    ]


def criar_alertas_controlados(
    *,
    telegram_sucesso: bool = True,
    email_sucesso: bool = True,
    telegram_lanca_excecao: bool = False,
):
    """Cria o sistema real usando canais falsos e um logger auditável."""

    telegram = CanalControlado(
        "telegram",
        sucesso=telegram_sucesso,
        erro=(
            None
            if telegram_sucesso
            else "Telegram indisponível"
        ),
        lancar_excecao=telegram_lanca_excecao,
    )
    email = CanalControlado(
        "email",
        sucesso=email_sucesso,
        erro=(
            None
            if email_sucesso
            else "Email indisponível"
        ),
    )
    logger = Mock()
    sistema = SistemaAlertas(
        canal_principal=telegram,
        canal_secundario=email,
        logger=logger,
    )
    return sistema, telegram, email, logger


def enviar_alerta_da_crise(
    sistema: SistemaAlertas,
    *,
    severidade: Severidade,
    cenario: str,
) -> ResultadoAlerta:
    """Dispara o alerta que seria apresentado como evidência da crise."""

    return sistema.enviar_alerta(
        severidade=severidade,
        mensagem=f"Cenário de crise detectado: {cenario}",
        contexto={
            "execution_id": f"exec-{cenario}",
            "correlation_id": "corr-simulacao-crise",
            "bot_id": "teste-integracao-crise",
        },
    )


def resposta_ml_valida(
    *,
    confianca: float,
) -> dict:
    return {
        "causa_provavel": "falta_peca",
        "confianca_ml": confianca,
        "versao_modelo": "2.0.0-simulacao",
    }


def test_cenario_1_base_referencia_instavel(
    planilha_controlada_factory,
    caplog,
):
    """A base falha, o lote segue para revisão e o ML não é chamado."""

    caplog.set_level(
        logging.INFO,
        logger="botcity_permorfer",
    )
    entrada = planilha_controlada_factory(
        nome="crise_base_referencia.xlsx"
    )
    consulta_base = Mock(
        side_effect=ConnectionError("Base de referência instável")
    )
    sleeper = Mock()
    classificador = Mock()

    # A função não deve lançar exceção, mesmo após todas as tentativas.
    registros = ler_e_validar(
        entrada,
        classificador=classificador,
        consulta_base_referencia=consulta_base,
        configuracao_retry_base=ConfiguracaoRetryBase(
            max_tentativas=3,
            backoff_seconds=0,
        ),
        sleeper_base=sleeper,
    )

    sistema, telegram, email, _ = criar_alertas_controlados()
    alerta = enviar_alerta_da_crise(
        sistema,
        severidade=Severidade.CRITICO,
        cenario="base-referencia-instavel",
    )

    assert len(registros) == 20
    assert all(
        registro.status == "PENDENTE_REVISAO"
        for registro in registros
    )
    assert all(
        registro.classificacao == "PENDENTE_REVISAO"
        for registro in registros
    )
    assert consulta_base.call_count == 3
    assert sleeper.call_count == 2
    classificador.classificar.assert_not_called()

    assert alerta.sucesso is True
    assert alerta.canal == "telegram"
    assert len(telegram.alertas) == 1
    assert email.alertas == []
    assert "infraestrutura_degradada" in caplog.messages


def test_cenario_2_servico_ml_fora_do_ar():
    """A API offline produz fallback para todos os itens do lote."""

    cliente = ClienteMLControlado(
        erro=MLServiceUnavailableError("API ML fora do ar")
    )
    classificador = ClassificadorDivergencia(
        cliente_ml=cliente,
        ml_enabled=True,
        confianca_minima=0.75,
    )
    logger_auditoria = Mock()
    auditoria = AuditoriaPipelineHibrido(
        execution_id="exec-ml-offline",
        logger=logger_auditoria,
    )

    resultados = processar_lote_divergente(
        classificador,
        auditoria,
    )

    sistema, telegram, email, _ = criar_alertas_controlados()
    alerta = enviar_alerta_da_crise(
        sistema,
        severidade=Severidade.ERRO,
        cenario="ml-fora-do-ar",
    )

    assert len(resultados) == 2
    assert all(
        resultado.classificacao == "Divergência"
        for resultado in resultados
    )
    assert all(
        resultado.origem_decisao == "fallback"
        for resultado in resultados
    )
    assert all(
        resultado.motivo_fallback
        == MotivoFallback.SERVICO_INDISPONIVEL.value
        for resultado in resultados
    )
    assert len(cliente.observacoes) == 2
    assert len(auditoria.decisoes) == 2
    assert logger_auditoria.info.call_count == 2

    assert alerta.sucesso is True
    assert len(telegram.alertas) == 1
    assert email.alertas == []


def test_cenario_3_servico_ml_acima_do_timeout():
    """O timeout é diferenciado de indisponibilidade e não para o lote."""

    cliente = ClienteMLControlado(
        erro=MLTimeoutError("Tempo limite excedido")
    )
    classificador = ClassificadorDivergencia(
        cliente_ml=cliente,
        ml_enabled=True,
        confianca_minima=0.75,
    )
    auditoria = AuditoriaPipelineHibrido(
        execution_id="exec-ml-timeout"
    )

    resultados = processar_lote_divergente(
        classificador,
        auditoria,
    )

    sistema, telegram, email, _ = criar_alertas_controlados()
    alerta = enviar_alerta_da_crise(
        sistema,
        severidade=Severidade.ERRO,
        cenario="ml-timeout",
    )

    assert len(resultados) == 2
    assert all(
        resultado.origem_decisao == "fallback"
        for resultado in resultados
    )
    assert all(
        resultado.motivo_fallback
        == MotivoFallback.TIMEOUT.value
        for resultado in resultados
    )
    assert len(auditoria.decisoes) == 2
    assert {
        decisao.motivo_fallback
        for decisao in auditoria.decisoes
    } == {MotivoFallback.TIMEOUT.value}

    assert alerta.sucesso is True
    assert len(telegram.alertas) == 1
    assert email.alertas == []


def test_cenario_4_ml_com_confianca_abaixo_do_limiar():
    """Uma predição fraca é descartada sem inventar confiança ou causa."""

    cliente = ClienteMLControlado(
        resposta=resposta_ml_valida(confianca=0.60)
    )
    classificador = ClassificadorDivergencia(
        cliente_ml=cliente,
        ml_enabled=True,
        confianca_minima=0.75,
    )
    auditoria = AuditoriaPipelineHibrido(
        execution_id="exec-baixa-confianca"
    )

    resultados = processar_lote_divergente(
        classificador,
        auditoria,
    )

    sistema, telegram, email, _ = criar_alertas_controlados()
    alerta = enviar_alerta_da_crise(
        sistema,
        severidade=Severidade.AVISO,
        cenario="ml-baixa-confianca",
    )

    assert len(resultados) == 2
    assert all(
        resultado.origem_decisao == "fallback"
        for resultado in resultados
    )
    assert all(
        resultado.motivo_fallback
        == MotivoFallback.BAIXA_CONFIANCA.value
        for resultado in resultados
    )
    assert all(
        resultado.confianca_ml is None
        for resultado in resultados
    )
    assert all(
        resultado.causa_provavel == "nao_classificado"
        for resultado in resultados
    )
    assert len(auditoria.decisoes) == 2

    assert alerta.sucesso is True
    assert len(telegram.alertas) == 1
    assert email.alertas == []


def test_cenario_5_telegram_indisponivel_aciona_email():
    """O Telegram falha e o Email entrega o alerta crítico."""

    # Primeiro, prova que o lote foi processado normalmente.
    cliente = ClienteMLControlado(
        resposta=resposta_ml_valida(confianca=0.95)
    )
    classificador = ClassificadorDivergencia(
        cliente_ml=cliente,
        ml_enabled=True,
        confianca_minima=0.75,
    )
    auditoria = AuditoriaPipelineHibrido(
        execution_id="exec-telegram-offline"
    )
    resultados = processar_lote_divergente(
        classificador,
        auditoria,
    )

    sistema, telegram, email, logger = criar_alertas_controlados(
        telegram_sucesso=False,
        email_sucesso=True,
        # Também valida uma falha inesperada, e não somente um
        # ResultadoAlerta com sucesso=False.
        telegram_lanca_excecao=True,
    )

    # A chamada não deve propagar a exceção do Telegram.
    alerta = enviar_alerta_da_crise(
        sistema,
        severidade=Severidade.CRITICO,
        cenario="telegram-indisponivel",
    )

    assert len(resultados) == 2
    assert all(
        resultado.origem_decisao == OrigemDecisao.ML.value
        for resultado in resultados
    )
    assert len(auditoria.decisoes) == 2

    assert alerta.sucesso is True
    assert alerta.canal == "email"
    assert alerta.fallback_acionado is True
    assert len(alerta.tentativas) == 2
    assert [
        tentativa.canal
        for tentativa in alerta.tentativas
    ] == ["telegram", "email"]
    assert [
        tentativa.sucesso
        for tentativa in alerta.tentativas
    ] == [False, True]

    assert len(telegram.alertas) == 1
    assert len(email.alertas) == 1

    # O log estruturado pode ser utilizado como evidência da apresentação.
    auditoria_entrega = logger.info.call_args.kwargs["extra"]
    assert auditoria_entrega["evento"] == "alerta_entregue"
    assert auditoria_entrega["canal_entrega"] == "email"
    assert auditoria_entrega["fallback_acionado"] is True