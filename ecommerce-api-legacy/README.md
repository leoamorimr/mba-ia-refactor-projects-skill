# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Configuração via variáveis de ambiente (veja `.env.example`). `ADMIN_API_KEY` é obrigatória — a aplicação falha ao subir (com um erro claro) se essa variável não estiver definida, seja via `.env` local (carregado automaticamente por `dotenv`) ou via variável de ambiente real em produção.

## Autenticação de administrador

O relatório financeiro (`GET /api/admin/financial-report`) e a exclusão de usuário (`DELETE /api/users/:id`) exigem um header `x-admin-key` com o valor de `ADMIN_API_KEY`. Requisições sem esse header, ou com um valor incorreto, recebem `401 Unauthorized`.

```bash
curl -H "x-admin-key: <set-a-strong-admin-key>" http://localhost:3000/api/admin/financial-report
```

Exemplos de requisições estão em `api.http`.

## Análise Manual

Antes da refatoração, o código legado (`src/AppManager.js` e `src/utils.js`, um único
arquivo "god file" sem nenhuma separação em camadas) foi auditado manualmente. Foram
identificados **21 achados** — 7 CRITICAL, 4 HIGH, 6 MEDIUM, 4 LOW. O relatório completo,
com descrição, impacto e recomendação de cada item, está em
[`reports/audit-ecommerce-api-legacy.md`](reports/audit-ecommerce-api-legacy.md).

| Severidade | Achado                                                                          | Local original          |
| ---------- | ------------------------------------------------------------------------------- | ----------------------- |
| CRITICAL   | God Class / God File — toda a aplicação em uma única classe                     | `AppManager.js:4-139`   |
| CRITICAL   | Autenticação quebrada — senha nunca verificada no checkout de usuário existente | `AppManager.js:40-76`   |
| CRITICAL   | Dado sensível logado em texto puro (cartão + chave do gateway de pagamento)     | `AppManager.js:45`      |
| CRITICAL   | Endpoint de admin sem autenticação (`GET /api/admin/financial-report`)          | `AppManager.js:80-129`  |
| CRITICAL   | Endpoint destrutivo sem autenticação (`DELETE /api/users/:id`)                  | `AppManager.js:131-137` |
| CRITICAL   | Credenciais/segredos hardcoded no código-fonte                                  | `utils.js:1-7`          |
| CRITICAL   | "Hash" de senha caseiro e reversível (`badCrypto`)                              | `utils.js:17-23`        |
| HIGH       | Acoplamento forte / ausência de injeção de dependência                          | `AppManager.js:5-8`     |
| HIGH       | Controller inchado — lógica de checkout no handler da rota                      | `AppManager.js:28-78`   |
| HIGH       | Controller inchado — agregação do relatório financeiro no handler da rota       | `AppManager.js:80-129`  |
| HIGH       | Estado global mutável (`globalCache`/`totalRevenue`)                            | `utils.js:9-15`         |
| MEDIUM     | Sem tratamento centralizado de erros / sem log estruturado                      | `AppManager.js:28-137`  |
| MEDIUM     | Falta de validação de entrada — payload do checkout                             | `AppManager.js:29-35`   |
| MEDIUM     | Falta de paginação no relatório financeiro                                      | `AppManager.js:80-129`  |
| MEDIUM     | Consultas N+1 no relatório financeiro                                           | `AppManager.js:83-126`  |
| MEDIUM     | Falta de validação de entrada — parâmetro `id` do delete                        | `AppManager.js:131-133` |
| MEDIUM     | Delete quebra integridade referencial (deixa `enrollments`/`payments` órfãos)   | `AppManager.js:131-137` |
| LOW        | Código morto / import não utilizado (`totalRevenue`)                            | `AppManager.js:2`       |
| LOW        | Nomenclatura pouco descritiva (`u`, `e`, `p`, `cid`, `cc`)                      | `AppManager.js:29-33`   |
| LOW        | Número mágico — regra de aprovação de cartão (`cc.startsWith("4")`)             | `AppManager.js:46`      |
| LOW        | Números mágicos nas constantes do `badCrypto`                                   | `utils.js:17-23`        |

Todos os 21 achados foram corrigidos na refatoração para a estrutura MVC atual (ver
histórico de commits e `.refactor-arch/phase-3-validation.md` para o mapeamento
achado → correção e a validação end-to-end de cada endpoint).

## Construção da Skill

**Decisões de design.** A mesma skill `refactor-arch` de `code-smells-project` (SKILL.md idêntico, copiado sem alterações para `.claude/skills/refactor-arch/`) orquestra o workflow de 3 fases estritamente sequenciais, cada uma despachada como um subagente dedicado que lê só os arquivos de referência daquela fase. O estado intermediário persiste em `.refactor-arch/phase-{1,2,3}-*.md`. Entre a Fase 2 e a Fase 3 há um gate de confirmação humana obrigatório (`SKILL.md:51-57`) — a skill imprime o relatório de auditoria e pede confirmação explícita via `AskUserQuestion` antes de tocar em qualquer arquivo.

**Anti-patterns incluídos e por quê.** Dos 20 anti-patterns do catálogo, os que mais pesaram neste projeto foram os 7 achados CRITICAL: God Class/God File (`AppManager.js` concentrando toda a aplicação), autenticação quebrada (senha nunca verificada no checkout de usuário existente), dado sensível (cartão + chave de gateway) logado em texto puro, dois endpoints administrativos sem autenticação e um "hash" de senha caseiro e reversível (`badCrypto`). Foi este projeto que motivou a entrada específica de catálogo para hashing de senha caseiro/fraco (MD5/SHA1/homegrown) — o `badCrypto` daqui é o exemplo canônico.

