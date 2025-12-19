"""
TrueTrend CN - 微博热搜爬虫
参考 BettaFish 项目实现，使用 Playwright + httpx 异步爬取
"""

import asyncio
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from ..data_fetcher import DataFetcher


@dataclass
class WeiboHotItem:
    """微博热搜条目"""
    rank: int
    keyword: str
    hot_value: int  # 热度值
    tag: str  # 热/新/沸/爆
    url: str
    category: Optional[str] = None


class WeiboFetcher(DataFetcher):
    """
    微博热搜数据获取器
    
    数据来源：
    1. 微博热搜榜 HTML 页面解析
    2. 微博移动端 API (备用)
    
    参考 BettaFish MindSpider 实现
    """
    
    # 微博热搜页面 URL
    WEIBO_HOT_URL = "https://s.weibo.com/top/summary"
    WEIBO_REALTIME_URL = "https://s.weibo.com/top/summary?cate=realtimehot"
    
    # 微博移动端 API (备用方案)
    WEIBO_MOBILE_API = "https://m.weibo.cn/api/container/getIndex"
    WEIBO_HOT_CONTAINER_ID = "106003type=25&t=3&disable_hot=1&filter_type=realtimehot"
    
    # 请求头 (模拟浏览器)
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://weibo.com/",
    }
    
    def __init__(self, cookie: Optional[str] = None):
        """
        初始化微博爬虫
        
        Args:
            cookie: 可选的登录 Cookie，用于绕过登录限制
        """
        super().__init__("weibo")
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
        获取微博热搜榜
        
        Args:
            limit: 返回条目数量限制
            
        Returns:
            热搜列表，每个条目包含:
            - keyword: 热词
            - raw_heat_score: 热度值
            - timestamp: 获取时间
            - metadata: {rank, tag, url, category}
        """
        try:
            # 方案1: 解析 HTML 页面
            items = await self._fetch_from_html()
            
            if not items:
                # 方案2: 使用移动端 API (备用)
                items = await self._fetch_from_mobile_api()
            
            self.update_fetch_time()
            
            # 转换为标准格式
            results = []
            for item in items[:limit]:
                results.append({
                    "keyword": item.keyword,
                    "raw_heat_score": float(item.hot_value),
                    "timestamp": datetime.now().isoformat(),
                    "platform": "weibo",
                    "metadata": {
                        "rank": item.rank,
                        "tag": item.tag,
                        "url": item.url,
                        "category": item.category,
                    }
                })
            
            return results
            
        except Exception as e:
            print(f"[WeiboFetcher] 获取热搜失败: {e}")
            return []
    
    async def _fetch_from_html(self) -> List[WeiboHotItem]:
        """从 HTML 页面解析热搜"""
        client = await self._get_client()
        
        try:
            response = await client.get(self.WEIBO_HOT_URL)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            items = []
            
            # 查找热搜表格
            table = soup.find("table", class_="table")
            if not table:
                # 尝试查找其他可能的容器
                table = soup.find("div", id="pl_top_realtimehot")
            
            if not table:
                return []
            
            rows = table.find_all("tr")
            
            for row in rows:
                try:
                    # 跳过表头
                    if row.find("th"):
                        continue
                    
                    cells = row.find_all("td")
                    if len(cells) < 2:
                        continue
                    
                    # 获取排名
                    rank_cell = cells[0]
                    rank_text = rank_cell.get_text(strip=True)
                    rank = int(rank_text) if rank_text.isdigit() else 0
                    
                    # 获取关键词
                    keyword_cell = cells[1]
                    keyword_link = keyword_cell.find("a")
                    if not keyword_link:
                        continue
                    
                    keyword = keyword_link.get_text(strip=True)
                    url = keyword_link.get("href", "")
                    if url and not url.startswith("http"):
                        url = f"https://s.weibo.com{url}"
                    
                    # 获取热度值
                    hot_span = keyword_cell.find("span")
                    hot_value = 0
                    if hot_span:
                        hot_text = hot_span.get_text(strip=True)
                        hot_value = self._parse_hot_value(hot_text)
                    
                    # 获取标签 (热/新/沸/爆)
                    tag = ""
                    tag_icon = keyword_cell.find("i")
                    if tag_icon:
                        tag_class = tag_icon.get("class", [])
                        if "icon-txt-new" in tag_class:
                            tag = "新"
                        elif "icon-txt-hot" in tag_class:
                            tag = "热"
                        elif "icon-txt-fei" in tag_class:
                            tag = "沸"
                        elif "icon-txt-bao" in tag_class:
                            tag = "爆"
                    
                    items.append(WeiboHotItem(
                        rank=rank,
                        keyword=keyword,
                        hot_value=hot_value,
                        tag=tag,
                        url=url,
                    ))
                    
                except Exception as e:
                    print(f"[WeiboFetcher] 解析行失败: {e}")
                    continue
            
            return items
            
        except httpx.HTTPStatusError as e:
            print(f"[WeiboFetcher] HTTP 错误: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"[WeiboFetcher] HTML 解析失败: {e}")
            return []
    
    async def _fetch_from_mobile_api(self) -> List[WeiboHotItem]:
        """从移动端 API 获取热搜 (备用方案)"""
        client = await self._get_client()
        
        try:
            params = {
                "containerid": self.WEIBO_HOT_CONTAINER_ID,
            }
            
            response = await client.get(self.WEIBO_MOBILE_API, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = []
            
            if data.get("ok") != 1:
                return []
            
            cards = data.get("data", {}).get("cards", [])
            
            for card in cards:
                card_group = card.get("card_group", [])
                for item in card_group:
                    try:
                        desc = item.get("desc", "")
                        keyword = item.get("desc_extr", "") or desc
                        
                        if not keyword:
                            continue
                        
                        # 提取热度
                        hot_value = item.get("desc_extr", 0)
                        if isinstance(hot_value, str):
                            hot_value = self._parse_hot_value(hot_value)
                        
                        scheme = item.get("scheme", "")
                        
                        items.append(WeiboHotItem(
                            rank=len(items) + 1,
                            keyword=keyword,
                            hot_value=hot_value if isinstance(hot_value, int) else 0,
                            tag="",
                            url=scheme,
                        ))
                        
                    except Exception:
                        continue
            
            return items
            
        except Exception as e:
            print(f"[WeiboFetcher] 移动端 API 获取失败: {e}")
            return []
    
    def _parse_hot_value(self, text: str) -> int:
        """
        解析热度值文本，如 "233万" -> 2330000
        """
        if not text:
            return 0
        
        text = text.strip()
        
        # 匹配数字和单位
        match = re.match(r"([\d.]+)\s*(万|亿)?", text)
        if not match:
            return 0
        
        value = float(match.group(1))
        unit = match.group(2)
        
        if unit == "万":
            value *= 10000
        elif unit == "亿":
            value *= 100000000
        
        return int(value)
    
    async def fetch_keyword_history(
        self, 
        keyword: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        获取关键词的历史热度数据
        
        注意: 微博没有公开的历史热度 API，此功能需要借助第三方服务或自建数据库
        目前返回空列表，后续可接入清博、知微等舆情平台 API
        """
        # TODO: 接入历史数据源
        # 可选方案:
        # 1. 清博大数据 API
        # 2. 知微传播分析
        # 3. 自建定时采集数据库
        return []
    
    def get_platform_weight(self) -> float:
        """
        获取微博平台权重
        
        微博是中国最大的社交媒体平台之一，舆论影响力大
        """
        return 0.9
