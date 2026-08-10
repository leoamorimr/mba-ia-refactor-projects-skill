# Criação de Skills — Refatoração Arquitetural Automatizada

Ao longo do curso você aprendeu o que são Skills e como elas permitem que um agente de IA atue como um especialista em tarefas específicas. Agora imagine o seguinte cenário: você herdou 3 projetos legados com problemas de arquitetura, segurança e qualidade de código. Revisar e corrigir tudo manualmente levaria dias.

Neste desafio, você vai criar uma Skill que automatiza esse processo — analisando, auditando e refatorando qualquer projeto para o padrão MVC, independente da tecnologia.

## Objetivo

Você deve entregar uma Skill capaz de:

- Analisar uma codebase detectando linguagem, framework e arquitetura atual
- Identificar anti-patterns e code smells, classificando por severidade com arquivo e linha exatos
- Gerar um relatório de auditoria estruturado com todos os achados
- Refatorar o projeto para o padrão MVC (Model-View-Controller), eliminando os problemas encontrados
- Validar o resultado garantindo que a aplicação continua funcionando após as mudanças

A skill deve ser agnóstica de tecnologia, funcionando com diferentes linguagens e frameworks.

## Contexto

### Definição de Severidades

Para padronizar a sua auditoria e os relatórios gerados pela IA, utilize a seguinte escala de classificação baseada em problemas de MVC e SOLID:

- **CRITICAL:** Falhas graves de arquitetura ou segurança que impedem o funcionamento correto, expõem dados sensíveis (ex: credenciais hardcoded, SQL Injection) ou violam completamente a separação de responsabilidades (ex: "God Class" contendo banco de dados, lógicas complexas e roteamento no mesmo arquivo).
- **HIGH:** Fortes violações do padrão MVC ou princípios SOLID que dificultam muito a manutenção e testes (ex: lógicas de negócio pesadas presas dentro de Controllers, forte acoplamento sem Injeção de Dependência, ou uso de estado global mutável em toda a aplicação).
- **MEDIUM:** Problemas de padronização, duplicação de código ou gargalos de performance moderada (ex: Queries N+1 no banco de dados, uso inadequado de middlewares, validações ausentes nas rotas).
- **LOW:** Melhorias de legibilidade, nomenclatura de variáveis ruins, ou "magic numbers" soltos pelo código.

### Exemplo de Uso no CLI

```bash
# Executar a skill no projeto com problemas
cd code-smells-project
claude "/refactor-arch"
```

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:      Flask 3.1.1
Dependencies:  flask-cors
Domain:        E-commerce API (produtos, pedidos, usuários)
Architecture:  Monolítica — tudo em 4 arquivos, sem separação de camadas
Source files:  4 files analyzed
DB tables:     produtos, usuarios, pedidos, itens_pedido
================================
```

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask
Files:   4 analyzed | ~800 lines of code

## Summary
CRITICAL: 4 | HIGH: 5 | MEDIUM: 2 | LOW: 3

## Findings

### [CRITICAL] God Class / God Method
File: models.py:1-350
Description: Arquivo único contém toda lógica de negócio, queries SQL, validação e formatação para 4 domínios diferentes.
Impact: Impossível testar em isolamento, qualquer mudança afeta tudo.
Recommendation: Separar em models e controllers por domínio.

### [CRITICAL] Hardcoded Credentials
File: app.py:8
Description: SECRET_KEY hardcoded como 'minha-chave-super-secreta-123'
...

================================
Total: 14 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y
```

```
[... refatoração executada ...]

================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
src/
├── config/settings.py
├── models/
│   ├── produto_model.py
│   └── usuario_model.py
├── views/
│   └── routes.py
├── controllers/
│   ├── produto_controller.py
│   └── pedido_controller.py
├── middlewares/error_handler.py
└── app.py (composition root)

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly
  ✓ Zero anti-patterns remaining
================================
```

## Tecnologias obrigatórias

- **Ferramenta:** uma das três opções abaixo (não são aceitas outras ferramentas):
  - Claude Code
  - Gemini CLI
  - OpenAI Codex
- **Recurso:** Custom Skills (ou o equivalente na ferramenta escolhida)
- **Formato dos arquivos de referência:** Markdown
- **Projetos-alvo:** Python/Flask (2 projetos) e Node.js/Express (1 projeto) (fornecidos no repositório base)

> **Nota sobre a ferramenta:** Os exemplos deste documento usam o Claude Code (`.claude/skills/`) como referência, pois é a ferramenta utilizada no curso. Se você optar por Gemini CLI ou Codex, adapte o nome da pasta e o comando de invocação conforme a convenção dela — o conceito de skill e a estrutura interna (SKILL.md + arquivos de referência) permanecem os mesmos.

## Requisitos

### 1. Análise Manual dos Projetos

Antes de criar a skill, você deve entender os problemas que ela vai resolver.

**Tarefas:**

