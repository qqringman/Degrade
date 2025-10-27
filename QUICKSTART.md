# 快速開始指南

## 📦 檔案說明

- `app.py` - Flask 主應用程式
- `jira_degrade_manager.py` - JIRA 資料管理模組
- `config.py` - 設定檔（可直接修改 JIRA 帳號資訊）
- `requirements.txt` - Python 套件依賴
- `templates/index.html` - 網頁介面
- `test_connection.py` - JIRA 連線測試腳本
- `start.sh` - Linux/Mac 啟動腳本
- `start.bat` - Windows 啟動腳本
- `README.md` - 完整說明文件

## 🚀 快速啟動（3 步驟）

### Windows:
```cmd
1. 雙擊 start.bat
2. 等待載入完成
3. 開啟瀏覽器訪問 http://localhost:5000
```

### Linux/Mac:
```bash
1. ./start.sh
2. 等待載入完成
3. 開啟瀏覽器訪問 http://localhost:5000
```

### 手動啟動:
```bash
# 1. 安裝套件
pip install -r requirements.txt

# 2. 測試連線（可選）
python test_connection.py

# 3. 啟動應用
python app.py
```

## ⚙️ 設定說明

JIRA 帳號資訊已經預設在 `config.py` 中，如需修改：

```python
# 編輯 config.py
JIRA_USER = '你的帳號'
JIRA_PASSWORD = '你的密碼'
JIRA_TOKEN = '你的Token'
```

## 📊 功能說明

1. **整體統計** - 顯示 Degrade %, Degrade 總數, Resolved 總數
2. **每週趨勢圖** - 顯示每週 Degrade % 的變化趨勢
3. **數量對比圖** - 顯示每週 Degrade 與 Resolved 的數量對比
4. **Assignee 分布** - 顯示誰解最多題、誰有最多 degrade

## 🔍 資料來源

系統會從以下 4 個 JIRA Filter 取得資料：

**Degrade Issues (分子):**
- Filter 64959: 內部 SQA+QC degrade
- Filter 22062: Vendor QC Degrade

**Resolved Issues (分母):**
- Filter 64958: 內部 resolved (過濾 gerrit URL)
- Filter 23916: Vendor resolved (過濾 gerrit URL)

## 💡 使用技巧

1. **首次載入較慢** - 需要從 JIRA 取得所有資料，請耐心等待
2. **資料快取** - 資料會快取 1 小時，可點擊「重新載入資料」強制刷新
3. **查看圖表** - 滑鼠移到圖表上可以看到詳細數據
4. **網路要求** - 確保可以連接到 jira.realtek.com 和 vendorjira.realtek.com

## 🐛 疑難排解

**問題: 無法啟動**
```bash
# 檢查 Python 版本 (需要 3.8+)
python --version

# 重新安裝套件
pip install --upgrade -r requirements.txt
```

**問題: 無法連接 JIRA**
```bash
# 測試連線
python test_connection.py

# 檢查設定
cat config.py
```

**問題: 載入很慢**
- 正常現象，第一次載入需要取得大量資料
- 可以查看終端機的進度訊息
- 資料載入後會快取 1 小時

## 📧 需要幫助？

查看完整說明: `README.md`
測試連線: `python test_connection.py`
