from datetime import datetime
from rss_sources import fetch_yahoo_rss
from itmedia import fetch_itmedia
import os


def write_markdown_log():
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    log_path = os.path.join("logs", f"{date_str}.md")

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"# ニュースログ（{date_str}）\n\n")

        # Yahooニュース
        yahoo_data = fetch_yahoo_rss()
        for category_data in yahoo_data:
            f.write(f"## Yahooニュース: {category_data['category']}\n")
            for item in category_data["items"]:
                f.write(f"- [{item['title']}]({item['link']})\n")
            f.write("\n")

        # ITmedia
        f.write("## ITmedia\n")
        itmedia_items = fetch_itmedia()
        for item in itmedia_items:
            f.write(f"- [{item['title']}]({item['link']})\n")
        f.write("\n")


if __name__ == "__main__":
    write_markdown_log()
