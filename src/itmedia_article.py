import requests
from bs4 import BeautifulSoup


def fetch_itmedia_article_body(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # ITmedia の本文は articleText 内にある
        article = soup.select_one(".articleText") or soup.select_one(".article-body")

        if not article:
            return ""

        paragraphs = article.find_all("p")
        body = "\n".join(p.get_text(strip=True) for p in paragraphs)

        return body

    except Exception as e:
        print(f"ITmedia本文取得エラー: {e}")
        return ""
