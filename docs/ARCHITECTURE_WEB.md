# Web版アーキテクチャ設計書

## 概要
Streamlit版をサーバーレスWeb版に変換。Next.js + TypeScript フロントエンド、AWS Lambda + API Gateway バックエンド、S3静的ホスティングで構成。

## アーキテクチャ図

```
┌─────────────────────────────────────────────────────────────┐
│                      クライアント                              │
│          Next.js (TypeScript) + Tailwind CSS                │
│                  デプロイ: Vercel または S3 + CloudFront     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (REST)                       │
│                   CORS有効、認証なし（MVP）                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ Lambda   │  │ Lambda   │  │ Lambda   │
  │ analyze  │  │ status   │  │ export   │
  └──────────┘  └──────────┘  └──────────┘
        │
        ├─→ YouTube Data API v3
        ├─→ OpenAI API
        └─→ DynamoDB (ジョブ管理・キャッシュ)
```

## 技術スタック

### フロントエンド
- **Framework**: Next.js 14 (App Router)
- **言語**: TypeScript 5.x
- **UI**: Tailwind CSS + shadcn/ui
- **状態管理**: React Query (TanStack Query)
- **デプロイ**: Vercel（推奨）または S3 + CloudFront

### バックエンド
- **Runtime**: AWS Lambda (Python 3.11)
- **API**: API Gateway (REST API)
- **ストレージ**: DynamoDB（ジョブ管理、キャッシュ、分析結果）
- **認証**: 環境変数（Lambda）、将来的にCognito
- **IaC**: AWS SAM または Serverless Framework

### 外部API
- YouTube Data API v3
- OpenAI API (gpt-4o-mini)

## API設計

### エンドポイント

#### 1. POST /analyze
**説明**: コメント分析ジョブを開始

**リクエスト**:
```json
{
  "videoId": "string",
  "maxComments": 500,
  "lang": "ja"
}
```

**レスポンス** (202 Accepted):
```json
{
  "jobId": "uuid-v4",
  "status": "queued",
  "createdAt": "ISO8601"
}
```

#### 2. GET /analyze/{jobId}
**説明**: ジョブ状態と結果取得

**レスポンス** (200 OK):
```json
{
  "jobId": "string",
  "status": "completed|running|failed",
  "progress": {
    "fetched": 450,
    "analyzed": 450,
    "total": 500
  },
  "result": {
    "summary": {...},
    "comments": [...]
  }
}
```

#### 3. GET /analyze/{jobId}/export
**説明**: CSV エクスポート

**レスポンス**: CSV ファイル (Content-Type: text/csv)

## データモデル (DynamoDB)

### テーブル: AnalysisJobs

```
PK: jobId (String, UUID)
Attributes:
  - videoId (String)
  - status (String: queued|running|completed|failed)
  - createdAt (Number, timestamp)
  - updatedAt (Number, timestamp)
  - params (Map: maxComments, lang)
  - progress (Map: fetched, analyzed, total)
  - result (Map: summary, comments)
  - ttl (Number, 7日後に自動削除)
```

### テーブル: CommentCache (オプション)

```
PK: videoId (String)
SK: pageToken (String)
Attributes:
  - comments (List)
  - fetchedAt (Number)
  - ttl (Number, 24時間)
```

## Lambda関数設計

### 1. analyze_handler (POST /analyze)
- **タイムアウト**: 15秒
- **メモリ**: 512MB
- **処理**:
  1. リクエストバリデーション
  2. jobId生成（UUID v4）
  3. DynamoDBにジョブ登録（status: queued）
  4. 非同期処理キュー（SQS or Step Functions）にジョブ投入
  5. 202レスポンス返却

### 2. process_analysis (非同期Worker)
- **タイムアウト**: 15分
- **メモリ**: 2048MB
- **処理**:
  1. YouTube API でコメント取得（ページング）
  2. OpenAI API でバッチ感情分析（20件/回）
  3. Janome でトークン化
  4. 進捗を逐次DynamoDB更新
  5. 完了時にresultを保存

### 3. status_handler (GET /analyze/{jobId})
- **タイムアウト**: 5秒
- **メモリ**: 256MB
- **処理**: DynamoDBからジョブ情報取得して返却

