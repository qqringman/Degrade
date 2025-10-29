#!/bin/bash

#============================================================#
#  JIRA Degrade % 分析系統 - 啟動腳本                         #
#  作者: Vince                                                #
#  說明: 自動檢查環境並啟動 Flask 應用程式                     #
#============================================================#

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "============================================================"
echo -e "${BLUE}📊 JIRA Degrade % 分析系統 - 啟動中...${NC}"
echo "============================================================"
echo ""

# 切換到腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
echo -e "${GREEN}✓${NC} 工作目錄: $SCRIPT_DIR"
echo ""

#============================================================#
# 1. 檢查 Python 版本
#============================================================#
echo -e "${BLUE}[1/5] 檢查 Python 環境...${NC}"

# 嘗試找到 Python 命令
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}✗ 錯誤: 找不到 Python！${NC}"
    echo ""
    echo "請先安裝 Python 3.8 或以上版本："
    echo "  - Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  - macOS: brew install python3"
    echo "  - Windows: 從 https://www.python.org/ 下載安裝"
    echo ""
    exit 1
fi

# 檢查 Python 版本
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo -e "${GREEN}✓${NC} Python 版本: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${YELLOW}⚠ 警告: Python 版本過舊（需要 3.8+）${NC}"
    echo "建議升級 Python 以獲得最佳體驗"
fi
echo ""

#============================================================#
# 2. 檢查環境變數
#============================================================#
echo -e "${BLUE}[2/5] 檢查環境變數...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${RED}✗ 錯誤: 找不到 .env 文件！${NC}"
    echo ""
    echo "請按照以下步驟設定環境變數："
    echo "  1. 創建 .env 文件:"
    echo "     touch .env"
    echo ""
    echo "  2. 編輯 .env 文件，填入你的 JIRA 帳號資訊:"
    echo "     nano .env  # 或使用 vim, code 等編輯器"
    echo ""
    echo "  3. .env 文件內容範例:"
    echo "     JIRA_SITE=jira.realtek.com"
    echo "     JIRA_USER=your_username"
    echo "     JIRA_PASSWORD=your_password"
    echo "     ..."
    echo ""
    echo "  4. 或參考 README.md 的完整說明"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓${NC} 找到 .env 文件"

# 載入並檢查必要的環境變數
source .env

MISSING_VARS=()

if [ -z "$JIRA_SITE" ]; then MISSING_VARS+=("JIRA_SITE"); fi
if [ -z "$VENDOR_JIRA_SITE" ]; then MISSING_VARS+=("VENDOR_JIRA_SITE"); fi

# 檢查至少有帳密或 token
if [ -z "$JIRA_TOKEN" ] && ([ -z "$JIRA_USER" ] || [ -z "$JIRA_PASSWORD" ]); then
    MISSING_VARS+=("JIRA_USER/PASSWORD or JIRA_TOKEN");
fi

if [ -z "$VENDOR_JIRA_TOKEN" ] && ([ -z "$VENDOR_JIRA_USER" ] || [ -z "$VENDOR_JIRA_PASSWORD" ]); then
    MISSING_VARS+=("VENDOR_JIRA_USER/PASSWORD or VENDOR_JIRA_TOKEN");
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}✗ 錯誤: .env 文件缺少必要的環境變數！${NC}"
    echo ""
    echo "缺少的變數: ${MISSING_VARS[*]}"
    echo ""
    echo "請編輯 .env 文件並填入完整資訊"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓${NC} 環境變數已載入"
echo ""

#============================================================#
# 3. 檢查檔案結構
#============================================================#
echo -e "${BLUE}[3/5] 檢查檔案結構...${NC}"

MISSING_FILES=()

if [ ! -f "app.py" ]; then MISSING_FILES+=("app.py"); fi
if [ ! -f "jira_degrade_manager.py" ]; then MISSING_FILES+=("jira_degrade_manager.py"); fi
if [ ! -d "templates" ]; then MISSING_FILES+=("templates/"); fi
if [ ! -f "templates/index.html" ]; then MISSING_FILES+=("templates/index.html"); fi
if [ ! -f "requirements.txt" ]; then MISSING_FILES+=("requirements.txt"); fi

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo -e "${RED}✗ 錯誤: 缺少必要的檔案！${NC}"
    echo ""
    echo "缺少的檔案: ${MISSING_FILES[*]}"
    echo ""
    echo "請確認所有檔案都已正確放置"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓${NC} 所有必要檔案都存在"
echo ""

#============================================================#
# 4. 安裝 Python 套件
#============================================================#
echo -e "${BLUE}[4/5] 檢查 Python 套件...${NC}"

# 嘗試找到 pip 命令
PIP_CMD=""
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo -e "${YELLOW}⚠ 警告: 找不到 pip！${NC}"
    echo "嘗試使用 $PYTHON_CMD -m pip"
    PIP_CMD="$PYTHON_CMD -m pip"
fi

# 檢查關鍵套件是否已安裝
PACKAGES_TO_CHECK=("Flask" "requests" "python-dotenv" "openpyxl" "flask-cors")
MISSING_PACKAGES=()

for package in "${PACKAGES_TO_CHECK[@]}"; do
    if ! $PYTHON_CMD -c "import ${package,,}" 2>/dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠ 需要安裝以下套件: ${MISSING_PACKAGES[*]}${NC}"
    echo ""
    echo "正在安裝套件..."
    
    if $PIP_CMD install -r requirements.txt --quiet; then
        echo -e "${GREEN}✓${NC} 套件安裝完成"
    else
        echo -e "${RED}✗ 錯誤: 套件安裝失敗！${NC}"
        echo ""
        echo "請手動執行："
        echo "  $PIP_CMD install -r requirements.txt"
        echo ""
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} 所有必要套件已安裝"
fi
echo ""

#============================================================#
# 5. 啟動應用程式
#============================================================#
echo -e "${BLUE}[5/5] 啟動 Flask 應用程式...${NC}"
echo ""
echo "============================================================"
echo -e "${GREEN}🚀 啟動成功！${NC}"
echo "============================================================"
echo ""
echo -e "請在瀏覽器開啟: ${GREEN}http://localhost:5000${NC}"
echo ""
echo "或使用下方顯示的實際 IP 位址"
echo ""
echo -e "${YELLOW}提示:${NC}"
echo "  • 首次載入需要 30-60 秒"
echo "  • 按 Ctrl+C 停止服務"
echo "  • 查看 README.md 了解更多功能"
echo ""
echo "============================================================"
echo ""

# 執行 Flask 應用
exec $PYTHON_CMD app.py