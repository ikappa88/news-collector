import requests
import json
import re
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5"

# table_formatter.py と同期したカテゴリ定義
# HN・NewsAPI用カテゴリ
HN_CATEGORIES = [
    "AI / ML",
    "Dev Tools",
    "Security",
    "Infra / Cloud",
    "Business",
    "Science",
    "Policy / Law",
    "Other",
]

# 国内ニュース（朝日・毎日）用カテゴリ
JP_CATEGORIES = [
    "政治・行政",
    "経済・産業",
    "国際",
    "社会・事件",
    "科学・環境",
    "文化・スポーツ",
    "その他",
]

VALID_CATEGORIES = HN_CATEGORIES + JP_CATEGORIES


def fix_json_string(s: str) -> str:
    """
    LLM が出力した壊れた JSON を修復する。

    主な修正内容:
    - JSON文字列値の中に含まれる生の改行文字（\\n）を \\\\n にエスケープ
      （旧実装の .replace("\\n", " ") は日本語テキストを途中で切断していた）
    - トレイリングカンマの除去
    """
    # トレイリングカンマを除去
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)

    # 文字列リテラル内の生の改行・復帰を JSON エスケープに変換
    result = []
    in_string = False
    escape = False
    for ch in s:
        if escape:
            result.append(ch)
            escape = False
        elif ch == "\\":
            result.append(ch)
            escape = True
        elif ch == '"':
            result.append(ch)
            in_string = not in_string
        elif in_string and ch == "\n":
            result.append("\\n")  # 生改行 → エスケープ
        elif in_string and ch == "\r":
            pass  # CR は除去
        else:
            result.append(ch)
    return "".join(result)


def force_category(value: str) -> str:
    """
    LLM が返したカテゴリ文字列を VALID_CATEGORIES に強制補正する。
    部分一致で最も近いものを選び、どれにも当てはまらなければ "Other" を返す。
    """
    v = value.strip().lower()

    # 完全一致優先
    for cat in VALID_CATEGORIES:
        if cat.lower() == v:
            return cat

    # 部分一致エイリアス
    ALIASES = {
        "ai": "AI / ML",
        "ml": "AI / ML",
        "machine": "AI / ML",
        "llm": "AI / ML",
        "deep": "AI / ML",
        "dev": "Dev Tools",
        "tool": "Dev Tools",
        "oss": "Dev Tools",
        "library": "Dev Tools",
        "cli": "Dev Tools",
        "security": "Security",
        "vuln": "Security",
        "crypto": "Security",
        "privacy": "Security",
        "infra": "Infra / Cloud",
        "cloud": "Infra / Cloud",
        "server": "Infra / Cloud",
        "database": "Infra / Cloud",
        "network": "Infra / Cloud",
        "business": "Business",
        "startup": "Business",
        "funding": "Business",
        "acquisition": "Business",
        "science": "Science",
        "research": "Science",
        "space": "Science",
        "biology": "Science",
        "policy": "Policy / Law",
        "law": "Policy / Law",
        "regulation": "Policy / Law",
        "legal": "Policy / Law",
        # 国内ニュース用エイリアス
        "政治": "政治・行政",
        "選挙": "政治・行政",
        "行政": "政治・行政",
        "経済": "経済・産業",
        "産業": "経済・産業",
        "企業": "経済・産業",
        "金融": "経済・産業",
        "国際": "国際",
        "外交": "国際",
        "海外": "国際",
        "事件": "社会・事件",
        "事故": "社会・事件",
        "社会": "社会・事件",
        "科学": "科学・環境",
        "環境": "科学・環境",
        "気候": "科学・環境",
        "文化": "文化・スポーツ",
        "スポーツ": "文化・スポーツ",
        "芸能": "文化・スポーツ",
    }
    for alias, cat in ALIASES.items():
        if alias in v:
            return cat

    return "Other"


def force_score(value) -> int:
    """重要度スコアを 1〜10 の整数に強制補正する"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(10, int(round(v))))


def _fallback(title: str, source_url: str) -> dict:
    """パース失敗時に返すフォールバック辞書"""
    return {
        "title": str(data.get("title_ja", title)) or title,
        "title_en": title,
        "url": source_url,
        "summary": "要約生成に失敗しました",
        "score": 1,
        "published": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "category": "Other",
        "note": "解析エラーのため簡易情報のみ表示",
    }


def analyze_news_with_llm(
    title: str,
    date: str,
    source_url: str,
    body_text: str,
    hn_points: int = 0,
    comments: int = 0,
) -> dict:
    """
    ニュース本文を LLM に渡して分析し、必ず dict を返す。

    返り値のフィールド（table_formatter.py と対応）:
        title     : str   記事タイトル
        url       : str   記事URL
        summary   : str   日本語要約
        score     : int   重要度スコア（1〜10）
        published : str   公開日時
        category  : str   HNカテゴリ（VALID_CATEGORIES のいずれか）
        hn_points : int   HNポイント（upvote数）
        note      : str   補足メモ（任意）
    """

    prompt = (
        """あなたは日本語で回答するアシスタントです。
以下のニュース記事を分析し、JSON 形式のみで返してください。

【厳守事項】
- JSON のみを返す（前後に説明文を入れない）
- すべての文字列フィールドは必ず日本語で記述する（英語・中国語・その他の言語は使わない）
- category は以下のいずれか 1 つのみ：
  "AI / ML", "Dev Tools", "Security", "Infra / Cloud",
  "Business", "Science", "Policy / Law", "Other"
- score は記事の重要度を表す 1〜10 の整数

【出力フィールド】
{
  "title_ja":  "タイトルの日本語訳",
  "summary":   "200字以内の日本語要約",
  "score":     重要度スコア（整数 1〜10）,
  "category":  "上記カテゴリのいずれか",
  "note":      "補足があれば。なければ空文字"
}

【ニュース記事】
タイトル: """
        + title
        + """
公開日時: """
        + date
        + """
本文:
"""
        + body_text
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json().get("response", "")
    except Exception as e:
        print(f"[LLM ERROR] Request failed: {e}")
        result = _fallback(title, source_url)
        result["hn_points"] = hn_points
        return result

    # JSON 部分抽出
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end <= start:
        print(f"[LLM ERROR] JSON not found in response: {raw[:200]}")
        result = _fallback(title, source_url)
        result["hn_points"] = hn_points
        return result

    json_str = fix_json_string(raw[start:end])

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[LLM ERROR] JSON parse failed: {e}\nRaw: {json_str[:300]}")
        result = _fallback(title, source_url)
        result["hn_points"] = hn_points
        return result

    # --- フィールド補正・統合 ---
    return {
        "title": title,
        "url": source_url,
        "summary": str(data.get("summary", "要約なし")),
        "score": force_score(data.get("score", 1)),
        "published": date or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "category": force_category(str(data.get("category", ""))),
        "hn_points": hn_points,
        "comments": comments,
        "note": str(data.get("note", "")),
    }
