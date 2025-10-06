"""YouTube コメント分析バックエンドモジュール"""
import html
import re
import time
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from janome.tokenizer import Tokenizer


YOUTUBE_API_ENDPOINT = "https://www.googleapis.com/youtube/v3/commentThreads"


def extract_video_id(url_or_id: str) -> str:
    """URLまたはIDからvideoIdを抽出"""
    if "youtube.com" in url_or_id or "youtu.be" in url_or_id:
        # query param v=
        m = re.search(r"[?&]v=([\w-]{11})", url_or_id)
        if m:
            return m.group(1)
        # youtu.be short
        m2 = re.search(r"youtu\.be/([\w-]{11})", url_or_id)
        if m2:
            return m2.group(1)
        raise ValueError("URLからvideoIdを抽出できませんでした。")
    # assume already an id
    if re.fullmatch(r"[\w-]{11}", url_or_id):
        return url_or_id
    raise ValueError("不正なvideoId/URLです。11文字のIDが必要です。")


def strip_html(text: str) -> str:
    """HTML タグを除去"""
    text = html.unescape(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def clean_text(text: str) -> str:
    """テキストのクリーニング"""
    text = text.replace("\r", "\n")
    text = strip_html(text)
    # URLs -> <URL>
    text = re.sub(r"https?://\S+", "<URL>", text)
    # Mentions -> <MENTION>
    text = re.sub(r"@[\w_]+", "<MENTION>", text)
    # Normalize spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_comments(
    api_key: str,
    video_id: str,
    max_comments: int = 1000,
    include_replies: bool = True,
    timeout_s: int = 10,
    progress_callback=None,
) -> List[Dict]:
    """YouTube Data API v3でコメントを取得"""
    comments: List[Dict] = []
    params = {
        "part": "snippet,replies" if include_replies else "snippet",
        "videoId": video_id,
        "maxResults": 100,
        "key": api_key,
        "textFormat": "html",
        "order": "time",
    }
    next_page: Optional[str] = None
    
    while True:
        if next_page:
            params["pageToken"] = next_page
        else:
            params.pop("pageToken", None)
        
        try:
            resp = requests.get(YOUTUBE_API_ENDPOINT, params=params, timeout=timeout_s)
            if resp.status_code == 403 or resp.status_code == 429:
                wait_s = 2.0
                if progress_callback:
                    progress_callback(f"レート制限: {wait_s}秒待機中...")
                time.sleep(wait_s)
                continue
            resp.raise_for_status()
        except Exception as e:
            raise Exception(f"API呼び出しエラー: {e}")
        
        data = resp.json()

        for item in data.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            comments.append(
                {
                    "commentId": item["snippet"]["topLevelComment"]["id"],
                    "videoId": video_id,
                    "authorDisplayName": top.get("authorDisplayName"),
                    "textOriginal": top.get("textDisplay", ""),
                    "likeCount": int(top.get("likeCount", 0)),
                    "publishedAt": top.get("publishedAt"),
                    "updatedAt": top.get("updatedAt"),
                    "parentId": None,
                    "isReply": False,
                }
            )
            if include_replies and "replies" in item:
                for rep in item["replies"].get("comments", []):
                    rs = rep["snippet"]
                    comments.append(
                        {
                            "commentId": rep.get("id"),
                            "videoId": video_id,
                            "authorDisplayName": rs.get("authorDisplayName"),
                            "textOriginal": rs.get("textDisplay", ""),
                            "likeCount": int(rs.get("likeCount", 0)),
                            "publishedAt": rs.get("publishedAt"),
                            "updatedAt": rs.get("updatedAt"),
                            "parentId": rs.get("parentId"),
                            "isReply": True,
                        }
                    )
            
            if progress_callback:
                progress_callback(f"取得中: {len(comments)} 件")
            
            if len(comments) >= max_comments:
                break

        if len(comments) >= max_comments:
            break
        next_page = data.get("nextPageToken")
        if not next_page:
            break

    return comments[:max_comments]


def tokenize_ja(
    text: str, tokenizer: Tokenizer, include_pos: Tuple[str, ...] = ("名詞", "動詞")
) -> List[str]:
    """日本語形態素解析でトークン抽出"""
    tokens: List[str] = []
    for token in tokenizer.tokenize(text):
        pos_major = token.part_of_speech.split(",")[0]
        if pos_major not in include_pos:
            continue
        base = token.base_form if token.base_form != "*" else token.surface
        if len(base) < 2:
            continue
        tokens.append(base)
    return tokens


JP_STOPWORDS = set(
    [
        "する",
        "ある",
        "なる",
        "いる",
        "こと",
        "これ",
        "それ",
        "あれ",
        "ため",
        "よう",
        "さん",
        "です",
        "ます",
        "ん",
        "の",
        "に",
        "を",
        "が",
        "は",
        "と",
        "て",
        "で",
        "から",
        "まで",
        "より",
        "へ",
        "だ",
        "な",
        "ね",
        "よ",
        "けど",
        "そして",
    ]
)


def analyze_comments(comments: List[Dict], sentiment_analyzer) -> Dict:
    """コメントの前処理・トークン化・感情分析"""
    tokenizer = Tokenizer()
    all_tokens: List[str] = []
    pos = neg = neu = 0
    analyzed: List[Dict] = []
    
    for c in comments:
        cleaned = clean_text(c.get("textOriginal", ""))
        c["textClean"] = cleaned

        # OpenAI APIで感情分析
        sentiment_result = sentiment_analyzer(cleaned)
        c["sentimentLabel"] = sentiment_result["label"]
        c["sentimentScore"] = sentiment_result["score"]
        c["sentimentReason"] = sentiment_result.get("reason", "")

        if sentiment_result["label"] == "positive":
            pos += 1
        elif sentiment_result["label"] == "negative":
            neg += 1
        else:
            neu += 1

        tokens = [t for t in tokenize_ja(cleaned, tokenizer) if t not in JP_STOPWORDS]
        c["tokens"] = tokens
        all_tokens.extend(tokens)
        analyzed.append(c)

    token_freq = Counter(all_tokens)
    top_tokens = token_freq.most_common(30)

    summary = {
        "totalComments": len(comments),
        "sentimentDist": {"positive": pos, "neutral": neu, "negative": neg},
        "topTokens": top_tokens,
        "generatedAt": datetime.utcnow().isoformat() + "Z",
    }
    return {"summary": summary, "comments": analyzed}

