# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Estrutura

O projeto segue um layout MVC (`src/config`, `src/models`, `src/controllers`,
`src/views`, `src/middlewares`, `src/services`, `src/database`), com
`src/app.py` como composition root.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # ajuste os valores conforme necessário
python src/app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é
criado automaticamente no primeiro boot, já com produtos e usuários de
exemplo (senhas já armazenadas com hash).

## Variáveis de ambiente

| Variável       | Obrigatória | Descrição                                             |
|----------------|:-----------:|--------------------------------------------------------|
| `SECRET_KEY`   | recomendada | Chave de assinatura de sessão do Flask. Sem ela, uma chave aleatória é gerada a cada boot (não persiste entre reinícios). |
| `FLASK_DEBUG`  | não         | `true`/`false` (padrão `false`). Nunca usar `true` em produção. |
| `DB_PATH`      | não         | Caminho do arquivo SQLite (padrão `loja.db`).           |
| `ADMIN_TOKEN`  | sim, para usar `/admin/*` | Token exigido no header `X-Admin-Token` pelos endpoints administrativos. Sem ele, `/admin/*` fica inacessível. |
| `HOST`/`PORT`  | não         | Endereço/porta do servidor (padrão `0.0.0.0:5000`).     |

## Análise Manual

Antes da refatoração, o código legado (`app.py`, `controllers.py`, `models.py` e
`database.py`, sem nenhuma separação em camadas) foi auditado manualmente. Foram
identificados **30 achados** — 8 CRITICAL, 4 HIGH, 10 MEDIUM, 8 LOW. O relatório
completo, com descrição, impacto e recomendação de cada item, está em
[`reports/audit-code-smells-project.md`](reports/audit-code-smells-project.md).

| Severidade | Achado                                                                          | Local original                                  |
| ---------- | -------------------------------------------------------------------------------- | ------------------------------------------------ |
| CRITICAL   | Credenciais/segredos hardcoded (`SECRET_KEY`)                                    | `app.py:7`                                        |
| CRITICAL   | Endpoint destrutivo sem autenticação (`POST /admin/reset-db`)                    | `app.py:47-57`                                    |
| CRITICAL   | Endpoint sem autenticação com console SQL aberto (`POST /admin/query`)           | `app.py:59-78`                                    |
| CRITICAL   | Endpoint destrutivo sem autenticação (`DELETE /produtos/<id>`)                   | `controllers.py:98-109`                           |
| CRITICAL   | Segredo e config interna vazados em `/health`                                    | `controllers.py:264-292`                          |
| CRITICAL   | God Class / God File — todo o acesso a dados de 4 domínios em um único arquivo   | `models.py:1-314`                                 |
| CRITICAL   | SQL Injection via concatenação de string (praticamente todas as queries)         | `models.py:28-299`                                |
| CRITICAL   | Senha em texto puro — sem hashing, nem no cadastro nem no login                  | `models.py:105-131`                               |
| HIGH       | Controller inchado — envio de notificação (print) no handler de criar pedido    | `controllers.py:188-220`                          |
| HIGH       | Controller inchado — regra de transição de status e "restauração" falsa de estoque | `controllers.py:237-255`                       |
| HIGH       | Estado global mutável (`db_connection`)                                          | `database.py:4-11`                                |
| HIGH       | Acoplamento forte / ausência de injeção de dependência                           | `models.py:1-314`                                 |
| MEDIUM     | Modo debug do Flask habilitado no entrypoint                                     | `app.py:8,88`                                     |
| MEDIUM     | Sem tratamento centralizado de erros / sem log estruturado                       | `controllers.py:1-292`                            |
| MEDIUM     | Falta de validação de entrada — `atualizar_produto` mais permissivo que criar    | `controllers.py:64-96`                            |
| MEDIUM     | Falta de validação de entrada — cadastro de usuário (email/senha)                | `controllers.py:146-165`                          |
| MEDIUM     | Falta de validação de entrada — itens do pedido (`quantidade` negativa)          | `controllers.py:188-220`                          |
| MEDIUM     | Falta de paginação nos endpoints de listagem                                     | `models.py:4-22,72-87,203-233,285-314`            |
| MEDIUM     | Delete quebra integridade referencial (produto deletado deixa `itens_pedido` órfãos) | `models.py:65-70`                             |
| MEDIUM     | Consultas N+1 na criação de pedido                                               | `models.py:133-169`                               |
| MEDIUM     | Consultas N+1 no histórico de pedidos por usuário                                | `models.py:171-201`                               |
| MEDIUM     | Consultas N+1 na listagem geral de pedidos                                       | `models.py:203-233`                               |
| LOW        | Tratamento de exceção genérico demais (`except Exception`)                       | `controllers.py:10-12`                            |
| LOW        | Código duplicado — validação de campos entre criar/atualizar produto             | `controllers.py:24-96`                            |
| LOW        | Números mágicos — limites de tamanho do nome do produto                          | `controllers.py:47-50`                            |
| LOW        | Código morto / import não utilizado (`os`)                                       | `database.py:2`                                   |
| LOW        | Código morto / import não utilizado (`sqlite3`)                                  | `models.py:2`                                     |
| LOW        | Código duplicado — listagem de pedidos por usuário vs. geral                     | `models.py:171-233`                               |
| LOW        | Nomenclatura pouco descritiva (`cursor2`, `cursor3`)                             | `models.py:187-199,219-231`                       |
| LOW        | Números mágicos — faixas de desconto do relatório de vendas                      | `models.py:256-262`                               |