- Analisar o projeto `code-smells-project/` (Python/Flask — API de E-commerce)
- Analisar o projeto `ecommerce-api-legacy/` (Node.js/Express — LMS API com fluxo de checkout)
- Analisar o projeto `task-manager-api/` (Python/Flask — API de Task Manager)

Para cada projeto, identificar e documentar no mínimo 5 problemas, incluindo pelo menos:

- 1 de severidade CRITICAL ou HIGH
- 2 de severidade MEDIUM
- 2 de severidade LOW

Documentar os achados na seção "Análise Manual" do seu `README.md`

> **Dica:** Não precisa encontrar todos os problemas — foque nos que têm maior impacto arquitetural. Use os projetos como insumo para entender quais padrões sua skill precisa detectar.

> **Por que 3 projetos?** Dois são Python/Flask (com níveis de organização diferentes) e um é Node.js/Express. Sua skill precisa funcionar nos 3 para provar que é verdadeiramente agnóstica de tecnologia — lidando tanto com código completamente desestruturado quanto com projetos que já possuem alguma separação de camadas.

### 2. Criação da Skill

Agora que você conhece os problemas, crie uma skill que os detecte, gere um relatório de auditoria e corrija automaticamente.

**Tarefas:**

Criar a skill dentro do projeto `code-smells-project/` e implementar o SKILL.md com 3 fases sequenciais:

- **Fase 1 — Análise:** Detectar stack, mapear arquitetura atual, imprimir resumo
- **Fase 2 — Auditoria:** Cruzar código contra catálogo de anti-patterns, gerar relatório, pedir confirmação
- **Fase 3 — Refatoração:** Reestruturar para o padrão MVC, validar que funciona

Criar arquivos de referência em Markdown que forneçam à skill o conhecimento necessário para executar as 3 fases. Os arquivos devem cobrir **obrigatoriamente** as seguintes áreas de conhecimento:

| Área de conhecimento | O que deve conter |
|---|---|
| Análise de projeto | Heurísticas para detecção de linguagem, framework, banco de dados e mapeamento de arquitetura |
| Catálogo de anti-patterns | Anti-patterns com sinais de detecção e classificação de severidade |
| Template de relatório | Formato padronizado do relatório de auditoria (Fase 2) |
| Guidelines de arquitetura | Regras do padrão MVC alvo (camadas Models, Views/Routes e Controllers, responsabilidades de cada uma) |
| Playbook de refatoração | Padrões concretos de transformação para cada anti-pattern (com exemplos de código) |

> **Nota:** Você tem liberdade para organizar os arquivos de referência como preferir — pode usar os nomes e a quantidade de arquivos que fizer sentido para sua skill. O importante é que todas as 5 áreas de conhecimento estejam cobertas. O nome da skill (`refactor-arch`) e o arquivo `SKILL.md` são obrigatórios e não devem ser alterados. O path da skill segue a convenção da ferramenta escolhida (no Claude Code, por exemplo, é `.claude/skills/refactor-arch/`).

**Requisitos da skill:**

- Deve ser agnóstica de tecnologia — deve funcionar corretamente nos 3 projetos fornecidos, independente da stack ou nível de organização
- O catálogo de anti-patterns deve conter no mínimo 8 anti-patterns com severidade distribuída (CRITICAL, HIGH, MEDIUM, LOW)
- O catálogo deve incluir detecção de APIs deprecated — identificar uso de APIs obsoletas e recomendar o equivalente moderno
- O playbook deve ter no mínimo 8 padrões de transformação com exemplos de código antes/depois
- A Fase 2 deve pausar e pedir confirmação antes de modificar qualquer arquivo
- A Fase 3 deve validar o resultado (boot da aplicação + endpoints funcionando)

### 3. Execução da Skill

Execute sua skill nos 3 projetos e valide que ela funciona em todas as stacks.

#### Projeto 1 — code-smells-project (Python/Flask)

Invocar a skill no Claude Code:

```bash
claude "/refactor-arch"
```

> **Nota:** O comando acima é o exemplo com Claude Code. Se você estiver usando Gemini CLI ou Codex, utilize o comando equivalente para invocar uma skill na sua ferramenta.

- Verificar que a Fase 1 detecta corretamente a stack e imprime o resumo
- Verificar que a Fase 2 encontra no mínimo 5 dos problemas documentados na sua análise manual
- Confirmar a execução da Fase 3
- Verificar que a Fase 3:
  - Cria a estrutura de diretórios baseada em MVC
  - A aplicação inicia sem erros
  - Os endpoints originais continuam respondendo
- Salvar o relatório de auditoria (output da Fase 2) em `reports/audit-project-1.md`
- Commitar o código refatorado do projeto no repositório

#### Projeto 2 — ecommerce-api-legacy (Node.js/Express)

Prove que sua skill é reutilizável em outro projeto de backend, mas com stack diferente.

- Copiar a pasta `.claude/skills/refactor-arch/` para dentro de `ecommerce-api-legacy/`
- Invocar a skill:

