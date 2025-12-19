"""
TrueTrend CN - B站热搜爬虫
异步获取 B 站热搜数据
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx

from ..data_fetcher import DataFetcher


@dataclass
class BilibiliHotItem:
    """B站热搜条目"""
    rank: int
    keyword: str
    show_name: str
    hot_value: int
    icon: str  # 热/新
    url: str


class BilibiliFetcher(DataFetcher):
    """
    B站热搜数据获取器
    
    数据来源: B站搜索热词 API
    """
    
    # B站热搜 API
    BILIBILI_HOT_API = "https://s.search.bilibili.com/main/hotword"
    
    # B站热门视频 API (备用)
    BILIBILI_POPULAR_API = "https://api.bilibili.com/x/web-interface/popular"
    
    # 实时热搜
    BILIBILI_TRENDING_API = "https://api.bilibili.com/x/web-interface/search/square"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
    }
    
    def __init__(self, cookie: Optional[str] = None):
        super().__init__("bilibili")
        self.cookie = cookie
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            headers = self.HEADERS.copy()
            if self.cookie:
                headers["Cookie"] = self.cookie
            
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client
    
    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def fetch_trending(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取B站热搜
        
        Args:
            limit: 返回条目数量限制
            
        Returns:
            热搜列表
        """
        try:
            # 尝试获取热搜词
            items = await self._fetch_hotword()
            
            if not items:
                # 备用：获取实时热搜
                items = await self._fetch_trending_square()
            
            self.update_fetch_time()
            
            results = []
            for item in items[:limit]:
                results.append({
                    "keyword": item.keyword,
                    "raw_heat_score": float(item.hot_value),
                    "timestamp": datetime.now().isoformat(),
                    "platform": "bilibili",
                    "metadata": {
                        "rank": item.rank,
                        "show_name": item.show_name,
                        "icon": item.icon,
                        "url": item.url,
                    }
                })
            
            return results
            
        except Exception as e:
            print(f"[BilibiliFetcher] 获取热搜失败: {e}")
            return []
    
    async def _fetch_hotword(self) -> List[BilibiliHotItem]:
        """从 B 站热词 API 获取数据"""
        client = await self._get_client()
        
        try:
            response = await client.get(self.BILIBILI_HOT_API)
            response.raise_for_status()
            
            data = response.json()
            items = []
            
            if data.get("code") != 0:
                return []
            
            hot_list = data.get("list", [])
            
            for idx, item in enumerate(hot_list):
                try:
                    keyword = item.get("keyword", "")
                    show_name = item.get("show_name", keyword)
                    
                    if not keyword:
                        continue
                    
                    # B站热词接口没有直接的热度值，使用位置作为热度估算
                    # 第1位热度最高
                    hot_value = (len(hot_list) - idx) * 10000
                    
                    icon = item.get("icon", "")
                    url = f"https://search.bilibili.com/all?keyword={keyword}"
                    
                    items.append(BilibiliHotItem(
                        rank=idx + 1,
                        keyword=keyword,
                        show_name=show_name,
                        hot_value=hot_value,
                        icon=icon,
                        url=url,
                    ))
                    
                except Exception as e:
                    print(f"[BilibiliFetcher] 解析条目失败: {e}")
                    continue
            
            return items
            
        except Exception as e:
            print(f"[BilibiliFetcher] 热词 API 请求失败: {e}")
            return []
    
    async def _fetch_trending_square(self) -> List[BilibiliHotItem]:
        """从 B 站热搜广场 API 获取数据 (备用)"""
        client = await self._get_client()
        
        try:
            params = {
                "limit": 50,
            }
            
            response = await client.get(self.BILIBILI_TRENDING_API, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = []
            
            if data.get("code") != 0:
                return []
            
            trending = data.get("data", {}).get("trending", {}).get("list", [])
            
            for idx, item in enumerate(trending):
                try:
                    keyword = item.get("keyword", "") or item.get("show_name", "")
                    
                    if not keyword:
                        continue
                    
                    # 热度值
                    hot_value = item.get("heat_score", 0) or (len(trending) - idx) * 10000
                    
                    items.append(BilibiliHotItem(
                        rank=idx + 1,
                        keyword=keyword,
                        show_name=item.get("show_name", keyword),
                        hot_value=hot_value,
                        icon=item.get("icon", ""),
                        url=f"https://search.bilibili.com/all?keyword={keyword}",
                    ))
                    
                except Exception:
                    continue
            
            return items
            
        except Exception as e:
            print(f"[BilibiliFetcher] 热搜广场 API 请求失败: {e}")
            return []
    
    async def fetch_keyword_history(
        self, 
        keyword: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """获取关键词历史数据 (暂未实现)"""
        return []
    
    def get_platform_weight(self) -> float:
        """
        B站平台权重
        
        B站用户以年轻人为主，二次元和科技内容影响力大
        """
        return 0.8
