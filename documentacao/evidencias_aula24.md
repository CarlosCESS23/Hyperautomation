# Pacote de evidências — Aula 24

## Artefatos verificáveis

- `reports/relatorio_conferencia_lotes.xlsx`
- `reports/resumo_executivo.md`
- `tests/integration/test_relatorio_consolidado.py`
- `documentacao/checklist_aula24.md`

## Comandos de reprodução

```bash
python -m pytest tests/integration/test_relatorio_consolidado.py -q
python -m pytest -m unit -q
python -m pytest -m integration -q
python -m pytest -m regression -q
python -m pytest -m e2e -q
python -m pytest -q
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

Os testes criam entradas e saídas em `tmp_path`; nenhum caminho permanente ou
dado externo é necessário para validar o relatório consolidado.

## Resultado da validação final

- Suíte: **53 passed, 1 skipped, 1 xfailed**.
- Cobertura de `src`: **95,65%** (mínimo exigido: 80%).
- `operational_indicators.py`: **100%**.
- `validacao_lotes.py`: **100%**.
