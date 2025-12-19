"""
TrueTrend CN - 抽象数据获取器基类
未来可扩展为微博、知乎、B站的具体实现
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime


class DataFetcher(ABC):
    """
    抽象数据获取器基类
    定义统一的数据获取接口，便于未来接入真实 API
    """
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.last_fetch_time: datetime | None = None
    
    @abstractmethod
    async def fetch_trending(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取热门话题/热搜
        
        Args:
            limit: 获取数量限制
            
        Returns:
            List of trending items with:
                - keyword: str
                - raw_heat_score: float
                - timestamp: datetime
                - metadata: dict (平台特定的额外信息)
        """
        pass
    
    @abstractmethod
    async def fetch_keyword_history(
        self, 
        keyword: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        获取某个关键词的历史热度数据
        
        Args:
            keyword: 查询的关键词
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List of historical data points with:
                - timestamp: datetime
                - heat_score: float
        """
        pass
    
    @abstractmethod
    def get_platform_weight(self) -> float:
        """
        获取该平台的权重系数
        不同平台的用户基数和影响力不同
        
        Returns:
            平台权重 (0.0 - 1.0)
        """
        pass
    
    def update_fetch_time(self):
        """更新最后获取时间"""
        self.last_fetch_time = datetime.now()


# ============================================================
# 未来的具体实现示例 (目前为占位符)
# ============================================================

class WeiboFetcher(DataFetcher):
    """微博数据获取器 - 待实现"""
    
    def __init__(self):
        super().__init__("weibo")
    
    async def fetch_trending(self, limit: int = 50) -> List[Dict[str, Any]]:
        # TODO: 接入微博 API
        raise NotImplementedError("微博 API 尚未接入")
    
    async def fetch_keyword_history(
        self, keyword: str, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("微博 API 尚未接入")
    
    def get_platform_weight(self) -> float:
        return 0.9  # 微博影响力较高


class ZhihuFetcher(DataFetcher):
    """知乎数据获取器 - 待实现"""
    
    def __init__(self):
        super().__init__("zhihu")
    
    async def fetch_trending(self, limit: int = 50) -> List[Dict[str, Any]]:
        raise NotImplementedError("知乎 API 尚未接入")
    
    async def fetch_keyword_history(
        self, keyword: str, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("知乎 API 尚未接入")
    
    def get_platform_weight(self) -> float:
        return 0.85  # 知乎偏深度讨论


class BilibiliFetcher(DataFetcher):
    """B站数据获取器 - 待实现"""
    
    def __init__(self):
        super().__init__("bilibili")
    
    async def fetch_trending(self, limit: int = 50) -> List[Dict[str, Any]]:
        raise NotImplementedError("B站 API 尚未接入")
    
    async def fetch_keyword_history(
        self, keyword: str, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("B站 API 尚未接入")
    
    def get_platform_weight(self) -> float:
        return 0.8  # B站年轻用户为主
