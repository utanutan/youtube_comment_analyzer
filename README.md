### YouTube コメント分析 MVP0（Streamlit GUI版）

YouTube動画のコメントを取得し、**OpenAI API（ChatGPT）**で感情分析＋頻出語抽出を行うGUIツールです。

#### 機能
- YouTube Data API v3でコメント取得（返信含む）
- OpenAI API（gpt-4o-mini推奨）でバッチ感情分析
- 日本語形態素解析（Janome）で頻出キーワード抽出
- Streamlit GUIで視覚的に結果表示
- CSV エクスポート

#### 使い方
1) **依存インストール**
```bash
pip install -r requirements.txt
```

2) **APIキー準備**
- YouTube Data API v3 キー: [Google Cloud Console](https://console.cloud.google.com/)
- OpenAI API キー: [OpenAI Platform](https://platform.openai.com/)

環境変数で設定する場合（PowerShell）:

**方法A: 現在のセッションのみ（即座に有効、推奨）**
```powershell
$env:YT_API_KEY = "YOUR_YOUTUBE_API_KEY"
$env:OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
```
その後、**同じPowerShellウィンドウで** `streamlit run app.py` を実行。

**方法B: 永続的に設定（再起動後も有効）**
```powershell
setx YT_API_KEY "YOUR_YOUTUBE_API_KEY"
setx OPENAI_API_KEY "YOUR_OPENAI_API_KEY"
```
※ PowerShellを再起動してから `streamlit run app.py` を実行。

**方法C: GUI上で直接入力（最も簡単）**
環境変数を使わず、Streamlitのサイドバーで直接APIキーを入力。

3) **起動**
```bash
streamlit run app.py
```

ブラウザが自動で開き、`http://localhost:8501` でGUIが表示されます。

4) **操作**
- サイドバーで各種設定（取得件数、バッチサイズ、モデル選択）
- 動画URLまたはVideo IDを入力
- 「🔍 分析開始」をクリック
- 結果が表示されたら、CSV ダウンロード可能

#### 注意
- OpenAI APIは**有料**です（gpt-4o-miniは低コスト、500コメント～数十円程度）。
- YouTube Data API v3のクォータ制限に注意（1日10,000ユニット、1コメント取得=1ユニット程度）。
- 大量コメント取得時は時間がかかります（500件で1～2分程度）。

#### ファイル構成
- `app.py`: Streamlit GUIメイン
- `youtube_analyzer.py`: YouTube取得・前処理モジュール
- `openai_sentiment.py`: OpenAI感情分析モジュール
- `mvp0.py`: 旧CLI版（レガシー、非推奨）
- `requirements.txt`: 依存パッケージ


