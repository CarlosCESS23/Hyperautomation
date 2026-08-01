# Bot de Inspeção de Lotes Diários

## Regra de negócio Implementadas

### RN01 - Validação de Estrutura (Padrão de Colunas)

* **Idea:** Foi criada uma funcionalidade para atender a regra RN01, que realiza a verificação de conformidade do layout da planilha recebida para garantir que ela possua exatamente os campos esperados pelo sistema.
* **Como funciona:** O sistema extrai o cabeçalho da planilha carregada e realiza uma operação de diferença de conjuntos (`set`) contra uma coleção de colunas de referência (`lote_id`, `produto`, `linha`, `turno`, `status`, `responsavel`, `data`, `observacao`). A verificação ocorre de forma bidirecional, identificando tanto colunas obrigatórias que estão ausentes quanto colunas intrusas (não padronizadas) que foram inseridas.
* **Tratamento:** Se a estrutura diferir da referência, o sistema levanta uma exceção `ValueError` detalhando exatamente quais colunas faltam ou sobram, registra o evento via *logger* como erro crítico e interrompe o processamento do arquivo.

### RN02 - Validação de Campos Obrigatórios (Valores Nulos)

* **Idea:** Foi criada uma funcionalidade para atender a regra RN02, cujo objetivo é assegurar a completude dos dados processados, impedindo a ingestão de registros com informações essenciais em branco.
* **Como funciona:** O sistema aplica uma máscara booleana vetorizada (`isna()`) sobre todo o *DataFrame* para rastrear a presença de valores nulos nativos (`None` ou `NaN`). Quando a máscara retorna verdadeiro, o algoritmo mapeia as coordenadas matriciais para isolar o índice exato da linha e o nome da coluna da ocorrência.
* **Tratamento:** Ao detectar o primeiro campo vazio, o sistema levanta uma exceção `ValueError` contendo as coordenadas exatas da falha (ex: "linha 1, coluna 'produto'"), registra o evento no log de erros e aborta a validação.

### RN03 - Validação de Existência (Cruzamento com base_referência)

* **Idea:** Foi criado uma funcionalidade para atender a regra RN03, que  realiza o cruzamento de dados para garantir 
a integridade dos lotes recebidos na inspeção diária.

* **Como funciona:** O sistema lê a planilha exportada pelo operador e cruza a coluna `lote_id` com a aba `Base_Referencia`
* **Tratamento:** Se o lote informado não existe na base_referencial, o sistema levanta uma exceção **"Lote não existente"**,
que classifica o registro como divergência. Somente tem a responsabilidade de iniciar a leitura a partir de linha correta

### RN04 - Validação e Normalização de Status

* **Idea:** Foi criada uma funcionalidade para atender a regra RN04, cujo objetivo é assegurar que o status do lote inspecionado esteja contido no domínio de valores permitidos e padronizados pelo sistema.
* **Como funciona:** O algoritmo intercepta o valor da coluna de status de cada registro, realiza uma limpeza de formatação (remoção de espaços em branco e conversão para maiúsculas) e aplica uma normalização preliminar (mapeando "OK" para "APROVADO" e "NOK" para "REPROVADO"). Após a normalização, o valor é validado contra um conjunto de referência de escopo fechado (`{"APROVADO", "REPROVADO", "PENDENTE"}`) utilizando busca em complexidade de tempo O(1).
* **Tratamento:** Se o status recebido não for reconhecido e não puder ser normalizado, o sistema levanta uma exceção `ValueError` detalhando o erro e a linha correspondente, efetua o registro no *log* e interrompe o pipeline de processamento.

---

### RN05 - [Nome da Validação - Necessita Definição]

* **Idea:** [Inserir o objetivo de negócio da regra. Exemplo: Assegurar a unicidade dos registros, impedindo a ingestão de lotes duplicados no mesmo turno.]
* **Como funciona:** [Inserir a mecânica de software da regra. Exemplo: O sistema aplica o método `.duplicated()` sobre a coluna `lote_id`, retornando uma máscara booleana para mapear colisões de dados na planilha atual.]
* **Tratamento:** [Inserir o comportamento de falha. Exemplo: Ao identificar a duplicidade, o sistema levanta uma exceção `ValueError` indicando as linhas conflitantes e aborta o processamento.]

### RN07 -  Condição de Campo de Observação
Garante que todo o lote recusado pela produção possua uma justificativa rasterável.

* **Ação:** O Sistema avalia se a coluna `status` de cada registro esteja REPROVADO
* **Tratamento:** Caso a coluna `status` seja reprovado, ele verificará se possui o campo de observação, caso não tenha,
registrará como um caso de divergência
* 

### Geração de Relatórios
O bot consolida todas as divergências encontradas durante a validação das regras de negócio (Lotes Inexistentes, 
Status divergentes, Falta de Observação, etc.) e exporta automaticamente um arquivo `.xlsx` estruturado, seguindo o 
padrão da seção 12 do PDD.

#### Rodando testes

```python
# Para rodar todos os testes com saída detalhada
pytest test/ -v

# Rodar apenas os testes que falharam na última execução
pytest --last-failed
```

#### Rodando o bot

```bash
#Para rodar o bot, digite seguinte comando:
python bot.py
```



## Dependência e Instalação

**Python:** Pode ser utilizado o Python entre 3.11 até 3.14

Biblioteca|Descrição|Versão
:-:|:-:|:-:
Pytest|É um framework de teste para Python que permite desenvolver teste unitários|9.1.1
Pandas|É usado para analisar e manipular dados em tabelas, como se fosse excel|3.0.3
openpyxl|É uma biblioteca que é usada para ler, criar e modificar os arqivos do Excel, não tendo necessidade do software Microsoft Office|3.1.5


