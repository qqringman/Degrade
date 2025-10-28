"""
JIRA Degrade % 計算網頁應用程式
"""
import os
from flask import Flask, render_template, jsonify
from jira_degrade_manager import JiraDegradeManager
from datetime import datetime
from collections import defaultdict

# 載入 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ 已載入 .env 文件")
except ImportError:
    print("⚠ python-dotenv 未安裝，使用系統環境變數")
except Exception as e:
    print(f"⚠ 載入 .env 失敗: {e}")

# 取得當前目錄的絕對路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

# 建立 Flask app，明確指定模板目錄
app = Flask(__name__, template_folder=TEMPLATE_DIR)

# JIRA 設定 - 從環境變數讀取
JIRA_CONFIG = {
    'internal': {
        'site': os.getenv('JIRA_SITE', 'jira.realtek.com'),
        'user': os.getenv('JIRA_USER', ''),
        'password': os.getenv('JIRA_PASSWORD', ''),
        'token': os.getenv('JIRA_TOKEN', '')
    },
    'vendor': {
        'site': os.getenv('VENDOR_JIRA_SITE', 'vendorjira.realtek.com'),
        'user': os.getenv('VENDOR_JIRA_USER', ''),
        'password': os.getenv('VENDOR_JIRA_PASSWORD', ''),
        'token': os.getenv('VENDOR_JIRA_TOKEN', '')
    }
}

# Filter IDs
FILTERS = {
    'degrade': {
        'internal': '64959',  # 內部 SQA+QC degrade from 2020/09/02
        'vendor': '22062'     # Vendor QC Degrade from 2022/09/02
    },
    'resolved': {
        'internal': '64958',  # 內部 all resolved issue from 2020/09/02
        'vendor': '23916'     # Vendor all customer resolved issue from 2020/09/02
    }
}

# 注意：已移除快取機制，每次都載入最新資料

def get_cached_data():
    """取得資料 - 每次都重新載入真實資料，不使用快取"""
    print("重新載入最新資料...")
    data = load_all_data()
    return data

def load_all_data():
    """載入所有 JIRA 資料"""
    print("開始載入 JIRA 資料...")
    
    # 檢查環境變數
    print(f"檢查內部 JIRA 設定:")
    print(f"  - Site: {JIRA_CONFIG['internal']['site']}")
    print(f"  - User: {JIRA_CONFIG['internal']['user']}")
    print(f"  - Token: {'已設定' if JIRA_CONFIG['internal']['token'] else '未設定'}")
    print(f"  - Password: {'已設定' if JIRA_CONFIG['internal']['password'] else '未設定'}")
    
    print(f"檢查 Vendor JIRA 設定:")
    print(f"  - Site: {JIRA_CONFIG['vendor']['site']}")
    print(f"  - User: {JIRA_CONFIG['vendor']['user']}")
    print(f"  - Token: {'已設定' if JIRA_CONFIG['vendor']['token'] else '未設定'}")
    print(f"  - Password: {'已設定' if JIRA_CONFIG['vendor']['password'] else '未設定'}")
    
    # 建立 JIRA managers
    internal_jira = JiraDegradeManager(
        site=JIRA_CONFIG['internal']['site'],
        user=JIRA_CONFIG['internal']['user'],
        password=JIRA_CONFIG['internal']['password'],
        token=JIRA_CONFIG['internal']['token']
    )
    
    vendor_jira = JiraDegradeManager(
        site=JIRA_CONFIG['vendor']['site'],
        user=JIRA_CONFIG['vendor']['user'],
        password=JIRA_CONFIG['vendor']['password'],
        token=JIRA_CONFIG['vendor']['token']
    )
    
    # 取得分子資料 (degrade issues)
    print("載入 degrade issues...")
    internal_degrade = internal_jira.get_filter_issues(FILTERS['degrade']['internal'])
    vendor_degrade = vendor_jira.get_filter_issues(FILTERS['degrade']['vendor'])
    
    # 標記來源並合併
    for issue in internal_degrade:
        issue['_source'] = 'internal'
    for issue in vendor_degrade:
        issue['_source'] = 'vendor'
    
    all_degrade = internal_degrade + vendor_degrade
    
    # 取得分母資料 (resolved issues) - 不再過濾 gerrit URL
    print("載入 resolved issues...")
    internal_resolved = internal_jira.get_filter_issues(FILTERS['resolved']['internal'])
    vendor_resolved = vendor_jira.get_filter_issues(FILTERS['resolved']['vendor'])
    
    # 標記來源並合併
    for issue in internal_resolved:
        issue['_source'] = 'internal'
    for issue in vendor_resolved:
        issue['_source'] = 'vendor'
    
    all_resolved = internal_resolved + vendor_resolved
    
    # 統計每週資料
    print("統計每週資料...")
    degrade_weekly = internal_jira.analyze_by_week(all_degrade)
    resolved_weekly = internal_jira.analyze_by_week(all_resolved)
    
    # 統計 assignee 分布
    print("統計 assignee 分布...")
    degrade_assignees = internal_jira.get_assignee_distribution(all_degrade)
    resolved_assignees = internal_jira.get_assignee_distribution(all_resolved)
    
    print(f"資料載入完成: {len(all_degrade)} degrade, {len(all_resolved)} resolved")
    
    return {
        'degrade': {
            'total': len(all_degrade),
            'weekly': degrade_weekly,
            'assignees': degrade_assignees,
            'issues': all_degrade
        },
        'resolved': {
            'total': len(all_resolved),
            'weekly': resolved_weekly,
            'assignees': resolved_assignees,
            'issues': all_resolved
        },
        'jira_sites': {
            'internal': JIRA_CONFIG['internal']['site'],
            'vendor': JIRA_CONFIG['vendor']['site']
        }
    }

