# task-manager-api

API de Task Manager em Python/Flask. Estrutura em camadas MVC: `models/` (dados), `controllers/` (regras de negócio), `routes/` (HTTP), `middlewares/` (auth + tratamento de erros), `config/` (variáveis de ambiente) e `utils/` (validação/formatação compartilhada).

## Como rodar

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edite .env e defina um SECRET_KEY real (ex: python3 -c "import secrets; print(secrets.token_hex(32))")

python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` por padrão (host/porta/debug configuráveis via `.env`). O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**, caso contrário os endpoints vão retornar listas vazias.

Rotas de escrita (`POST`/`PUT`/`DELETE` em `/tasks`, `/users` e `/categories`) exigem autenticação: faça `POST /login` com um usuário existente para obter um token JWT e envie-o como `Authorization: Bearer <token>`.

## Análise Manual

Antes da refatoração, o código legado (`app.py`, `models/`, `routes/`, `services/`,
`utils/`) já tinha alguma separação em camadas, mas as responsabilidades vazavam
entre elas — rotas reimplementavam lógica de serialização/validação que já existia
nos models e em `utils/helpers.py`, e um serviço inteiro (`NotificationService`)
existia sem nunca ser usado. Foram identificados **22 achados** — 5 CRITICAL, 2
HIGH, 6 MEDIUM, 9 LOW. O relatório completo, com descrição, impacto e recomendação
de cada item, está em
[`reports/audit-task-manager-api.md`](reports/audit-task-manager-api.md).

| Severidade | Achado                                                                          | Local original                                                                    |
| ---------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| CRITICAL   | Credenciais/segredos hardcoded — Flask `SECRET_KEY`                              | `app.py:13`                                                                          |
| CRITICAL   | Hash de senha exposto nas respostas da API (`User.to_dict()`)                    | `models/user.py:16-25`                                                              |
| CRITICAL   | Hash de senha caseiro e fraco (MD5, sem salt)                                    | `models/user.py:27-32`                                                              |
| CRITICAL   | Endpoints destrutivos sem autenticação (`DELETE` de categories/tasks/users)      | `routes/report_routes.py:211-223`, `routes/task_routes.py:225-238`, `routes/user_routes.py:134-151` |
| CRITICAL   | Credenciais/segredos hardcoded — senha SMTP no `NotificationService`             | `services/notification_service.py:7-10`                                             |
| HIGH       | Controller inchado — lógica de negócio na camada de rotas                       | `routes/report_routes.py:12-101`, `routes/task_routes.py:11-63,273-299`             |
| HIGH       | Tokens de autenticação forjáveis/previsíveis (`'fake-jwt-token-' + id`)          | `routes/user_routes.py:210`                                                         |
| MEDIUM     | Modo debug do Flask habilitado no entrypoint, bind em `0.0.0.0`                  | `app.py:34`                                                                          |
| MEDIUM     | Falta de validação de entrada na borda das rotas                                | `routes/report_routes.py:190-209`, `routes/task_routes.py:113-114,181-184`          |
| MEDIUM     | Delete de categoria quebra integridade referencial (tasks órfãs)                | `routes/report_routes.py:211-223`                                                   |
| MEDIUM     | Falta de paginação nos endpoints de listagem                                    | `routes/task_routes.py:14`, `routes/user_routes.py:12`, `routes/report_routes.py:159` |
| MEDIUM     | Consultas N+1 (tasks, relatório por usuário, contagem por categoria)            | `routes/task_routes.py:41-57`                                                       |
| MEDIUM     | Sem log estruturado / sem tratamento centralizado de erros                      | `routes/task_routes.py:146-154`                                                     |
| LOW        | API deprecated — `datetime.utcnow()` usado em todo o projeto                    | `models/task.py:15-16` (e ~15 outros locais)                                        |
| LOW        | Dependências mortas em `requirements.txt` (`marshmallow`, `requests`, `python-dotenv`) | `requirements.txt:4-6`                                                         |
| LOW        | Código duplicado — checagem de overdue reimplementada 6 vezes                   | `routes/report_routes.py:34-37` (e outros)                                          |
| LOW        | Nomenclatura pouco descritiva (`u`, `t`, `c`, `p`)                               | `routes/report_routes.py:53-68`                                                     |
| LOW        | Código morto / imports não utilizados (`json`, `os`, `sys`, `time`, `hashlib`)   | `routes/task_routes.py:7`                                                           |
| LOW        | Tratamento de exceção genérico demais (`except:` nu)                            | `routes/task_routes.py:62-63`                                                       |
| LOW        | Números mágicos — limites de título e faixa de prioridade                       | `routes/task_routes.py:96-100`                                                      |
| LOW        | Código morto / abstração não utilizada — `NotificationService`                  | `services/notification_service.py:1-48`                                             |
| LOW        | Código morto / abstrações não utilizadas em `utils/helpers.py`                  | `utils/helpers.py:9-116`                                                            |

Os 22 achados foram corrigidos na refatoração para a estrutura MVC atual (ver
histórico de commits e `.refactor-arch/phase-3-validation.md` para o mapeamento
achado → correção e a validação end-to-end de cada endpoint).

## Construção da Skill

**Decisões de design.** A mesma skill `refactor-arch` usada em `code-smells-project/` e `ecommerce-api-legacy/` (SKILL.md idêntico, copiado sem alterações para `.claude/skills/refactor-arch/`) orquestra o workflow de 3 fases estritamente sequenciais, cada uma despachada como um subagente dedicado que lê só os arquivos de referência daquela fase. O estado intermediário persiste em `.refactor-arch/phase-{1,2,3}-*.md`. Entre a Fase 2 e a Fase 3 há um gate de confirmação humana obrigatório (`SKILL.md:51-57`) — a skill imprime o relatório de auditoria e pede confirmação explícita via `AskUserQuestion` antes de tocar em qualquer arquivo.

**Anti-patterns incluídos e por quê.** Este foi o projeto que mais exercitou a categoria MEDIUM/LOW do catálogo (`references/anti-pattern-catalog.md`): código morto/abstrações não usadas (o `NotificationService` inteiro, e boa parte de `utils/helpers.py`), N+1 queries em `/tasks`, `/users` e `/reports/summary`, tokens de autenticação forjáveis (`'fake-jwt-token-' + id`) e a entrada de **API deprecated** (`datetime.utcnow()`, usado em ~15 locais) — exatamente o tipo de achado que só aparece em um projeto com alguma maturidade prévia de código, ao contrário do monolito cru de `code-smells-project`. O achado CRITICAL de hash de senha exposto em `User.to_dict()` também motivou uma entrada própria no catálogo (vazamento de dado sensível na serialização, distinto de "hash fraco").

**Garantia de agnosticismo de tecnologia.** Apesar de ser Python/Flask como `code-smells-project`, este projeto testou uma dimensão diferente de agnosticismo: lidar com um projeto **parcialmente organizado**. `references/architecture-guidelines.md` tem uma seção própria — "adapting to a partially-organized project" — usada aqui para manter os nomes de pasta já existentes (`models/`, `routes/`, `utils/`) e introduzir apenas as camadas que faltavam (`controllers/`, `middlewares/`), em vez de recriar a árvore do zero como nos outros dois projetos. A mesma cópia da skill, sem alterações, soube diferenciar "sem nenhuma camada" (os outros 2 projetos) de "camadas presentes mas mal usadas" (este).

**Desafios encontrados.**
- **Datetime deprecated vs. compatibilidade com dados já persistidos**: substituir `datetime.utcnow()` pela recomendação "óbvia" (`datetime.now(timezone.utc)`) quebraria toda comparação de datas, porque o SQLite/SQLAlchemy sempre grava/lê datetimes *naive* — comparar um valor tz-aware com um naive vindo do banco lança `TypeError`. Solução: um helper `utc_now()` que retorna um datetime naive-porém-UTC, eliminando a chamada deprecated sem quebrar `is_overdue()` e os relatórios.
- **Decidir se uma camada morta deveria ser reaproveitada ou removida**: `services/` só continha um `NotificationService` nunca importado em nenhum lugar, com uma senha SMTP hardcoded (achado CRITICAL). Em vez de apenas mover o secret para uma env var, a decisão foi deletar o arquivo e a pasta inteira — resolve o achado na raiz, em vez de só relocá-lo, e evita desenhar uma feature de notificação fora do escopo deste refactor.
- **Nenhum sistema de autenticação real preexistente**: os tokens eram literais forjáveis (`'fake-jwt-token-' + id`). A skill precisou introduzir JWT real assinado (PyJWT, HS256) do zero, não apenas substituir uma verificação já existente.

## Resultados

**Resumo da auditoria (Fase 2 da skill):** 22 findings — 5 CRITICAL / 2 HIGH / 6 MEDIUM / 9 LOW ([relatório completo](reports/audit-task-manager-api.md)), batendo exatamente com a análise manual documentada acima.

**Antes/depois da estrutura:**
```
# Antes — organização parcial, responsabilidades vazando entre camadas
app.py  database.py  seed.py
models/ (task, user, category)
routes/ (task_routes, user_routes, report_routes)
services/ (só NotificationService, código morto)
utils/ (helpers.py com abstrações não usadas)

