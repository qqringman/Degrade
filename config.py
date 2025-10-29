"""
JIRA 設定檔
從環境變數讀取設定，不直接存儲敏感資訊
"""
import os

# 內部 JIRA 設定
JIRA_SITE = os.getenv('JIRA_SITE', 'jira.realtek.com')
JIRA_USER = os.getenv('JIRA_USER', '')
JIRA_PASSWORD = os.getenv('JIRA_PASSWORD', '')
JIRA_TOKEN = os.getenv('JIRA_TOKEN', '')

# Vendor JIRA 設定
VENDOR_JIRA_SITE = os.getenv('VENDOR_JIRA_SITE', 'vendorjira.realtek.com')
VENDOR_JIRA_USER = os.getenv('VENDOR_JIRA_USER', '')
VENDOR_JIRA_PASSWORD = os.getenv('VENDOR_JIRA_PASSWORD', '')
VENDOR_JIRA_TOKEN = os.getenv('VENDOR_JIRA_TOKEN', '')

# Filter IDs
FILTER_INTERNAL_DEGRADE = os.getenv('FILTER_INTERNAL_DEGRADE', '64959')
FILTER_VENDOR_DEGRADE = os.getenv('FILTER_VENDOR_DEGRADE', '23919')
FILTER_INTERNAL_RESOLVED = os.getenv('FILTER_INTERNAL_RESOLVED', '64958')
FILTER_VENDOR_RESOLVED = os.getenv('FILTER_VENDOR_RESOLVED', '23916')

# 快取設定（秒）
CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))

# Flask 設定
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

