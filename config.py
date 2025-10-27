"""
JIRA 設定檔
可以直接在這裡修改設定，或使用環境變數
"""

# 內部 JIRA 設定
JIRA_SITE = 'jira.realtek.com'
JIRA_USER = 'vince_lin'
JIRA_PASSWORD = 'Amon100!'
JIRA_TOKEN = ''

# Vendor JIRA 設定
VENDOR_JIRA_SITE = 'vendorjira.realtek.com'
VENDOR_JIRA_USER = 'vince_lin'
VENDOR_JIRA_PASSWORD = 'Amon100!'
VENDOR_JIRA_TOKEN = ''

# Filter IDs
FILTER_INTERNAL_DEGRADE = '64959'   # 內部 SQA+QC degrade from 2020/09/02
FILTER_VENDOR_DEGRADE = '22062'     # Vendor QC Degrade from 2022/09/02
FILTER_INTERNAL_RESOLVED = '64958'  # 內部 all resolved issue from 2020/09/02
FILTER_VENDOR_RESOLVED = '23916'    # Vendor all customer resolved issue from 2020/09/02

# 快取設定（秒）
CACHE_TTL = 3600  # 1 小時

# Flask 設定
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = True
