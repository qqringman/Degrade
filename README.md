# JIRA Degrade % 分析系統

📊 **公版 SQA/QC Degrade 問題統計分析工具**

## 📋 目錄

- [功能特點](#功能特點)
- [系統需求](#系統需求)
- [快速開始](#快速開始)
- [使用說明](#使用說明)
- [配置說明](#配置說明)
- [API 文檔](#api-文檔)
- [疑難排解](#疑難排解)
- [作者](#作者)

## ✨ 功能特點

### 📊 數據統計
- **整體統計**: Degrade/Resolved Issues 總數與百分比
- **內部/Vendor 分離**: 自動區分內部 JIRA 和 Vendor JIRA
- **週次趨勢**: 自動計算每週 Degrade % 趨勢
- **Assignee 分析**: 統計每個人員的 Degrade 和 Resolved 分布

### 📈 視覺化圖表
- 每週 Degrade % 與 Resolved 數量雙線趨勢圖
- 每週 Degrade vs Resolved 數量對比圖
- 內部/Vendor 週次分布圖（可點擊跳轉 JIRA）
- Assignee 分布橫向柱狀圖（可點擊查看個人 Issues）
- 動態高度圖表，支援顯示 20-5000 筆數據

### 🔍 過濾功能
- **日期範圍過濾**: 選擇開始/結束日期
- **人員過濾**: 按 Assignee 篩選
- **圖表筆數控制**: 20/50/100/200/500/1000/5000 筆可選

### 💾 匯出功能
- **Excel 匯出**: 多頁籤 Excel，包含 Degrade/Resolved 明細
- **HTML 匯出**: 完整互動式報告，支援圖表點擊跳轉 JIRA

### ⚡ 性能優化
- **並行載入**: 4 個 Filter 同時載入，速度提升 4 倍
- **智能快取**: 資料快取 1 小時，重複查詢秒開
- **大批次載入**: 每次載入 500 筆，減少 API 請求次數

## 💻 系統需求

- **Python**: 3.8 或以上
- **作業系統**: Windows / macOS / Linux
- **網路**: 能連接到 Realtek JIRA 伺服器
- **瀏覽器**: Chrome / Firefox / Edge / Safari（支援 HTML5）

## 🚀 快速開始

### 1. 安裝 Python 套件

```bash
# 方法 A: 使用 pip 安裝（推薦）
pip install -r requirements.txt

# 方法 B: 使用 pip3
pip3 install -r requirements.txt
```

### 2. 設定環境變數

**方法 A: 使用 .env 文件（推薦）**

```bash
# 1. 創建 .env 文件
touch .env

# 2. 編輯 .env，填入你的 JIRA 帳號資訊
nano .env  # 或使用 vim, code 等編輯器
```

**`.env` 文件內容範例：**

```bash
# 內部 JIRA 設定
JIRA_SITE=jira.realtek.com
JIRA_USER=your_username
JIRA_PASSWORD=your_password
JIRA_TOKEN=  # 如果有 API token 就填，沒有就用帳密

# Vendor JIRA 設定
VENDOR_JIRA_SITE=vendorjira.realtek.com
VENDOR_JIRA_USER=your_username
VENDOR_JIRA_PASSWORD=your_password
VENDOR_JIRA_TOKEN=  # 如果有 API token 就填，沒有就用帳密
```

**⚠️ 重要提醒：**
- **切勿**將 `.env` 文件提交到 Git！
- `.env` 已加入 `.gitignore`
- 只提交 `.env.example` 作為範例

**方法 B: 直接設定環境變數**

```bash
# Linux / macOS
export JIRA_TOKEN='your_token_here'
export JIRA_USER='your_username'
export JIRA_PASSWORD='your_password'
# ... 其他環境變數

# Windows (PowerShell)
$env:JIRA_TOKEN='your_token_here'
$env:JIRA_USER='your_username'
# ... 其他環境變數
```

### 3. 啟動應用程式

**方法 A: 使用啟動腳本（推薦）**

```bash
# Linux / macOS
chmod +x start.sh
./start.sh

# Windows (Git Bash)
bash start.sh
```

**方法 B: 直接執行 Python**

```bash
python app.py
# 或
python3 app.py
```

### 4. 開啟瀏覽器

啟動成功後，在瀏覽器開啟：

```
http://localhost:5000
```

或使用 console 顯示的實際 IP 位址（例如：http://172.22.48.92:5000）

## 📖 使用說明

### 主要操作流程

1. **首次載入**: 
   - 頁面會自動載入最近一年的資料
   - 載入時間約 30-60 秒（取決於資料量）
   - 載入完成後資料會快取 1 小時

2. **過濾資料**:
   - 選擇日期範圍（開始日期/結束日期）
   - 選擇特定 Assignee
   - 調整圖表顯示筆數（20-5000）
   - 點擊「🔍 套用過濾」

3. **查看統計**:
   - 整體統計卡片：顯示總數和百分比
   - 紅框小數字可點擊：直接跳轉到 JIRA 查看該類型的 Issues
   - 趨勢圖表：觀察時間變化
   - Assignee 分布：了解人員負荷

4. **互動功能**:
   - **點擊週次 Bar**: 跳轉到 JIRA 查看該週的 Issues
   - **點擊 Assignee Bar**: 跳轉到 JIRA 查看該人員的 Issues
   - **點擊統計小數字**: 跳轉到對應的 JIRA Filter

5. **匯出報告**:
   - **📊 匯出 Excel**: 下載多頁籤 Excel，包含所有明細
   - **🌐 匯出 HTML**: 下載完整互動式報告，可離線查看

6. **重新載入**:
   - 點擊「🔄 重新載入」強制從 JIRA 更新資料
   - 或等待快取過期（1 小時）自動更新

### 日期欄位說明

- **Degrade Issues**: 使用 **created** 日期（問題建立時間）
- **Resolved Issues**: 使用 **resolutiondate** 日期（問題解決時間）

## ⚙️ 配置說明

### JIRA Filter IDs

系統使用以下 Filter ID（在 `app.py` 中設定）：

```python
FILTERS = {
    'degrade': {
        'internal': '64959',  # 內部 SQA+QC degrade from 2020/09/02
        'vendor': '22062'     # Vendor Jira QC Degrade from 2022/09/02
    },
    'resolved': {
        'internal': '64958',  # 內部 all resolved from 2020/09/02
        'vendor': '23916'     # Vendor all customer resolved from 2020/09/02
    }
}
```

**如需修改 Filter ID**：
1. 編輯 `app.py` 中的 `FILTERS` 字典
2. 重新啟動應用程式

### 快取時間調整

預設快取時間為 1 小時（3600 秒），如需修改：

```python
# app.py 第 58 行
cache = DataCache(ttl_seconds=3600)  # 改為你想要的秒數
```

### 圖表顯示筆數

預設顯示 Top 20，可在網頁下拉選單調整：
- 20 / 50 / 100 / 200 / 500 / 1000 / 5000

## 📡 API 文檔

### GET /api/stats

取得統計資料（JSON 格式）

**查詢參數**:
- `start_date`: 開始日期（YYYY-MM-DD）
- `end_date`: 結束日期（YYYY-MM-DD）
- `owner`: Assignee 名稱

**範例**:
```bash
curl "http://localhost:5000/api/stats?start_date=2024-01-01&end_date=2024-12-31&owner=John"
```

### GET /api/cache-status

查詢快取狀態

**回應**:
```json
{
  "valid": true,
  "age_seconds": 1234,
  "age_minutes": 20.5
}
```

### POST /api/refresh

強制重新載入資料

**範例**:
```bash
curl -X POST "http://localhost:5000/api/refresh"
```

### GET /api/export/excel

匯出 Excel 檔案

**查詢參數**: 同 `/api/stats`

### GET /api/export/html

匯出 HTML 報告

**查詢參數**: 
- 同 `/api/stats`
- `chart_limit`: 圖表顯示筆數（預設 20）

## 🔧 疑難排解

### 問題 1: 載入很慢或超時

**原因**: 資料量太大或網路不穩

**解決方法**:
1. 使用日期過濾，縮小資料範圍
2. 檢查網路連線
3. 增加批次大小（編輯 `jira_degrade_manager.py` 的 `batch_size`）

### 問題 2: 認證失敗

**原因**: 帳號密碼或 Token 錯誤

**解決方法**:
1. 檢查 `.env` 文件中的帳號資訊
2. 確認 JIRA 帳號可以正常登入
3. 如果用 Token，確認 Token 還有效

### 問題 3: 圖表顯示不正常

**原因**: 瀏覽器快取或 Chart.js 載入失敗

**解決方法**:
1. 清除瀏覽器快取
2. 重新整理頁面（Ctrl+F5 或 Cmd+Shift+R）
3. 檢查 Console 是否有錯誤訊息

### 問題 4: 匯出的 Excel 打不開

**原因**: openpyxl 套件未安裝或版本不對

**解決方法**:
```bash
pip install --upgrade openpyxl
```

### 問題 5: 週次日期不正確

**原因**: ISO 8601 週次計算與 JIRA 不一致

**解決方法**:
- 系統已使用 ISO 8601 標準
- 確認 JIRA Filter 的日期欄位設定正確

## 📂 檔案結構

```
.
├── app.py                      # Flask 主應用程式
├── jira_degrade_manager.py     # JIRA 資料管理模組
├── requirements.txt            # Python 套件依賴
├── start.sh                    # 啟動腳本
├── .env                        # 環境變數（不要提交到 Git）
├── .env.example                # 環境變數範例
├── templates/
│   └── index.html             # 網頁介面
└── README.md                  # 本文件
```

## 🔐 安全性提醒

1. **切勿**將 `.env` 文件或 JIRA 帳密提交到 Git
2. 定期更換密碼和 Token
3. 不要在公開網路環境執行（僅限內部網路）
4. 如果要部署到伺服器，建議使用 HTTPS

## 🆕 更新日誌

### v2.0 (2025-10-29)
- ✅ 修復合併數量與分開數量不一致問題
- ✅ Degrade 改用 created 日期
- ✅ Resolved 改用 resolutiondate 日期
- ✅ 趨勢圖加入 resolved 數量線（雙 Y 軸）
- ✅ 週次日期範圍計算精確化
- ✅ 匯出 HTML 加入可點擊圖表和完整表格
- ✅ 圖表顯示筆數可調整（20-5000）

### v1.0 (2024-XX-XX)
- 初始版本發布

## 👨‍💻 作者

**Vince**  
© 2025 Copyright by Vince. All rights reserved.

---

## 🙏 致謝

- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [Chart.js](https://www.chartjs.org/) - 圖表庫
- [OpenPyXL](https://openpyxl.readthedocs.io/) - Excel 處理
- [Realtek](https://www.realtek.com/) - JIRA 系統提供

---

**如有問題或建議，歡迎聯繫開發者**

Made with ❤️ by Vince
