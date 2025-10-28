# JIRA Degrade % 分析系統

這是一個用於分析 JIRA degrade 問題百分比的 Flask 網頁應用程式。

## 功能特點

1. **整體統計**
   - Degrade issues 總數
   - Resolved issues 總數（包含 gerrit URL）
   - 整體 Degrade 百分比

2. **每週趨勢分析**
   - 每週 Degrade % 趨勢圖
   - 每週 Degrade vs Resolved 數量對比圖

3. **Assignee 分布**
   - Degrade issues 的 assignee 分布表格
   - Resolved issues 的 assignee 分布表格
   - Top 10 assignee 圖表

## 檔案結構

```
.
├── app.py                      # Flask 主應用程式
├── jira_degrade_manager.py     # JIRA 資料管理模組
├── requirements.txt            # Python 套件依賴
├── templates/
│   └── index.html             # 網頁介面
└── README.md                  # 說明文件
```

## 安裝步驟

1. 安裝 Python 套件：
```bash
pip install -r requirements.txt
```

2. 設定環境變數：

**方法 A: 使用 .env 文件（推薦）**
```bash
# 複製範例文件
cp .env.example .env

# 編輯 .env 文件，填入你的真實 JIRA 帳號資訊
# 使用任何文字編輯器打開 .env
nano .env  # 或 vim .env 或 code .env
```

**方法 B: 直接設定環境變數**
```bash
export JIRA_TOKEN='your_token_here'
export JIRA_SITE='jira.realtek.com'
export JIRA_USER='your_username'
export JIRA_PASSWORD='your_password'

export VENDOR_JIRA_TOKEN='your_vendor_token_here'
export VENDOR_JIRA_SITE='vendorjira.realtek.com'
export VENDOR_JIRA_USER='your_username'
export VENDOR_JIRA_PASSWORD='your_password'
```

**⚠️ 重要提醒：**
- **切勿**將 `.env` 文件提交到 Git！
- `.env` 文件已加入 `.gitignore`
- 只提交 `.env.example` 作為範例

## 使用方式

1. 啟動應用程式：
```bash
python app.py
```

2. 開啟瀏覽器，訪問：
```
http://localhost:5000
```

3. 第一次載入時會自動從 JIRA 取得資料（可能需要幾分鐘）

4. 資料會快取 1 小時，可以點擊「重新載入資料」按鈕手動刷新

## JIRA Filter 設定

系統使用以下 Filter：

**分子（Degrade Issues）：**
- 內部 SQA+QC degrade (Filter ID: 64959)
  - https://jira.realtek.com/issues/?filter=64959
- Vendor QC Degrade (Filter ID: 22062)
  - https://vendorjira.realtek.com/issues/?filter=22062

**分母（Resolved Issues）：**
- 內部 all resolved issue (Filter ID: 64958)
  - https://jira.realtek.com/issues/?filter=64958
  - 會過濾出包含 sa/sd gerrit URL 的 issues
- Vendor all customer resolved issue (Filter ID: 23916)
  - https://vendorjira.realtek.com/issues/?filter=23916
  - 會過濾出包含 sa/sd gerrit URL 的 issues

## 資料處理邏輯

1. **Degrade %** = (Degrade Issues 總數) / (Resolved Issues 總數) × 100%

2. **Resolved Issues 過濾條件**：
   - Status = resolved 或 closed
   - 日期 >= 2020/09/02
   - Description 包含 sa 或 sd gerrit URL

3. **每週統計**：
   - 使用 resolutiondate 欄位
   - 按 ISO 週次統計（YYYY-Wxx）

## API 端點

- `GET /` - 網頁介面
- `GET /api/stats` - 取得統計資料（JSON）
- `GET /api/refresh` - 手動刷新資料

## 注意事項

1. 首次載入可能需要較長時間（取決於 issues 數量）
2. 資料預設快取 1 小時
3. 確保 JIRA 認證資訊正確
4. 確保網路可以連接到 JIRA 伺服器

## 疑難排解

如果遇到問題，請檢查：

1. Python 版本（建議 3.8+）
2. JIRA 認證資訊是否正確
3. 網路連線是否正常
4. Filter ID 是否正確
5. 查看終端機的錯誤訊息

## 技術棧

- **後端**：Flask (Python)
- **前端**：HTML5, CSS3, JavaScript
- **圖表**：Chart.js
- **資料來源**：JIRA REST API
