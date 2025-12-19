"""
TrueTrend CN - 数据聚合器
聚合多平台数据，自动合并相同热词
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Type
from collections import defaultdict

from ..data_fetcher import DataFetcher
from .weibo_fetcher import WeiboFetcher
from .zhihu_fetcher import ZhihuFetcher
from .bilibili_fetcher import BilibiliFetcher


class FetcherManager:
    """
    数据聚合管理器
    
    功能:
    1. 并发获取多平台数据
    2. 合并相同热词
    3. 缓存机制 (避免频繁请求)
    """
    
    # 缓存有效期 (秒)
    CACHE_TTL = 60 * 5  # 5 分钟
    
    def __init__(self):
        self.fetchers: Dict[str, DataFetcher] = {}
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_time: Dict[str, datetime] = {}
    
    def register_fetcher(self, name: str, fetcher: DataFetcher):
        """注册数据获取器"""
        self.fetchers[name] = fetcher
    
    def register_default_fetchers(
        self,
        weibo_cookie: Optional[str] = None,
        zhihu_cookie: Optional[str] = None,
        bilibili_cookie: Optional[str] = None,
    ):
        """注册默认的三个平台获取器"""
        self.register_fetcher("weibo", WeiboFetcher(cookie=weibo_cookie))
        self.register_fetcher("zhihu", ZhihuFetcher(cookie=zhihu_cookie))
        self.register_fetcher("bilibili", BilibiliFetcher(cookie=bilibili_cookie))
    
    async def close_all(self):
        """关闭所有获取器的连接"""
        for fetcher in self.fetchers.values():
            if hasattr(fetcher, 'close'):
                await fetcher.close()
    
    def _is_cache_valid(self, platform: str) -> bool:
        """检查缓存是否有效"""
        if platform not in self._cache_time:
            return False
        
        elapsed = (datetime.now() - self._cache_time[platform]).total_seconds()
        return elapsed < self.CACHE_TTL
    
    async def fetch_single_platform(
        self, 
        platform: str, 
        limit: int = 50,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取单个平台的数据
        
        Args:
            platform: 平台名称 (weibo/zhihu/bilibili)
            limit: 返回数量限制
            use_cache: 是否使用缓存
        """
        if platform not in self.fetchers:
            raise ValueError(f"未注册的平台: {platform}")
        
        # 检查缓存
        if use_cache and self._is_cache_valid(platform):
            return self._cache.get(platform, [])[:limit]
        
        # 获取数据
        fetcher = self.fetchers[platform]
        data = await fetcher.fetch_trending(limit)
        
        # 更新缓存
        self._cache[platform] = data
        self._cache_time[platform] = datetime.now()
        
        return data
    
    async def fetch_all_platforms(
        self, 
        limit_per_platform: int = 30,
        use_cache: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        并发获取所有平台数据
        
        Args:
            limit_per_platform: 每个平台的返回数量限制
            use_cache: 是否使用缓存
            
        Returns:
            {platform: [items]}
        """
        tasks = []
        platforms = []
        
        for platform in self.fetchers:
            platforms.append(platform)
            tasks.append(self.fetch_single_platform(platform, limit_per_platform, use_cache))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data = {}
        for platform, result in zip(platforms, results):
            if isinstance(result, Exception):
                print(f"[FetcherManager] {platform} 获取失败: {result}")
                data[platform] = []
            else:
                data[platform] = result
        
        return data
    
    async def fetch_and_merge(
        self, 
        limit_per_platform: int = 30,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取并合并所有平台数据
        
        相同关键词会被合并，记录出现的所有平台
        
        Returns:
            合并后的热词列表，按总热度排序
        """
        all_data = await self.fetch_all_platforms(limit_per_platform, use_cache)
        
        # 按关键词聚合
        keyword_map: Dict[str, Dict[str, Any]] = {}
        
        for platform, items in all_data.items():
            for item in items:
                keyword = item["keyword"]
                
                # 标准化关键词 (去除空格、统一标点)
                normalized_keyword = self._normalize_keyword(keyword)
                
                if normalized_keyword not in keyword_map:
                    keyword_map[normalized_keyword] = {
                        "keyword": keyword,  # 保留原始格式
                        "platforms": [],
                        "raw_heat_scores": {},
                        "total_raw_heat": 0,
                        "first_seen": item["timestamp"],
                        "metadata_by_platform": {},
                    }
                
                entry = keyword_map[normalized_keyword]
                
                # 记录平台
                if platform not in entry["platforms"]:
                    entry["platforms"].append(platform)
                
                # 记录热度
                entry["raw_heat_scores"][platform] = item["raw_heat_score"]
                entry["total_raw_heat"] += item["raw_heat_score"]
                
                # 记录元数据
                entry["metadata_by_platform"][platform] = item.get("metadata", {})
        
        # 转换为列表并排序
        merged = []
        for norm_keyword, data in keyword_map.items():
            merged.append({
                "keyword": data["keyword"],
                "platforms": data["platforms"],
                "platform_count": len(data["platforms"]),
                "raw_heat_score": data["total_raw_heat"],
                "heat_by_platform": data["raw_heat_scores"],
                "first_seen": data["first_seen"],
                "last_seen": datetime.now().isoformat(),
                "metadata": data["metadata_by_platform"],
            })
        
        # 按总热度降序排序
        merged.sort(key=lambda x: x["raw_heat_score"], reverse=True)
        
        return merged
    
    def _normalize_keyword(self, keyword: str) -> str:
        """
        标准化关键词用于匹配
        
        - 去除首尾空格
        - 统一为小写
        - 移除特殊字符
        """
        import re
        
        # 去除空格
        normalized = keyword.strip()
        
        # 移除特殊符号 (保留中文、英文、数字)
        normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', normalized)
        
        # 统一小写
        normalized = normalized.lower()
        
        return normalized
    
    def clear_cache(self, platform: Optional[str] = None):
        """
        清除缓存
        
        Args:
            platform: 指定平台，None 则清除所有
        """
        if platform:
            self._cache.pop(platform, None)
            self._cache_time.pop(platform, None)
        else:
            self._cache.clear()
            self._cache_time.clear()


# 全局单例
_fetcher_manager: Optional[FetcherManager] = None


def get_fetcher_manager() -> FetcherManager:
    """获取全局 FetcherManager 实例"""
    global _fetcher_manager
    
    if _fetcher_manager is None:
        _fetcher_manager = FetcherManager()
        _fetcher_manager.register_default_fetchers()
    
    return _fetcher_manager
