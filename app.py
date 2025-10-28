#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JIRA Degrade % 分析系統 - 增強版
新增功能：
1. 週次圖表（內部/Vendor 分開）
2. 匯出 Excel（多頁籤）
3. 匯出 HTML（靜態）
4. UI 美化 + 載入動畫
"""

from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from collections import defaultdict
from jira_degrade_manager import JiraDegradeManagerFast, load_all_filters_parallel
import time
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from urllib.parse import quote
import json

# 載入環境變數
load_dotenv()

app = Flask(__name__)
CORS(app)

# JIRA 連線設定
JIRA_CONFIG = {
    'internal': {
        'site': os.getenv('JIRA_SITE', 'jira.realtek.com'),
        'user': os.getenv('JIRA_USER'),
        'password': os.getenv('JIRA_PASSWORD'),
        'token': os.getenv('JIRA_TOKEN')
    },
    'vendor': {
        'site': os.getenv('VENDOR_JIRA_SITE', 'vendorjira.realtek.com'),
        'user': os.getenv('VENDOR_JIRA_USER'),
        'password': os.getenv('VENDOR_JIRA_PASSWORD'),
        'token': os.getenv('VENDOR_JIRA_TOKEN')
    }
}

# Filter IDs
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

class DataCache:
    """記憶體快取"""
    def __init__(self, ttl_seconds=3600):
        self.data = None
        self.timestamp = None
        self.ttl = ttl_seconds
    
    def set(self, data):
        self.data = data
        self.timestamp = time.time()
    
    def get(self):
        if self.data is None or self.timestamp is None:
            return None
        
        if time.time() - self.timestamp > self.ttl:
            return None
        
        return self.data
    
    def age(self):
        """回傳快取年齡（秒）"""
        if self.timestamp is None:
            return None
        return time.time() - self.timestamp
    
    def clear(self):
        self.data = None
        self.timestamp = None

# 建立全域快取（1小時過期）
cache = DataCache(ttl_seconds=3600)

def load_data():
    """載入資料並快取"""
    try:
        print("📥 開始載入資料...")
        raw_data = load_all_filters_parallel(JIRA_CONFIG, FILTERS)
        
        # 驗證資料格式
        if not isinstance(raw_data, dict):
            print(f"❌ 錯誤: raw_data 不是字典，類型為 {type(raw_data)}")
            return None
        
        if 'degrade' not in raw_data or 'resolved' not in raw_data:
            print(f"❌ 錯誤: raw_data 缺少必要的鍵")
            print(f"   raw_data 的鍵: {list(raw_data.keys())}")
            return None
        
        # 檢查是否為新格式（包含 issues 子鍵）
        if isinstance(raw_data['degrade'], dict) and 'issues' in raw_data['degrade']:
            print("📦 檢測到新格式資料（包含統計資訊）")
            # 新格式：{'degrade': {'issues': [...], 'total': ..., 'weekly': ..., 'assignees': ...}}
            data = {
                'degrade': raw_data['degrade']['issues'],
                'resolved': raw_data['resolved']['issues'],
                'metadata': raw_data.get('metadata', {})
            }
            print(f"✅ 資料載入成功: degrade={len(data['degrade'])}, resolved={len(data['resolved'])}")
        elif isinstance(raw_data['degrade'], list):
            print("📦 檢測到舊格式資料（純列表）")
            # 舊格式：{'degrade': [...], 'resolved': [...]}
            data = raw_data
            print(f"✅ 資料載入成功: degrade={len(data['degrade'])}, resolved={len(data['resolved'])}")
        else:
            print(f"❌ 錯誤: data['degrade'] 格式不正確，類型為 {type(raw_data['degrade'])}")
            if isinstance(raw_data['degrade'], dict):
                print(f"   degrade 的鍵: {list(raw_data['degrade'].keys())}")
            return None
        
        # 驗證最終格式
        if not isinstance(data['degrade'], list):
            print(f"❌ 錯誤: 處理後 data['degrade'] 仍不是列表")
            return None
        
        if not isinstance(data['resolved'], list):
            print(f"❌ 錯誤: 處理後 data['resolved'] 仍不是列表")
            return None
        
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

def get_iso_week_dates(year, week):
    """
    根據 ISO 8601 標準計算指定年份和週次的起始和結束日期
    ISO 週次規則：
    - 每週從星期一開始，星期日結束
    - 一年的第一週是包含該年第一個星期四的那一週
    """
    # 找到該年的第一天
    jan_4 = datetime(year, 1, 4)  # ISO 規則：包含 1 月 4 日的週就是第一週
    # 找到該週的星期一
    week_1_monday = jan_4 - timedelta(days=jan_4.weekday())
    # 計算目標週的星期一
    target_monday = week_1_monday + timedelta(weeks=week - 1)
    # 計算星期日
    target_sunday = target_monday + timedelta(days=6)
    
    return target_monday, target_sunday

def analyze_by_week_with_dates(issues, date_field='created'):
    """統計週次分布，並返回每週的起始和結束日期（符合 ISO 8601 標準）"""
    weekly_stats = {}
    
    for issue in issues:
        fields = issue.get('fields', {})
        date_str = fields.get(date_field)
        
        if not date_str:
            continue
        
        try:
            issue_date = datetime.strptime(date_str[:10], '%Y-%m-%d')
            # 計算 ISO 週次
            iso_calendar = issue_date.isocalendar()
            iso_year = iso_calendar[0]
            iso_week = iso_calendar[1]
            week_key = f"{iso_year}-W{iso_week:02d}"
            
            if week_key not in weekly_stats:
                # 使用正確的 ISO 週次計算方法
                week_start, week_end = get_iso_week_dates(iso_year, iso_week)
                
                weekly_stats[week_key] = {
                    'count': 0,
                    'issues': [],
                    'start_date': week_start.strftime('%Y-%m-%d'),
                    'end_date': week_end.strftime('%Y-%m-%d')
                }
            
            weekly_stats[week_key]['count'] += 1
            weekly_stats[week_key]['issues'].append(issue.get('key'))
            
        except Exception as e:
            print(f"⚠️  週次統計錯誤: {e}")
            continue
    
    return weekly_stats

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
    
    # 確保 issues 是列表
    if not isinstance(issues, list):
        print(f"⚠️  警告: issues 不是列表，類型為 {type(issues)}")
        return []
    
    for issue in issues:
        # 確保 issue 是字典
        if not isinstance(issue, dict):
            print(f"⚠️  警告: issue 不是字典，類型為 {type(issue)}")
            continue
            
        fields = issue.get('fields', {})
        
        # 日期過濾 - 使用 created
        if start_date or end_date:
            created_date = fields.get('created')
            if created_date:
                try:
                    issue_date = datetime.strptime(created_date[:10], '%Y-%m-%d')
                    if start_date and issue_date < datetime.strptime(start_date, '%Y-%m-%d'):
                        continue
                    if end_date and issue_date > datetime.strptime(end_date, '%Y-%m-%d'):
                        continue
                except Exception as e:
                    print(f"⚠️  日期解析錯誤: {e}")
                    pass
        
        # Owner 過濾
        if owner:
            assignee = fields.get('assignee')
            if isinstance(assignee, dict):
                assignee_name = assignee.get('displayName', 'Unassigned')
            else:
                assignee_name = 'Unassigned'
            
            if assignee_name != owner:
                continue
        
        filtered.append(issue)
    
    return filtered

@app.route('/')
def index():
    """首頁"""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """取得統計資料"""
    try:
        data = get_data()
        if not data:
            return jsonify({'success': False, 'error': '載入資料失敗'}), 500
        
        # 確保資料格式正確
        if not isinstance(data.get('degrade'), list):
            print(f"❌ 錯誤: data['degrade'] 不是列表，類型為 {type(data.get('degrade'))}")
            return jsonify({'success': False, 'error': 'degrade 資料格式錯誤'}), 500
        
        if not isinstance(data.get('resolved'), list):
            print(f"❌ 錯誤: data['resolved'] 不是列表，類型為 {type(data.get('resolved'))}")
            return jsonify({'success': False, 'error': 'resolved 資料格式錯誤'}), 500
        
        # 取得過濾參數
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        owner = request.args.get('owner')
        
        print(f"📊 過濾參數: start_date={start_date}, end_date={end_date}, owner={owner}")
        print(f"📊 原始資料: degrade={len(data['degrade'])}, resolved={len(data['resolved'])}")
        
        # 過濾資料 - 全部使用 created 日期
        filtered_degrade = filter_issues(data['degrade'], start_date, end_date, owner)
        filtered_resolved = filter_issues(data['resolved'], start_date, end_date, owner)
        
        print(f"📊 過濾後: degrade={len(filtered_degrade)}, resolved={len(filtered_resolved)}")
        
        # 收集所有 assignees
        all_owners = set()
        for issue in data['degrade'] + data['resolved']:
            fields = issue.get('fields', {})
            assignee = fields.get('assignee')
            if assignee:
                all_owners.add(assignee.get('displayName', 'Unassigned'))
            else:
                all_owners.add('Unassigned')
        
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
        
        # 分離內部和 Vendor issues
        internal_degrade = [i for i in filtered_degrade if i.get('_source') == 'internal']
        vendor_degrade = [i for i in filtered_degrade if i.get('_source') == 'vendor']
        internal_resolved = [i for i in filtered_resolved if i.get('_source') == 'internal']
        vendor_resolved = [i for i in filtered_resolved if i.get('_source') == 'vendor']
        
        # 檢查是否有遺失的 issues（沒有 _source 或 _source 不是 internal/vendor）
        missing_degrade = [i for i in filtered_degrade if i.get('_source') not in ['internal', 'vendor']]
        missing_resolved = [i for i in filtered_resolved if i.get('_source') not in ['internal', 'vendor']]
        
        if missing_degrade:
            print(f"⚠️  警告: 有 {len(missing_degrade)} 個 degrade issues 沒有正確的 _source 標記")
            for issue in missing_degrade[:5]:  # 只顯示前 5 個
                print(f"   - {issue.get('key')}: _source = {issue.get('_source')}")
        
        if missing_resolved:
            print(f"⚠️  警告: 有 {len(missing_resolved)} 個 resolved issues 沒有正確的 _source 標記")
            for issue in missing_resolved[:5]:
                print(f"   - {issue.get('key')}: _source = {issue.get('_source')}")
        
        # 如果有遺失的 issues，將它們加到 internal 或 vendor（根據 jira site 判斷）
        for issue in missing_degrade:
            # 根據 issue key 或 self URL 判斷來源
            if 'vendorjira' in issue.get('self', '').lower():
                issue['_source'] = 'vendor'
                vendor_degrade.append(issue)
            else:
                issue['_source'] = 'internal'
                internal_degrade.append(issue)
        
        for issue in missing_resolved:
            if 'vendorjira' in issue.get('self', '').lower():
                issue['_source'] = 'vendor'
                vendor_resolved.append(issue)
            else:
                issue['_source'] = 'internal'
                internal_resolved.append(issue)
        
        # 驗證數量
        print(f"📊 分離驗證:")
        print(f"   Degrade: total={len(filtered_degrade)}, internal={len(internal_degrade)}, vendor={len(vendor_degrade)}, sum={len(internal_degrade)+len(vendor_degrade)}")
        print(f"   Resolved: total={len(filtered_resolved)}, internal={len(internal_resolved)}, vendor={len(vendor_resolved)}, sum={len(internal_resolved)+len(vendor_resolved)}")
        
        # Assignee 分布
        degrade_assignees_internal = manager.get_assignee_distribution(internal_degrade)
        degrade_assignees_vendor = manager.get_assignee_distribution(vendor_degrade)
        resolved_assignees_internal = manager.get_assignee_distribution(internal_resolved)
        resolved_assignees_vendor = manager.get_assignee_distribution(vendor_resolved)
        
        # 週次統計 - 全部使用 created
        degrade_weekly = analyze_by_week_with_dates(filtered_degrade, date_field='created')
        resolved_weekly = analyze_by_week_with_dates(filtered_resolved, date_field='created')
        weekly_stats = calculate_weekly_percentage(degrade_weekly, resolved_weekly)
        
        degrade_weekly_internal = analyze_by_week_with_dates(internal_degrade, date_field='created')
        degrade_weekly_vendor = analyze_by_week_with_dates(vendor_degrade, date_field='created')
        resolved_weekly_internal = analyze_by_week_with_dates(internal_resolved, date_field='created')
        resolved_weekly_vendor = analyze_by_week_with_dates(vendor_resolved, date_field='created')
        
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
                'weekly_by_source': {
                    'internal': degrade_weekly_internal,
                    'vendor': degrade_weekly_vendor
                },
                'weekly_by_source_resolved': {
                    'internal': resolved_weekly_internal,
                    'vendor': resolved_weekly_vendor
                },
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
        print(f"❌ API 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cache-status')
def cache_status():
    """快取狀態"""
    age = cache.age()
    return jsonify({
        'valid': age is not None and age < cache.ttl,
        'age_seconds': age,
        'age_minutes': age / 60 if age else None
    })

@app.route('/api/refresh', methods=['POST'])
def refresh():
    """強制重新載入資料"""
    try:
        cache.clear()
        data = load_data()
        if data:
            return jsonify({'success': True, 'message': '資料重新載入完成'})
        else:
            return jsonify({'success': False, 'error': '載入失敗'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/excel')
def export_excel():
    """匯出 Excel - 多頁籤，可 filter"""
    try:
        data = get_data()
        if not data:
            return jsonify({'success': False, 'error': '無資料可匯出'}), 500
        
        # 取得過濾參數
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        owner = request.args.get('owner')
        
        # 過濾資料
        filtered_degrade = filter_issues(data['degrade'], start_date, end_date, owner)
        filtered_resolved = filter_issues(data['resolved'], start_date, end_date, owner)
        
        # 建立 Excel
        wb = Workbook()
        wb.remove(wb.active)  # 移除預設工作表
        
        # 樣式定義
        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_alignment = Alignment(horizontal='center', vertical='center')
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        def create_sheet(wb, title, data, columns, source_filter=None):
            """建立工作表"""
            ws = wb.create_sheet(title=title)
            
            # 過濾資料
            if source_filter:
                data = [i for i in data if i.get('_source') == source_filter]
            
            # 寫入標題
            for col_idx, (header, _) in enumerate(columns, 1):
                cell = ws.cell(row=1, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = border
            
            # 寫入資料
            for row_idx, issue in enumerate(data, 2):
                fields = issue.get('fields', {})
                for col_idx, (_, field_func) in enumerate(columns, 1):
                    value = field_func(issue, fields)
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.border = border
            
            # 自動調整欄寬
            for col_idx in range(1, len(columns) + 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = 15
            
            # 啟用篩選
            ws.auto_filter.ref = ws.dimensions
            
            return ws
        
        # 定義欄位
        issue_columns = [
            ('Issue Key', lambda i, f: i.get('key', '')),
            ('Assignee', lambda i, f: f.get('assignee', {}).get('displayName', 'Unassigned') if f.get('assignee') else 'Unassigned'),
            ('Created', lambda i, f: f.get('created', '')[:10] if f.get('created') else ''),
            ('Week', lambda i, f: f"{datetime.strptime(f.get('created', '')[:10], '%Y-%m-%d').isocalendar()[0]}-W{datetime.strptime(f.get('created', '')[:10], '%Y-%m-%d').isocalendar()[1]:02d}" if f.get('created') else ''),
            ('Source', lambda i, f: i.get('_source', 'unknown').upper())
        ]
        
        # 建立工作表
        create_sheet(wb, 'Degrade All', filtered_degrade, issue_columns)
        create_sheet(wb, 'Degrade Internal', filtered_degrade, issue_columns, 'internal')
        create_sheet(wb, 'Degrade Vendor', filtered_degrade, issue_columns, 'vendor')
        create_sheet(wb, 'Resolved All', filtered_resolved, issue_columns)
        create_sheet(wb, 'Resolved Internal', filtered_resolved, issue_columns, 'internal')
        create_sheet(wb, 'Resolved Vendor', filtered_resolved, issue_columns, 'vendor')
        
        # 統計摘要
        ws_summary = wb.create_sheet(title='Summary', index=0)
        summary_data = [
            ['統計項目', '數量'],
            ['Degrade Issues (Total)', len(filtered_degrade)],
            ['Degrade Issues (Internal)', len([i for i in filtered_degrade if i.get('_source') == 'internal'])],
            ['Degrade Issues (Vendor)', len([i for i in filtered_degrade if i.get('_source') == 'vendor'])],
            ['Resolved Issues (Total)', len(filtered_resolved)],
            ['Resolved Issues (Internal)', len([i for i in filtered_resolved if i.get('_source') == 'internal'])],
            ['Resolved Issues (Vendor)', len([i for i in filtered_resolved if i.get('_source') == 'vendor'])],
            ['Degrade %', f"{(len(filtered_degrade) / len(filtered_resolved) * 100) if len(filtered_resolved) > 0 else 0:.2f}%"],
        ]
        
        for row_idx, (label, value) in enumerate(summary_data, 1):
            cell_label = ws_summary.cell(row=row_idx, column=1, value=label)
            cell_value = ws_summary.cell(row=row_idx, column=2, value=value)
            if row_idx == 1:
                cell_label.font = header_font
                cell_label.fill = header_fill
                cell_value.font = header_font
                cell_value.fill = header_fill
            cell_label.border = border
            cell_value.border = border
        
        ws_summary.column_dimensions['A'].width = 30
        ws_summary.column_dimensions['B'].width = 20
        
        # 儲存到記憶體
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"jira_degrade_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Excel 匯出失敗: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/html')
def export_html():
    """匯出 HTML - 靜態，包含可點擊圖表"""
    try:
        data = get_data()
        if not data:
            return jsonify({'success': False, 'error': '無資料可匯出'}), 500
        
        # 取得過濾參數
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        owner = request.args.get('owner')
        
        # 過濾資料
        filtered_degrade = filter_issues(data['degrade'], start_date, end_date, owner)
        filtered_resolved = filter_issues(data['resolved'], start_date, end_date, owner)
        
        # 分離內部和 Vendor
        internal_degrade = [i for i in filtered_degrade if i.get('_source') == 'internal']
        vendor_degrade = [i for i in filtered_degrade if i.get('_source') == 'vendor']
        internal_resolved = [i for i in filtered_resolved if i.get('_source') == 'internal']
        vendor_resolved = [i for i in filtered_resolved if i.get('_source') == 'vendor']
        
        manager = JiraDegradeManagerFast(
            site=JIRA_CONFIG['internal']['site'],
            user=JIRA_CONFIG['internal']['user'],
            password=JIRA_CONFIG['internal']['password'],
            token=JIRA_CONFIG['internal']['token']
        )
        
        # 統計分析 - 全部使用 created
        total_degrade = len(filtered_degrade)
        total_resolved = len(filtered_resolved)
        overall_percentage = (total_degrade / total_resolved * 100) if total_resolved > 0 else 0
        
        degrade_weekly = analyze_by_week_with_dates(filtered_degrade, date_field='created')
        resolved_weekly = analyze_by_week_with_dates(filtered_resolved, date_field='created')
        weekly_stats = calculate_weekly_percentage(degrade_weekly, resolved_weekly)
        
        degrade_weekly_internal = analyze_by_week_with_dates(internal_degrade, date_field='created')
        degrade_weekly_vendor = analyze_by_week_with_dates(vendor_degrade, date_field='created')
        resolved_weekly_internal = analyze_by_week_with_dates(internal_resolved, date_field='created')
        resolved_weekly_vendor = analyze_by_week_with_dates(vendor_resolved, date_field='created')
        
        degrade_assignees_internal = manager.get_assignee_distribution(internal_degrade)
        degrade_assignees_vendor = manager.get_assignee_distribution(vendor_degrade)
        resolved_assignees_internal = manager.get_assignee_distribution(internal_resolved)
        resolved_assignees_vendor = manager.get_assignee_distribution(vendor_resolved)
        
        # 週次趨勢數據（最近 20 週）
        recent_weekly = weekly_stats[-20:] if len(weekly_stats) > 20 else weekly_stats
        trend_labels = json.dumps([w['week'] for w in recent_weekly])
        trend_data = json.dumps([w['percentage'] for w in recent_weekly])
        
        # 週次數量對比數據
        count_degrade = json.dumps([w['degrade_count'] for w in recent_weekly])
        count_resolved = json.dumps([w['resolved_count'] for w in recent_weekly])
        
        # 週次分布數據（內部/Vendor）
        all_weeks_internal = sorted(set(list(degrade_weekly_internal.keys()) + list(resolved_weekly_internal.keys())))[-20:]
        all_weeks_vendor = sorted(set(list(degrade_weekly_vendor.keys()) + list(resolved_weekly_vendor.keys())))[-20:]
        
        weekly_internal_labels = json.dumps(all_weeks_internal)
        weekly_internal_degrade = json.dumps([degrade_weekly_internal.get(w, {}).get('count', 0) for w in all_weeks_internal])
        weekly_internal_resolved = json.dumps([resolved_weekly_internal.get(w, {}).get('count', 0) for w in all_weeks_internal])
        
        weekly_vendor_labels = json.dumps(all_weeks_vendor)
        weekly_vendor_degrade = json.dumps([degrade_weekly_vendor.get(w, {}).get('count', 0) for w in all_weeks_vendor])
        weekly_vendor_resolved = json.dumps([resolved_weekly_vendor.get(w, {}).get('count', 0) for w in all_weeks_vendor])
        
        # Assignee 數據（前 20 名）
        degrade_assignees_internal_top = dict(sorted(degrade_assignees_internal.items(), key=lambda x: x[1], reverse=True)[:20])
        degrade_assignees_vendor_top = dict(sorted(degrade_assignees_vendor.items(), key=lambda x: x[1], reverse=True)[:20])
        resolved_assignees_internal_top = dict(sorted(resolved_assignees_internal.items(), key=lambda x: x[1], reverse=True)[:20])
        resolved_assignees_vendor_top = dict(sorted(resolved_assignees_vendor.items(), key=lambda x: x[1], reverse=True)[:20])
        
        degrade_int_labels = json.dumps(list(degrade_assignees_internal_top.keys()))
        degrade_int_data = json.dumps(list(degrade_assignees_internal_top.values()))
        degrade_vnd_labels = json.dumps(list(degrade_assignees_vendor_top.keys()))
        degrade_vnd_data = json.dumps(list(degrade_assignees_vendor_top.values()))
        resolved_int_labels = json.dumps(list(resolved_assignees_internal_top.keys()))
        resolved_int_data = json.dumps(list(resolved_assignees_internal_top.values()))
        resolved_vnd_labels = json.dumps(list(resolved_assignees_vendor_top.keys()))
        resolved_vnd_data = json.dumps(list(resolved_assignees_vendor_top.values()))
        
        # 生成 HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JIRA Degrade % 分析報告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            color: #333;
            font-size: 2.2em;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: #666;
            font-size: 1em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            text-align: center;
        }}
        
        .stat-card h3 {{
            color: #666;
            font-size: 1em;
            margin-bottom: 10px;
            text-transform: uppercase;
        }}
        
        .stat-card .value {{
            font-size: 3em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .chart-container {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            margin-bottom: 30px;
        }}
        
        .chart-container h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}
        
        .chart-wrapper {{
            position: relative;
            height: 400px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.7em;
            margin-left: 10px;
        }}
        
        .badge-internal {{
            background: #e3f2fd;
            color: #1976d2;
        }}
        
        .badge-vendor {{
            background: #fff3e0;
            color: #f57c00;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 JIRA Degrade % 分析報告</h1>
            <p>公版 SQA/QC Degrade 問題統計分析</p>
            <p style="margin-top: 10px; font-size: 0.9em; color: #999;">
                生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Degrade Issues</h3>
                <div class="value">{total_degrade}</div>
            </div>
            <div class="stat-card">
                <h3>Resolved Issues</h3>
                <div class="value">{total_resolved}</div>
            </div>
            <div class="stat-card">
                <h3>Degrade %</h3>
                <div class="value">{overall_percentage:.2f}%</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>📈 每週 Degrade % 趨勢</h2>
            <div class="chart-wrapper">
                <canvas id="trendChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>📊 每週 Degrade vs Resolved 數量</h2>
            <div class="chart-wrapper">
                <canvas id="countChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>📅 每週 Degrade 數量分布 <span class="badge badge-internal">內部 JIRA</span></h2>
            <div class="chart-wrapper">
                <canvas id="weeklyInternal"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>📅 每週 Degrade 數量分布 <span class="badge badge-vendor">Vendor JIRA</span></h2>
            <div class="chart-wrapper">
                <canvas id="weeklyVendor"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>👤 Degrade Issues Assignee 分布 <span class="badge badge-internal">內部 JIRA</span></h2>
            <div class="chart-wrapper">
                <canvas id="degradeAssigneeInternal"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>👤 Degrade Issues Assignee 分布 <span class="badge badge-vendor">Vendor JIRA</span></h2>
            <div class="chart-wrapper">
                <canvas id="degradeAssigneeVendor"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>👤 Resolved Issues Assignee 分布 <span class="badge badge-internal">內部 JIRA</span></h2>
            <div class="chart-wrapper">
                <canvas id="resolvedAssigneeInternal"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>👤 Resolved Issues Assignee 分布 <span class="badge badge-vendor">Vendor JIRA</span></h2>
            <div class="chart-wrapper">
                <canvas id="resolvedAssigneeVendor"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        // 趨勢圖
        new Chart(document.getElementById('trendChart'), {{
            type: 'line',
            data: {{
                labels: {trend_labels},
                datasets: [{{
                    label: 'Degrade %',
                    data: {trend_data},
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false
            }}
        }});
        
        // 數量圖
        new Chart(document.getElementById('countChart'), {{
            type: 'bar',
            data: {{
                labels: {trend_labels},
                datasets: [
                    {{
                        label: 'Degrade Issues',
                        data: {count_degrade},
                        backgroundColor: '#ff6b6b'
                    }},
                    {{
                        label: 'Resolved Issues',
                        data: {count_resolved},
                        backgroundColor: '#51cf66'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false
            }}
        }});
        
        // 週次分布 - 內部
        new Chart(document.getElementById('weeklyInternal'), {{
            type: 'bar',
            data: {{
                labels: {weekly_internal_labels},
                datasets: [
                    {{
                        label: 'Degrade Issues',
                        data: {weekly_internal_degrade},
                        backgroundColor: '#ff6b6b'
                    }},
                    {{
                        label: 'Resolved Issues',
                        data: {weekly_internal_resolved},
                        backgroundColor: '#51cf66'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false
            }}
        }});
        
        // 週次分布 - Vendor
        new Chart(document.getElementById('weeklyVendor'), {{
            type: 'bar',
            data: {{
                labels: {weekly_vendor_labels},
                datasets: [
                    {{
                        label: 'Degrade Issues',
                        data: {weekly_vendor_degrade},
                        backgroundColor: '#ff6b6b'
                    }},
                    {{
                        label: 'Resolved Issues',
                        data: {weekly_vendor_resolved},
                        backgroundColor: '#51cf66'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false
            }}
        }});
        
        // Assignee - Degrade Internal
        new Chart(document.getElementById('degradeAssigneeInternal'), {{
            type: 'bar',
            data: {{
                labels: {degrade_int_labels},
                datasets: [{{
                    label: 'Degrade Issues',
                    data: {degrade_int_data},
                    backgroundColor: '#ff6b6b'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y'
            }}
        }});
        
        // Assignee - Degrade Vendor
        new Chart(document.getElementById('degradeAssigneeVendor'), {{
            type: 'bar',
            data: {{
                labels: {degrade_vnd_labels},
                datasets: [{{
                    label: 'Degrade Issues',
                    data: {degrade_vnd_data},
                    backgroundColor: '#ff6b6b'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y'
            }}
        }});
        
        // Assignee - Resolved Internal
        new Chart(document.getElementById('resolvedAssigneeInternal'), {{
            type: 'bar',
            data: {{
                labels: {resolved_int_labels},
                datasets: [{{
                    label: 'Resolved Issues',
                    data: {resolved_int_data},
                    backgroundColor: '#51cf66'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y'
            }}
        }});
        
        // Assignee - Resolved Vendor
        new Chart(document.getElementById('resolvedAssigneeVendor'), {{
            type: 'bar',
            data: {{
                labels: {resolved_vnd_labels},
                datasets: [{{
                    label: 'Resolved Issues',
                    data: {resolved_vnd_data},
                    backgroundColor: '#51cf66'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y'
            }}
        }});
    </script>
</body>
</html>
"""
        
        output = io.BytesIO(html_content.encode('utf-8'))
        output.seek(0)
        
        filename = f"jira_degrade_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        return send_file(
            output,
            mimetype='text/html',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ HTML 匯出失敗: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 啟動 JIRA Degrade 分析系統（增強版）...")
    print("   新功能:")
    print("   ✅ 週次圖表（內部/Vendor 分開）")
    print("   ✅ 匯出 Excel（多頁籤）")
    print("   ✅ 匯出 HTML（靜態）")
    print("   ✅ UI 美化 + 載入動畫")
    print("   ✅ 全部使用 created 日期")
    app.run(debug=True, host='0.0.0.0', port=5000)