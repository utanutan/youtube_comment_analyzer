# YouTube Analyzer - Backend (AWS Lambda)

## アーキテクチャ

- **API Gateway**: REST API エンドポイント
- **Lambda関数**:
  - `analyze`: POST /analyze - ジョブ作成
  - `status`: GET /analyze/{jobId} - ステータス取得
  - `export`: GET /analyze/{jobId}/export - CSV エクスポート
  - `process`: SQSトリガー - 非同期処理（YouTube取得 + OpenAI分析）
- **DynamoDB**: ジョブ管理
- **SQS**: 非同期処理キュー

## セットアップ

### 前提条件

- AWS CLI設定済み
- AWS SAM CLI インストール済み
- Python 3.11

### デプロイ

```bash
# ビルド
sam build

# ローカルテスト
sam local start-api

# 本番デプロイ（初回）
sam deploy --guided

# 2回目以降
sam deploy
```

### 環境変数設定

デプロイ時にパラメータとして設定:

- `YouTubeAPIKey`: YouTube Data API v3 キー
- `OpenAIAPIKey`: OpenAI API キー

または、AWS Systems Manager Parameter Storeを使用（推奨）。

## ローカル開発

```bash
# Dockerが必要
sam build
sam local start-api --env-vars env.json

# env.json サンプル:
{
  "AnalyzeFunction": {
    "DYNAMODB_TABLE_JOBS": "youtube-analyzer-jobs",
    "SQS_QUEUE_URL": "http://localhost:9324/000000000000/youtube-analyzer-process-queue"
  },
  "ProcessFunction": {
    "YT_API_KEY": "YOUR_YT_KEY",
    "OPENAI_API_KEY": "YOUR_OPENAI_KEY",
    "DYNAMODB_TABLE_JOBS": "youtube-analyzer-jobs"
  }
}
```

## API仕様

詳細は `docs/API.md` を参照。

### POST /analyze
ジョブ作成

**Request**:
```json
{
  "videoId": "XXXXXXXXXXX",
  "maxComments": 500,
  "lang": "ja"
}
```

**Response** (202):
```json
{
  "jobId": "uuid",
  "status": "queued",
  "createdAt": 1234567890
}
```

### GET /analyze/{jobId}
ステータス取得

**Response** (200):
```json
{
  "jobId": "uuid",
  "status": "completed",
  "progress": {...},
  "result": {...}
}
```

### GET /analyze/{jobId}/export
CSV エクスポート

**Response**: CSV file

## コスト見積もり

月間1,000リクエスト想定:
- Lambda: ~$0.50
- API Gateway: ~$0.01
- DynamoDB: ~$0.50
- SQS: ~$0.01

合計: ~$1/月（外部API除く）

