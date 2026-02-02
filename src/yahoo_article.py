import requests
from bs4 import BeautifulSoup


def fetch_yahoo_article_body(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Yahooニュースの本文は article タグ内にあることが多い
        article = soup.select_one("article")

        if not article:
            return ""

        paragraphs = article.find_all("p")
        body = "\n".join(p.get_text(strip=True) for p in paragraphs)

        return body

    except Exception as e:
        print(f"Yahoo本文取得エラー: {e}")
        return ""
