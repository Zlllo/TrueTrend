"""
TrueTrend CN - 知乎热榜爬虫
异步获取知乎热榜数据
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx

from ..data_fetcher import DataFetcher


@dataclass
class ZhihuHotItem:
    """知乎热榜条目"""
    rank: int
    title: str
    hot_value: int
    excerpt: str
    url: str
    answer_count: int = 0
    question_id: Optional[str] = None


class ZhihuFetcher(DataFetcher):
    """
    知乎热榜数据获取器
    
    数据来源: 知乎热榜 API
    """
    
    # 知乎热榜 API
    ZHIHU_HOT_API = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
    
    # 备用: 知乎热榜页面
    ZHIHU_HOT_PAGE = "https://www.zhihu.com/hot"
    
    # 请求头
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.zhihu.com/hot",
        "X-Requested-With": "fetch",
    }
    
    def __init__(self, cookie: Optional[str] = None):
        super().__init__("zhihu")
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
        获取知乎热榜
        
        Args:
            limit: 返回条目数量限制
            
        Returns:
            热榜列表
        """
        try:
            items = await self._fetch_from_api()
            self.update_fetch_time()
            
            results = []
            for item in items[:limit]:
                results.append({
                    "keyword": item.title,
                    "raw_heat_score": float(item.hot_value),
                    "timestamp": datetime.now().isoformat(),
                    "platform": "zhihu",
                    "metadata": {
                        "rank": item.rank,
                        "excerpt": item.excerpt,
                        "url": item.url,
                        "answer_count": item.answer_count,
                        "question_id": item.question_id,
                    }
                })
            
            return results
            
        except Exception as e:
            print(f"[ZhihuFetcher] 获取热榜失败: {e}")
            return []
    
    async def _fetch_from_api(self) -> List[ZhihuHotItem]:
        """从知乎 API 获取热榜"""
        client = await self._get_client()
        
        try:
            params = {
                "limit": 50,
                "desktop": "true",
            }
            
            response = await client.get(self.ZHIHU_HOT_API, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = []
            
            hot_list = data.get("data", [])
            
            for idx, item in enumerate(hot_list):
                try:
                    target = item.get("target", {})
                    
                    title = target.get("title", "") or target.get("question", {}).get("title", "")
                    if not title:
                        continue
                    
                    # 热度值
                    detail_text = item.get("detail_text", "0 万热度")
                    hot_value = self._parse_hot_value(detail_text)
                    
                    # 问题链接
                    question_id = str(target.get("id", ""))
                    url = f"https://www.zhihu.com/question/{question_id}" if question_id else ""
                    
                    # 回答数
                    answer_count = target.get("answer_count", 0)
                    
                    # 摘要
                    excerpt = target.get("excerpt", "")
                    
                    items.append(ZhihuHotItem(
                        rank=idx + 1,
                        title=title,
                        hot_value=hot_value,
                        excerpt=excerpt[:100] if excerpt else "",
                        url=url,
                        answer_count=answer_count,
                        question_id=question_id,
                    ))
                    
                except Exception as e:
                    print(f"[ZhihuFetcher] 解析条目失败: {e}")
                    continue
            
            return items
            
        except httpx.HTTPStatusError as e:
            print(f"[ZhihuFetcher] HTTP 错误: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"[ZhihuFetcher] API 请求失败: {e}")
            return []
    
    def _parse_hot_value(self, text: str) -> int:
        """
        解析热度值，如 "1234 万热度" -> 12340000
        """
        import re
        
        if not text:
            return 0
        
        # 匹配数字
        match = re.search(r"([\d.]+)\s*(万)?", text)
        if not match:
            return 0
        
        value = float(match.group(1))
        if match.group(2) == "万":
            value *= 10000
        
        return int(value)
    
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
        知乎平台权重
        
        知乎偏向深度讨论和专业内容
        """
        return 0.85
