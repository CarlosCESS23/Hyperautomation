# ChangeLog
Todas as modificações notáveis neste projeto serão documentadas neste arquivo.

## [Unreleased] (ou [v1.0.0] - 2026-07-13)

### Adicionado
* **Regras de Negócio (Validações):**
  * **RN01:** Implementada a função `verificar_estrutura_rn01` no módulo `src/validacao.py` para garantir a presença das colunas obrigatórias na planilha[cite: 2].
  * **RN02:** Implementada a função `validar_campos_obrigatorios_rn02` no módulo `src/validacao.py` para identificar valores nulos utilizando o `pandas`, ignorando campos opcionais como "observação"[cite: 2].
  * **RN03:** Implementada a função `verificar_lotes` para confirmar a existência do `id_lote` na base de referência.
* **Testes Unitários (Pytest):**
  * Criação de testes abrangendo os cenários de "caminho feliz" e "casos de falha" para as regras RN01, RN02 e RN03.
  * Simulação de logs (mock) através da biblioteca `unittest.mock` para manter a saída dos testes limpa.

### Corrigido
* **Resolução de Importações (Pytest):** 
  * Correção do erro `ImportError: attempted relative import with no known parent package`.
  * Substituição de importações relativas por absolutas nos arquivos de teste.
  * Estruturação das pastas `src/` e `tests/` como pacotes Python (através da adição dos arquivos `__init__.py`).