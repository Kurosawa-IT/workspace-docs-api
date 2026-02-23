# ADR0004: Document仕様と状態遷移（publish/archive）方針

Status: Accepted  
Date: 2026-02-23

## Context

本プロジェクトはワークスペース配下でドキュメントを管理するSaaS APIである。
ドキュメントは「作成→編集→公開→アーカイブ」の流れを想定し、運用上の事故（任意のstatus書き換え、監査不能、整合性崩れ）を防ぐため、
フィールド仕様と状態遷移の方針を先に固定する。

## Decision

### 1. Documentのフィールド仕様

- title: 1〜200文字（必須）
- body: 1文字以上（必須、Markdown文字列を想定）
- tags: 0個以上の配列（text[]）
  - 初期は単純なラベル用途（検索/フィルタに利用）
  - 重複タグは許可（必要なら後で正規化/ユニーク化を検討）
- status: `draft` / `published` / `archived`
  - DB側はCHECK制約で3値に固定
  - 作成時のデフォルトは `draft`
- timestamps:
  - created_at / updated_at（必須）
  - published_at（published時にセット）
  - archived_at（archived時にセット）
- created_by / updated_by:
  - 作成時は created_by = updated_by = 実行ユーザー
  - 更新時は updated_by を実行ユーザーに更新

### 2. 状態遷移（専用APIでのみ変更）

statusはPATCHの更新対象に含めない。状態遷移は専用APIに限定する。

- `POST /workspaces/{wid}/docs/{doc_id}/publish`
- `POST /workspaces/{wid}/docs/{doc_id}/archive`

遷移ルール（固定）:

- `draft -> published` は許可（publish）
- `published -> archived` は許可（archive）
- 上記以外は拒否（409 Conflict）
  - `published -> published`（再publish）: 拒否
  - `draft -> archived`: 拒否
  - `archived -> published`（復帰）: 現時点では拒否
  - `archived -> archived`: 拒否

※ 「archivedからの復帰」を許すかはプロダクト仕様によって変わるため、現時点では安全側（不可）で固定する。
必要になったら別ADR/別チケットで、復帰APIと監査/権限/運用を含めて設計する。

### 3. status更新をPATCHに含めない理由

- 任意のstatus書き換えが可能になると、運用事故（誤って公開/非公開、監査不能、時刻の不整合）が起きやすい
- 状態遷移は「許可される遷移」と「付随更新（published_at/archived_at）」がセットであるべき
- 専用APIにすると、レビューとテストで遷移ルールを固定しやすい（409の条件も明確）

## Consequences

メリット:

- 状態遷移の責務が明確になり、事故りやすい変更を防げる
- published_at/archived_at 等の付随フィールドが常に整合する
- テストで遷移ルールを固定できる（回帰が起きにくい）

デメリット/注意点:

- 状態が増える（例: review中、scheduled公開など）場合は遷移が複雑化する
- archived復帰を将来入れる場合は、権限・監査・通知など追加要件が出やすい

## Alternatives

- PATCHでstatusを書き換え可能にする
  - 実装は早いが、事故と不整合を誘発しやすいので不採用
- DB enumでstatusを固定
  - 厳密性は増すが、マイグレーションが重くなるため現時点はCHECK制約を採用
