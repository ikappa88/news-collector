import feedparser

RSS_FEEDS = {
    "主要": "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
    "国内": "https://news.yahoo.co.jp/rss/topics/domestic.xml",
    "国際": "https://news.yahoo.co.jp/rss/topics/world.xml",
    "経済": "https://news.yahoo.co.jp/rss/topics/business.xml",
    "IT": "https://news.yahoo.co.jp/rss/topics/it.xml",
    "科学": "https://news.yahoo.co.jp/rss/topics/science.xml",
}


def fetch_yahoo_rss():
    results = []

    for category, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        category_items = []

        for entry in feed.entries:
            category_items.append({"title": entry.title, "link": entry.link})

        results.append({"category": category, "items": category_items})

    return results
