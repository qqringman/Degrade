"""
JIRA Degrade 分析管理模組 - 超快速版本
使用並行處理和優化的 batch size
修改：
- Degrade issues 使用 created 欄位
- Resolved issues 使用 resolutiondate 欄位
- 加入詳細的錯誤檢測和警告機制
"""
import os
import requests
import re
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

class JiraDegradeManagerFast:
    """JIRA Degrade 統計管理類別 - 優化版本"""
    
    def __init__(self, site, user, password, token=None):
        self.site = site
        self.user = user
        self.password = password
        self.token = token
        self.base_url = f"https://{site}"
        
        # 設定認證方式
        if token:
            self.auth = None
            self.headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {token}"
            }
        else:
            self.auth = (user, password)
            self.headers = {"Accept": "application/json"}
    
    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """統一的請求方法"""
        headers = kwargs.get('headers', {})
        headers.update(self.headers)
        kwargs['headers'] = headers
        
        if not self.token and self.auth:
            kwargs['auth'] = self.auth
        
        if method.upper() == 'GET':
            return requests.get(url, **kwargs)
        elif method.upper() == 'POST':
            return requests.post(url, **kwargs)
        else:
            raise ValueError(f"不支援的 HTTP 方法: {method}")
        
    def get_filter_issues_fast(self, filter_id: str, max_results: int = None) -> Dict[str, Any]:
        """
        快速取得指定 filter 的所有 issues
        """
        all_issues = []
        start_at = 0
        batch_size = 500
        filter_owner = None  # 初始為 None
        
        start_time = time.time()
        
        try:
            # ✅ 嘗試取得 filter 資訊（包含 owner）
            try:
                filter_url = f"{self.base_url}/rest/api/2/filter/{filter_id}"
                filter_response = self._make_request(filter_url, timeout=10)
                if filter_response.status_code == 200:
                    filter_data = filter_response.json()
                    owner_info = filter_data.get('owner', {})
                    filter_owner = owner_info.get('displayName') or owner_info.get('name')
                    if filter_owner:
                        print(f"  📋 Filter {filter_id} owner: {filter_owner}")
            except Exception as e:
                print(f"  ⚠️  無法取得 Filter {filter_id} 的 owner 資訊: {e}")
            
            # ✅ 如果無法取得 filter owner，使用連線帳號作為 fallback
            if not filter_owner:
                filter_owner = self.user  # 使用連線的帳號
                print(f"  📋 Filter {filter_id} 使用連線帳號: {filter_owner}")
            
            while True:
                url = f"{self.base_url}/rest/api/2/search"
                params = {
                    'jql': f'filter={filter_id}',
                    'startAt': start_at,
                    'maxResults': batch_size,
                    'fields': 'key,assignee,created,resolutiondate,updated,duedate'
                }
                
                response = self._make_request(url, params=params, timeout=60)
                
                # 檢查認證失敗
                if response.status_code == 401:
                    error_msg = f"認證失敗 - 請先登入 JIRA"
                    print(f"  ❌ Filter {filter_id} 失敗: {error_msg}")
                    return {
                        'success': False,
                        'issues': [],
                        'error': error_msg,
                        'error_type': 'AUTH_FAILED',
                        'site': self.site,
                        'filter_id': filter_id,
                        'filter_owner': filter_owner or self.user  # ✅ 確保有值
                    }
                
                # 檢查權限不足
                if response.status_code == 403:
                    error_msg = f"權限不足 - 無法存取 Filter {filter_id}"
                    print(f"  ❌ Filter {filter_id} 失敗: {error_msg}")
                    return {
                        'success': False,
                        'issues': [],
                        'error': error_msg,
                        'error_type': 'PERMISSION_DENIED',
                        'site': self.site,
                        'filter_id': filter_id,
                        'filter_owner': filter_owner or self.user  # ✅ 確保有值
                    }
                
                # 檢查 filter 不存在
                if response.status_code == 404:
                    error_msg = f"Filter 不存在 - Filter ID: {filter_id}"
                    print(f"  ❌ Filter {filter_id} 失敗: {error_msg}")
                    return {
                        'success': False,
                        'issues': [],
                        'error': error_msg,
                        'error_type': 'FILTER_NOT_FOUND',
                        'site': self.site,
                        'filter_id': filter_id,
                        'filter_owner': filter_owner or self.user  # ✅ 確保有值
                    }
                
                # 其他 HTTP 錯誤（包含 HTTP 500）
                if response.status_code != 200:
                    error_msg = f"HTTP {response.status_code}"
                    print(f"  ❌ Filter {filter_id} 失敗: {error_msg}")
                    return {
                        'success': False,
                        'issues': [],
                        'error': error_msg,
                        'error_type': 'HTTP_ERROR',
                        'site': self.site,
                        'filter_id': filter_id,
                        'filter_owner': filter_owner or self.user  # ✅ 確保有值
                    }
                
                data = response.json()
                issues = data.get('issues', [])
                
                if not issues:
                    break
                
                all_issues.extend(issues)
                
                total = data.get('total', 0)
                print(f"  📊 Filter {filter_id}: 已載入 {len(all_issues)}/{total} 筆")
                
                if max_results and len(all_issues) >= max_results:
                    break
                
                if start_at + batch_size >= total:
                    break
                
                start_at += batch_size
            
            elapsed = time.time() - start_time
            print(f"  ✓ Filter {filter_id} 完成: {len(all_issues)} 筆 ({elapsed:.1f}秒)")
            
            final_issues = all_issues[:max_results] if max_results else all_issues
            return {
                'success': True,
                'issues': final_issues,
                'site': self.site,
                'filter_id': filter_id,
                'filter_owner': filter_owner or self.user  # ✅ 確保有值
            }
            
        except requests.exceptions.Timeout:
            error_msg = f"連線逾時 - 請檢查網路連線"
            print(f"  ❌ Filter {filter_id} 失敗: {error_msg}")
            return {
                'success': False,
                'issues': [],
                'error': error_msg,
                'error_type': 'TIMEOUT',
                'site': self.site,
                'filter_id': filter_id,
                'filter_owner': filter_owner or self.user  # ✅ 確保有值
            }
        except requests.exceptions.ConnectionError:
            error_msg = f"無法連線到 {self.site}"
            print(f"  ❌ Filter {filter_id} 失敗: {error_msg}")
            return {
                'success': False,
                'issues': [],
                'error': error_msg,
                'error_type': 'CONNECTION_ERROR',
                'site': self.site,
                'filter_id': filter_id,
                'filter_owner': filter_owner or self.user  # ✅ 確保有值
            }
        except Exception as e:
            error_msg = str(e)
            print(f"  ❌ Filter {filter_id} 失敗: {error_msg}")
            return {
                'success': False,
                'issues': [],
                'error': error_msg,
                'error_type': 'UNKNOWN_ERROR',
                'site': self.site,
                'filter_id': filter_id,
                'filter_owner': filter_owner or self.user  # ✅ 確保有值
            }
    
    def get_week_number(self, date_str: str) -> str:
        """
        將日期轉換為週次 (YYYY-Wxx)
        """
        try:
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
            
            date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
            iso_calendar = date_obj.isocalendar()
            return f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"
        except Exception as e:
            return "Unknown"
    
    def analyze_by_week(self, issues: List[Dict[str, Any]], date_field: str = 'updated') -> Dict[str, Any]:
        """
        按週統計 issues - 優化版本
        支援不同的日期欄位：created, resolutiondate, updated
        """
        weekly_stats = defaultdict(lambda: {
            'count': 0,
            'issues': [],
            'assignees': defaultdict(int)
        })
        
        for issue in issues:
            fields = issue.get('fields', {})
            date_str = fields.get(date_field)
            
            if not date_str:
                continue
            
            week = self.get_week_number(date_str)
            weekly_stats[week]['count'] += 1
            weekly_stats[week]['issues'].append(issue.get('key'))
            
            assignee = fields.get('assignee')
            if assignee:
                assignee_name = assignee.get('displayName', 'Unassigned')
            else:
                assignee_name = 'Unassigned'
            
            weekly_stats[week]['assignees'][assignee_name] += 1
        
        return dict(weekly_stats)
    
    def get_assignee_distribution(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        統計 assignee 分布 - 優化版本
        """
        assignee_stats = defaultdict(int)
        
        for issue in issues:
            fields = issue.get('fields', {})
            assignee = fields.get('assignee')
            
            if assignee:
                assignee_name = assignee.get('displayName', 'Unassigned')
            else:
                assignee_name = 'Unassigned'
            
            assignee_stats[assignee_name] += 1
        
        return dict(assignee_stats)


def load_all_filters_parallel(jira_configs, filters):
    """
    並行載入所有 filters - 這是速度提升的關鍵！
    
    Args:
        jira_configs: JIRA 連線設定
        filters: Filter IDs
        
    Returns:
        所有資料 + 警告信息
    """
    print("=" * 70)
    print("🚀 開始並行載入 JIRA 資料...")
    start_time = time.time()
    
    # 建立 JIRA managers
    internal_jira = JiraDegradeManagerFast(
        site=jira_configs['internal']['site'],
        user=jira_configs['internal']['user'],
        password=jira_configs['internal']['password'],
        token=jira_configs['internal']['token']
    )
    
    vendor_jira = JiraDegradeManagerFast(
        site=jira_configs['vendor']['site'],
        user=jira_configs['vendor']['user'],
        password=jira_configs['vendor']['password'],
        token=jira_configs['vendor']['token']
    )
    
    # 定義要執行的任務
    tasks = [
        ('internal_degrade', internal_jira, filters['degrade']['internal'], 'internal', 'degrade'),
        ('vendor_degrade', vendor_jira, filters['degrade']['vendor'], 'vendor', 'degrade'),
        ('internal_resolved', internal_jira, filters['resolved']['internal'], 'internal', 'resolved'),
        ('vendor_resolved', vendor_jira, filters['resolved']['vendor'], 'vendor', 'resolved')
    ]
    
    # 使用 ThreadPoolExecutor 並行執行
    results = {}
    warnings = []  # 收集警告信息
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        # 提交所有任務
        future_to_task = {
            executor.submit(jira.get_filter_issues_fast, filter_id): (task_name, source, type_name)
            for task_name, jira, filter_id, source, type_name in tasks
        }
        
        # 收集結果
        for future in as_completed(future_to_task):
            task_name, source, type_name = future_to_task[future]
            try:
                result = future.result()
                
                if result['success']:
                    results[task_name] = result['issues']
                else:
                    # 載入失敗，加入警告
                    results[task_name] = []
                    warning = {
                        'source': source,
                        'type': type_name,
                        'site': result.get('site', ''),
                        'filter_id': result.get('filter_id', ''),
                        'filter_owner': result.get('filter_owner', 'Unknown'),
                        'error': result.get('error', '未知錯誤'),
                        'error_type': result.get('error_type', 'UNKNOWN_ERROR')
                    }
                    warnings.append(warning)
                    print(f"  ⚠️  {task_name} 載入失敗，已加入警告")
                    
            except Exception as e:
                print(f"  ❌ {task_name} 失敗: {e}")
                results[task_name] = []
                warnings.append({
                    'source': source,
                    'type': type_name,
                    'error': str(e),
                    'error_type': 'UNKNOWN_ERROR'
                })
    
    # 標記來源並合併
    for issue in results.get('internal_degrade', []):
        issue['_source'] = 'internal'
    for issue in results.get('vendor_degrade', []):
        issue['_source'] = 'vendor'
    for issue in results.get('internal_resolved', []):
        issue['_source'] = 'internal'
    for issue in results.get('vendor_resolved', []):
        issue['_source'] = 'vendor'
    
    all_degrade = results.get('internal_degrade', []) + results.get('vendor_degrade', [])
    all_resolved = results.get('internal_resolved', []) + results.get('vendor_resolved', [])
    
    print("\n📊 統計分析中...")
    # 使用任一 manager 做統計
    # Degrade 使用 created，Resolved 使用 resolutiondate
    degrade_weekly = internal_jira.analyze_by_week(all_degrade, date_field='created')
    resolved_weekly = internal_jira.analyze_by_week(all_resolved, date_field='resolutiondate')
    degrade_assignees = internal_jira.get_assignee_distribution(all_degrade)
    resolved_assignees = internal_jira.get_assignee_distribution(all_resolved)
    
    total_time = time.time() - start_time
    print(f"\n✅ 資料載入完成！")
    print(f"  ⏱  總耗時: {total_time:.1f} 秒")
    print(f"  📈 Degrade: {len(all_degrade)} 筆 (使用 created 日期)")
    print(f"  📈 Resolved: {len(all_resolved)} 筆 (使用 resolutiondate)")
    
    if warnings:
        print(f"  ⚠️  警告: {len(warnings)} 個來源載入失敗")
        for w in warnings:
            print(f"     - {w['source']} {w['type']}: {w['error']}")
    
    print(f"  🚀 平均每秒處理: {(len(all_degrade) + len(all_resolved)) / total_time:.0f} 筆" if total_time > 0 else "  🚀 即時完成")
    print("=" * 70)
    
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
        'metadata': {
            'load_time': total_time,
            'timestamp': datetime.now().isoformat(),
            'warnings': warnings  # 加入警告信息
        }
    }