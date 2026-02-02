from dotenv import load_dotenv

load_dotenv()

import os
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

from rss_sources import fetch_yahoo_rss
from itmedia import fetch_itmedia
from yahoo_article import fetch_yahoo_article_body
from itmedia_article import fetch_itmedia_article_body
from llm_analyzer import analyze_news_with_llm
from table_formatter import records_to_markdown_table
from llm_title_filter import analyze_title_fast

print("main.py started")

# ★ 全体処理開始時間
start_time = time.time()


def log_error(message: str):
    """エラーを logs/error_*.txt に保存"""
    os.makedirs("logs", exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = os.path.join("logs", f"error_{now}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(message)
    print(f"[ERROR] Logged to {path}")


def collect_and_analyze_news():
    print("Fetching Yahoo RSS...")
    try:
        yahoo_data = fetch_yahoo_rss()
        print("Yahoo RSS fetched")
    except Exception as e:
        log_error(f"Yahoo RSS error: {e}")
        yahoo_data = []

    print("Fetching ITmedia...")
    try:
        itmedia_items = fetch_itmedia()
        print("ITmedia fetched")
    except Exception as e:
        log_error(f"ITmedia error: {e}")
        itmedia_items = []

    # タイトル前捌き
    buckets = {}

    # Yahoo
    for category_data in yahoo_data:
        for item in category_data.get("items", []):
            title = item.get("title", "")
            if not title:
                continue

            fast = analyze_title_fast(title)
            if not fast:
                continue

            steep = fast.get("steep_category", "").strip()
            score = int(fast.get("news_importance", 0)) + int(
                fast.get("company_impact", 0)
            )

            if steep:
                buckets.setdefault(steep, []).append(
                    (score, {"source": "yahoo", "item": item})
                )

    # ITmedia
    for item in itmedia_items:
        title = item.get("title", "")
        if not title:
            continue

        fast = analyze_title_fast(title)
        if not fast:
            continue

        steep = fast.get("steep_category", "").strip()
        score = int(fast.get("news_importance", 0)) + int(fast.get("company_impact", 0))

        if steep:
            buckets.setdefault(steep, []).append(
                (score, {"source": "itmedia", "item": item})
            )

    # 上位5件
    selected_entries = []
    for steep, entries in buckets.items():
        entries.sort(key=lambda x: x[0], reverse=True)
        selected_entries.extend([entry for _, entry in entries[:5]])

    # 本文取得 → LLM 詳細分析
    records = []

    for entry in selected_entries:
        source = entry["source"]
        item = entry["item"]

        title = item.get("title", "")
        link = item.get("link", "")
        date = item.get("pubDate") or item.get("dc:date") or ""

        if not link:
            log_error(f"Missing link for title: {title}")
            continue

        # 本文取得
        try:
            if source == "itmedia":
                body_text = fetch_itmedia_article_body(link)
            else:
                body_text = fetch_yahoo_article_body(link)
        except Exception as e:
            log_error(f"Article fetch error: {title}\n{e}")
            continue

        # ★ LLM 処理時間計測
        llm_start = time.time()
        record = analyze_news_with_llm(
            title=title,
            date=date,
            source_url=link,
            body_text=body_text,
        )
        llm_elapsed = time.time() - llm_start
        print(f"LLM processed: {title[:20]}... ({llm_elapsed:.2f} sec)")

        if record:
            record["llm_time"] = llm_elapsed
            records.append(record)
        else:
            log_error(f"LLM returned None for: {title}")

    return records


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
    print("Collecting, filtering, and analyzing news...")
    records = collect_and_analyze_news()

    print("Generating markdown table...")
    table_md = records_to_markdown_table(records)

    # 送信内容ログ保存
    now = datetime.now().strftime("%Y-%m-%d_%H%M")
    log_path = os.path.join("logs", f"sent_{now}.md")
    os.makedirs("logs", exist_ok=True)

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(table_md)

    # ★ 全体処理時間を追記
    total_elapsed = time.time() - start_time
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n\n---\n生成にかかった時間: {total_elapsed:.2f} 秒\n")

    print(f"Saved sent log: {log_path}")

    print("Sending email...")
    send_email_notification("ニュース分析結果", table_md)
    print("Email sent.")

print("main.py finished")
