#!/bin/bash

echo "=================================="
echo "JIRA Degrade % 分析系統"
echo "=================================="
echo ""

# 切換到腳本所在目錄
cd "$(dirname "$0")"
echo "工作目錄: $(pwd)"
echo ""

# 檢查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ 錯誤: 找不到 .env 文件"
    echo ""
    echo "請先設定環境變數："
    echo "1. 複製 .env.example 為 .env:"
    echo "   cp .env.example .env"
    echo ""
    echo "2. 編輯 .env 文件，填入你的 JIRA 帳號資訊"
    echo ""
    echo "3. 或在終端設定環境變數:"
    echo "   export JIRA_TOKEN='your_token'"
    echo "   export JIRA_USER='your_username'"
    echo "   ..."
    echo ""
    exit 1
fi

echo "✓ 找到 .env 文件"
echo "載入環境變數..."

# 載入 .env 文件
set -a
source .env
set +a

echo "✓ 環境變數已載入"
echo ""

echo "檢查 Python 環境..."
python3 --version

echo ""
echo "檢查檔案結構..."
if [ ! -d "templates" ]; then
    echo "錯誤: templates 目錄不存在！"
    exit 1
fi

if [ ! -f "templates/index.html" ]; then
    echo "錯誤: templates/index.html 不存在！"
    exit 1
fi

echo "✓ templates/index.html 存在"

echo ""
echo "檢查套件..."
pip3 show Flask > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Flask 未安裝，正在安裝..."
    pip3 install -r requirements.txt
fi

# 檢查是否需要安裝 python-dotenv
pip3 show python-dotenv > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "安裝 python-dotenv..."
    pip3 install python-dotenv
fi

echo ""
echo "啟動 Flask 應用程式..."
echo "請在瀏覽器開啟: http://localhost:5000"
echo ""
echo "按 Ctrl+C 停止服務"
echo ""

python3 app.py
