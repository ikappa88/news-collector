# News Collector

News Collector は、毎日決まった時間にニュースを自動収集し、AI による要約・分類・重要度評価を行い、Markdown 形式で保存しつつ、必要に応じてメール通知も行う自動化システムです。

Windows タスクスケジューラと Python、そしてローカル LLM（Ollama）を組み合わせて動作します。このシステムは、Yahoo!ニュースと ITmedia の最新記事を取得し、タイトルの高速分類、本文の詳細分析、STEEP 分類（Social / Technological / Economic / Environmental / Political）、重要度・影響度の評価を行います。

分析結果は Markdown テーブルとして保存され、Gmail を使ってメール通知することもできます。

## 主な機能

- Yahoo!ニュースのカテゴリ別 RSS 取得
- ITmedia の最新記事取得
- タイトルの高速 LLM 分類（前処理）
- 本文の詳細 LLM 分析（要約・分類・重要度評価）
- 壊れた JSON の自動修復と補正
- Markdown 形式でのレポート生成（`logs` フォルダに保存）
- Gmail を使ったメール通知
- Windows タスクスケジューラによる毎日の自動実行
- 必要に応じて GitHub への自動 push（任意）

## STEEP 分類

分析結果は以下の 5 分類のいずれかに強制的に補正されます。

- **Social**
- **Technological**
- **Economic**
- **Environmental**
- **Political**

## プロジェクト構成

```
news-collector
├── src/                    # 主要ロジック
│   ├── main.py            # 全体の実行フロー
│   ├── llm_analyzer.py    # 本文の詳細分析
│   ├── llm_title_filter.py # タイトルの高速分類
│   ├── rss_sources.py     # RSS 取得
│   ├── yahoo_article.py   # Yahoo本文取得
│   ├── itmedia_article.py # ITmedia本文取得
│   ├── itmedia.py         # ITmedia RSS
│   └── table_formatter.py # Markdown テーブル生成
├── logs/                   # レポートとエラーログ
│   ├── sent_YYYY-MM-DD_HHMM.md  # 送信済みレポート
│   └── error_YYYY-MM-DD_HHMM.txt # エラーログ
├── .env                    # Gmail 認証情報
├── .gitignore
├── requirements.txt
└── README.md
```

## 環境変数（.env）

メールアドレスやアプリパスワードなどの秘密情報は `.env` に保存します。このファイルは GitHub に公開されません。

```env
GMAIL_ADDRESS=あなたの Gmail
GMAIL_APP_PASSWORD=アプリパスワード
GMAIL_TO=送信先メールアドレス
```

## セットアップ手順

1. **仮想環境を作成する**
   ```bash
   python -m venv .venv
   ```

2. **仮想環境を有効化する**
   - Windows: `.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`

3. **依存パッケージをインストールする**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ollama でモデルを準備する**
   ```bash
   ollama pull qwen2.5
   ```

5. **`.env` を作成して Gmail の設定を記入する**

6. **実行する**
   ```bash
   python src/main.py
   ```

## 自動実行（Windows タスクスケジューラ）

1. タスクスケジューラを開く
2. 新しいタスクを作成
3. **操作**で以下を設定
   - プログラム: `C:\Windows\System32\cmd.exe`
   - 引数: `/c "C:\path\to\news-collector\auto_push.bat"`
   - 開始位置: `C:\path\to\news-collector`
4. **トリガー**で毎日実行時間を指定

## ログについて

### 成功ログ（送信済みレポート）

`logs/sent_YYYY-MM-DD_HHMM.md`

### エラーログ（本文取得失敗・LLMエラーなど）

`logs/error_YYYY-MM-DD_HHMM.txt`

## 注意事項

- `.env` や `logs` フォルダは GitHub に公開されません
- Gmail のアプリパスワードは絶対に共有しないこと
- 公開に不要なファイルはコミットしないこと
