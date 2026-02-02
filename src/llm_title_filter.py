import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"


def analyze_title_fast(title):
    prompt = f"""
あなたはニュースタイトルを高速に分類するアシスタントです。
以下のタイトルを読み、次の項目を JSON 形式で返してください。

項目:
- steep_category: S/T/E/E/P のいずれか
- news_importance: ニュースの重要度（1〜5）
- company_impact: 飲料メーカーへの影響度（1〜5）

タイトル:
{title}

JSONのみを返してください。
"""

    response = requests.post(
        OLLAMA_URL, json={"model": MODEL_NAME, "prompt": prompt, "stream": False}
    )

    raw = response.json().get("response", "")

    start = raw.find("{")
    end = raw.rfind("}") + 1
    json_str = raw[start:end]

    try:
        return json.loads(json_str)
    except:
        return None
