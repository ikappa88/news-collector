"""
newsapi_news.py

NewsAPI 無料プラン対応版。
/v2/top-headlines を使用（/v2/everything は有料プランのみ）。

無料プランの制限：
- /v2/top-headlines のみ使用可能
- country=us または q= での絞り込みが必要
- language=ja は記事数が極めて少ないため en を使用
- LLMが日本語に要約・翻訳するため英語記事でも問題なし

APIキーは .env に NEWSAPI_KEY として設定してください。
"""

import os
import requests
from datetime import datetime, timezone

NEWSAPI_BASE = "https://newsapi.org/v2"
FETCH_TIMEOUT = 10

# トピック定義：NewsAPI の category パラメータ対応
# top-headlines は category で絞り込み可能
TOPICS = [
    {
        "label": "AI・テクノロジー",
        "category": "technology",
        "q": "AI OR artificial intelligence",
    },
    {"label": "ビジネス・経済", "category": "business", "q": None},
    {"label": "政治・国際", "category": "general", "q": None},
    {"label": "科学", "category": "science", "q": None},
]

ARTICLES_PER_TOPIC = 5
MAX_ARTICLES = 20


def _parse_published(raw: str) -> str:
    """ISO 8601形式を YYYY-MM-DD HH:MM に変換する"""
    try:
        dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw


def _normalize_article(article: dict) -> dict | None:
    """NewsAPIのarticleを正規化する"""
    url = article.get("url", "")
    title = article.get("title", "")

    if not url or not title or title == "[Removed]":
        return None

    return {
        "title": title,
        "link": url,
        "published": _parse_published(article.get("publishedAt", "")),
        "source": article.get("source", {}).get("name", ""),
        "description": article.get("description", "") or "",
    }


def fetch_newsapi_articles(api_key: str | None = None) -> list[dict]:
    """
    NewsAPI top-headlines からトピックごとに記事を取得する。
    無料プラン対応：/v2/top-headlines + country=us を使用。
    """
    key = api_key or os.getenv("NEWSAPI_KEY", "")
    if not key:
        print("[NewsAPI] ERROR: NEWSAPI_KEY が設定されていません。")
        return []

    all_articles: list[dict] = []
    seen_urls: set[str] = set()

    for topic in TOPICS:
        try:
            params = {
                "country": "us",
                "category": topic["category"],
                "pageSize": ARTICLES_PER_TOPIC,
                "apiKey": key,
            }
            # q が指定されている場合は追加（country と q は併用可）
            if topic["q"]:
                params["q"] = topic["q"]

            resp = requests.get(
                f"{NEWSAPI_BASE}/top-headlines",
                params=params,
                timeout=FETCH_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "ok":
                print(
                    f"[NewsAPI] Error for '{topic['label']}': {data.get('message')} (code: {data.get('code')})"
                )
                continue

            count = 0
            for article in data.get("articles", []):
                normalized = _normalize_article(article)
                if normalized and normalized["link"] not in seen_urls:
                    normalized["topic"] = topic["label"]
                    all_articles.append(normalized)
                    seen_urls.add(normalized["link"])
                    count += 1

            print(f"[NewsAPI] {topic['label']}: {count} 件取得")

        except Exception as e:
            print(f"[NewsAPI] Failed for '{topic['label']}': {e}")

    all_articles.sort(key=lambda x: x["published"], reverse=True)
    result = all_articles[:MAX_ARTICLES]
    print(f"[NewsAPI] 合計 {len(result)} 件取得完了")
    return result
