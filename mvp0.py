import argparse
import csv
import html
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from janome.tokenizer import Tokenizer


YOUTUBE_API_ENDPOINT = "https://www.googleapis.com/youtube/v3/commentThreads"


def extract_video_id(url_or_id: str) -> str:
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
    text = html.unescape(text)
    # allow simple <br> as newline then strip tags
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def clean_text(text: str) -> str:
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
) -> List[Dict]:
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
        resp = requests.get(YOUTUBE_API_ENDPOINT, params=params, timeout=timeout_s)
        if resp.status_code == 403 or resp.status_code == 429:
            # simple backoff on quota/rate
            wait_s = 2.0
            time.sleep(wait_s)
            continue
        resp.raise_for_status()
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
            if len(comments) >= max_comments:
                break

        if len(comments) >= max_comments:
            break
        next_page = data.get("nextPageToken")
        if not next_page:
            break

    return comments[:max_comments]


def tokenize_ja(text: str, tokenizer: Tokenizer, include_pos: Tuple[str, ...] = ("名詞", "動詞")) -> List[str]:
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
        "です",
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


POSITIVE_LEXICON = set(
    [
        "最高",
        "面白い",
        "素晴らしい",
        "好き",
        "神",
        "ありがとう",
        "かわいい",
        "かっこいい",
        "上手",
        "役立つ",
        "助かった",
        "良い",
        "楽しい",
    ]
)

NEGATIVE_LEXICON = set(
    [
        "最悪",
        "つまらない",
        "嫌い",
        "無理",
        "ひどい",
        "悪い",
        "怒",
        "腹立つ",
        "うざい",
        "微妙",
        "ダサい",
        "悲しい",
        "残念",
        "遅い",
        "バグ",
        "詐欺",
        "低評価",
    ]
)


def sentiment_score(text: str) -> int:
    score = 0
    for w in POSITIVE_LEXICON:
        if w in text:
            score += text.count(w)
    for w in NEGATIVE_LEXICON:
        if w in text:
            score -= text.count(w)
    return score


def classify_sentiment(score: int) -> str:
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"


def analyze_comments(comments: List[Dict]) -> Dict:
    tokenizer = Tokenizer()
    all_tokens: List[str] = []
    pos = neg = neu = 0
    analyzed: List[Dict] = []
    for c in comments:
        cleaned = clean_text(c.get("textOriginal", ""))
        c["textClean"] = cleaned

        score = sentiment_score(cleaned)
        label = classify_sentiment(score)
        c["sentimentScore"] = score
        c["sentimentLabel"] = label

        if label == "positive":
            pos += 1
        elif label == "negative":
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


def ensure_output_dir(path: str = "outputs") -> str:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
    return path


def save_outputs(analysis: Dict, out_dir: str) -> None:
    # JSON report
    report_path = os.path.join(out_dir, "mvp0_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(analysis["summary"], f, ensure_ascii=False, indent=2)

    # Tokens CSV
    tokens_csv = os.path.join(out_dir, "tokens_top.csv")
    with open(tokens_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["token", "count"])
        for token, cnt in analysis["summary"]["topTokens"]:
            writer.writerow([token, cnt])

    # Comments CSV
    comments_csv = os.path.join(out_dir, "comments.csv")
    with open(comments_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "commentId",
                "isReply",
                "likeCount",
                "publishedAt",
                "authorDisplayName",
                "sentimentLabel",
                "sentimentScore",
                "textClean",
            ]
        )
        for c in analysis["comments"]:
            writer.writerow(
                [
                    c.get("commentId"),
                    c.get("isReply"),
                    c.get("likeCount"),
                    c.get("publishedAt"),
                    c.get("authorDisplayName"),
                    c.get("sentimentLabel"),
                    c.get("sentimentScore"),
                    c.get("textClean", ""),
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube コメント MVP0 分析ツール")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", type=str, help="YouTube動画URL")
    group.add_argument("--video-id", type=str, help="YouTube videoId (11文字)")
    parser.add_argument("--api-key", type=str, help="YouTube Data APIキー（未指定時は環境変数YT_API_KEYを使用）")
    parser.add_argument("--max-comments", type=int, default=1000, help="最大取得件数（デフォルト: 1000）")
    parser.add_argument("--no-replies", action="store_true", help="返信コメントを取得しない")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("YT_API_KEY")
    if not api_key:
        print("APIキーが見つかりません。--api-key か 環境変数YT_API_KEY を設定してください。", file=sys.stderr)
        sys.exit(1)

    try:
        video_id = extract_video_id(args.url if args.url else args.video_id)
    except Exception as e:
        print(f"videoId抽出エラー: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] コメント取得開始 videoId={video_id} max={args.max_comments} replies={not args.no_replies}")
    comments = fetch_comments(
        api_key=api_key,
        video_id=video_id,
        max_comments=args.max_comments,
        include_replies=(not args.no_replies),
    )
    print(f"[INFO] 取得件数: {len(comments)}")

    print("[INFO] 前処理・簡易分析...")
    analysis = analyze_comments(comments)
    summary = analysis["summary"]
    print("[RESULT] 件数:", summary["totalComments"])
    print("[RESULT] 感情分布:", summary["sentimentDist"])
    print("[RESULT] 上位トークン(10):", summary["topTokens"][:10])

    out_dir = ensure_output_dir()
    save_outputs(analysis, out_dir)
    print(f"[INFO] 出力先: {out_dir} (mvp0_report.json, tokens_top.csv, comments.csv)")


if __name__ == "__main__":
    main()


