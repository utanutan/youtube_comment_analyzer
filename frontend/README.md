# YouTube Analyzer - Frontend (Next.js)

## 技術スタック

- **Framework**: Next.js 14 (App Router)
- **言語**: TypeScript
- **UI**: Tailwind CSS
- **状態管理**: TanStack Query (React Query)
- **チャート**: Recharts
- **HTTP Client**: Axios

## セットアップ

### インストール

```bash
npm install
```

### 環境変数

`.env.local` を作成:

```env
NEXT_PUBLIC_API_URL=https://your-api-gateway-url.execute-api.region.amazonaws.com/prod
```

### 開発サーバー

```bash
npm run dev
```

http://localhost:3000 で起動

### ビルド

```bash
npm run build
npm run start
```

## デプロイ

### Vercel（推奨）

```bash
# Vercel CLIインストール
npm install -g vercel

# デプロイ
vercel

# 本番デプロイ
vercel --prod
```

環境変数を Vercel ダッシュボードで設定:
- `NEXT_PUBLIC_API_URL`: API Gateway URL

### 手動デプロイ (S3 + CloudFront)

```bash
npm run build
# out/ ディレクトリを S3 にアップロード
aws s3 sync out/ s3://your-bucket-name/ --delete
# CloudFront キャッシュ無効化
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

## ディレクトリ構成

```
frontend/
├── app/                    # Next.js App Router
│   ├── page.tsx           # メインページ
│   ├── layout.tsx         # ルートレイアウト
│   ├── providers.tsx      # React Query Provider
│   └── globals.css        # グローバルスタイル
├── components/            # Reactコンポーネント
│   ├── AnalysisForm.tsx
│   └── ResultDashboard.tsx
├── lib/                   # ユーティリティ
│   ├── api.ts            # API Client
│   └── utils.ts          # ヘルパー関数
└── package.json
```

## 主要機能

- ✅ YouTube URL/ID 入力
- ✅ リアルタイム進捗表示（3秒ポーリング）
- ✅ 感情分布の可視化（円グラフ）
- ✅ 頻出キーワード（棒グラフ）
- ✅ コメント一覧テーブル
- ✅ CSV エクスポート
- ✅ レスポンシブデザイン

## API連携

`lib/api.ts` でバックエンドと連携:

- `POST /analyze`: 分析ジョブ開始
- `GET /analyze/{jobId}`: ステータス取得（ポーリング）
- `GET /analyze/{jobId}/export`: CSV ダウンロード

## スタイリング

Tailwind CSS + カスタムCSS変数で統一感のあるデザイン。
ダーク/ライトモード対応は今後実装予定。

