"""
hackernews.py

Hacker News 公式 Firebase API を使ってトップ記事を取得する。
RSS版から置き換え。

API仕様: https://github.com/HackerNews/API
- Top Stories: https://hacker-news.firebaseio.com/v0/topstories.json
- Item:        https://hacker-news.firebaseio.com/v0/item/{id}.json

返り値フィールド（main.py と対応）:
    title       : str   記事タイトル（英語原文）
    link        : str   記事URL
    published   : str   投稿日時（YYYY-MM-DD HH:MM 形式）
    points      : int   HNポイント（upvote数）
    comments    : int   コメント数
    author      : str   投稿者名
    hn_id       : int   HN内部ID（コメントページURL生成に使用）
"""

import requests
import concurrent.futures
from datetime import datetime, timezone

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
TOP_STORIES_URL = f"{HN_API_BASE}/topstories.json"
ITEM_URL = f"{HN_API_BASE}/item/{{id}}.json"

FETCH_TIMEOUT = 10  # 1件あたりのタイムアウト（秒）
FETCH_WORKERS = 10  # 記事メタ取得の並列数（本文取得とは別）


def _fetch_item(item_id: int) -> dict | None:
    """HN APIから1件のアイテムを取得する"""
    try:
        resp = requests.get(
            ITEM_URL.format(id=item_id),
            timeout=FETCH_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[HN API] Failed to fetch item {item_id}: {e}")
        return None


def _normalize_item(raw: dict) -> dict | None:
    """
    HN APIのレスポンスを main.py が期待するフィールドに正規化する。
    story 以外（job, comment など）は除外。
    """
    if raw.get("type") != "story":
        return None
    if not raw.get("url"):
        # URLなし（HN内部記事 = Ask HN / Show HN のディスカッション）はスキップ
        # 必要なら HN コメントページ URL を生成してもよい
        return None

    # Unix timestamp → YYYY-MM-DD HH:MM
    ts = raw.get("time", 0)
    published = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    return {
        "title": raw.get("title", ""),
        "link": raw.get("url", ""),
        "published": published,
        "points": raw.get("score", 0),
        "comments": raw.get("descendants", 0),
        "author": raw.get("by", ""),
        "hn_id": raw.get("id", 0),
    }


def fetch_hn_top(limit: int = 30) -> list[dict]:
    """
    HN Top Stories を取得して正規化したリストを返す。

    Args:
        limit: 取得する最大件数（Top StoriesはAPIで最大500件返る）

    Returns:
        正規化済みアイテムのリスト（points降順）
    """
    # --- Top Stories IDリスト取得 ---
    try:
        resp = requests.get(TOP_STORIES_URL, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        story_ids = resp.json()[:limit]
    except Exception as e:
        print(f"[HN API] Failed to fetch top stories: {e}")
        return []

    print(f"[HN API] Fetching {len(story_ids)} items (workers={FETCH_WORKERS})...")

    # --- 各記事のメタ情報を並列取得 ---
    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
        futures = {executor.submit(_fetch_item, sid): sid for sid in story_ids}
        for future in concurrent.futures.as_completed(futures):
            raw = future.result()
            if raw:
                normalized = _normalize_item(raw)
                if normalized:
                    items.append(normalized)

    # points降順でソート（APIのTop順とは若干異なるが重要記事が上に来る）
    items.sort(key=lambda x: x["points"], reverse=True)
    print(f"[HN API] Fetched {len(items)} stories.")
    return items


def fetch_hn_article_body(url: str, timeout: int = 15) -> str:
    """
    記事URLから本文テキストを取得する。
    既存の実装を踏襲（BeautifulSoupで本文抽出）。
    """
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; news-collector/1.0)"},
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[BODY] Fetch failed: {url}\n  {e}")
        return ""

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")

        # script / style 除去
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        # 連続改行を圧縮
        import re

        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text[:8000]  # LLMのコンテキスト制限を考慮して8000文字に制限
    except Exception as e:
        print(f"[BODY] Parse failed: {url}\n  {e}")
        return ""