### 4. export_handler (GET /analyze/{jobId}/export)
- **タイムアウト**: 10秒
- **メモリ**: 512MB
- **処理**: DynamoDBから結果取得→CSV変換→返却

## 環境変数（Lambda）

```bash
YT_API_KEY=your_youtube_api_key
OPENAI_API_KEY=your_openai_api_key
DYNAMODB_TABLE_JOBS=AnalysisJobs
DYNAMODB_TABLE_CACHE=CommentCache (オプション)
SQS_QUEUE_URL=https://sqs.region.amazonaws.com/xxx (非同期処理用)
CORS_ORIGIN=https://your-nextjs-domain.vercel.app
```

## セキュリティ

1. **APIキー保護**: Lambda環境変数に暗号化保存
2. **CORS**: Next.jsドメインのみ許可
3. **レート制限**: API Gatewayでクォータ/スロットリング設定
4. **認証**: MVP段階は未実装、将来的にCognito + JWT
5. **PII保護**: コメント著者名はマスキング可能オプション

## コスト見積もり（月間1,000リクエスト想定）

- **Lambda**: ~$0.5（分析15分、他5秒）
- **API Gateway**: ~$0.01（1,000リクエスト）
- **DynamoDB**: ~$0.5（オンデマンド、7日TTL）
- **YouTube API**: 無料枠内
- **OpenAI API**: ~$10（gpt-4o-mini、500件/回×1,000）
- **Vercel**: 無料（Hobbyプラン）
- **合計**: ~$11/月

## デプロイフロー

### 開発環境
```bash
# バックエンド
cd backend
sam build
sam local start-api

# フロントエンド
cd frontend
npm run dev
```

### 本番デプロイ
```bash
# バックエンド
cd backend
sam build
sam deploy --guided

# フロントエンド
cd frontend
vercel --prod
```

## ディレクトリ構成

```
youtube_comment_analyzer/
├── frontend/                 # Next.js
│   ├── app/
│   │   ├── page.tsx         # メインページ
│   │   ├── layout.tsx
│   │   └── api/             # API routes (プロキシ)
│   ├── components/
│   │   ├── AnalysisForm.tsx
│   │   ├── ResultDashboard.tsx
│   │   └── ui/              # shadcn/ui
│   ├── lib/
│   │   ├── api.ts           # API client
│   │   └── types.ts
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                  # Lambda + SAM
│   ├── functions/
│   │   ├── analyze/
│   │   │   ├── handler.py
│   │   │   └── requirements.txt
│   │   ├── process/
│   │   │   ├── handler.py
│   │   │   ├── youtube_analyzer.py
│   │   │   ├── openai_sentiment.py
│   │   │   └── requirements.txt
│   │   ├── status/
│   │   └── export/
│   ├── shared/               # 共通モジュール (Layer)
│   │   └── python/
│   ├── template.yaml         # SAM template
│   └── samconfig.toml
│
├── docs/
│   ├── ARCHITECTURE_WEB.md   # 本ファイル
│   ├── API.md
│   └── DEPLOYMENT.md
│
└── README_WEB.md
```

## マイグレーション計画

### Phase 1: バックエンド構築（Week 1）
- [x] アーキテクチャ設計
- [ ] SAM template作成
- [ ] Lambda関数実装（analyze, process, status, export）
- [ ] DynamoDB テーブル設計
- [ ] ローカルテスト

### Phase 2: フロントエンド構築（Week 2）
- [ ] Next.js プロジェクト初期化
- [ ] UI コンポーネント実装
- [ ] API統合
- [ ] ローカル開発環境構築

### Phase 3: 統合テスト（Week 3）
- [ ] E2Eテスト
- [ ] パフォーマンステスト
- [ ] エラーハンドリング

### Phase 4: デプロイ（Week 4）
- [ ] AWS環境セットアップ
- [ ] Vercelデプロイ
- [ ] ドメイン設定
- [ ] 監視・ログ設定

## 今後の拡張

- [ ] Cognito認証
- [ ] WebSocket（リアルタイム進捗）
- [ ] S3バケット（大規模データ保存）
- [ ] CloudWatch監視・アラート
- [ ] CI/CD（GitHub Actions）
- [ ] 多言語対応
- [ ] トピックモデル（BERTopic）

