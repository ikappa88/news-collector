from dotenv import load_dotenv

load_dotenv()

import os
import time
from datetime import datetime  # ★ これが必要！

from rss_sources import fetch_yahoo_rss
from itmedia import fetch_itmedia
import smtplib
from email.mime.text import MIMEText

from yahoo_article import fetch_yahoo_article_body
from itmedia_article import fetch_itmedia_article_body
from llm_analyzer import analyze_news_with_llm
from table_formatter import records_to_markdown_table
from llm_title_filter import analyze_title_fast

print("main.py started")

# ★ 実行開始時刻
start_time = time.time()


def collect_and_analyze_news():
    """
    Yahooニュース & ITmedia のニュースを収集し、
    タイトルで前捌き → 本文取得 → LLM詳細分析 → レコード化 まで行う。
    """
    # -----------------------------
    # 1. RSS取得
    # -----------------------------
    print("Fetching Yahoo RSS...")
    try:
        yahoo_data = fetch_yahoo_rss()
        print("Yahoo RSS fetched")
    except Exception as e:
        print(f"Yahoo RSS error: {e}")
        yahoo_data = []

    print("Fetching ITmedia...")
    try:
        itmedia_items = fetch_itmedia()
        print("ITmedia fetched")
    except Exception as e:
        print(f"ITmedia error: {e}")
        itmedia_items = []

    # -----------------------------
    # 2. タイトルで前捌き（高速判定）
    # -----------------------------
    buckets = {}  # STEEPごとのバケット

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
            news_importance = int(fast.get("news_importance", 0) or 0)
            company_impact = int(fast.get("company_impact", 0) or 0)
            score = news_importance + company_impact

            if not steep:
                continue

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
        news_importance = int(fast.get("news_importance", 0) or 0)
        company_impact = int(fast.get("company_impact", 0) or 0)
        score = news_importance + company_impact

        if not steep:
            continue

        buckets.setdefault(steep, []).append(
            (score, {"source": "itmedia", "item": item})
        )

    # -----------------------------
    # 3. STEEPごとに上位5件を選抜
    # -----------------------------
    selected_entries = []

    for steep, entries in buckets.items():
        entries.sort(key=lambda x: x[0], reverse=True)
        top5 = entries[:5]
        for _, entry in top5:
            selected_entries.append(entry)

    # -----------------------------
    # 4. 選抜されたニュースだけ本文取得 → LLM詳細分析
    # -----------------------------
    records = []

    for entry in selected_entries:
        source = entry["source"]
        item = entry["item"]

        title = item.get("title", "")
        link = item.get("link", "")
        date = item.get("pubDate") or item.get("dc:date") or ""

        if not link:
            continue

        if source == "itmedia":
            body_text = fetch_itmedia_article_body(link)
        else:
            body_text = fetch_yahoo_article_body(link)

        record = analyze_news_with_llm(
            title=title,
            date=date,
            source_url=link,
            body_text=body_text,
        )

        if record:
            records.append(record)

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

    # 送信内容をログとして保存
    now = datetime.now().strftime("%Y-%m-%d_%H%M")
    log_path = os.path.join("logs", f"sent_{now}.md")

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(table_md)

    # ★ 生成時間を追記
    elapsed = time.time() - start_time
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n\n---\n生成にかかった時間: {elapsed:.2f} 秒\n")

    print(f"Saved sent log: {log_path}")

    # メール送信
    print("Sending email...")
    send_email_notification("ニュース分析結果", table_md)
    print("Email sent.")

print("main.py finished")
