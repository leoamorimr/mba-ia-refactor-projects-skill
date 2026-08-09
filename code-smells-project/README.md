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

28 dos 30 achados foram corrigidos na refatoração para a estrutura MVC atual (ver
histórico de commits e `.refactor-arch/phase-3-validation.md` para o mapeamento
achado → correção e a validação end-to-end de cada endpoint). Dois itens ficaram
fora do escopo desta rodada, por decisão explícita de escopo da tarefa:

- **Autenticação em `DELETE /produtos/<id>`** — a tarefa limitava o novo
  gate de autenticação apenas aos dois endpoints `/admin/*` e exigia manter
  inalterada a superfície pública da API. A injeção de SQL foi corrigida e o
  delete virou soft-delete (`ativo = 0`), mas o endpoint permanece sem
  autenticação — uma lacuna residual sinalizada como CRITICAL a ser
  revisitada quando existir um sistema de autenticação real.
- **Injeção de dependência via construtor** — uma camada de repositórios
  com injeção completa de conexão foi julgada grande demais para esta
  rodada. Em vez disso, o global mutável foi encapsulado em uma classe
  `DatabaseConnection`, e a divisão em um módulo de modelo por entidade foi
  concluída conforme especificado.
