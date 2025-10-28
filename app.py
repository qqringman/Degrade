"""
JIRA Degrade % 計算網頁應用程式 - 超快速版本
✨ 關鍵優化:
1. 並行處理 4 個 filters (4x 速度提升)
2. 增大 batch size 到 500 (5x 減少請求次數)
3. 只抓取需要的欄位 (減少數據傳輸)
4. 真正的記憶體快取 (1小時)
"""
import os
import time
from flask import Flask, render_template, jsonify, request
from jira_degrade_manager import JiraDegradeManagerFast, load_all_filters_parallel
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Thread, Lock

# 載入 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ 已載入 .env 文件")
except:
    print("⚠ 使用系統環境變數")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

# JIRA 設定
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

FILTERS = {
    'degrade': {
        'internal': '64959',
        'vendor': '22062'
    },
    'resolved': {
        'internal': '64958',
        'vendor': '23916'
    }
}

# ============ 快取系統 ============
class SimpleCache:
    """簡單高效的快取系統"""
    def __init__(self, ttl_seconds=3600):
        self.data = None
        self.timestamp = None
        self.ttl = ttl_seconds
        self.lock = Lock()
        self.loading = False
    
    def get(self):
        """取得快取"""
        with self.lock:
            if self.data is None or self.timestamp is None:
                return None
            
            age = (datetime.now() - self.timestamp).total_seconds()
            if age > self.ttl:
                return None  # 過期
            
            return self.data
    
    def set(self, data):
        """設定快取"""
        with self.lock:
            self.data = data
            self.timestamp = datetime.now()
            self.loading = False
    
    def is_valid(self):
        """檢查快取是否有效"""
        return self.get() is not None
    
    def age(self):
        """取得快取年齡"""
        if self.timestamp is None:
            return None
        return (datetime.now() - self.timestamp).total_seconds()

# 建立快取 (1小時)
cache = SimpleCache(ttl_seconds=3600)

