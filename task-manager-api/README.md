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
