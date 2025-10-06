# YouTube Comment Analyzer - Web Version (Serverless)

サーバーレスアーキテクチャによるYouTubeコメント分析ツール。Next.js + TypeScript フロントエンド、AWS Lambda + API Gateway バックエンド。

## 🏗 アーキテクチャ

```
Frontend (Next.js + TypeScript)
    ↓ HTTPS
API Gateway (REST API)
    ↓
Lambda Functions (Python 3.11)
    ├─ analyze  (POST /analyze)
    ├─ status   (GET /analyze/{jobId})
    ├─ export   (GET /analyze/{jobId}/export)
    └─ process  (SQS Worker: YouTube + OpenAI)
    ↓
DynamoDB (ジョブ管理)
SQS (非同期処理キュー)
```

詳細は [`docs/ARCHITECTURE_WEB.md`](docs/ARCHITECTURE_WEB.md) を参照。

## 📁 ディレクトリ構成

```
youtube_comment_analyzer/
├── frontend/              # Next.js (TypeScript)
│   ├── app/
│   ├── components/
│   └── lib/
├── backend/               # AWS Lambda (Python)
│   ├── functions/
│   │   ├── analyze/
│   │   ├── status/
│   │   ├── export/
│   │   └── process/
│   ├── shared/
│   └── template.yaml      # SAM template
├── docs/
│   └── ARCHITECTURE_WEB.md
└── README_WEB.md          # 本ファイル
```

## 🚀 クイックスタート

### 1. バックエンドデプロイ

```bash
cd backend

# ビルド
sam build

# デプロイ（初回）
sam deploy --guided
# YouTube API Key と OpenAI API Key を入力

# API Gateway URL を取得
aws cloudformation describe-stacks \
  --stack-name youtube-analyzer \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

### 2. フロントエンドデプロイ

```bash
cd frontend

# 依存インストール
npm install

# 環境変数設定
echo "NEXT_PUBLIC_API_URL=<API Gateway URL>" > .env.local

# ローカル開発
npm run dev

# Vercelデプロイ
vercel --prod
```

## 🔧 ローカル開発

### バックエンド

```bash
cd backend
sam build
sam local start-api --env-vars env.json
```

### フロントエンド

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

## 📊 主要機能

- ✅ YouTube動画のコメント取得（YouTube Data API v3）
- ✅ OpenAI APIによるバッチ感情分析（gpt-4o-mini）
- ✅ 日本語形態素解析と頻出キーワード抽出
- ✅ リアルタイム進捗表示（ポーリング）
- ✅ 感情分布・キーワード可視化（Recharts）
- ✅ CSV エクスポート
- ✅ サーバーレスで自動スケール

## 💰 コスト見積もり（月間1,000リクエスト）

- Lambda: ~$0.50
- API Gateway: ~$0.01
- DynamoDB: ~$0.50
- SQS: ~$0.01
- OpenAI API: ~$10（gpt-4o-mini, 500件/回）
- **合計: ~$11/月**

## 🔐 セキュリティ

- APIキーはLambda環境変数に暗号化保存
- CORS設定でフロントエンドドメインのみ許可
- DynamoDB TTL（7日）で自動データ削除
- 認証機能（Cognito）は将来実装予定

## 📖 ドキュメント

- [アーキテクチャ設計](docs/ARCHITECTURE_WEB.md)
- [バックエンドREADME](backend/README.md)
- [フロントエンドREADME](frontend/README.md)

## 🔀 ブランチ

- `master`: Streamlit版（monolithic）
- `web-version`: Web版（serverless）← 本ブランチ

## 🚧 今後の拡張

- [ ] Cognito認証
- [ ] WebSocket（リアルタイム進捗）
- [ ] トピックモデル（BERTopic）
- [ ] 競合動画比較
- [ ] 多言語対応

## 📝 ライセンス

Private Repository

