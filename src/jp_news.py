"""
jp_news.py

BBC公式RSSから国際・アジアニュースを取得する。
（朝日・毎日はBot対策によりフェッチ不可のため置き換え）

使用フィード（feeds.bbci.co.uk - 安定稼働）:
  - BBC World : https://feeds.bbci.co.uk/news/world/rss.xml

返り値フィールド:
    title       : str   記事タイトル
    link        : str   記事URL
    published   : str   公開日時（YYYY-MM-DD HH:MM）
    source      : str   "BBC News"
    description : str   リード文（本文フォールバック用）
"""

import requests
import concurrent.futures
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FETCH_TIMEOUT = 15
MAX_PER_FEED = 20

FEEDS = [
    {
        "source_key": "bbc_world",
        "label": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
    },
]


def _parse_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw


def _fetch_feed(feed: dict) -> list[dict]:
    try:
        resp = requests.get(
            feed["url"],
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; news-collector/1.0)"},
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[{feed['label']}] Fetch failed: {e}")
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        print(f"[{feed['label']}] XML parse failed: {e}")
        return []

    results = []
    for item in root.findall(".//item")[:MAX_PER_FEED]:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub = item.findtext("pubDate", "")
        desc = item.findtext("description", "").strip()

        if not title or not link:
            continue

        results.append(
            {
                "title": title,
                "link": link,
                "published": _parse_date(pub),
                "source": feed["label"],
                "description": desc,
            }
        )

    print(f"[{feed['label']}] {len(results)} 件取得")
    return results


def fetch_jp_news() -> dict[str, list[dict]]:
    """
    BBCのフィードを並列取得し、ソースキーでグループ化した辞書を返す。
    Returns: { "bbc_world": [...] }
    """
    results: dict[str, list[dict]] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(_fetch_feed, feed): feed for feed in FEEDS}
        for future in concurrent.futures.as_completed(futures):
            feed = futures[future]
            items = future.result()
            if items:
                results[feed["source_key"]] = items

    return results
