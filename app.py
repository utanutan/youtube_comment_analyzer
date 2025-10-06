"""Streamlit YouTube コメント分析 GUI"""
import os
import pandas as pd
import streamlit as st

from openai_sentiment import OpenAISentimentAnalyzer
from youtube_analyzer import analyze_comments, extract_video_id, fetch_comments


st.set_page_config(page_title="YouTube コメント分析", page_icon="🎥", layout="wide")

st.title("🎥 YouTube コメント分析ツール（MVP0）")
st.markdown("動画のコメントを取得し、OpenAI APIで感情分析＋頻出語を抽出します。")

# サイドバー設定
st.sidebar.header("⚙️ 設定")

youtube_api_key = st.sidebar.text_input(
    "YouTube API Key",
    type="password",
    value=os.getenv("YT_API_KEY", ""),
    help="YouTube Data API v3のAPIキー",
)

openai_api_key = st.sidebar.text_input(
    "OpenAI API Key",
    type="password",
    value=os.getenv("OPENAI_API_KEY", ""),
    help="OpenAI APIキー（gpt-4o-mini使用）",
)

model_name = st.sidebar.selectbox(
    "OpenAI モデル",
    ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
    index=0,
    help="感情分析に使用するモデル",
)

max_comments = st.sidebar.number_input(
    "最大取得件数",
    min_value=10,
    max_value=5000,
    value=500,
    step=50,
    help="取得するコメント数の上限",
)

include_replies = st.sidebar.checkbox("返信コメントも取得", value=True)

batch_size = st.sidebar.number_input(
    "感情分析バッチサイズ",
    min_value=5,
    max_value=50,
    value=20,
    step=5,
    help="1回のAPI呼び出しで分析するコメント数",
)

# メイン入力
video_url = st.text_input(
    "YouTube 動画 URL または Video ID",
    placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX",
)

analyze_button = st.button("🔍 分析開始", type="primary", use_container_width=True)

# セッション状態初期化
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if analyze_button:
    if not video_url:
        st.error("動画URLまたはVideo IDを入力してください。")
    elif not youtube_api_key:
        st.error("YouTube API Keyを設定してください。")
    elif not openai_api_key:
        st.error("OpenAI API Keyを設定してください。")
    else:
        try:
            # Video ID抽出
            video_id = extract_video_id(video_url)
            st.info(f"Video ID: `{video_id}`")
            
            # コメント取得
            with st.spinner("コメント取得中..."):
                progress_placeholder = st.empty()
                
                def progress_cb(msg):
                    progress_placeholder.text(msg)
                
                comments = fetch_comments(
                    api_key=youtube_api_key,
                    video_id=video_id,
                    max_comments=max_comments,
                    include_replies=include_replies,
                    progress_callback=progress_cb,
                )
                progress_placeholder.empty()
            
            st.success(f"✅ {len(comments)} 件のコメントを取得しました。")
            
            # 感情分析
            with st.spinner("OpenAI APIで感情分析中..."):
                analyzer = OpenAISentimentAnalyzer(
                    api_key=openai_api_key, model=model_name, batch_size=batch_size
                )
                
                sentiment_progress = st.empty()
                
                def sentiment_cb(msg):
                    sentiment_progress.text(msg)
                
                texts = [c.get("textOriginal", "") for c in comments]
                sentiments = analyzer.analyze_batch(texts, progress_callback=sentiment_cb)
                sentiment_progress.empty()
                
                # 感情結果を統合
                def sentiment_analyzer_func(text):
                    # バッチ結果から検索（簡易実装）
                    idx = texts.index(text) if text in texts else 0
                    return sentiments[idx] if idx < len(sentiments) else {"label": "neutral", "score": 0.0, "reason": ""}
                
                analysis = analyze_comments(comments, sentiment_analyzer_func)
            
            st.success("✅ 感情分析が完了しました。")
            st.session_state.analysis_result = analysis
        
        except Exception as e:
            st.error(f"エラー: {e}")

# 結果表示
if st.session_state.analysis_result:
    result = st.session_state.analysis_result
    summary = result["summary"]
    comments_data = result["comments"]
    
    st.divider()
    st.header("📊 分析結果")
    
    # サマリ指標
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("総コメント数", summary["totalComments"])
    with col2:
        st.metric("ポジティブ", summary["sentimentDist"]["positive"])
    with col3:
        st.metric("ニュートラル", summary["sentimentDist"]["neutral"])
    with col4:
        st.metric("ネガティブ", summary["sentimentDist"]["negative"])
    
    # 感情分布円グラフ
    st.subheader("感情分布")
    sentiment_df = pd.DataFrame(
        {
            "感情": ["ポジティブ", "ニュートラル", "ネガティブ"],
            "件数": [
                summary["sentimentDist"]["positive"],
                summary["sentimentDist"]["neutral"],
                summary["sentimentDist"]["negative"],
            ],
        }
    )
    st.bar_chart(sentiment_df.set_index("感情"))
    
    # 頻出トークン
    st.subheader("頻出キーワード（Top 20）")
    top_tokens = summary["topTokens"][:20]
    token_df = pd.DataFrame(top_tokens, columns=["トークン", "出現回数"])
    st.dataframe(token_df, use_container_width=True)
    
    # コメント一覧
    st.subheader("コメント詳細")
    comments_df = pd.DataFrame(comments_data)
    display_cols = [
        "authorDisplayName",
        "textClean",
        "sentimentLabel",
        "sentimentScore",
        "sentimentReason",
        "likeCount",
        "publishedAt",
    ]
    available_cols = [c for c in display_cols if c in comments_df.columns]
    st.dataframe(
        comments_df[available_cols].rename(
            columns={
                "authorDisplayName": "著者",
                "textClean": "コメント",
                "sentimentLabel": "感情",
                "sentimentScore": "スコア",
                "sentimentReason": "理由",
                "likeCount": "いいね",
                "publishedAt": "投稿日時",
            }
        ),
        use_container_width=True,
        height=400,
    )
    
    # CSV ダウンロード
    st.subheader("📥 ダウンロード")
    csv = comments_df[available_cols].to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="コメント CSV をダウンロード",
        data=csv,
        file_name="youtube_comments_analysis.csv",
        mime="text/csv",
    )

