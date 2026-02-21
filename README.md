# workspace-docs-api

社内ドキュメント（手順書/FAQ/Runbookを、ワークスペース単位で管理するためのB2B向けバックエンドAPIです。  
RBAC（権限管理）、監査ログ、検索、非同期エクスポート、可観測性まで含めた構成を目指す。

## 目的

- FastAPI + Postgresを軸に、バックエンドの必須要素（設計・DB・運用・信頼性）を一通り実装する
- ただ動く、ではなく「なぜそう設計したか」「障害時にどう追うか」まで説明できる状態にする

## 主要機能

実装済み（現状）

- Alembic（migration）導入と upgrade/downgrade 動作確認
- 認証：JWT（Bearer）

実装予定（ロードマップ）

- ワークスペース：作成・所属一覧
- RBAC：owner/admin/member/viewer
- ドキュメント：CRUD、検索、ページング、状態（draft/published/archived）
- 監査ログ：重要操作の追記-only記録 + 検索
- 非同期：エクスポート（CSV/JSON）をジョブ化（Idempotency-Key対応）
- 可観測性：request_id、構造化ログ、（可能なら）metrics/trace

## 技術スタック（想定）

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Redis（ジョブ/キャッシュ用途）
- Celery（非同期ジョブ）
- pytest（テスト）
- ruff（lint/format）

## セットアップ

### 1) 依存関係

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### 2) インフラ

```bash
docker compose up -d
```

### 3) 環境変数

```bash
APP_ENV=local
DATABASE_URL=postgresql+psycopg://etl_user:etl_password@127.0.0.1:5432/etl_db
REDIS_URL=redis://127.0.0.1:6379/0
JWT_SECRET=change-me
JWT_EXPIRES_MINUTES=60
```

### 4) マイグレーション

```bash
alembic current
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```