def calculate_weekly_percentage(data):
    """計算每週的 degrade 百分比"""
    degrade_weekly = data['degrade']['weekly']
    resolved_weekly = data['resolved']['weekly']
    
    # 取得所有週次並排序
    all_weeks = sorted(set(list(degrade_weekly.keys()) + list(resolved_weekly.keys())))
    
    weekly_stats = []
    for week in all_weeks:
        degrade_count = degrade_weekly.get(week, {}).get('count', 0)
        resolved_count = resolved_weekly.get(week, {}).get('count', 0)
        
        if resolved_count > 0:
            percentage = (degrade_count / resolved_count) * 100
        else:
            percentage = 0
        
        weekly_stats.append({
            'week': week,
            'degrade_count': degrade_count,
            'resolved_count': resolved_count,
            'percentage': round(percentage, 2)
        })
    
    return weekly_stats

@app.route('/')
def index():
    """首頁"""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """取得統計資料 API，支援過濾參數"""
    from flask import request
    from datetime import datetime as dt
    
    try:
        data = get_cached_data()
        
        # 取得過濾參數
        start_date = request.args.get('start_date')  # YYYY-MM-DD
        end_date = request.args.get('end_date')      # YYYY-MM-DD
        owner = request.args.get('owner')            # assignee name
        
        # 過濾 degrade issues
        filtered_degrade = data['degrade']['issues']
        if start_date or end_date or owner:
            filtered_degrade = filter_issues(
                data['degrade']['issues'], 
                start_date, 
                end_date, 
                owner
            )
        
        # 過濾 resolved issues
        filtered_resolved = data['resolved']['issues']
        if start_date or end_date or owner:
            filtered_resolved = filter_issues(
                data['resolved']['issues'], 
                start_date, 
                end_date, 
                owner
            )
        
        # 重新計算統計
        from collections import defaultdict
        
        # 計算整體百分比
        total_degrade = len(filtered_degrade)
        total_resolved = len(filtered_resolved)
        overall_percentage = (total_degrade / total_resolved * 100) if total_resolved > 0 else 0
        
        # 重新計算每週統計
        internal_jira = JiraDegradeManager(
            site=JIRA_CONFIG['internal']['site'],
            user=JIRA_CONFIG['internal']['user'],
            password=JIRA_CONFIG['internal']['password'],
            token=JIRA_CONFIG['internal']['token']
        )
        
        degrade_weekly = internal_jira.analyze_by_week(filtered_degrade)
        resolved_weekly = internal_jira.analyze_by_week(filtered_resolved)
        weekly_stats = calculate_weekly_percentage_from_data(degrade_weekly, resolved_weekly)
        
        # 重新計算 assignee 分布
        degrade_assignees = internal_jira.get_assignee_distribution(filtered_degrade)
        resolved_assignees = internal_jira.get_assignee_distribution(filtered_resolved)
        
        # 獲取所有 unique owners
        all_owners = set()
        for issue in data['degrade']['issues'] + data['resolved']['issues']:
            assignee = issue.get('fields', {}).get('assignee')
            if assignee:
                all_owners.add(assignee.get('displayName', 'Unassigned'))
            else:
                all_owners.add('Unassigned')
        
        return jsonify({
            'success': True,
            'data': {
                'overall': {
                    'degrade_count': total_degrade,
                    'resolved_count': total_resolved,
                    'percentage': round(overall_percentage, 2)
                },
                'weekly': weekly_stats,
                'assignees': {
                    'degrade': degrade_assignees,
                    'resolved': resolved_assignees
                },
                'jira_sites': data['jira_sites'],
                'all_owners': sorted(list(all_owners)),
                'filters': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'owner': owner
                }
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def filter_issues(issues, start_date, end_date, owner):
    """根據條件過濾 issues"""
    from datetime import datetime as dt
    filtered = []
    
    for issue in issues:
        fields = issue.get('fields', {})
        
        # 過濾日期
        resolution_date = fields.get('resolutiondate')
        if resolution_date:
            try:
                issue_date = dt.strptime(resolution_date[:10], '%Y-%m-%d')
                
                if start_date:
                    start = dt.strptime(start_date, '%Y-%m-%d')
                    if issue_date < start:
                        continue
                
                if end_date:
                    end = dt.strptime(end_date, '%Y-%m-%d')
                    if issue_date > end:
                        continue
            except:
                pass
        
        # 過濾 owner
        if owner:
            assignee = fields.get('assignee')
            if assignee:
                assignee_name = assignee.get('displayName', 'Unassigned')
            else:
                assignee_name = 'Unassigned'
            
            if assignee_name != owner:
                continue
        
        filtered.append(issue)
    
    return filtered

def calculate_weekly_percentage_from_data(degrade_weekly, resolved_weekly):
    """從週統計資料計算百分比"""
    all_weeks = sorted(set(list(degrade_weekly.keys()) + list(resolved_weekly.keys())))
    
    weekly_stats = []
    for week in all_weeks:
        degrade_count = degrade_weekly.get(week, {}).get('count', 0)
        resolved_count = resolved_weekly.get(week, {}).get('count', 0)
        
        if resolved_count > 0:
            percentage = (degrade_count / resolved_count) * 100
        else:
            percentage = 0
        
        weekly_stats.append({
            'week': week,
            'degrade_count': degrade_count,
            'resolved_count': resolved_count,
            'percentage': round(percentage, 2)
        })
    
    return weekly_stats

@app.route('/api/refresh')
def refresh_data():
    """重新載入資料 (每次都是最新的，不需要特別刷新)"""
    try:
        data = get_cached_data()
        return jsonify({
            'success': True,
            'message': '資料已重新載入',
            'counts': {
                'degrade': len(data['degrade']['issues']),
                'resolved': len(data['resolved']['issues'])
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # 不預先載入資料，改為首次訪問時才載入
    # 這樣 Flask 可以快速啟動，避免阻塞
    print("Flask 服務啟動中...")
    print("資料將在首次訪問時載入")
    print("請訪問 http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
