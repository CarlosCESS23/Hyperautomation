# PDD — Aula 24: indicadores e produto executivo

## Objetivo do processo

Transformar a conferência de lotes em dois artefatos executivos consistentes:
um relatório Excel com oito abas e um resumo em Markdown.

## Desenho da solução

Após a leitura e a aplicação das RN01–RN12, o processo consolida os indicadores
uma única vez. O objeto resultante é entregue, sem recálculo, ao gerador Excel e
ao gerador do resumo executivo. O Excel preserva as seis abas operacionais e
acrescenta o ranking das regras e o dicionário de negócio.

## Indicadores

1. Total de registros.
2. Registros válidos.
3. Divergências.
4. Registros ambíguos.
5. Erros de entrada.
6. Regra mais acionada.
7. Taxa de retrabalho.
8. Taxa de revisão humana.
9. Taxa de qualidade da entrada.
10. Ganho estimado de tempo.

O ganho é uma estimativa didática: cinco minutos poupados para cada registro
válido. A premissa é exibida no resumo executivo.

## Controles

- A contagem de regras nasce durante a validação e não é refeita no relatório.
- O ranking é ordenado por quantidade decrescente e, em empate, pelo código.
- Excel e Markdown recebem a mesma instância de indicadores no fluxo principal.
- A integração automatizada valida abas, indicador 6, ranking e valores do
  Markdown em um diretório temporário.
