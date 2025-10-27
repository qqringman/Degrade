@echo off
echo ==================================
echo JIRA Degrade %% 分析系統
echo ==================================
echo.

REM 設定環境變數
set JIRA_TOKEN=
set JIRA_SITE=jira.realtek.com
set JIRA_USER=vince_lin
set JIRA_PASSWORD=Amon100!
set VENDOR_JIRA_TOKEN=
set VENDOR_JIRA_SITE=vendorjira.realtek.com
set VENDOR_JIRA_USER=vince_lin
set VENDOR_JIRA_PASSWORD=Amon100!

echo 檢查 Python 環境...
python --version

echo.
echo 檢查套件...
pip show Flask >nul 2>&1
if errorlevel 1 (
    echo Flask 未安裝，正在安裝...
    pip install -r requirements.txt
)

echo.
echo 啟動 Flask 應用程式...
echo 請在瀏覽器開啟: http://localhost:5000
echo.
echo 按 Ctrl+C 停止服務
echo.

python app.py
pause
