# Roteiro de apresentação — Exercício 22

Duração prevista: 5 minutos.

## 0:00–0:40 — Objetivo

“Transformamos as regras RN01–RN12 em um relatório executivo. O objetivo é
permitir que Fernanda identifique, em menos de 30 segundos, quantos registros
estão corretos e quais exigem ação.”

## 0:40–1:30 — Origem e validação

- A entrada contém 250 registros distribuídos em 10 dias úteis.
- A validação usa o serviço central `src/validacao_lotes.py`.
- RN11 é calculada separadamente por dia; a repetição em dias diferentes não é
  duplicidade.
- Cada registro recebe exatamente uma classificação.

## 1:30–2:40 — Indicadores do Resumo

Apontar os cinco cartões do dashboard:

- 250 registros processados;
- 150 válidos;
- 50 divergências;
- 20 ambíguos;
- 30 erros de entrada.

Explicar que existem **100 registros problemáticos no total**, correspondentes
à soma de 50 divergências, 20 ambíguos e 30 erros de entrada. Portanto, “100”
não significa 100 registros classificados exclusivamente como Divergência.

## 2:40–3:35 — Gráficos

- O gráfico de rosca mostra a participação percentual das quatro categorias.
- O gráfico de evolução mostra divergências, ambíguos e o total de problemas em
  cada um dos 10 dias.
- Destacar os dias de maior volume para priorizar a investigação.

## 3:35–4:30 — Decisão sustentada

Fernanda deve tomar três decisões olhando apenas o Resumo:

1. corrigir na origem os 30 erros de entrada;
2. conciliar os 50 registros divergentes com a base ou o processo;
3. encaminhar os 20 casos ambíguos para decisão humana.

## 4:30–5:00 — Evidências e encerramento

- Mostrar que as seis abas não misturam classificações.
- Informar que os gráficos são editáveis e nativos do Excel.
- Mostrar `reports/log_execucao.txt` e o PDF do dashboard.
- Encerrar com: “O painel transforma 250 linhas operacionais em uma fila clara
  de 100 ações, separadas pelo responsável pela decisão.”

## Pergunta de aceite

**O que Fernanda decide olhando apenas a aba Resumo?**

Ela decide o que pode ser aceito, o que precisa ser corrigido na origem, o que
deve ser conciliado com a base/processo e o que requer decisão humana.
