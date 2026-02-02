def records_to_markdown_table(records):
    """
    LLM が返した JSON レコードのリストを Markdown の表に変換する。
    """

    header = (
        "| STEEP | 日付 | タイトル | 要約 | 情報源 | 重要度 | 影響度 | 備考 |\n"
        "|-------|------|----------|------|--------|--------|--------|------|\n"
    )

    rows = ""
    for r in records:
        rows += (
            f"| {r['steep_category']} "
            f"| {r['date']} "
            f"| {r['title']} "
            f"| {r['summary']} "
            f"| [link]({r['source']}) "
            f"| {r['news_importance']} "
            f"| {r['company_impact']} "
            f"| {r['note']} |\n"
        )

    return header + rows
