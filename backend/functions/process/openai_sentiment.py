"""OpenAI API を用いた感情分析モジュール"""
import json
import time
from typing import Dict, List

from openai import OpenAI


class OpenAISentimentAnalyzer:
    """OpenAI APIでバッチ感情分析"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", batch_size: int = 20):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.batch_size = batch_size
    
    def analyze_batch(self, texts: List[str], progress_callback=None) -> List[Dict]:
        """複数テキストをバッチで感情分析"""
        results = []
        total = len(texts)
        
        for i in range(0, total, self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_results = self._call_api_batch(batch)
            results.extend(batch_results)
            
            if progress_callback:
                progress_callback(f"感情分析中: {min(i + self.batch_size, total)}/{total}")
            
            # Rate limit対策
            time.sleep(0.5)
        
        return results
    
    def _call_api_batch(self, texts: List[str]) -> List[Dict]:
        """OpenAI APIを呼び出してバッチ分析"""
        # バッチプロンプト構築
        numbered_texts = "\n".join([f"{idx+1}. {text[:200]}" for idx, text in enumerate(texts)])
        
        prompt = f"""以下の日本語コメントそれぞれについて、感情を分析してください。

コメント:
{numbered_texts}

各コメントについて、以下のJSON配列で回答してください：
[
  {{"index": 1, "sentiment": "positive/neutral/negative", "score": -1から1の数値, "reason": "判定理由（30文字以内）"}},
  ...
]

判定基準:
- positive: 肯定的・好意的・感謝・賞賛
- neutral: 中立的・事実記述・質問
- negative: 否定的・批判・不満・攻撃的

score: positive=0.5～1.0, neutral=-0.3～0.3, negative=-1.0～-0.5
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは日本語テキストの感情分析の専門家です。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            
            content = response.choices[0].message.content.strip()
            # JSONブロック抽出
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(content)
            
            # 結果をマッピング
            results = []
            for item in parsed:
                idx = item.get("index", 1) - 1
                if idx < len(texts):
                    results.append({
                        "label": item.get("sentiment", "neutral"),
                        "score": float(item.get("score", 0.0)),
                        "reason": item.get("reason", ""),
                    })
            
            # 不足分は中立で埋める
            while len(results) < len(texts):
                results.append({"label": "neutral", "score": 0.0, "reason": "解析失敗"})
            
            return results[:len(texts)]
        
        except Exception as e:
            # エラー時は全て中立で返す
            return [{"label": "neutral", "score": 0.0, "reason": f"API Error: {str(e)[:30]}"} for _ in texts]
    
    def analyze_single(self, text: str) -> Dict:
        """単一テキストの感情分析（即時）"""
        result = self.analyze_batch([text])
        return result[0] if result else {"label": "neutral", "score": 0.0, "reason": ""}

