# ChangeLog
Todas as modificações notáveis neste projeto serão documentadas neste arquivo.

## [Unreleased] (ou [v1.0.0] - 2026-08-02)

### Adicionado
* **RN01:** Implementada a função `verificar_estrutura_rn01` no módulo `src/validacao.py` para garantir a presença das colunas obrigatórias na planilha.
* **RN02:** Implementada a função `validar_campos_obrigatorios_rn02` no módulo `src/validacao.py` para identificar valores nulos utilizando o `pandas`.
* **RN03:** Implementada a função `verificar_lotes` para confirmar a existência do `id_lote` na base de referência.
* **RN04:** Implementada a função `verificar_status_rn04` no módulo `src/validacao.py` para validar se o status pertence ao escopo de regras permitido (APROVADO, REPROVADO, PENDENTE).
* **RN05:** Implementada a função `normalizar_status_rn05` no módulo `src/validacao.py` para normalizar automaticamente as entradas "OK" e "NOK".
* **Testes Unitários:** Criação de testes abrangendo os cenários de "caminho feliz" e "casos de falha" para as regras RN01 a RN05.
* **Técnicas de Teste:** Aplicação de simulação de logs (`unittest.mock`) e parametrização de múltiplos cenários (`pytest.mark.parametrize`) para maior cobertura de código.

### Corrigido
* **Resolução de Importações:** Correção do erro `ImportError: attempted relative import` no ambiente de testes.
* **Estrutura de Pacotes:** Substituição de importações relativas por absolutas e adição dos arquivos `__init__.py` nas pastas `src/` e `tests/`.