```bash
cd ../ecommerce-api-legacy
claude "/refactor-arch"
```

- Verificar que as 3 fases executam corretamente neste projeto
- Salvar o relatório em `reports/audit-project-2.md`
- Commitar o código refatorado do projeto no repositório

#### Projeto 3 — task-manager-api (Python/Flask)

Agora o teste com um projeto Python/Flask que já possui alguma organização de camadas (models, routes, services, utils).

- Copiar a pasta `.claude/skills/refactor-arch/` para dentro de `task-manager-api/`
- Invocar a skill:

```bash
cd ../task-manager-api
claude "/refactor-arch"
```

- Verificar que:
  - A Fase 1 detecta corretamente Python/Flask como stack e identifica o domínio de Task Manager
  - A Fase 2 identifica problemas mesmo em um projeto parcialmente organizado
  - A Fase 3 melhora a estrutura sem quebrar a aplicação (todos os endpoints devem continuar respondendo)
- Salvar o relatório em `reports/audit-project-3.md`
- Commitar o código refatorado do projeto no repositório

> **Nota:** Este projeto já possui alguma separação de camadas, mas isso não significa que a arquitetura está adequada. A skill deve identificar tanto problemas de código (segurança, performance, qualidade) quanto oportunidades de melhoria arquitetural. Se houver mudanças estruturais necessárias, a skill deve propô-las e executá-las.

#### Validação

Para cada projeto refatorado, valide o seguinte checklist:

```markdown
## Checklist de Validação

### Fase 1 — Análise
- [ ] Linguagem detectada corretamente
- [ ] Framework detectado corretamente
- [ ] Domínio da aplicação descrito corretamente
- [ ] Número de arquivos analisados condiz com a realidade

### Fase 2 — Auditoria
- [ ] Relatório segue o template definido nos arquivos de referência
- [ ] Cada finding tem arquivo e linhas exatos
- [ ] Findings ordenados por severidade (CRITICAL → LOW)
- [ ] Mínimo de 5 findings identificados
- [ ] Detecção de APIs deprecated incluída (se aplicável)
- [ ] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [ ] Estrutura de diretórios segue padrão MVC
- [ ] Configuração extraída para módulo de config (sem hardcoded)
- [ ] Models criados para abstrair dados
- [ ] Views/Routes separadas para visualização ou roteamento
- [ ] Controllers concentram o fluxo da aplicação
- [ ] Error handling centralizado
- [ ] Entry point claro
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem corretamente
```

> **Dica:** Se a skill não detectou problemas suficientes ou a refatoração falhou, ajuste os arquivos de referência e execute novamente. É normal precisar de 2-4 iterações.

## Entregável

Repositório público no GitHub (fork do repositório base) contendo:

- Skill completa em `.claude/skills/refactor-arch/` (dentro dos 3 projetos)
- Código refatorado dos 3 projetos (resultado da execução da Fase 3, commitado no repositório)
- Relatórios de auditoria em `reports/` (3 arquivos)
- `README.md` atualizado

### Estrutura do repositório

Faça um fork do repositório base contendo os três projetos com code smells.

> **Nota:** A estrutura abaixo usa Claude Code como exemplo (`.claude/skills/`). Se estiver usando outra ferramenta, adapte os caminhos conforme a convenção dela.

```
desafio-skills/
├── README.md                              # Sua documentação
│
├── code-smells-project/                   # Projeto 1 — Python/Flask (API de E-commerce)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← SUA SKILL AQUI
│   │           ├── SKILL.md
│   │           └── (arquivos de referência)
│   ├── app.py
│   ├── controllers.py
│   ├── models.py
│   ├── database.py
│   └── requirements.txt
│
├── ecommerce-api-legacy/                  # Projeto 2 — Node.js/Express (LMS API com checkout)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← CÓPIA DA SKILL
│   │           └── ...
│   ├── src/
│   │   ├── app.js
│   │   ├── AppManager.js
│   │   └── utils.js
│   ├── api.http
│   └── package.json
│
├── task-manager-api/                      # Projeto 3 — Python/Flask (API de Task Manager)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← CÓPIA DA SKILL
│   │           └── ...
│   ├── app.py
│   ├── database.py
│   ├── seed.py
│   ├── requirements.txt
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
│
└── reports/                               # Relatórios gerados
    ├── audit-project-1.md                 # Saída da Fase 2 no projeto 1
    ├── audit-project-2.md                 # Saída da Fase 2 no projeto 2
    └── audit-project-3.md                 # Saída da Fase 2 no projeto 3
```

**O que você vai criar:**

- `.claude/skills/refactor-arch/` — A skill completa (SKILL.md + arquivos de referência)
- Código refatorado dos 3 projetos — resultado da execução da Fase 3, commitado no repositório
- `reports/audit-project-{1,2,3}.md` — Relatório de auditoria de cada projeto
- `README.md` — Documentação do seu processo

