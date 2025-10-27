#!/bin/bash

echo "=================================="
echo "JIRA Degrade % 分析系統"
echo "=================================="
echo ""

# 設定環境變數
export JIRA_TOKEN=''
export JIRA_SITE='jira.realtek.com'
export JIRA_USER='vince_lin'
export JIRA_PASSWORD='Amon100!'
export VENDOR_JIRA_TOKEN=''
export VENDOR_JIRA_SITE='vendorjira.realtek.com'
export VENDOR_JIRA_USER='vince_lin'
export VENDOR_JIRA_PASSWORD='Amon100!'

echo "檢查 Python 環境..."
python3 --version

echo ""
echo "檢查套件..."
pip3 show Flask > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Flask 未安裝，正在安裝..."
    pip3 install -r requirements.txt
fi

echo ""
echo "啟動 Flask 應用程式..."
echo "請在瀏覽器開啟: http://localhost:5000"
echo ""
echo "按 Ctrl+C 停止服務"
echo ""

python3 app.py
