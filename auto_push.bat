@echo off

REM プロジェクトフォルダへ移動
cd /d "C:\Users\je_is\python_notebook\Git_Folder\news-collector"

REM 仮想環境の python.exe を直接使う
"C:\Users\je_is\python_notebook\Git_Folder\news-collector\.venv\Scripts\python.exe" src/main.py

REM Git 操作
git add logs
git commit -m "Update news log" || echo No changes to commit
git push origin main
