# Hyperautomation

Repositório destinado às atividades desenvolvidas na disciplina de **Hyperautomation** do projeto **AXAcademy**.

O objetivo deste repositório é centralizar o desenvolvimento das atividades, documentações e artefatos produzidos ao longo da disciplina, mantendo um padrão de organização que facilite a colaboração entre os integrantes da equipe.

---

# Equipe

**Equipe 01**

- Gustavo Nunes de Oliveira
- Carlos Eduardo
- Raquel Andrade

---

# Objetivo do Repositório

Este repositório concentra todos os materiais produzidos durante a disciplina, incluindo:

- Códigos-fonte;
- Documentações técnicas;
- Diagramas BPMN;
- Documentos PDD;
- Materiais de apoio;
- Histórico de desenvolvimento.

A branch **main** representa o ponto central da documentação do projeto, reunindo as versões oficiais dos documentos e servindo como referência para todas as demais branches.

Sempre que houver alterações em processos ou implementações, a documentação deverá ser atualizada juntamente com o código.

---

# Estrutura do Repositório

```text
.
├── BPMN/                    # Diagramas de processos
├── PDD/                     # Documentos de definição de processos
├── documentos_referencia/   # Materiais de apoio da disciplina
│   ├── docker/
│   ├── gitflow/
│   └── CI-CD/
├── README.md
```

---

# Organização das Branches

Cada atividade será desenvolvida em sua própria branch.

O padrão adotado é:

```text
TIPO_BRANCH-NOME_ATIVIDADE/TITULO_BRANCH
```

Exemplo:

```text
feature-selenium/raspagem-site
```

Esse padrão permite identificar rapidamente:

- o tipo da alteração;
- a atividade relacionada;
- a funcionalidade implementada.

---

# Tipos de Branch

| Branch | Responsabilidade |
|---------|------------------|
| **main** | Versão oficial do repositório. Contém apenas código estável e documentação consolidada. |
| **develop** | Branch de integração entre as funcionalidades, utilizar como main de cada atividade. |
| **feature** | Desenvolvimento de novas funcionalidades. |
| **fix** | Correção de bugs. |
| **hotfix** | Correções urgentes em produção. |
| **docs** | Alterações exclusivamente na documentação. |
| **style** | Ajustes de formatação, interface ou organização visual. |
| **refactor** | Melhorias internas sem alteração de comportamento. |

---

# Fluxo de Desenvolvimento

Cada nova atividade deverá seguir o seguinte fluxo:

1. Atualizar a branch principal.

```bash
git switch main
git pull
```

2. Criar uma nova branch.

```bash
git switch -c feature-atividade/nome-da-feature
```

3. Desenvolver a funcionalidade.

4. Realizar commits seguindo o padrão definido.

5. Enviar a branch ao GitHub.

```bash
git push -u origin NOME_DA_BRANCH
```

6. Abrir um Pull Request para respectiva branch develop.

7. Após aprovação, realizar o merge.

---

# Releases

Para cada atividade completa, deve-se realizar um release dela, é por meio da release que organizaremos e entrega das atividades

---

# Padrão de Commits

Todos os commits devem possuir mensagens claras e objetivas.

Formato:

```text
PREFIXO: descrição da alteração
```

Exemplo:

```text
feat: adicionar integração com Google Sheets
```

## Prefixos

| Prefixo | Utilização |
|----------|------------|
| feat | Nova funcionalidade |
| fix | Correção de bugs |
| docs | Documentação |
| style | Formatação e organização visual |
| refactor | Refatoração interna |
| test | Testes |
| ci | Alterações em CI/CD |
| chore | Manutenção geral |
| perf | Melhorias de desempenho |
| revert | Reversão de commits |

Evite mensagens genéricas como:

- ajuste
- mudanças
- update
- teste

Prefira mensagens que descrevam exatamente a alteração realizada.

---

# Organização dos Projetos

Cada atividade deve possuir uma estrutura semelhante à seguinte:

```text
atividade/
├── docs/
│   ├── README.md
│   ├── BPMN/
│   └── PDD/
├── src/
├── tests/
├── assets/
├── data/
├── requirements.txt
├── .gitignore
└── README.md
```

## Descrição das Pastas

| Pasta | Finalidade |
|--------|------------|
| **src/** | Código-fonte da aplicação. |
| **tests/** | Testes automatizados e casos de teste. |
| **docs/** | Documentação específica da atividade. |
| **assets/** | Arquivos auxiliares, imagens e recursos. |
| **data/** | Arquivos csv, jsons, banco de dados. |
| **README.md** | Guia da atividade, instruções de execução e documentação técnica. |

---

# Boas Práticas

Durante o desenvolvimento, recomenda-se:

- manter o README atualizado;
- documentar alterações importantes;
- manter os BPMNs sincronizados com o processo implementado;
- manter o PDD atualizado sempre que houver mudanças de negócio;
- realizar commits pequenos e descritivos;
- evitar subir arquivos temporários;
- utilizar Pull Requests para revisão de código;
- manter a branch `main` sempre estável.

---

# Documentação

Toda atividade deverá conter, quando aplicável:

- README específico;
- BPMN atualizado;
- PDD correspondente;
- instruções de execução;
- requisitos;
- dependências utilizadas.

A documentação faz parte da entrega e deve evoluir juntamente com o código.

---

# Convenções

- Utilize nomes de arquivos e pastas em letras minúsculas.
- Utilize nomes descritivos para branches e commits.
- Não versione credenciais, arquivos temporários ou ambientes virtuais.
- Mantenha o histórico Git limpo e organizado.
- Sempre revise a documentação antes de realizar o merge para a branch principal.