**O que já vem pronto:**

- `code-smells-project/` — API de E-commerce Python/Flask com code smells intencionais
- `ecommerce-api-legacy/` — LMS API Node.js/Express (com fluxo de checkout) e problemas de implementação
- `task-manager-api/` — API de Task Manager Python/Flask com organização parcial e problemas de segurança/qualidade

> **Dica:** Cada projeto contém problemas intencionais de diferentes severidades (CRITICAL, HIGH, MEDIUM, LOW), incluindo falhas de segurança, violações arquiteturais e problemas de qualidade de código. Parte do desafio é identificá-los por conta própria através da análise manual do código.

### README.md deve conter

**A) Seção "Análise Manual":**

- Lista dos problemas identificados manualmente em cada projeto
- Classificação por severidade
- Justificativa de por que cada problema é relevante

**B) Seção "Construção da Skill":**

- Decisões de design: como estruturou o SKILL.md e os arquivos de referência
- Quais anti-patterns incluiu no catálogo e por quê
- Como garantiu que a skill é agnóstica de tecnologia
- Desafios encontrados e como resolveu

**C) Seção "Resultados":**

- Resumo dos relatórios de auditoria dos 3 projetos (quantos findings por severidade em cada)
- Comparação antes/depois da estrutura de cada projeto
- Checklist de validação preenchido para cada projeto
- Screenshots ou logs mostrando as aplicações rodando após refatoração
- Observações sobre como a skill se comportou em stacks diferentes

**D) Seção "Como Executar":**

- Pré-requisitos (a ferramenta escolhida — Claude Code, Gemini CLI ou Codex — instalada e configurada)
- Comandos para executar a skill em cada projeto
- Como validar que a refatoração funcionou

### Ordem de execução sugerida

**1. Analisar os projetos manualmente**

Leia o código dos três projetos e documente os problemas encontrados.

**2. Criar a skill**

Escreva o SKILL.md e os arquivos de referência.

**3. Executar nos 3 projetos**

```bash
# Projeto 1
cd code-smells-project
claude "/refactor-arch"

# Projeto 2
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3
cd ../task-manager-api
claude "/refactor-arch"
```

Salve a saída da Fase 2 de cada projeto em `reports/audit-project-{1,2,3}.md`.

**4. Iterar**

Se a skill não detectou problemas suficientes ou a refatoração falhou, ajuste os arquivos de referência e execute novamente. É normal precisar de 2-4 iterações.

## Critérios de Aceite

A skill deve atingir os seguintes mínimos em **todos os 3 projetos**:

| Critério | Requisito |
|---|---|
| Fase 1 detecta stack corretamente | OBRIGATÓRIO (3/3 projetos) |
| Fase 2 encontra >= 5 findings | OBRIGATÓRIO (3/3 projetos) |
| Fase 2 inclui pelo menos 1 CRITICAL ou HIGH | OBRIGATÓRIO (3/3 projetos) |
| Fase 3 aplicação funciona após refatoração | OBRIGATÓRIO (3/3 projetos) |

**IMPORTANTE:** Todos os critérios devem ser atingidos nos 3 projetos, não apenas em um!

> **Sobre o projeto 3 (task-manager-api):** Este projeto já possui alguma organização. "aplicação funciona" significa que a API inicia sem erros e todos os endpoints continuam respondendo corretamente.

## Referências

