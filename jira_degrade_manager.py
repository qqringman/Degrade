"""
JIRA Degrade 分析管理模組
擴展 JIRA API 功能，支援 filter 查詢和統計分析
"""
import os
import requests
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

class JiraDegradeManager:
    """JIRA Degrade 統計管理類別"""
    
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
    
    def get_filter_issues(self, filter_id: str, max_results: int = 1000) -> List[Dict[str, Any]]:
        """
        取得指定 filter 的所有 issues
        
        Args:
            filter_id: JIRA filter ID
            max_results: 最多取得幾筆資料
            
        Returns:
            issues 列表
        """
        all_issues = []
        start_at = 0
        batch_size = 100
        
        try:
            while len(all_issues) < max_results:
                url = f"{self.base_url}/rest/api/2/search"
                params = {
                    'jql': f'filter={filter_id}',
                    'startAt': start_at,
                    'maxResults': batch_size,
                    'fields': 'key,summary,assignee,status,resolutiondate,created,updated,description'
                }
                
                response = self._make_request(url, params=params, timeout=60)
                
                if response.status_code != 200:
                    print(f"取得 filter {filter_id} 失敗: HTTP {response.status_code}")
                    break
                
                data = response.json()
                issues = data.get('issues', [])
                
                if not issues:
                    break
                
                all_issues.extend(issues)
                
                # 檢查是否還有更多資料
                total = data.get('total', 0)
                if start_at + batch_size >= total:
                    break
                
                start_at += batch_size
            
            print(f"成功取得 filter {filter_id} 共 {len(all_issues)} 筆 issues")
            return all_issues[:max_results]
            
        except Exception as e:
            print(f"取得 filter {filter_id} 失敗: {str(e)}")
            return []
    
    def has_gerrit_url(self, description: str) -> bool:
        """
        檢查 description 是否包含 sa 或 sd gerrit 網址
        
        Args:
            description: issue 的 description
            
        Returns:
            是否包含 gerrit URL
        """
        if not description:
            return False
        
        # 檢查是否包含 sa 或 sd gerrit URL
        gerrit_patterns = [
            r'https?://[^\s]*gerrit[^\s]*/(sa|sd)[^\s]*',
            r'gerrit[^\s]*/(sa|sd)',
            r'(sa|sd)[^\s]*gerrit'
        ]
        
        for pattern in gerrit_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return True
        
        return False
    
    def filter_issues_with_gerrit(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        過濾出包含 gerrit URL 的 issues
        
        Args:
            issues: issue 列表
            
        Returns:
            過濾後的 issue 列表
        """
        filtered = []
        for issue in issues:
            description = issue.get('fields', {}).get('description', '')
            if self.has_gerrit_url(description):
                filtered.append(issue)
        
        return filtered
    
    def get_week_number(self, date_str: str) -> str:
        """
        將日期轉換為週次 (YYYY-Wxx)
        
        Args:
            date_str: ISO 格式日期字串
            
        Returns:
            週次字串
        """
        try:
            # 處理不同的日期格式
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
            
            date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
            # 使用 ISO 週次 (週一為一週的開始)
            iso_calendar = date_obj.isocalendar()
            return f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"
        except Exception as e:
            print(f"日期轉換失敗: {date_str}, 錯誤: {str(e)}")
            return "Unknown"
    
    def analyze_by_week(self, issues: List[Dict[str, Any]], date_field: str = 'resolutiondate') -> Dict[str, Any]:
        """
        按週統計 issues
        
        Args:
            issues: issue 列表
            date_field: 使用的日期欄位 (resolutiondate, created, updated)
            
        Returns:
            週統計資料
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
            
            # 統計 assignee
            assignee = fields.get('assignee')
            if assignee:
                assignee_name = assignee.get('displayName', 'Unassigned')
            else:
                assignee_name = 'Unassigned'
            
            weekly_stats[week]['assignees'][assignee_name] += 1
        
        return dict(weekly_stats)
    
    def get_assignee_distribution(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        統計 assignee 分布
        
        Args:
            issues: issue 列表
            
        Returns:
            assignee 統計
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
