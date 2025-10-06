## 開発履歴 - YouTube コメント分析ツール

### 2025年10月6日 - MVP0 開発

#### 1. プロジェクト企画
**指示**: 対称のyoutube動画のコメント欄を分析して、動画ネタを検討するツールを作成したい。まずは作成するためのPRDを作成して。

**成果物**:
- `PRD.md` を作成
  - 目的: YouTube動画コメントから視聴者インサイトと動画ネタ候補を抽出
  - KPI: 5,000件/≤2分、抽出再現率≥80%
  - 機能要件: 収集、前処理、感情分析、トピックモデル、ネタ候補生成
  - 技術選定: Python + FastAPI、NLP（sentence-transformers、BERTopic）
  - マイルストーン: M1〜M5（収集→分析→ネタ生成→UI→安定化）

#### 2. MVP1 仕様書作成
**指示**: MVP1の仕様書を作成して。

**成果物**:
- `MVP1_SPEC.md` を作成
  - スコープ: コメント取得、前処理、キャッシュ（感情分析は次フェーズ）
  - API仕様: POST /analyze, GET /analysis/{jobId}, DELETE /cache/{videoId}
  - データモデル: Video, Comment, AnalysisRun, CacheIndex（SQLite）
  - 前処理: 正規化、言語判定、重複/スパム除去、トークン化
  - 受入基準: 5,000件/≤2分、キャッシュヒット≤30秒

#### 3. MVP0 CLI版作成
**指示**: MVP0でpythonで簡単にコメント分析するツールを作成して。

**成果物**:
- `mvp0.py`: CLIツール
  - YouTube Data API v3でコメント取得
  - 日本語形態素解析（Janome）
  - 簡易感情分析（辞書ベース）
  - 頻出トークン抽出
  - CSV/JSON出力
- `requirements.txt`: 依存パッケージ
- `README.md`: 使い方ガイド

#### 4. OpenAI API統合 + Streamlit GUI化
**指示**: センチメント分析はopenAIのchatGPTのAPIを用いるようにして。streamlitを用いてGUIにして。

**成果物**:
- `youtube_analyzer.py`: コメント取得・前処理モジュール
  - URL/ID抽出、HTML除去、正規化
  - YouTube API呼び出し（ページング、リトライ）
  - 進捗コールバック対応
  
- `openai_sentiment.py`: OpenAI感情分析モジュール
  - バッチ処理（デフォルト20件/回）
  - プロンプトエンジニアリング（positive/neutral/negative + スコア + 理由）
  - エラーハンドリング、レート制限対策
  
- `app.py`: Streamlit GUIアプリ
  - サイドバー設定（APIキー、モデル選択、取得件数、バッチサイズ）
  - リアルタイム進捗表示
  - 結果可視化（メトリクス、グラフ、テーブル）
  - CSVダウンロード機能
  
- `requirements.txt` 更新:
  - streamlit==1.31.1
  - openai>=1.30.0
  - pandas==2.2.0
  
- `README.md` 全面改訂:
  - Streamlit起動方法
  - APIキー設定（3つの方法）
  - 使い方、注意事項、コスト目安

#### 5. トラブルシューティング

**問題1**: 環境変数設定エラー
- 症状: `setx` コマンド全体がAPIキーとして読み込まれる
- 原因: PowerShellの環境変数設定方法の誤解
- 解決: `$env:VAR = "value"` または GUI入力を推奨

**問題2**: OpenAI API エラー
- 症状: `Client.init() got an unexpected keyword argument 'proxies'`
- 原因: openaiライブラリのバージョン不整合（1.12.0）
- 解決: `pip install --upgrade openai` → 2.1.0にアップグレード

#### 6. GitHub リポジトリ作成
**指示**: githubにコミットして → ghコマンドでプッシュして → privateで

**実行内容**:
```bash
git init
git add .
git commit -m "feat: YouTube コメント分析ツール MVP0 - Streamlit GUI + OpenAI API統合"
gh repo create youtube_comment_analyzer --private --source=. --remote=origin --push
```

**成果物**:
- リポジトリURL: https://github.com/utanutan/youtube_comment_analyzer
- 可視性: Private
- ブランチ: master

### 主要機能（MVP0完成版）

✅ YouTube Data API v3でコメント取得（返信含む）
✅ OpenAI API（gpt-4o-mini/gpt-4o/gpt-3.5-turbo選択可）でバッチ感情分析
✅ 日本語形態素解析（Janome）で頻出キーワード抽出
✅ Streamlit GUIで視覚的表示
✅ リアルタイム進捗表示
✅ CSVエクスポート
✅ エラーハンドリング、レート制限対策

### 技術スタック

- **言語**: Python 3.12
- **GUI**: Streamlit 1.31.1
- **API統合**: 
  - YouTube Data API v3（requests）
  - OpenAI API 2.1.0（gpt-4o-mini推奨）
- **NLP**: Janome 0.5.0（日本語形態素解析）
- **データ処理**: pandas 2.2.0
- **バージョン管理**: Git + GitHub CLI

### コスト目安

- **OpenAI API**: gpt-4o-mini使用時、500コメント ≈ 数十円
- **YouTube API**: 無料枠1日10,000ユニット（500コメント ≈ 500ユニット消費）

### 次のステップ（今後の拡張案）

- [ ] トピックモデル（BERTopic）でテーマクラスタリング
- [ ] 動画ネタ候補の自動生成＋優先度スコアリング
- [ ] 時系列トレンド分析（感情・話題の変化）
- [ ] 未解決質問・要望の自動抽出
- [ ] 競合動画比較機能
- [ ] データベース永続化（SQLite/PostgreSQL）
- [ ] WordCloud可視化
- [ ] 多言語対応（英語コメント）

### ファイル構成

```
youtube_comment_analyzer/
├── PRD.md                  # 製品要件定義書
├── MVP1_SPEC.md            # MVP1仕様書
├── history.md              # 本ファイル（開発履歴）
├── README.md               # 使い方ガイド
├── requirements.txt        # 依存パッケージ
├── .gitignore              # Git除外設定
├── app.py                  # Streamlit GUIメイン
├── youtube_analyzer.py     # YouTube API連携モジュール
├── openai_sentiment.py     # OpenAI感情分析モジュール
└── mvp0.py                 # レガシーCLI版（非推奨）
```

### 学んだこト・改善点

1. **環境変数設定**: PowerShellでは `$env:VAR` が即座に有効、`setx` は再起動必要
2. **依存バージョン管理**: `openai>=1.30.0` で柔軟性を確保
3. **バッチ処理**: OpenAI APIのコスト削減のため、20件/回のバッチ処理
4. **エラーハンドリング**: API失敗時は中立（neutral）で埋めて継続
5. **進捗表示**: Streamlitの `st.empty()` + `progress_callback` でUX向上
6. **セキュリティ**: `.gitignore` で `.env`, `*.key` を除外、README内のAPIキーは削除推奨

---

**開発完了日**: 2025年10月6日  
**開発者**: AI Assistant + User  
**所要時間**: 約2時間