- [Claude Code: Skills](https://docs.anthropic.com/en/docs/claude-code/skills) — Documentação oficial sobre como criar e estruturar Skills
- [Claude Code: Overview](https://docs.anthropic.com/en/docs/claude-code/overview) — Visão geral do Claude Code e suas capacidades
- [The Complete Guide to Building Skills for Claude (PDF)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) — Guia completo da Anthropic sobre construção de Skills
- [Equipping Agents for the Real World with Agent Skills](https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills) — Blog oficial da Anthropic sobre Agent Skills

---

## Dicas Finais

- **Comece pela análise manual** — entender os problemas profundamente é essencial para criar uma skill que os detecte.
- **O SKILL.md é um prompt** — ele instrui o agente sobre o que fazer, enquanto os arquivos de referência fornecem o conhecimento de domínio.
- **Seja específico nos sinais de detecção** — "código ruim" não ajuda; "query SQL dentro de loop for" é acionável.
- **Teste incrementalmente** — não tente criar a skill perfeita de primeira.
- **A skill deve ser copiável** — se ela só funciona em um projeto específico, está acoplada demais. Teste nos 3 projetos para validar.
- **Projetos diferentes exigem adaptação** — a Fase 3 de um projeto já parcialmente organizado não vai ter as mesmas transformações de um monolito. Sua skill deve se adaptar ao contexto.
- **Pedir confirmação na Fase 2 é obrigatório** — o humano deve revisar o relatório antes de qualquer modificação.
- **Consulte as referências do curso** — revise a documentação oficial da ferramenta escolhida e os materiais das aulas para relembrar a estrutura e anatomia de uma skill.

---

# Minha Entrega

Documentação do processo real de análise, construção da skill e execução nos 3 projetos. As seções abaixo cobrem os 3 projetos de forma consolidada, já que a skill `refactor-arch` é idêntica nos 3 (mesma pasta `.claude/skills/refactor-arch/`, copiada sem alterações).

## Análise Manual

A análise manual completa de cada projeto (tabela achado-a-achado com severidade, arquivo:linha e justificativa) está documentada no `README.md` do próprio projeto, na seção "Análise Manual", junto com o link para o relatório de auditoria salvo em `reports/`. Resumo:

| Projeto | Stack | Organização original do código | Achados manuais | CRITICAL / HIGH / MEDIUM / LOW | Detalhe |
|---|---|---|---|---|---|
| `code-smells-project` | Python/Flask | Monolito total — 4 arquivos na raiz, sem nenhuma separação em camadas | 30 | 8 / 4 / 10 / 8 | [Análise Manual](code-smells-project/README.md#análise-manual) · [relatório](code-smells-project/reports/audit-code-smells-project.md) |
| `ecommerce-api-legacy` | Node.js/Express | God File único (`AppManager.js` + `utils.js`) | 21 | 7 / 4 / 6 / 4 | [Análise Manual](ecommerce-api-legacy/README.md#análise-manual) · [relatório](ecommerce-api-legacy/reports/audit-ecommerce-api-legacy.md) |
| `task-manager-api` | Python/Flask | Parcialmente organizado — `models/`, `routes/`, `services/`, `utils/` já existiam, mas responsabilidades vazavam entre eles | 22 | 5 / 2 / 6 / 9 | [Análise Manual](task-manager-api/README.md#análise-manual) · [relatório](task-manager-api/reports/audit-task-manager-api.md) |

Os 3 projetos, propositalmente, representam 3 pontos diferentes de "quão organizado" um legado pode estar: nenhuma camada, uma única classe monstro, e camadas presentes mas mal usadas. Isso guiou diretamente o catálogo de anti-patterns da skill (abaixo) — cada padrão do catálogo mapeia para pelo menos um achado real observado em algum dos 3 projetos.

## Construção da Skill

### Decisões de design

`SKILL.md` (idêntico em `code-smells-project/.claude/skills/refactor-arch/`, `ecommerce-api-legacy/.claude/skills/refactor-arch/` e `task-manager-api/.claude/skills/refactor-arch/`) funciona como orquestrador de um workflow de **3 fases estritamente sequenciais** — nunca pula uma fase, e a fase N nunca re-deriva do zero o que a fase N-1 já apurou:

- Cada fase é despachada como um **subagente** dedicado, que recebe um briefing específico e só lê os arquivos de referência que aquela fase precisa (nunca os 5 de uma vez) — mantém o contexto de cada subagente pequeno e focado.
- O estado intermediário de cada fase persiste em `<projeto>/.refactor-arch/phase-{1,2,3}-*.md` — uma pasta de scratch dentro do próprio projeto-alvo, para sobreviver entre invocações de subagente sem misturar arquivos de trabalho com o entregável final (`reports/`, código refatorado).
- Entre a Fase 2 e a Fase 3 existe um **gate de confirmação humana obrigatório** (`SKILL.md:51-57`): a skill imprime o relatório de auditoria, pergunta explicitamente "Proceed with refactoring (Phase 3)? [y/n]" via `AskUserQuestion`, e o próprio `SKILL.md` proíbe tratar silêncio ou "julgamento próprio" como consentimento. Nenhum arquivo é modificado antes dessa confirmação.
- Cinco arquivos de referência em Markdown, cada um cobrindo exatamente uma das áreas de conhecimento exigidas:
  - `references/project-analysis.md` — heurísticas de detecção de linguagem/framework/banco/domínio (Fase 1).
  - `references/anti-pattern-catalog.md` — catálogo de anti-patterns com sinais de detecção e severidade (Fase 2).
  - `references/report-template.md` — formato exato do relatório de auditoria (Fase 2).
  - `references/architecture-guidelines.md` — regras do MVC alvo, incluindo uma seção dedicada a "adapting to a partially-organized project" (Fase 3).
  - `references/refactoring-playbook.md` — **12 padrões de transformação** com exemplos de código antes/depois (Fase 3) — acima do mínimo de 8 exigido.

### Anti-patterns incluídos no catálogo e por quê

O catálogo (`references/anti-pattern-catalog.md`) tem **20 entradas**, distribuídas pela escala fixa de severidade do desafio, e cada uma foi escolhida porque apareceu de fato em pelo menos um dos 3 projetos durante a análise manual:

- **CRITICAL (5):** SQL Injection via concatenação de string; credenciais/segredos hardcoded; God Class/God File; endpoint destrutivo/admin sem autenticação; hashing de senha caseiro ou fraco (MD5/SHA1/homegrown).
- **HIGH (4):** Fat Controller (lógica de negócio na camada de rotas); acoplamento forte sem injeção de dependência; estado global mutável; tokens de autenticação forjáveis/previsíveis.
- **MEDIUM (6):** consultas N+1; falta de validação de entrada na borda das rotas; ausência de log estruturado/tratamento centralizado de erros; falta de paginação; deletes que quebram integridade referencial; **uso de APIs deprecated** (com tabela de padrões concretos por stack — `datetime.utcnow()`, `app.run(debug=True)`, `new Buffer(...)`, `Model.query.get(id)` do SQLAlchemy legado, `body-parser` standalone no Express).
- **LOW (5):** código duplicado; magic numbers; nomenclatura ruim; código morto/imports não utilizados; tratamento de exceção genérico demais (`except:` nu).

A distribuição não é arbitrária: ela espelha a escala de severidade do próprio desafio (`README.md:21-28`) e a tabela de deprecated-APIs foi incluída porque o requisito da skill exige essa detecção explicitamente (`README.md:175`) — sem ela, o achado LOW "`datetime.utcnow()` deprecated" (presente nos 3 projetos) não teria uma categoria própria no catálogo.

### Garantia de agnosticismo de tecnologia

- **Detecção por evidência, não por nome hardcoded**: `project-analysis.md` detecta a stack por extensão de arquivo + parsing de manifest (`requirements.txt`/`package.json`), nunca assumindo nomes de arquivo específicos de um projeto.
- **Tabelas de inferência genéricas**: o mapeamento rota→domínio e a tabela de APIs deprecated cobrem exemplos tanto Python quanto Node lado a lado, em vez de assumir uma única linguagem.
- **Adaptação estrutural explícita**: `architecture-guidelines.md` adapta os nomes de pastas à convenção da stack (`views/` para rotas Flask vs. `routes/` para Express, por exemplo) e tem uma seção própria — "adapting to a partially-organized project" — para quando o projeto-alvo já tem alguma camada (o caso de `task-manager-api`).
- **Nota explícita anti-acoplamento no próprio `SKILL.md:72`**: "the reference files intentionally avoid hardcoding filenames or entity names from any one project."
- **Prova empírica**: a mesma pasta `.claude/skills/refactor-arch/`, sem uma única alteração, foi copiada para os 3 projetos e completou as 3 fases com sucesso nos 3 — um monolito Python total, um god-file Node, e um Python parcialmente organizado (ver seção "Resultados" abaixo).

### Desafios encontrados e como resolveu

- **Datetime deprecated vs. compatibilidade com dados já persistidos**: substituir `datetime.utcnow()` por `datetime.now(timezone.utc)` (a recomendação "óbvia") quebraria toda comparação de datas em `task-manager-api`, porque o SQLite/SQLAlchemy sempre grava/lê datetimes *naive* — comparar um valor tz-aware com um naive vindo do banco lança `TypeError`. Solução: um helper `utc_now()` que retorna um datetime naive-porém-UTC, eliminando a chamada deprecated sem quebrar as comparações existentes.
- **Decidir o que fica fora do escopo de uma única rodada de refatoração** (para não violar a exigência de preservar a superfície pública da API): em `code-smells-project`, a tarefa limitava o novo gate de autenticação apenas aos endpoints `/admin/*`, então `DELETE /produtos/<id>` permaneceu sem autenticação (a injeção de SQL foi corrigida e o delete virou soft-delete); a injeção de dependência via construtor foi julgada grande demais para a rodada e foi parcialmente resolvida encapsulando o global mutável em uma classe `DatabaseConnection`.
- **Adaptar a Fase 3 ao nível de organização prévio de cada projeto**: um monolito puro (`code-smells-project`) exigiu criar toda a árvore MVC do zero; um god-file único (`ecommerce-api-legacy`) exigiu extrair Model/Controller/Routes/Services de um único arquivo; um projeto já parcialmente organizado (`task-manager-api`) exigiu manter os nomes de pasta existentes (`models/`, `routes/`, `utils/`) e introduzir apenas as camadas que faltavam (`controllers/`, `middlewares/`), removendo a camada morta (`services/`) em vez de forçá-la a existir.
- **Projetos sem nenhum sistema de autenticação preexistente** (`ecommerce-api-legacy`, `task-manager-api`): a skill precisou *introduzir* um mecanismo de auth do zero (chave admin compartilhada num, JWT real assinado no outro) em vez de apenas corrigir um mecanismo existente — decisão documentada explicitamente nos relatórios de validação de cada projeto como "known deviation" intencional, não regressão.

## Resultados

### Resumo dos relatórios de auditoria (Fase 2 da skill)

| Projeto | Total | CRITICAL | HIGH | MEDIUM | LOW |
|---|---|---|---|---|---|
| code-smells-project | 30 | 8 | 4 | 10 | 8 |
| ecommerce-api-legacy | 21 | 7 | 4 | 6 | 4 |
| task-manager-api | 22 | 5 | 2 | 6 | 9 |

Os 3 relatórios batem exatamente com a análise manual documentada na seção "Análise Manual" de cada projeto — a skill encontrou o mesmo conjunto de problemas de forma automatizada.

### Comparação antes/depois da estrutura

**code-smells-project** — de um monolito de 4 arquivos na raiz (`app.py`, `controllers.py`, `models.py`, `database.py`) para:
```
src/{config,database,models,controllers,views,middlewares,services}/ + app.py (composition root)
```

**ecommerce-api-legacy** — de 3 arquivos planos (`src/app.js`, `src/AppManager.js`, `src/utils.js`) para:
```
src/{config,models,controllers,routes,middlewares,services,utils}/ + app.js (composition root)
```

**task-manager-api** — de uma organização parcial (`models/`, `routes/`, `services/` só com código morto, `utils/`) para:
```
{config,models,controllers,routes,middlewares,utils}/ + app.py (composition root) — services/ removido (só continha código morto)
```

Detalhe completo de cada árvore, com anotações do que foi criado/removido, está em `.refactor-arch/phase-3-validation.md` de cada projeto.

### Checklist de validação preenchida

**code-smells-project**
```markdown
### Fase 1 — Análise
- [x] Linguagem detectada corretamente (Python)
- [x] Framework detectado corretamente (Flask 3.1.1)
- [x] Domínio da aplicação descrito corretamente (E-commerce: produtos, pedidos, usuários)
- [x] Número de arquivos analisados condiz com a realidade (4 arquivos)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados (30 findings)
- [x] Detecção de APIs deprecated incluída (Flask debug mode em produção)
- [x] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC
- [x] Configuração extraída para módulo de config (sem hardcoded)
- [x] Models criados para abstrair dados (um por entidade)
- [x] Views/Routes separadas para roteamento (Flask Blueprints)
- [x] Controllers concentram o fluxo da aplicação
- [x] Error handling centralizado (`middlewares/error_handler.py`)
- [x] Entry point claro (`src/app.py`)
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente (19 rotas verificadas via curl)
```

**ecommerce-api-legacy**
```markdown
### Fase 1 — Análise
- [x] Linguagem detectada corretamente (Node.js)
- [x] Framework detectado corretamente (Express ^4.18.2)
- [x] Domínio da aplicação descrito corretamente (LMS com fluxo de checkout)
- [x] Número de arquivos analisados condiz com a realidade (3 arquivos em src/)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados (21 findings)
- [ ] Detecção de APIs deprecated incluída — não aplicável: nenhum padrão deprecated (Buffer legado, body-parser standalone etc.) foi encontrado neste código
- [x] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC (convenção Node/Express)
- [x] Configuração extraída para módulo de config (sem hardcoded)
- [x] Models criados para abstrair dados (5 arquivos, um por entidade)
- [x] Views/Routes separadas para roteamento
- [x] Controllers concentram o fluxo da aplicação
- [x] Error handling centralizado (`middlewares/errorHandler.js`)
- [x] Entry point claro (`src/app.js`)
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente (happy-path idêntico, 9 cenários de curl verificados)
```

**task-manager-api**
```markdown
### Fase 1 — Análise
- [x] Linguagem detectada corretamente (Python)
- [x] Framework detectado corretamente (Flask 3.0.0 + Flask-SQLAlchemy 3.1.1)
- [x] Domínio da aplicação descrito corretamente (Task Manager: tasks/users/categories)
- [x] Número de arquivos analisados condiz com a realidade (15 arquivos .py + requirements.txt)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados (22 findings)
- [x] Detecção de APIs deprecated incluída (`datetime.utcnow()`)
- [x] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC
- [x] Configuração extraída para módulo de config (sem hardcoded, falha no boot se `SECRET_KEY` ausente)
- [x] Models criados/mantidos para abstrair dados
- [x] Views/Routes separadas para roteamento (`routes/`, incl. novo `category_routes.py`)
- [x] Controllers concentram o fluxo da aplicação (camada nova — não existia)
- [x] Error handling centralizado (`middlewares/error_handler.py`)
- [x] Entry point claro (`app.py`)
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente (~45 requisições verificadas via curl, todas PASS)
```

### Logs das aplicações rodando após a refatoração

Não há capturas de tela (a skill roda inteiramente via CLI); a evidência de execução é o log de boot + as respostas HTTP reais, capturadas em `.refactor-arch/phase-3-validation.md` de cada projeto. Trecho do boot do `task-manager-api`:

```
$ source venv/bin/activate && python3 app.py
 * Serving Flask app 'app'
 * Debug mode: off
2026-08-10 09:20:29,309 INFO werkzeug: WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
2026-08-10 09:21:27,121 INFO controllers.task_controller: Task updated: id=11
2026-08-10 09:21:27,121 INFO werkzeug: 127.0.0.1 - - [10/Aug/2026 09:21:27] "PUT /tasks/11 HTTP/1.1" 200 -
2026-08-10 09:21:27,137 INFO werkzeug: 127.0.0.1 - - [10/Aug/2026 09:21:27] "DELETE /tasks/1 HTTP/1.1" 401 -
```

Trecho do `ecommerce-api-legacy` (log estruturado em JSON, substituindo os antigos `console.log`):
```
{"level":"info","message":"Database seeded with initial data","timestamp":"2026-08-09T17:51:34.240Z"}
{"level":"info","message":"Frankenstein LMS rodando na porta 3000...","timestamp":"2026-08-09T17:51:34.243Z"}
{"level":"warn","message":"Credenciais inválidas",...,"statusCode":401,"path":"/api/checkout"}
```

Trecho do `code-smells-project`:
```
==================================================
SERVIDOR INICIADO
Rodando em http://localhost:5050
==================================================
 * Serving Flask app 'app'
 * Debug mode: off
```

Nenhum endpoint regrediu em nenhum dos 3 projetos — as únicas mudanças de comportamento observadas são as intencionais (respostas passam a exigir autenticação onde antes eram públicas, e a resposta de erro passa a ser JSON estruturado em vez de HTML/texto ad-hoc).

### Observações sobre o comportamento da skill em stacks diferentes

- A mesma cópia da skill, sem alterações, completou as 3 fases com sucesso em Python/Flask (2 projetos) e Node.js/Express (1 projeto).
- O fator que mais influenciou o esforço da Fase 3 não foi a linguagem, e sim o **nível de organização prévio**: o monolito total (`code-smells-project`) e o god-file (`ecommerce-api-legacy`) exigiram criar toda a árvore de camadas do zero; o projeto parcialmente organizado (`task-manager-api`) exigiu um refactor mais cirúrgico — manter nomes de pasta existentes, remover uma camada morta (`services/`) e só então introduzir o que faltava.
- Nenhum dos 3 projetos tinha um sistema de autenticação real antes da refatoração — a skill precisou desenhar (não só corrigir) um mecanismo de auth em 2 dos 3 casos, usando o padrão mais simples que resolvia o achado CRITICAL correspondente em cada stack (chave de admin compartilhada via header no Node; JWT assinado no Python).

## Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado (`claude` disponível no `PATH`).
- Por projeto:
  - `code-smells-project/` e `task-manager-api/` (Python/Flask): Python 3.11+, `pip`, `venv`.
  - `ecommerce-api-legacy/` (Node.js/Express): Node.js + `npm`.
- Nenhuma variável de ambiente é obrigatória para rodar a skill (ela cria/valida `.env` a partir do `.env.example` de cada projeto durante a Fase 3, quando necessário).

### Comandos para executar a skill em cada projeto

A skill já está commitada em `.claude/skills/refactor-arch/` dentro de cada um dos 3 projetos — não é necessário copiá-la manualmente.

```bash
# Projeto 1 — code-smells-project (Python/Flask)
cd code-smells-project
claude "/refactor-arch"

# Projeto 2 — ecommerce-api-legacy (Node.js/Express)
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3 — task-manager-api (Python/Flask, parcialmente organizado)
cd ../task-manager-api
claude "/refactor-arch"
```

Em cada execução, a skill imprime o resumo da Fase 1, depois o relatório completo da Fase 2 e pausa com `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` — responda `y` para prosseguir com a Fase 3, ou `n`/ajuste os arquivos de referência e execute novamente se os findings não baterem com o esperado.

### Como validar que a refatoração funcionou

1. **Saída da própria skill**: ao final da Fase 3, a skill imprime a nova árvore de diretórios e confirma "Application boots without errors" + "All endpoints respond correctly" — se algo falhar, ela reporta o que quebrou em vez de declarar sucesso.
2. **Subir a aplicação manualmente** seguindo a seção "Como rodar" do `README.md` de cada projeto (ex.: `python src/app.py` em `code-smells-project`, `npm start` em `ecommerce-api-legacy`, `python app.py` em `task-manager-api`) e testar os endpoints originais com `curl` — os exemplos completos (incluindo casos de borda) estão nas tabelas endpoint-a-endpoint de `.refactor-arch/phase-3-validation.md` de cada projeto.
3. **Comparar relatório vs. correção**: cruzar `reports/audit-<projeto>.md` (achados) com `.refactor-arch/phase-3-validation.md` (mapeamento achado → correção) e confirmar que todo item CRITICAL/HIGH aparece corrigido — ou, quando não corrigido, com uma nota de escopo explícita (como o caso de `DELETE /produtos/<id>` em `code-smells-project`).
4. **Checklist de validação** — usar o checklist preenchido na seção "Resultados" acima como referência do que já foi verificado; para uma nova rodada da skill (ex.: após ajustar um arquivo de referência), reexecutar o checklist do zero.