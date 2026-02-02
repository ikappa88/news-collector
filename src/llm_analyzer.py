import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"


def fix_json_string(s: str) -> str:
    """
    LLM が壊した JSON を自動修復する。
    - 二重のダブルクォートを修正
    - 改行を削除
    - 末尾のカンマを削除
    - エスケープ漏れを修正
    """

    # 改行を削除
    s = s.replace("\n", " ")

    # 二重のダブルクォート → 一つに
    s = re.sub(r'""', '"', s)

    # キーの前後の空白を削除
    s = re.sub(r'\s+"', '"', s)

    # 末尾のカンマを削除
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)

    return s


def analyze_news_with_llm(title, date, source_url, body_text):
    prompt = f"""
あなたは日本語で回答するニュース分析アシスタントです。
以下のニュース記事を読み、飲料メーカーの視点で分析し、
次の項目を **必ず日本語のみで** JSON 形式で返してください。

【重要ルール】
- 英語を一切使用しないでください。
- 意味不明な文字列、機械語のような文字列を絶対に出力しないでください。
- JSON の前後に説明文を付けないでください。
- JSON の値もすべて日本語で書いてください。

【出力項目】
- steep_category
- date
- title
- summary
- source
- news_importance
- company_impact
- note

【ニュース本文】
タイトル: {title}
日付: {date}
URL: {source_url}

本文:
{body_text}
"""

    response = requests.post(
        OLLAMA_URL, json={"model": MODEL_NAME, "prompt": prompt, "stream": False}
    )

    raw = response.json().get("response", "")

    # JSON部分だけ抽出
    start = raw.find("{")
    end = raw.rfind("}") + 1

    if start == -1 or end == -1:
        print("⚠ JSON形式が見つかりませんでした:")
        print(raw)
        return None

    json_str = raw[start:end]

    # JSON自動修復
    json_str = fix_json_string(json_str)

    try:
        return json.loads(json_str)
    except Exception as e:
        print("⚠ JSON解析失敗（修復後）:", e)
        print("修復後データ:")
        print(json_str)
        return None
