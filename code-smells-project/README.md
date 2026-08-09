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
