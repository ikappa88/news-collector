import requests
from bs4 import BeautifulSoup

URL = "https://www.itmedia.co.jp/news/"


def fetch_itmedia():
    res = requests.get(URL)

    # ★ 文字化け対策：推定エンコーディングを使用
    res.encoding = res.apparent_encoding

    soup = BeautifulSoup(res.text, "html.parser")

    # 複数のレイアウトに対応したセレクタ
    articles = soup.select("div.colBox h2 a, div.colBoxTitle a, .newsList a")

    items = []
    for a in articles:
        title = a.get_text(strip=True)
        link = a.get("href")

        if not link:
            continue

        if link.startswith("/"):
            link = "https://www.itmedia.co.jp" + link

        items.append({"title": title, "link": link})

    return items
