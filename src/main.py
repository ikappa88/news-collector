from dotenv import load_dotenv

load_dotenv()

import os
from datetime import datetime
from rss_sources import fetch_yahoo_rss
from itmedia import fetch_itmedia
import os
import smtplib
from email.mime.text import MIMEText

print("main.py started")


def write_markdown_log():
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    log_path = os.path.join("logs", f"{date_str}.md")

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"# ニュースログ（{date_str}）\n\n")

        # Yahooニュース
        print("Fetching Yahoo RSS...")
        try:
            yahoo_data = fetch_yahoo_rss()
            print("Yahoo RSS fetched")
        except Exception as e:
            print(f"Yahoo RSS error: {e}")
            yahoo_data = []

        for category_data in yahoo_data:
            f.write(f"## Yahooニュース: {category_data['category']}\n")
            for item in category_data["items"]:
                f.write(f"- [{item['title']}]({item['link']})\n")
            f.write("\n")

        # ITmedia
        print("Fetching ITmedia...")
        try:
            itmedia_items = fetch_itmedia()
            print("ITmedia fetched")
        except Exception as e:
            print(f"ITmedia error: {e}")
            itmedia_items = []

        f.write("## ITmedia\n")
        for item in itmedia_items:
            f.write(f"- [{item['title']}]({item['link']})\n")
        f.write("\n")

    return log_path


def send_email_notification(subject, body):

    sender = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")
    recipient = os.getenv("GMAIL_TO")
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)


if __name__ == "__main__":
    log_file = write_markdown_log()

    # ログ内容を読み込む
    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()

    print("Sending email...")
    send_email_notification("ニュース収集結果", log_content)
    print("Email sent.")

print("main.py finished")
