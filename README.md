# news-collector

LLM（Ollama）を使って複数のニュースソースを自動収集・要約し、Markdownダイジェストをメールで配信するツール。

## 機能

- 複数ソースからニュースを並列取得
- ローカルLLM（qwen2.5）で日本語要約・タイトル翻訳・カテゴリ分類
- Markdownダイジェストを自動生成・メール送信
- キャッシュ機能でデバッグ時の繰り返し実行を高速化

## ニュースソース構成

| ブロック | ソース | 言語 | 最大件数 |
|---|---|---|---|
| 第1 | Yahoo!ニュース（主要・国内・経済・IT/科学） | 日本語 | 各20件 → TOP10統合 |
| 第2 | BBC World | 英語 | 20件 |
| 第3 | Hacker News（公式API） | 英語 | 20件 |

## ファイル構成

```
news-collector/
├── .env                   # APIキー・メール設定
├── README.md
├── requirements.txt
└── src/
    ├── main.py            # エントリポイント・並列処理オーケストレーション
    ├── hackernews.py      # HN Firebase API取得
    ├── yahoo_news.py      # Yahoo!ニュースRSS取得
    ├── jp_news.py         # BBC World RSS取得
    ├── llm_analyzer.py    # LLM分析（要約・翻訳・カテゴリ・スコア）
    ├── llm_title_filter.py# タイトル高速フィルタ（LLM）
    └── table_formatter.py # Markdownダイジェスト生成
```

## セットアップ

### 1. 必要パッケージのインストール

```bash
pip install requests python-dotenv beautifulsoup4
```

### 2. Ollama のインストールとモデル取得

```bash
# Ollamaインストール後
ollama pull qwen2.5
```

### 3. `.env` の設定

```ini
# NewsAPI（オプション）
NEWSAPI_KEY=your_key_here

# Gmail送信設定
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=your_app_password
GMAIL_TO=recipient@gmail.com
```

> Gmail App Passwordの取得：Googleアカウント → セキュリティ → 2段階認証 → アプリパスワード

### 4. 実行

```bash
python src/main.py
```

## カテゴリ定義

### Yahoo! / 国内ニュース用
| カテゴリ | 絵文字 |
|---|---|
| 政治・行政 | 🏛️ |
| 経済・産業 | 💹 |
| 国際 | 🌏 |
| 社会・事件 | 📰 |
| 科学・環境 | 🔬 |
| 文化・スポーツ | 🎭 |

### Hacker News用
| カテゴリ | 絵文字 |
|---|---|
| AI / ML | 🤖 |
| Dev Tools | 🛠️ |
| Security | 🔒 |
| Infra / Cloud | ☁️ |
| Business | 💼 |
| Science | 🔬 |
| Policy / Law | 🏛️ |

## 新しいニュースソースの追加方法

1. `src/` に `xxx_news.py` を作成（`fetch_xxx() -> dict[str, list[dict]]` を実装）
2. `table_formatter.py` の `BLOCKS` リストにブロック定義を追加
3. `main.py` の `__main__` ブロックに収集処理を追加

## 出力例

```
logs/result_2026-03-01_120000.md  ← Markdownダイジェスト
logs/error_*.txt                  ← エラーログ
.cache/hn_top.json                ← HNキャッシュ（デバッグ用）
```

## 注意事項

- Yahoo!ニュースRSSは個人利用の範囲で使用してください
- Ollamaがローカルで起動している必要があります（`ollama serve`）
- 実行時間の目安：約2〜3分（ソース数・記事数による）