def load_data():
    """載入資料並快取"""
    try:
        data = load_all_filters_parallel(JIRA_CONFIG, FILTERS)
        data['jira_sites'] = {
            'internal': JIRA_CONFIG['internal']['site'],
            'vendor': JIRA_CONFIG['vendor']['site']
        }
        cache.set(data)
        return data
    except Exception as e:
        print(f"❌ 載入資料失敗: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_data():
    """取得資料（優先使用快取）"""
    data = cache.get()
    if data:
        age = cache.age()
        print(f"✓ 使用快取 (年齡: {age:.0f}秒)")
        return data
    
    print("⚠ 快取無效，重新載入...")
    return load_data()

def calculate_weekly_percentage(degrade_weekly, resolved_weekly):
    """計算每週百分比"""
    all_weeks = sorted(set(list(degrade_weekly.keys()) + list(resolved_weekly.keys())))
    
    weekly_stats = []
    for week in all_weeks:
        degrade_count = degrade_weekly.get(week, {}).get('count', 0)
        resolved_count = resolved_weekly.get(week, {}).get('count', 0)
        percentage = (degrade_count / resolved_count * 100) if resolved_count > 0 else 0
        
        weekly_stats.append({
            'week': week,
            'degrade_count': degrade_count,
            'resolved_count': resolved_count,
            'percentage': round(percentage, 2)
        })
    
    return weekly_stats

def filter_issues(issues, start_date, end_date, owner):
    """過濾 issues - 使用 created 日期"""
    filtered = []
    
    for issue in issues:
        fields = issue.get('fields', {})
        
        # 日期過濾 - 改用 created
        if start_date or end_date:
            created_date = fields.get('created')  # ← 改用 created
            if created_date:
                try:
                    issue_date = datetime.strptime(created_date[:10], '%Y-%m-%d')
                    if start_date and issue_date < datetime.strptime(start_date, '%Y-%m-%d'):
                        continue
                    if end_date and issue_date > datetime.strptime(end_date, '%Y-%m-%d'):
                        continue
                except:
                    pass
        
        # Owner 過濾
        if owner:
            assignee = fields.get('assignee')
            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
            if assignee_name != owner:
                continue
        
        filtered.append(issue)
    
    return filtered

@app.route('/')
def index():
    """首頁"""
    return render_template('index.html')

@app.route('/api/cache-status')
def cache_status():
    """快取狀態"""
    age = cache.age()
    return jsonify({
        'valid': cache.is_valid(),
        'age_seconds': age,
        'age_minutes': age / 60 if age else None,
        'loading': cache.loading,
        'timestamp': cache.timestamp.isoformat() if cache.timestamp else None
    })

@app.route('/api/stats')
def get_stats():
    """取得統計資料"""
    try:
        # 取得快取資料
        data = get_data()
        if not data:
            return jsonify({
                'success': False,
                'error': '資料載入失敗'
            }), 500
        
        # 取得過濾參數
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        owner = request.args.get('owner')
        
        # 過濾
        filtered_degrade = data['degrade']['issues']
        filtered_resolved = data['resolved']['issues']
        
        if start_date or end_date or owner:
            filtered_degrade = filter_issues(filtered_degrade, start_date, end_date, owner)
            filtered_resolved = filter_issues(filtered_resolved, start_date, end_date, owner)
        
        # 重新統計
        manager = JiraDegradeManagerFast(
            site=JIRA_CONFIG['internal']['site'],
            user=JIRA_CONFIG['internal']['user'],
            password=JIRA_CONFIG['internal']['password'],
            token=JIRA_CONFIG['internal']['token']
        )
        
        total_degrade = len(filtered_degrade)
        total_resolved = len(filtered_resolved)
        overall_percentage = (total_degrade / total_resolved * 100) if total_resolved > 0 else 0
        
        # 每週統計：全部使用 created 日期
        degrade_weekly = manager.analyze_by_week(filtered_degrade, date_field='created')
        resolved_weekly = manager.analyze_by_week(filtered_resolved, date_field='created')
        weekly_stats = calculate_weekly_percentage(degrade_weekly, resolved_weekly)
        
        # Assignee 分布：拆分內部和 Vendor
        # 分離內部和 Vendor 的 issues
        internal_degrade = [i for i in filtered_degrade if i.get('_source') == 'internal']
        vendor_degrade = [i for i in filtered_degrade if i.get('_source') == 'vendor']
        internal_resolved = [i for i in filtered_resolved if i.get('_source') == 'internal']
        vendor_resolved = [i for i in filtered_resolved if i.get('_source') == 'vendor']
        
        degrade_assignees_internal = manager.get_assignee_distribution(internal_degrade)
        degrade_assignees_vendor = manager.get_assignee_distribution(vendor_degrade)
        resolved_assignees_internal = manager.get_assignee_distribution(internal_resolved)
        resolved_assignees_vendor = manager.get_assignee_distribution(vendor_resolved)
        
        # 所有 owners
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
                    'percentage': round(overall_percentage, 2),
                    'internal': {
                        'degrade_count': len(internal_degrade),
                        'resolved_count': len(internal_resolved)
                    },
                    'vendor': {
                        'degrade_count': len(vendor_degrade),
                        'resolved_count': len(vendor_resolved)
                    }
                },
                'weekly': weekly_stats,
                'assignees': {
                    'degrade': {
                        'internal': degrade_assignees_internal,
                        'vendor': degrade_assignees_vendor
                    },
                    'resolved': {
                        'internal': resolved_assignees_internal,
                        'vendor': resolved_assignees_vendor
                    }
                },
                'jira_sites': data['jira_sites'],
                'all_owners': sorted(list(all_owners)),
                'filters': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'owner': owner
                },
                'filter_ids': FILTERS,
                'cache_age': cache.age(),
                'load_time': data['metadata']['load_time']
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/refresh')
def refresh_data():
    """重新載入資料"""
    try:
        if cache.loading:
            return jsonify({
                'success': False,
                'error': '載入中，請稍候'
            }), 429
        
        cache.loading = True
        
        # 背景執行
        def bg_load():
            load_data()
        
        thread = Thread(target=bg_load)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': '開始重新載入...'
        })
    except Exception as e:
        cache.loading = False
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 JIRA Degrade 分析系統 - 超快速版本")
    print("=" * 70)
    print("✨ 優化特性:")
    print("  1. 並行處理 4 個 filters (4x 速度)")
    print("  2. 大 batch size (500) - 減少 5x 請求次數")
    print("  3. 只抓取需要的欄位")
    print("  4. 記憶體快取 (1小時)")
    print("=" * 70)
    
    # 背景預載入
    print("📦 背景預載入資料...")
    thread = Thread(target=load_data)
    thread.daemon = True
    thread.start()
    
    print("✓ 伺服器啟動")
    print("📍 URL: http://localhost:5000")
    print("⏱  預計載入時間: 10-30 秒（取決於網路速度）")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)