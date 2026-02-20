# ADR0001: 技術スタック選定

Status: Accepted
Date: 2026-02-20

## Context

本プロジェクトは「ワークスペース型の社内ドキュメント管理SaaS（API）」を実装する。
短いサイクルで開発を進めつつ、DBマイグレーションの安全性、運用時の可観測性、テスト容易性を確保したい。

## Decision

- API: FastAPI
- DB: PostgreSQL
- ORM/Migrations: SQLAlchemy 2 + Alembic
- Async jobs: Celery + Redis
- Testing: pytest (+ httpx)
- Lint/Format: ruff (+ pre-commit)
- CI: GitHub Actions

## Consequences

メリット:

- FastAPIによりAPI実装が高速で、型/バリデーションを比較的強く保てる
- SQLAlchemy 2 + Alembicにより、DB変更をマイグレーションとして明示的に管理できる
- Celery + Redisで非同期処理（export/import等）の実装が可能
- ruff + pre-commit + CIにより、コード品質の最低ラインを自動で担保できる

デメリット/注意点:

- 非同期ジョブとDB整合性（冪等性、リトライ、トランザクション境界）を設計で吸収する必要がある
- 依存関係の固定（requirements等）は後で整備しないと、環境差分が出る可能性がある

## 代替案 / Alternatives

- API: Django（管理画面が強いが、今回の目的はAPI設計/運用/非同期を明示的に学ぶこと）
- ORM: SQLModel（簡便だが、SQLAlchemy 2の理解を優先）
- 非同期: RQ（簡単だが、実務遭遇率と拡張性でCeleryを優先）
  EOF
