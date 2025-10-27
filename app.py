"""
JIRA Degrade % 計算網頁應用程式
"""
import os
from flask import Flask, render_template, jsonify
from jira_degrade_manager import JiraDegradeManager
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

# JIRA 設定
JIRA_CONFIG = {
    'internal': {
        'site': os.getenv('JIRA_SITE', 'jira.realtek.com'),
        'user': os.getenv('JIRA_USER', 'vince_lin'),
        'password': os.getenv('JIRA_PASSWORD', 'Amon100!'),
        'token': os.getenv('JIRA_TOKEN', '')
    },
    'vendor': {
        'site': os.getenv('VENDOR_JIRA_SITE', 'vendorjira.realtek.com'),
        'user': os.getenv('VENDOR_JIRA_USER', 'vince_lin'),
        'password': os.getenv('VENDOR_JIRA_PASSWORD', 'Amon100!'),
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

# 全域快取
cache = {
    'data': None,
    'timestamp': None,
    'ttl': 3600  # 快取 1 小時
}

def get_cached_data():
    """取得快取資料或重新載入"""
    now = datetime.now()
    
    # 檢查快取是否有效
    if cache['data'] is not None and cache['timestamp'] is not None:
        elapsed = (now - cache['timestamp']).total_seconds()
        if elapsed < cache['ttl']:
            print(f"使用快取資料 (已快取 {elapsed:.0f} 秒)")
            return cache['data']
    
    print("重新載入資料...")
    data = load_all_data()
    cache['data'] = data
    cache['timestamp'] = now
    return data

def load_all_data():
    """載入所有 JIRA 資料"""
    print("開始載入 JIRA 資料...")
    
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
    all_degrade = internal_degrade + vendor_degrade
    
    # 取得分母資料 (resolved issues)
    print("載入 resolved issues...")
    internal_resolved = internal_jira.get_filter_issues(FILTERS['resolved']['internal'])
    vendor_resolved = vendor_jira.get_filter_issues(FILTERS['resolved']['vendor'])
    
    # 過濾出包含 gerrit URL 的 resolved issues
    print("過濾包含 gerrit URL 的 resolved issues...")
    internal_resolved_filtered = internal_jira.filter_issues_with_gerrit(internal_resolved)
    vendor_resolved_filtered = vendor_jira.filter_issues_with_gerrit(vendor_resolved)
    all_resolved = internal_resolved_filtered + vendor_resolved_filtered
    
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
    """取得統計資料 API"""
    try:
        data = get_cached_data()
        
        # 計算整體百分比
        total_degrade = data['degrade']['total']
        total_resolved = data['resolved']['total']
        overall_percentage = (total_degrade / total_resolved * 100) if total_resolved > 0 else 0
        
        # 計算每週百分比
        weekly_stats = calculate_weekly_percentage(data)
        
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
                    'degrade': data['degrade']['assignees'],
                    'resolved': data['resolved']['assignees']
                }
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/refresh')
def refresh_data():
    """手動刷新資料"""
    try:
        cache['data'] = None
        cache['timestamp'] = None
        data = get_cached_data()
        return jsonify({
            'success': True,
            'message': '資料已重新載入',
            'counts': {
                'degrade': data['degrade']['total'],
                'resolved': data['resolved']['total']
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # 預先載入資料
    print("預先載入資料...")
    get_cached_data()
    
    # 啟動 Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
