### MVP1 仕様書（収集＋前処理＋キャッシュ）

#### 0) 要約
- **目的**: 対象YouTube動画のコメントを高速・確実に取得し、前処理を施し、再取得コストを抑えるキャッシュを整備する。
- **成果物**: API（/analyze, /analysis/{jobId}, /cache）、SQLiteスキーマ、取得・前処理パイプライン、基本メトリクス、TTLキャッシュ。

#### 1) スコープ
- 含む: コメント取得（threads, replies）、正規化・重複/スパム基礎対策、言語判定、絵文字/リンク処理、キャッシュ、ジョブ管理、リトライ。
- 含まない: 感情分析、トピックモデル、スコアリング、ダッシュボードの可視化（次フェーズ）。

#### 2) ユーザーフロー（MVP1）
1. ユーザーが動画URL/IDと取得パラメータを指定し実行。
2. サービスはキャッシュを確認し、未取得分のみYouTube Data APIから取得。
3. 前処理（正規化、言語、重複/スパム簡易除外）を実施し保存。
4. 進捗はジョブで確認可能。完了後は要約的な基本統計を返却。

#### 3) 機能要件
- **入力**
  - videoId または URL（URL→videoId 抽出対応）
  - maxComments（上限、例: 5,000）
  - since（ISO8601、任意）
  - lang（優先言語コード、例: "ja"）
  - options: { includeReplies: bool, forceRefresh: bool, cacheTtlHours: int }
- **収集**
  - API: commentThreads.list + comments.list（YouTube Data API v3）
  - ページング（nextPageToken），並列取得（最大同時3），レート制御
  - 返信の取得は `includeReplies` オプションで制御
  - 削除/制限コメントはスキップ
- **前処理**
  - 正規化: 全角半角、改行、空白、制御文字除去
  - クリーニング: URL・@メンション・引用記号の除去/置換
  - 絵文字: emoji→短コード（:smile:）または除去（設定）
  - 言語判定: ja/en/other（閾値つき）
  - 重複/類似: 同一`text`+`authorId`+短時間重複は統合
  - スパム簡易: 極短/極長、絵文字/URL過多、繰返し文字列のしきい値
- **キャッシュ**
  - キー: `videoId` + `pageToken` or `commentId`
  - TTL: 24h（デフォルト、設定可）
  - ポリシー: Hit時は未取得分のみ差分取得、`forceRefresh`で無視
  - ストレージ: SQLite（MVP）、後続でPostgreSQL可
- **ジョブ管理**
  - ステータス: queued / running / succeeded / failed / cancelled
  - 進捗: 取得件数、残ページ推定、推定残時間
- **ログ/監査/メトリクス**
  - 取得時間、API呼出回数、エラー種別、キャッシュヒット率
  - 動画単位の総コメント数、ユニーク作者数、言語比率、平均文字数

#### 4) 非機能要件
- 性能: 5,000件 ≤ 2分（標準回線）、10,000件 ≤ 5分
- 信頼性: API失敗時リトライ（指数バックオフ、最大5回）、部分結果保存
- 可観測性: 構造化ログ、基本メトリクス、ジョブIDトレース
- セキュリティ: APIキーの安全管理、Rate Limit遵守、外部出力最小化

#### 5) API 仕様
- POST `/analyze`
  - 入力(JSON):
    - videoId or url: string（必須のいずれか）
    - maxComments: number（デフォルト 5000, 上限 10000）
    - since: string(ISO8601)（任意）
    - lang: string（例: "ja"）
    - options: { includeReplies?: boolean, forceRefresh?: boolean, cacheTtlHours?: number }
  - 出力(202 Accepted): { jobId: string, status: "queued" | "running" }
- GET `/analysis/{jobId}`
  - 出力(200): {
      jobId: string,
      status: "queued"|"running"|"succeeded"|"failed",
      progress?: { fetched: number, estimatedTotal?: number },
      summary?: { total: number, uniqueAuthors: number, langDist: Record<string, number>, avgLen: number },
      startedAt: string, updatedAt: string, error?: { code: string, message: string }
    }
- DELETE `/cache/{videoId}`
  - 出力(200): { videoId: string, deleted: boolean }
- エラー（共通）
  - 400: validation_error
  - 404: not_found（job or video）
  - 429: rate_limited
  - 500: internal_error