# Depois — MVC completo
app.py                      # composition root
config/settings.py          # env vars, falha no boot se SECRET_KEY ausente
models/                     # task.py, user.py, category.py
controllers/                # NEW — task_, user_, category_, report_controller.py
routes/                     # task_, user_, category_ (NEW), report_routes.py
middlewares/                # NEW — auth.py (JWT real), error_handler.py
utils/helpers.py            # limpo — só o que é de fato importado/usado
# services/ removido — só continha código morto
```

**Checklist de validação preenchida:**
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

**Log de boot após a refatoração:**
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
Todas as ~45 requisições de validação (incluindo os campos que passaram a exigir `Authorization: Bearer <token>` e a remoção do campo `password` de toda resposta) retornaram `PASS`. Tabela endpoint-a-endpoint completa (antes/depois) em [`.refactor-arch/phase-3-validation.md`](.refactor-arch/phase-3-validation.md).

**Observações.** Este foi o projeto onde a Fase 3 exigiu o refactor mais cirúrgico dos 3: em vez de criar a árvore MVC do zero (como em `code-smells-project` e `ecommerce-api-legacy`), a skill manteve os nomes de pasta existentes, removeu uma camada morta (`services/`) e só então introduziu o que faltava (`controllers/`, `middlewares/`) — confirmando que o nível de organização prévio, não a linguagem, é o que mais influencia o esforço de refatoração.

## Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado (`claude` disponível no `PATH`).
- Python 3.11+, `pip`, `venv`.

### Comando para executar a skill

A skill (cópia idêntica da usada em `code-smells-project/` e `ecommerce-api-legacy/`) já está commitada em `.claude/skills/refactor-arch/`.

```bash
cd task-manager-api
claude "/refactor-arch"
```

A skill imprime o resumo da Fase 1, depois o relatório completo da Fase 2, e pausa com `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` — responda `y` para prosseguir com a Fase 3.

### Como validar que a refatoração funcionou

1. **Saída da própria skill** — ao final da Fase 3, ela confirma que a aplicação sobe sem erros e que todos os endpoints respondem corretamente.
2. **Subir a aplicação manualmente** seguindo a seção "Como rodar" acima (`python seed.py && python app.py`) e testar os endpoints com `curl`, incluindo obter um token via `POST /login` para as rotas de escrita — exemplos completos em [`.refactor-arch/phase-3-validation.md`](.refactor-arch/phase-3-validation.md).
3. **Cruzar achado vs. correção** — comparar [`reports/audit-task-manager-api.md`](reports/audit-task-manager-api.md) com `.refactor-arch/phase-3-validation.md` e confirmar que os 22 achados aparecem corrigidos.