Os 30 achados foram corrigidos na refatoração para a estrutura MVC atual (ver
histórico de commits e `.refactor-arch/phase-3-validation.md` para o mapeamento
achado → correção e a validação end-to-end de cada endpoint): **30/30**.

O último item, que havia ficado fora do escopo de uma rodada anterior por
decisão explícita — **injeção de dependência via construtor** — foi
concluído numa rodada seguinte: cada módulo de modelo virou uma classe de
repositório (`ProductRepository`, `UserRepository`, `OrderRepository`) que
recebe o `DatabaseConnection` compartilhado pelo construtor em vez de
importar o getter de um singleton em nível de módulo; cada controller virou
uma classe que recebe seus repositórios (e, no caso do controller de
pedidos, o `NotificationService`) pelo construtor; e cada blueprint do
Flask virou uma função fábrica (`create_*_blueprint(controller)`) que
recebe o controller já construído em vez de importar um módulo de
controller e chamar suas funções diretamente. `src/app.py` passou a ser o
único lugar que constrói esse grafo de objetos — nenhum módulo abaixo dele
depende de um singleton global para obter suas dependências. Detalhe
completo da mudança e da nova bateria de validação end-to-end em
[`.refactor-arch/phase-3-validation.md`](.refactor-arch/phase-3-validation.md).

`DELETE /produtos/<id>` — inicialmente deixado sem autenticação numa rodada
anterior de refatoração — foi revisitado e corrigido numa rodada seguinte:
o endpoint agora exige o mesmo guard `require_admin` usado em `/admin/*`
(header `X-Admin-Token`), fechando a lacuna CRITICAL de endpoint destrutivo
sem controle de acesso. Requisições sem token válido recebem `401`; com
token válido, o comportamento (soft-delete via `ativo = 0`) é o mesmo de
antes.

## Construção da Skill

**Decisões de design.** `SKILL.md` (em `.claude/skills/refactor-arch/`) orquestra um workflow de 3 fases estritamente sequenciais. Cada fase é despachada como um subagente dedicado, que só lê os arquivos de referência que aquela fase precisa (nunca os 5 de uma vez) — mantém o contexto de cada subagente pequeno e focado. O estado intermediário persiste em `.refactor-arch/phase-{1,2,3}-*.md`, dentro do próprio projeto, para sobreviver entre invocações de subagente sem misturar arquivos de trabalho com o entregável final (`reports/`, código refatorado). Entre a Fase 2 e a Fase 3 existe um **gate de confirmação humana obrigatório** (`SKILL.md:51-57`): a skill imprime o relatório de auditoria e pergunta explicitamente `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` via `AskUserQuestion` — nenhum arquivo é modificado antes dessa confirmação. Cinco arquivos de referência cobrem as 5 áreas de conhecimento exigidas: `project-analysis.md` (heurísticas de detecção), `anti-pattern-catalog.md` (catálogo com severidade), `report-template.md` (formato do relatório), `architecture-guidelines.md` (regras do MVC alvo) e `refactoring-playbook.md` (12 padrões de transformação com exemplos antes/depois — acima do mínimo de 8 exigido).

**Anti-patterns incluídos e por quê.** O catálogo (`references/anti-pattern-catalog.md`) tem 20 entradas cobrindo toda a escala de severidade do desafio (5 CRITICAL, 4 HIGH, 6 MEDIUM, 5 LOW). Neste projeto especificamente, os hits mais relevantes foram os 8 achados CRITICAL — SQL Injection via concatenação de string (presente em praticamente toda `models.py`), credenciais hardcoded, God Class/God File e dois endpoints administrativos sem autenticação — porque este era o legado mais desestruturado dos 3 projetos-alvo (monolito total, sem qualquer separação em camadas), e foi o principal insumo para calibrar a severidade CRITICAL do catálogo.

