from dotenv import load_dotenv
from pathlib import Path

# src/ と同階層、または1つ上の階層の .env を自動探索する
_here = Path(__file__).resolve().parent
load_dotenv(_here / ".env") or load_dotenv(_here.parent / ".env")

import os
import time
import json
import concurrent.futures
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime

# --- 情報源 ---
from hackernews import fetch_hn_top, fetch_hn_article_body
from jp_news import fetch_jp_news
from yahoo_news import fetch_yahoo_news

from llm_analyzer import analyze_news_with_llm
from table_formatter import build_digest
from llm_title_filter import analyze_title_fast

print("main.py started")


start_time = time.time()

# --- 設定 ---
MAX_ARTICLES = 20  # 1回の実行で収集する最大件数
MAX_WORKERS = 5  # LLM並列実行の同時実行数
FAST_SCORE_THRESHOLD = 3  # fast LLM スコアの足切り閾値

CACHE_DIR = ".cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def cached_fetch(func, key):
    """フェッチ結果をローカルにキャッシュする（繰り返し実行の高速化）"""
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        print(f"[CACHE] Loaded from {path}")
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    result = func()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result


def print_progress(current, total, prefix=""):
    bar_length = 30
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "█" * filled + "-" * (bar_length - filled)
    print(f"{prefix} [{bar}] {current}/{total}")


def log_error(message: str):
    os.makedirs("logs", exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = os.path.join("logs", f"error_{now}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(message)
    print(f"[ERROR] Logged to {path}")


def _parse_date(raw: str) -> str:
    """RSS形式の日付文字列を YYYY-MM-DD HH:MM に変換する。失敗時はそのまま返す。"""
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw


def _process_item(item: dict) -> dict | None:
    """
    1件のHN記事を処理する（タイトルフィルタ → 本文取得 → LLM分析）。
    スキップ・失敗時は None を返す。
    """
    title = item.get("title", "")
    link = item.get("link", "")

    # --- タイトルの簡易フィルタ（fast LLM） ---
    fast = analyze_title_fast(title)
    if not fast:
        print(f"[SKIP] Fast LLM returned None: {title[:50]}")
        return None

    fast_score = int(fast.get("news_importance", 0)) + int(
        fast.get("company_impact", 0)
    )
    if fast_score < FAST_SCORE_THRESHOLD:
        print(f"[SKIP] Score too low ({fast_score}): {title[:50]}")
        return None

    # --- 本文取得 ---
    try:
        body_text = fetch_hn_article_body(link)
    except Exception as e:
        log_error(f"Article fetch error: {title}\n{e}")
        return None

    if len(body_text) < 50:
        log_error(f"Body too short for: {title}\nURL: {link}")
        return None

    # --- LLM 詳細分析 ---
    llm_start = time.time()
    record = analyze_news_with_llm(
        title=title,
        date=_parse_date(item.get("published", "")),
        source_url=link,
        body_text=body_text,
        hn_points=item.get("points", 0),
        comments=item.get("comments", 0),
    )
    llm_elapsed = time.time() - llm_start
    record["llm_time"] = llm_elapsed
    print(f"[DONE] {llm_elapsed:.1f}s | score={record.get('score')} | {title[:50]}")

    return record


def collect_and_analyze_news() -> dict:
    """
    ニュースを収集・分析し、ソースキーでグループ化した辞書を返す。
    返り値: { "hn": [...records] }
    """
    # --- Hacker News RSS フェッチ（キャッシュあり） ---
    print(f"[1/2] Fetching Hacker News RSS...")
    try:
        hn_items = cached_fetch(lambda: fetch_hn_top(limit=MAX_ARTICLES), "hn_top")
        print(f"Hacker News API fetched ✓ ({len(hn_items)} items)")
    except Exception as e:
        log_error(f"Hacker News API error: {e}")
        return {}

    if not hn_items:
        print("No HN items found.")
        return {}

    # 上位 MAX_ARTICLES 件に絞る
    targets = hn_items[:MAX_ARTICLES]
    print(f"[2/2] Processing {len(targets)} articles (max_workers={MAX_WORKERS})...")

    # --- 並列処理：本文取得 + LLM分析 ---
    records = []
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_process_item, item): item for item in targets}
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            print_progress(completed, len(targets), prefix="Progress")
            try:
                result = future.result()
                if result is not None:
                    records.append(result)
            except Exception as e:
                item = futures[future]
                log_error(f"Unexpected error for {item.get('title', '')}: {e}")

    print(f"\nCollected {len(records)} records from {len(targets)} articles.")
    return {"hn": records} if records else {}


def _process_jp_items(source_key: str, items: list[dict]) -> list[dict]:
    """
    国内ニュース（朝日・毎日）の記事リストを並列処理してrecordリストを返す。
    """
    if not items:
        return []

    print(
        f"[{source_key}] Processing {len(items)} articles (max_workers={MAX_WORKERS})..."
    )

    records = []
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_process_jp_item, item): item for item in items}
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            print_progress(completed, len(items), prefix=source_key)
            try:
                result = future.result()
                if result is not None:
                    records.append(result)
            except Exception as e:
                item = futures[future]
                log_error(f"[{source_key}] Error for {item.get('title', '')}: {e}")

    print(f"[{source_key}] Collected {len(records)} records.")
    return records


def _process_jp_item(item: dict) -> dict | None:
    """国内ニュース1件を処理する（本文取得 → LLM分析）"""
    title = item.get("title", "")
    link = item.get("link", "")

    try:
        body_text = fetch_hn_article_body(link)
    except Exception as e:
        log_error(f"[JP] Article fetch error: {title}\n{e}")
        body_text = ""

    # 本文取得失敗時はRSSのdescriptionで補完
    if len(body_text) < 50:
        body_text = item.get("description", "")

    if len(body_text) < 20:
        return None

    llm_start = time.time()
    record = analyze_news_with_llm(
        title=title,
        date=item.get("published", ""),
        source_url=link,
        body_text=body_text,
        hn_points=0,
        comments=0,
    )
    llm_elapsed = time.time() - llm_start
    record["llm_time"] = llm_elapsed
    record["media_source"] = item.get("source", "")
    print(f"[DONE] {llm_elapsed:.1f}s | {title[:50]}")
    return record


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

    # --- ログファイルパスを定義 ---
    now_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", f"result_{now_str}.md")

    # --- ニュース収集・分析 ---
    print("\n--- Hacker News ---")
    grouped = collect_and_analyze_news()

    print("\n--- Yahoo!ニュース ---")
    yahoo_grouped = fetch_yahoo_news()
    for src_key, items in yahoo_grouped.items():
        yahoo_records = _process_jp_items(src_key, items)
        if yahoo_records:
            grouped[src_key] = yahoo_records

    print("\n--- BBC News ---")
    jp_grouped = fetch_jp_news()
    for src_key, items in jp_grouped.items():
        jp_records = _process_jp_items(src_key, items)
        if jp_records:
            grouped[src_key] = jp_records

    if not grouped:
        print("No records to output.")
    else:
        total_elapsed = time.time() - start_time
        md_output = build_digest(grouped)
        md_output += f"\n---\n生成にかかった時間: {total_elapsed:.2f} 秒\n"

        # --- ログ保存 ---
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(md_output)
        print(f"Saved log: {log_path}")

        # --- メール送信 ---
        print("Sending email...")
        try:
            send_email_notification("ニュース分析結果", md_output)
            print("Email sent.")
        except smtplib.SMTPException as e:
            log_error(f"Email failed: {e}")
            print("[WARN] Email could not be sent.")

    print("main.py finished")
