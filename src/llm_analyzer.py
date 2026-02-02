import requests
import json
import re
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5"


def fix_json_string(s: str) -> str:
    """LLM が壊した JSON を自動修復する"""
    s = s.replace("\n", " ")
    s = re.sub(r'""', '"', s)
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)
    return s


def force_steep_category(value: str) -> str:
    """STEEP を Social / Technological / Economic / Environmental / Political に強制補正"""

    mapping = {
        "S": "Social",
        "社会": "Social",
        "social": "Social",
        "T": "Technological",
        "技術": "Technological",
        "tech": "Technological",
        "E": "Economic",
        "経済": "Economic",
        "eco": "Economic",
        "En": "Environmental",
        "環境": "Environmental",
        "env": "Environmental",
        "P": "Political",
        "政治": "Political",
        "pol": "Political",
    }

    v = value.lower()

    for key, mapped in mapping.items():
        if key.lower() in v:
            return mapped

    # どれにも当てはまらない場合は Economic にしておく
    return "Economic"


def force_score(value):
    """重要度・影響度を 1〜5 に強制補正"""
    try:
        v = float(value)
    except:
        return 1
    return max(1, min(5, int(round(v))))


def analyze_news_with_llm(title, date, source_url, body_text):
    """ニュース本文を LLM に渡し、壊れても必ず dict を返す"""

    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
あなたは日本語で回答するアシスタントです。
以下の項目を JSON 形式で返してください。

【重要】
- JSON のみを返す
- 英語を使わない
- 意味不明な文字列を出さない
- steep_category は以下のいずれかのみ：
  "Social", "Technological", "Economic", "Environmental", "Political"
- news_importance と company_impact は 1〜5 の整数

【出力項目】
steep_category
date
title
summary
source
news_importance
company_impact
note

【ニュース本文】
タイトル: {title}
本文:
{body_text}
"""

    response = requests.post(
        OLLAMA_URL, json={"model": MODEL_NAME, "prompt": prompt, "stream": False}
    )

    raw = response.json().get("response", "")

    # JSON 部分抽出
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == -1:
        return {
            "steep_category": "Economic",
            "date": today,
            "title": title,
            "summary": "要約生成に失敗しました",
            "source": source_url,
            "news_importance": 1,
            "company_impact": 1,
            "note": "解析エラーのため簡易情報のみ表示",
        }

    json_str = fix_json_string(raw[start:end])

    # JSON パース
    try:
        data = json.loads(json_str)
    except:
        return {
            "steep_category": "Economic",
            "date": today,
            "title": title,
            "summary": "要約生成に失敗しました",
            "source": source_url,
            "news_importance": 1,
            "company_impact": 1,
            "note": "解析エラーのため簡易情報のみ表示",
        }

    # --- 補正処理 ---
    data["steep_category"] = force_steep_category(str(data.get("steep_category", "")))
    data["date"] = today
    data["title"] = title
    data["source"] = source_url
    data["news_importance"] = force_score(data.get("news_importance", 1))
    data["company_impact"] = force_score(data.get("company_impact", 1))

    return data
