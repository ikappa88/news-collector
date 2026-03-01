"""
table_formatter.py

ニュースダイジェストのMarkdown生成モジュール。

【ブロック構成】
  第1ブロック: Yahoo!ニュース（主要・国内・経済・IT/科学を統合、TOP10表示）
  第2ブロック: BBC World（TOP10表示）
  第3ブロック: Hacker News（TOP10表示）
"""

from __future__ import annotations
from datetime import datetime

# ── カテゴリ絵文字マップ ────────────────────────────────────

CATEGORY_EMOJI: dict[str, str] = {
    # HN用
    "AI / ML": "🤖",
    "Dev Tools": "🛠️",
    "Security": "🔒",
    "Infra / Cloud": "☁️",
    "Business": "💼",
    "Science": "🔬",
    "Policy / Law": "🏛️",
    "Other": "🔹",
    # Yahoo! / 国内ニュース用
    "政治・行政": "🏛️",
    "経済・産業": "💹",
    "国際": "🌏",
    "社会・事件": "📰",
    "科学・環境": "🔬",
    "文化・スポーツ": "🎭",
    "その他": "🔹",
    # BBC用
    "紛争・安全保障": "⚔️",
    "気候・環境": "🌍",
    "アジア": "🌏",
    # NewsAPI用（互換）
    "AI・テクノロジー": "🤖",
    "ビジネス・経済": "💼",
    "政治・国際": "🏛️",
}

# ── ブロック定義 ────────────────────────────────────────────
# 順番がそのまま出力順になる

BLOCKS: list[dict] = [
    # ── 第1ブロック：Yahoo!ニュース（4カテゴリ統合） ──
    {
        "id": "yahoo",
        "label": "Yahoo!ニュース",
        "sources": ["yahoo_top", "yahoo_domestic", "yahoo_business", "yahoo_science"],
        "top_n": 10,
        "columns": [
            ("スコア", "score", None),
            ("カテゴリ", "category", None),
            ("フィード", "source", 12),
            ("タイトル", "title", 55),
            ("要約", "summary", None),
            ("公開日時", "published", None),
            ("URL", "url", 50),
        ],
    },
    # ── 第2ブロック：BBC World ──
    {
        "id": "bbc",
        "label": "BBC World",
        "sources": ["bbc_world"],
        "top_n": 10,
        "columns": [
            ("スコア", "score", None),
            ("カテゴリ", "category", None),
            ("タイトル", "title", 60),
            ("要約", "summary", None),
            ("公開日時", "published", None),
            ("URL", "url", 50),
        ],
    },
    # ── 第3ブロック：Hacker News ──
    {
        "id": "hn",
        "label": "Hacker News",
        "sources": ["hn"],
        "top_n": 10,
        "columns": [
            ("スコア", "score", None),
            ("HNポイント", "hn_points", None),
            ("コメント", "comments", None),
            ("カテゴリ", "category", None),
            ("タイトル", "title", 55),
            ("要約", "summary", None),
            ("公開日時", "published", None),
            ("URL", "url", 50),
        ],
    },
]


# ── ユーティリティ ──────────────────────────────────────────


def _truncate(text: str, max_len: int | None) -> str:
    if not text:
        return ""
    if max_len is None or len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _escape_pipe(text: str) -> str:
    return text.replace("|", "\\|")


def _cell(record: dict, key: str, max_len: int | None) -> str:
    value = record.get(key, "")

    if key == "url":
        return _truncate(str(value), max_len)

    if key == "title":
        url = record.get("url", "")
        title_text = _truncate(str(value), max_len)
        return f"[{title_text}]({url})" if url else title_text

    if key == "score":
        return str(value)

    if key in ("hn_points", "comments"):
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return str(value)

    if key == "category":
        emoji = CATEGORY_EMOJI.get(str(value), "🔹")
        return f"{emoji} {value}"

    if key == "source":
        # フィード名を短縮表示
        FEED_SHORT = {
            "Yahoo!ニュース 主要": "主要",
            "Yahoo!ニュース 国内": "国内",
            "Yahoo!ニュース 経済": "経済",
            "Yahoo!ニュース IT・科学": "IT・科学",
            "BBC Asia": "Asia",
            "BBC World": "World",
        }
        label = FEED_SHORT.get(str(value), str(value))
        return _truncate(label, max_len)

    return _truncate(str(value), max_len)


# ── テーブル生成 ────────────────────────────────────────────


def _build_table(records: list[dict], columns: list[tuple]) -> str:
    if not records:
        return "_データなし_"
    headers = [col[0] for col in columns]
    header_row = "| " + " | ".join(headers) + " |"
    sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    rows = []
    for rec in records:
        cells = [_escape_pipe(_cell(rec, col[1], col[2])) for col in columns]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header_row, sep_row] + rows)


def _build_others_list(records: list[dict]) -> str:
    if not records:
        return ""
    lines = []
    for rec in records:
        title = rec.get("title", "（タイトルなし）")
        url = rec.get("url", "")
        src = rec.get("source", "")
        label = f"[{title}]({url})" if url else title
        lines.append(f"- {label}（{src}）" if src else f"- {label}")
    return "\n".join(lines)


# ── ブロック生成 ────────────────────────────────────────────


def _build_block(block: dict, grouped: dict[str, list[dict]]) -> str | None:
    """
    1ブロック分のMarkdownを生成する。
    対象ソースのレコードを統合してスコア降順で並べ、TOP Nを表示する。
    対象ソースが grouped に存在しない場合は None を返す。
    """
    # 対象ソースのレコードを統合
    all_records: list[dict] = []
    for src_key in block["sources"]:
        all_records.extend(grouped.get(src_key, []))

    if not all_records:
        return None

    top_n = block["top_n"]
    columns = block["columns"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    sorted_records = sorted(
        all_records, key=lambda r: int(r.get("score", 0)), reverse=True
    )
    top_records = sorted_records[:top_n]
    other_records = sorted_records[top_n:]

    lines: list[str] = [
        f"## {block['label']}",
        f"_生成日時: {now}_",
        f"### 重要ニュース TOP{top_n}",
        _build_table(top_records, columns),
    ]

    if other_records:
        lines.append(f"### その他のニュース（{len(other_records)} 件）")
        lines.append(_build_others_list(other_records))

    return "\n\n".join(lines)


# ── エントリポイント ────────────────────────────────────────


def build_digest(grouped: dict[str, list[dict]]) -> str:
    """
    grouped = { "yahoo_top": [...], "bbc_world": [...], "hn": [...], ... }
    を受け取り、BLOCKS 定義の順番でMarkdownダイジェストを生成する。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sections: list[str] = [
        "# ニュースダイジェスト",
        f"_生成日時: {now}_",
        "---",
    ]

    for block in BLOCKS:
        md = _build_block(block, grouped)
        if md:
            sections.append(md)
            sections.append("---")

    return "\n\n".join(sections) + "\n"
