# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Configuração via variáveis de ambiente (veja `.env.example`). Sem um `.env`, a aplicação usa valores padrão claramente marcados como "dev-only" apenas para desenvolvimento local.

## Autenticação de administrador

O relatório financeiro (`GET /api/admin/financial-report`) e a exclusão de usuário (`DELETE /api/users/:id`) exigem um header `x-admin-key` com o valor de `ADMIN_API_KEY` (padrão de desenvolvimento: `dev-only-insecure-admin-key`). Requisições sem esse header, ou com um valor incorreto, recebem `401 Unauthorized`.

```bash
curl -H "x-admin-key: dev-only-insecure-admin-key" http://localhost:3000/api/admin/financial-report
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
