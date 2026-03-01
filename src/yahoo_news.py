"""
yahoo_news.py

Yahoo!ニュース公式RSSから記事を取得する。
個人利用の範囲での使用を想定。

使用フィード:
  主要   : https://news.yahoo.co.jp/rss/topics/top-picks.xml
  国内   : https://news.yahoo.co.jp/rss/topics/domestic.xml
  経済   : https://news.yahoo.co.jp/rss/topics/business.xml
  IT・科学: https://news.yahoo.co.jp/rss/topics/science.xml

返り値フィールド:
    title       : str   記事タイトル
    link        : str   記事URL
    published   : str   公開日時（YYYY-MM-DD HH:MM）
    source      : str   フィードラベル
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
        "source_key": "yahoo_top",
        "label": "Yahoo!ニュース 主要",
        "url": "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
    },
    {
        "source_key": "yahoo_domestic",
        "label": "Yahoo!ニュース 国内",
        "url": "https://news.yahoo.co.jp/rss/topics/domestic.xml",
    },
    {
        "source_key": "yahoo_business",
        "label": "Yahoo!ニュース 経済",
        "url": "https://news.yahoo.co.jp/rss/topics/business.xml",
    },
    {
        "source_key": "yahoo_science",
        "label": "Yahoo!ニュース IT・科学",
        "url": "https://news.yahoo.co.jp/rss/topics/science.xml",
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
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
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

        # Yahoo!ニュースは<guid>が記事の元URL
        guid = item.findtext("guid", "").strip()
        if guid.startswith("http"):
            link = guid

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


def fetch_yahoo_news() -> dict[str, list[dict]]:
    """
    Yahoo!ニュースの各フィードを並列取得し、ソースキーでグループ化した辞書を返す。
    Returns: { "yahoo_top": [...], "yahoo_domestic": [...], ... }
    """
    results: dict[str, list[dict]] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_fetch_feed, feed): feed for feed in FEEDS}
        for future in concurrent.futures.as_completed(futures):
            feed = futures[future]
            items = future.result()
            if items:
                results[feed["source_key"]] = items

    return results