**Agnosticismo de tecnologia.** A skill detecta a stack por evidência (extensão de arquivo + parsing de `requirements.txt`), nunca assumindo nomes de arquivo específicos deste projeto (`app.py`/`controllers.py`/`models.py`/`database.py`). A mesma pasta `.claude/skills/refactor-arch/`, sem uma única alteração, foi depois copiada para `ecommerce-api-legacy/` (Node.js/Express) e `task-manager-api/` (Python/Flask parcialmente organizado) e completou as 3 fases com sucesso nos dois — prova empírica de que o conhecimento em `references/` não está acoplado a este projeto.

**Desafios encontrados.** O principal foi decidir o que ficava fora do escopo de uma única rodada de refatoração, para não violar a exigência de preservar a superfície pública da API: uma rodada anterior havia limitado o gate de autenticação apenas aos endpoints `/admin/*`, deixando `DELETE /produtos/<id>` sem autenticação; isso foi corrigido numa rodada seguinte aplicando o mesmo `require_admin` a essa rota, já que um endpoint destrutivo sem controle de acesso é CRITICAL independentemente do prefixo do path. A injeção de dependência via construtor também havia sido adiada por parecer grande demais para uma única rodada — o global mutável ficou, por um tempo, apenas encapsulado numa classe `DatabaseConnection` sem injeção real — mas foi concluída numa rodada seguinte convertendo modelos em repositórios, controllers em classes e blueprints em fábricas, todos recebendo suas dependências pelo construtor a partir de `src/app.py`.

## Resultados

**Resumo da auditoria (Fase 2 da skill):** 30 findings — 8 CRITICAL / 4 HIGH / 10 MEDIUM / 8 LOW ([relatório completo](reports/audit-code-smells-project.md)), batendo exatamente com a análise manual documentada acima.

**Antes/depois da estrutura:**
```
# Antes — monolito de 4 arquivos na raiz, sem camadas
app.py  controllers.py  models.py  database.py

# Depois — MVC completo
src/
├── app.py                    # composition root
├── config/settings.py
├── database/connection.py
├── models/                   # product_model.py, user_model.py, order_model.py
├── controllers/               # product_, user_, order_, report_, health_, admin_controller.py
├── views/                     # *_routes.py (Flask Blueprints)
├── middlewares/               # auth.py, error_handler.py
└── services/notification_service.py
```

**Checklist de validação preenchida:**
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

**Log de boot após a refatoração:**
```
==================================================
SERVIDOR INICIADO
Rodando em http://localhost:5050
==================================================
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5050
```
Os 19 endpoints originais foram verificados via `curl`, incluindo uma tentativa de SQL injection (payload `Hack'); DROP TABLE produtos;--` no nome de um produto) — armazenada como dado literal em vez de executada, confirmando as queries parametrizadas. Detalhe request-a-request completo em [`.refactor-arch/phase-3-validation.md`](.refactor-arch/phase-3-validation.md).

**Observações.** Este foi o projeto mais desestruturado dos 3 (monolito total em 4 arquivos, sem qualquer camada), por isso a Fase 3 precisou criar toda a árvore MVC do zero — o maior esforço de refatoração entre os 3 projetos, mas sem nenhuma regressão de comportamento em endpoints não-administrativos.

## Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado (`claude` disponível no `PATH`).
- Python 3.11+, `pip`, `venv`.

### Comando para executar a skill

A skill já está commitada em `.claude/skills/refactor-arch/` — não é necessário copiá-la manualmente.

```bash
cd code-smells-project
claude "/refactor-arch"
```

A skill imprime o resumo da Fase 1, depois o relatório completo da Fase 2, e pausa com `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` — responda `y` para prosseguir com a Fase 3.

### Como validar que a refatoração funcionou

1. **Saída da própria skill** — ao final da Fase 3, ela confirma "Application boots without errors" e "All endpoints respond correctly"; se algo falhar, reporta o que quebrou em vez de declarar sucesso.
2. **Subir a aplicação manualmente** seguindo a seção "Como rodar" acima e testar os endpoints com `curl` — exemplos completos (incluindo casos de borda e a tentativa de SQL injection) em [`.refactor-arch/phase-3-validation.md`](.refactor-arch/phase-3-validation.md).
3. **Cruzar achado vs. correção** — comparar [`reports/audit-code-smells-project.md`](reports/audit-code-smells-project.md) com `.refactor-arch/phase-3-validation.md` e confirmar que todos os 30 itens (CRITICAL a LOW) aparecem corrigidos, incluindo a injeção de dependência via construtor.