**Garantia de agnosticismo de tecnologia.** Este projeto foi o teste decisivo de que a skill funciona fora do Python: a mesma pasta `.claude/skills/refactor-arch/`, sem uma única linha alterada, foi copiada de `code-smells-project/` (Python/Flask) para aqui (Node.js/Express) e completou as 3 fases com sucesso. Isso só foi possível porque `references/project-analysis.md` detecta a stack por evidência (parsing de `package.json` + `require('express')`, em vez de assumir Python) e `references/architecture-guidelines.md` adapta os nomes de pastas à convenção Node (`routes/` em vez de `views/`).

**Desafios encontrados.**
- Este era o único dos 3 projetos sem nenhum sistema de autenticação preexistente — a skill precisou *desenhar* um mecanismo do zero (chave de admin compartilhada via header `x-admin-key`) em vez de apenas corrigir um mecanismo existente, decisão documentada como "known deviation" intencional em `.refactor-arch/phase-3-validation.md`, não como regressão.
- Extrair Model/Controller/Routes/Services de um único god-file (`AppManager.js`, 139 linhas concentrando conexão de banco, schema, seed e as 3 rotas com lógica de negócio inline) exigiu decidir os limites de cada camada nova do zero, sem nenhuma estrutura prévia para guiar a divisão.
- Preservar a superfície pública da API (mesmas rotas, métodos e formatos de resposta do caminho feliz) enquanto se corrigiam bugs de segurança que dependiam de mudar o comportamento de erro (ex.: checkout com senha errada, antes aceito silenciosamente, agora rejeitado com 401) — resolvido documentando essas mudanças de comportamento como correções intencionais, não quebras de contrato.

## Resultados

**Resumo da auditoria (Fase 2 da skill):** 21 findings — 7 CRITICAL / 4 HIGH / 6 MEDIUM / 4 LOW ([relatório completo](reports/audit-ecommerce-api-legacy.md)), batendo exatamente com a análise manual documentada acima.

**Antes/depois da estrutura:**
```
# Antes — 3 arquivos planos, sem camadas
src/app.js  src/AppManager.js  src/utils.js

# Depois — MVC completo (convenção Node/Express)
src/
├── app.js                     # composition root
├── config/                    # index.js (settings), database.js (conexão sqlite3)
├── models/                    # userModel, courseModel, enrollmentModel, paymentModel, auditLogModel
├── controllers/               # checkoutController, financialReportController, userController
├── routes/                    # index.js, checkoutRoutes, adminRoutes, userRoutes
├── middlewares/                # auth.js, errorHandler.js, validators.js
└── services/                  # paymentService, passwordService, cacheService
```

**Checklist de validação preenchida:**
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

**Log de boot após a refatoração:**
```
$ npm start
> node src/app.js

{"level":"info","message":"Database seeded with initial data","timestamp":"2026-08-09T17:51:34.240Z"}
{"level":"info","message":"Frankenstein LMS rodando na porta 3000...","timestamp":"2026-08-09T17:51:34.243Z"}
```
Nenhum secret/PII apareceu no log durante os testes (apenas o cartão mascarado, `**** **** **** 4444`) — confirmando a correção do achado de dado sensível logado em texto puro. Os 9 cenários de validação end-to-end (checkout novo/existente/senha errada, admin sem/com credenciais, delete sem/com credenciais, sanity check de integridade referencial pós-delete) estão detalhados em [`.refactor-arch/phase-3-validation.md`](.refactor-arch/phase-3-validation.md).

**Observações.** Foi o único dos 3 projetos em Node.js/Express, e o único sem pistas prévias de separação em camadas (nem mesmo pastas vazias) — a skill precisou inferir a divisão MVC inteiramente a partir do comportamento observado no código, não de uma estrutura já sugerida. O esforço de refatoração foi comparável ao de `code-smells-project` (criar tudo do zero), reforçando que o fator decisivo para o esforço da Fase 3 é o nível de organização prévio, não a linguagem.

## Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado (`claude` disponível no `PATH`).
- Node.js + `npm`.

### Comando para executar a skill

A skill (cópia idêntica da usada em `code-smells-project/`) já está commitada em `.claude/skills/refactor-arch/`.

```bash
cd ecommerce-api-legacy
claude "/refactor-arch"
```

A skill imprime o resumo da Fase 1, depois o relatório completo da Fase 2, e pausa com `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` — responda `y` para prosseguir com a Fase 3.

### Como validar que a refatoração funcionou

1. **Saída da própria skill** — ao final da Fase 3, ela confirma que a aplicação sobe sem erros e que todos os endpoints respondem corretamente.
2. **Subir a aplicação manualmente** (`npm install && npm start`) e testar os 3 endpoints originais (`POST /api/checkout`, `GET /api/admin/financial-report`, `DELETE /api/users/:id`) com `curl` — exemplos completos, incluindo os cenários negativos (senha errada, sem header de admin), em [`.refactor-arch/phase-3-validation.md`](.refactor-arch/phase-3-validation.md).
3. **Cruzar achado vs. correção** — comparar [`reports/audit-ecommerce-api-legacy.md`](reports/audit-ecommerce-api-legacy.md) com `.refactor-arch/phase-3-validation.md` e confirmar que os 21 achados aparecem corrigidos.
