"""
測試 JIRA 連線和資料載入
"""
import os
from jira_degrade_manager import JiraDegradeManager

# 設定環境變數
os.environ['JIRA_TOKEN'] = ''
os.environ['JIRA_SITE'] = 'jira.realtek.com'
os.environ['JIRA_USER'] = 'vince_lin'
os.environ['JIRA_PASSWORD'] = 'Amon100!'
os.environ['VENDOR_JIRA_TOKEN'] = ''
os.environ['VENDOR_JIRA_SITE'] = 'vendorjira.realtek.com'
os.environ['VENDOR_JIRA_USER'] = 'vince_lin'
os.environ['VENDOR_JIRA_PASSWORD'] = 'Amon100!'

def test_jira_connection():
    """測試 JIRA 連線"""
    print("=" * 80)
    print("測試 JIRA 連線")
    print("=" * 80)
    
    # 測試內部 JIRA
    print("\n1. 測試內部 JIRA (jira.realtek.com)")
    print("-" * 80)
    internal_jira = JiraDegradeManager(
        site=os.environ['JIRA_SITE'],
        user=os.environ['JIRA_USER'],
        password=os.environ['JIRA_PASSWORD'],
        token=os.environ['JIRA_TOKEN']
    )
    
    try:
        # 測試取得少量資料
        print("取得 filter 64959 的前 5 筆資料...")
        issues = internal_jira.get_filter_issues('64959', max_results=5)
        print(f"✓ 成功取得 {len(issues)} 筆資料")
        
        if issues:
            print(f"  範例 issue: {issues[0].get('key')}")
            print(f"  Summary: {issues[0].get('fields', {}).get('summary', 'N/A')}")
    except Exception as e:
        print(f"✗ 失敗: {str(e)}")
    
    # 測試 Vendor JIRA
    print("\n2. 測試 Vendor JIRA (vendorjira.realtek.com)")
    print("-" * 80)
    vendor_jira = JiraDegradeManager(
        site=os.environ['VENDOR_JIRA_SITE'],
        user=os.environ['VENDOR_JIRA_USER'],
        password=os.environ['VENDOR_JIRA_PASSWORD'],
        token=os.environ['VENDOR_JIRA_TOKEN']
    )
    
    try:
        # 測試取得少量資料
        print("取得 filter 22062 的前 5 筆資料...")
        issues = vendor_jira.get_filter_issues('22062', max_results=5)
        print(f"✓ 成功取得 {len(issues)} 筆資料")
        
        if issues:
            print(f"  範例 issue: {issues[0].get('key')}")
            print(f"  Summary: {issues[0].get('fields', {}).get('summary', 'N/A')}")
    except Exception as e:
        print(f"✗ 失敗: {str(e)}")
    
    print("\n" + "=" * 80)
    print("測試完成")
    print("=" * 80)

def test_gerrit_filter():
    """測試 gerrit URL 過濾功能"""
    print("\n" + "=" * 80)
    print("測試 Gerrit URL 過濾功能")
    print("=" * 80)
    
    internal_jira = JiraDegradeManager(
        site=os.environ['JIRA_SITE'],
        user=os.environ['JIRA_USER'],
        password=os.environ['JIRA_PASSWORD'],
        token=os.environ['JIRA_TOKEN']
    )
    
    # 測試範例
    test_cases = [
        ("https://gerrit.realtek.com/sa/test", True),
        ("https://gerrit.realtek.com/sd/test", True),
        ("https://gerrit.realtek.com/other/test", False),
        ("No gerrit URL here", False),
    ]
    
    print("\n測試案例:")
    for text, expected in test_cases:
        result = internal_jira.has_gerrit_url(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text[:50]}...' -> {result} (expected: {expected})")

if __name__ == '__main__':
    test_jira_connection()
    test_gerrit_filter()
