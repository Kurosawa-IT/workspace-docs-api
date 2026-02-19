# workspace-docs-api

## 開発ツール

- Lint/Format: ruff
- Git hooks: pre-commit

## セットアップ

```bash
pip install ruff pre-commit
pre-commit install
```

## コマンド

### 

```bash
ruff check .
ruff format --check .
pre-commit install
pre-commit run -a
```

### Docker起動

```bash
docker compose down -v
docker compose up -d
docker compose ps
docker compose logs -f --tail=50 postgres
docker compose logs -f --tail=50 redis
```

### DB接続

```bash
docker exec -it workspace_docs_postgres psql -U ${POSTGRES_USER:-workspace_docs_user} -d ${POSTGRES_DB:-workspace_docs} -c "select 1;"
docker exec -it workspace_docs_redis redis-cli ping
```
