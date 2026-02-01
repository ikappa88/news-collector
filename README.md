# News Collector

毎日決まった時間にニュースを自動収集し、Markdown形式で保存、さらに必要に応じてメール通知も行う自動化システムです。
**Windows タスクスケジューラ**と**Python**を組み合わせて動作します。

---

## 🚀 主な機能

- Yahooニュースのカテゴリ別RSS取得
- ITmediaの最新記事取得
- Markdown形式でのログ生成（`logs/YYYY-MM-DD.md`）
- Gmailを使ったメール通知（ニュース全文送信）
- GitHubへの自動push（任意）
- タスクスケジューラによる毎日の自動実行

---

## 📂 プロジェクト構成

```
news-collector/
├── src/
│   ├── main.py
│   ├── rss_sources.py
│   ├── itmedia.py
├── logs/            # 自動生成（.gitignoreで除外）
├── .env             # 秘密情報（.gitignoreで除外）
├── .gitignore
├── auto_push.bat
└── README.md
```

---

## 🔐 環境変数（`.env`）

このプロジェクトでは、メールアドレスやアプリパスワードなどの秘密情報を `.env` に保存します。
`.env` は `.gitignore` によりGitHubへは公開されません。

**`.env` の例：**
```
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=your_app_password
GMAIL_TO=destination@example.com
```

---

## 🛠 セットアップ手順

### 1. 仮想環境の作成

```sh
python -m venv .venv
```

### 2. 仮想環境の有効化

```sh
.venv\Scripts\activate  # Windows の場合
```
または
```sh
source .venv/bin/activate  # Mac/Linux の場合
```

### 3. 依存パッケージのインストール

```sh
pip install -r requirements.txt
```

必要に応じて `requirements.txt` を作成してください。

---

## ✉️ Gmail の設定

1. Googleアカウントで「2段階認証」を有効化
2. 「アプリパスワード」を発行
3. `.env` に反映

---

## 🖥 自動実行（Windows タスクスケジューラ）

1. **タスクスケジューラ**を開く
2. 新しいタスクを作成
3. 「操作」で以下を設定：

    - **プログラム**:
      `C:\Windows\System32\cmd.exe`
    - **引数**:
      `/c "C:\path\to\news-collector\auto_push.bat"`
    - **開始（Start in）**:
      `C:\path\to\news-collector`

4. トリガーで毎日8:00等、お好きな時間を指定

---

## 📝 ログ生成例

```
## Yahooニュース: 国内
- [ニュースタイトル1](リンク1)
- [ニュースタイトル2](リンク2)
...

## ITmedia
- [ITmedia記事タイトル1](リンク1)
...
```

---

## 📧 メール通知について

`main.py` の最後で、生成した最新ログファイルの内容をメール本文として送信します。

---

## 🤝 ライセンス

MIT License（必要に応じて変更してください）

---

## 📌 注意事項

- `.env` や `logs/` フォルダはGitHubに公開されません
- Gmailのアプリパスワードは**絶対に共有しないこと**
- 公開に必要な情報だけをコミットしてください

