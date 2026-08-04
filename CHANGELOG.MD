# Changelog

Este arquivo registra mudanças relevantes do código que está presente no
repositório. O formato segue as categorias de [Keep a
Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

### Alterado

- A documentação foi revisada para refletir a automação web atual baseada em
  Playwright, sua execução local e via Docker Compose, as variáveis efetivamente
  usadas e as saídas geradas.

## [1.0.0]

### Adicionado

- Automação do login do portal demonstrativo com Playwright.
- Portal estático de login e formulário de lote em `frontend/`.
- Logs estruturados em JSON, com identificadores de bot e execução.
- Geração de evidências de execução em `logs/` e `resultados/`.
- Ambiente Docker Compose com Nginx para o portal e contêiner Playwright para o
  bot.
