# ChangeLog
Todas as modificações notáveis neste projeto serão documentadas neste arquivo.

## [Unreleased] (ou [v1.0.0] - 2026-07-13)

### Adicionado
* **Regras de Negócio (RN01 e RN02):**
  * Implementação da RN01 (Validação de Estrutura) e RN02 (Validação de Campos Obrigatórios) no módulo `src/validacao.py`.
  * A RN01 foi implementada através da função `verificar_estrutura_rn01`.
  * A RN02 foi implementada através da função `validar_campos_obrigatorios_rn02`.