##### リクエスト/レスポンス例
```json
POST /analyze
{
  "url": "https://www.youtube.com/watch?v=XXXXXXXXXXX",
  "maxComments": 5000,
  "lang": "ja",
  "options": { "includeReplies": true, "forceRefresh": false }
}
```
```json
202 Accepted
{ "jobId": "job_20241006_abc123", "status": "queued" }
```
```json
GET /analysis/job_20241006_abc123 -> 200
{
  "jobId": "job_20241006_abc123",
  "status": "succeeded",
  "summary": {
    "total": 4321,
    "uniqueAuthors": 2897,
    "langDist": { "ja": 0.94, "en": 0.04, "other": 0.02 },
    "avgLen": 54.2
  },
  "startedAt": "2025-10-06T12:00:00Z",
  "updatedAt": "2025-10-06T12:01:41Z"
}
```

#### 6) データモデル（SQLite, MVP）
- `Video`
  - videoId (PK), title, channelId, fetchedAt, lastAnalyzedAt
- `Comment`
  - commentId (PK), videoId (FK), authorId, authorDisplayName, textOriginal, textClean,
    likeCount, publishedAt, updatedAt, parentId, isReply (bool), lang, spamFlag (bool)
- `AnalysisRun`
  - jobId (PK), videoId, params (JSON), status, progressFetched, estimatedTotal,
    errorCode, errorMessage, createdAt, updatedAt
- `CacheIndex`
  - videoId, pageToken, fetchedAt（将来の差分取得/検証用）

インデックス/制約:
- Comment(videoId), Comment(videoId,publishedAt), Comment(parentId)
- AnalysisRun(videoId), AnalysisRun(createdAt)

#### 7) 前処理アルゴリズム詳細
- 正規化: NFKC、連続空白→1、改行→スペース、制御文字除去
- URL/メンション除去: 正規表現で抽出しプレースホルダに置換（例: <URL>）
- 絵文字: ライブラリで検出し短コード置換（設定で除去可）
- 言語判定: 軽量モデル（fastText/lid.176 または cld3 代替）でスコア付与→主要3分類
- 重複/類似: ハッシュ（SimHash/MinHash）＋短時間・同一著者で圧縮
- スパム簡易: 長さ、繰返しパターン、URL密度、同文連投回数の閾値

#### 8) 取得ロジック/レート制御
- 1秒あたり呼出回数上限を設定（例: 5 req/s）しトークンバケットで制御
- HTTPエラー/クォータ超過時は指数バックオフ（初期待機500ms, 係数2.0, ジッタ）
- 中断復帰: `AnalysisRun` に進捗を逐次保存し再開可能

#### 9) 運用/監視
- ログ: requestId/jobId付き、APIレスポンス時間、payloadサマリ、失敗要因
- メトリクス: 取得時間、API回数、キャッシュヒット率、ドロップ率（スパム/重複）
- アラート（任意）: エラー率>5%/5分、取得時間>5分、クォータ近傍

#### 10) テスト/受け入れ基準
- 単体: URL→videoId抽出、ページング、正規化、言語判定、重複・スパム判定
- 結合: 5,000件/≤2分、キャッシュヒット時≤30秒、forceRefresh動作
- リグレッション: APIスキーマ互換、TTL超過時の再取得
- 受入:
  - 5,000件の取得・保存・前処理がエラーなく完了
  - キャッシュ有り再実行で30秒以内に完了
  - summaryに基本統計（total, authors, langDist, avgLen）が返る

#### 11) 技術選定（MVP1）
- 言語/ランタイム: Python 3.11
- Web/API: FastAPI + Uvicorn, httpx（YouTube API）
- リトライ: tenacity
- 正規化/解析: regex, emoji, unicodedata, langid/fastText
- DB: SQLite + SQLAlchemy, Alembic（簡易）
- 設定: pydantic-settings

#### 12) 実装計画（タスク分解）
1. プロジェクト雛形（FastAPI, settings, logging, DB 初期化）
2. YouTube API クライアント（認証、レート制御、ページング）
3. 前処理ユーティリティ（正規化、言語、スパム、重複）
4. スキーマ定義とマイグレーション（Video/Comment/AnalysisRun/CacheIndex）
5. 収集パイプライン（差分取得、保存、進捗管理）
6. API実装（/analyze, /analysis/{jobId}, /cache/{videoId}）
7. メトリクス/ログ整備、エラーハンドリング/リトライ
8. 負荷試験/受入テスト、ドキュメント更新


