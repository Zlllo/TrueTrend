"""
TrueTrend CN - RealScore 客观性加权算法
去伪存真：过滤营销内容，奖励跨平台传播
"""

import re
import math
from typing import List, Dict, Any
from datetime import datetime


# ============================================================
# 营销内容黑名单正则表达式
# ============================================================

MARKETING_PATTERNS = [
    # 商业活动
    r".*发布会$",
    r".*新品.*",
    r".*代言.*",
    r".*官宣.*",
    r".*预售.*",
    r".*大促.*",
    r".*折扣.*",
    r".*满减.*",
    
    # 电商节日
    r"^618.*",
    r".*618$",
    r"^双十一.*",
    r".*双十一$",
    r"^双11.*",
    r".*双11$",
    r"^双十二.*",
    r".*双十二$",
    
    # 粉丝应援
    r".*生日快乐$",
    r".*应援.*",
    r".*打榜.*",
    r".*超话.*",
    r".*出道.*周年",
    
    # 品牌关键词
    r"^#.*品牌.*#$",
]


class RealScoreCalculator:
    """
    RealScore 客观性加权算法
    
    公式: RealScore = BaseHeat × PlatformMultiplier × LongevityFactor × (1 - MarketingPenalty)
    
    核心思想：
    1. 跨平台验证 - 多平台同时出现的话题更真实
    2. 生命力因子 - 持续时间越长越真实
    3. 营销惩罚 - 疑似营销内容降权
    """
    
    def __init__(self):
        self.marketing_patterns = [re.compile(p, re.IGNORECASE) for p in MARKETING_PATTERNS]
    
    def calculate_platform_multiplier(self, platform_count: int) -> float:
        """
        计算平台多样性乘数
        
        规则:
        - 1 平台: 0.3 (严重降权，可能是刷的)
        - 2 平台: 1.0 (正常)
        - 3+ 平台: 1.5^(n-2) (指数级增强)
        """
        if platform_count <= 0:
            return 0.0
        elif platform_count == 1:
            return 0.3
        elif platform_count == 2:
            return 1.0
        else:
            # 指数增长，但设置上限防止过大
            multiplier = 1.5 ** (platform_count - 2)
            return min(multiplier, 5.0)  # 最大 5 倍
    
    def calculate_longevity_factor(self, first_seen: str, last_seen: str) -> float:
        """
        计算生命力因子
        
        规则: log2(活跃天数 + 1)
        - 1 天: log2(2) = 1.0
        - 7 天: log2(8) ≈ 3.0
        - 30 天: log2(31) ≈ 4.95
        """
        try:
            first = datetime.fromisoformat(first_seen)
            last = datetime.fromisoformat(last_seen)
            days = (last - first).days + 1
            return math.log2(days + 1)
        except (ValueError, TypeError):
            return 1.0
    
    def calculate_marketing_penalty(self, keyword: str, is_marketing_flag: bool = False) -> float:
        """
        计算营销惩罚因子
        
        返回 0-1 之间的值:
        - 0: 非营销内容，无惩罚
        - 0.5: 疑似营销，减半权重
        - 0.8: 明确营销标记，严重降权
        """
        # 如果已标记为营销
        if is_marketing_flag:
            return 0.8
        
        # 正则匹配检测
        for pattern in self.marketing_patterns:
            if pattern.match(keyword):
                return 0.5
        
        return 0.0
    
    def calculate_real_score(self, trend_data: Dict[str, Any]) -> float:
        """
        计算最终的 RealScore
        
        Args:
            trend_data: 包含以下字段的字典
                - keyword: str
                - raw_heat_score: float
                - platform_count: int
                - first_seen: str (ISO format)
                - last_seen: str (ISO format)
                - is_marketing: bool (optional)
        
        Returns:
            float: 加权后的 RealScore
        """
        keyword = trend_data.get("keyword", "")
        base_heat = trend_data.get("raw_heat_score", 0)
        platform_count = trend_data.get("platform_count", 1)
        first_seen = trend_data.get("first_seen", "")
        last_seen = trend_data.get("last_seen", "")
        is_marketing = trend_data.get("is_marketing", False)
        
        # 计算各因子
        platform_multiplier = self.calculate_platform_multiplier(platform_count)
        longevity_factor = self.calculate_longevity_factor(first_seen, last_seen)
        marketing_penalty = self.calculate_marketing_penalty(keyword, is_marketing)
        
        # 最终公式
        real_score = base_heat * platform_multiplier * longevity_factor * (1 - marketing_penalty)
        
        return round(real_score, 2)
    
    def process_all_trends(self, trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量处理所有热词，添加 RealScore 并排序
        
        Args:
            trends: 热词数据列表
            
        Returns:
            按 RealScore 降序排列的热词列表
        """
        processed = []
        
        for trend in trends:
            real_score = self.calculate_real_score(trend)
            trend_copy = trend.copy()
            trend_copy["real_score"] = real_score
            
            # 添加算法解释信息 (便于调试和展示)
            trend_copy["score_breakdown"] = {
                "base_heat": trend.get("raw_heat_score", 0),
                "platform_multiplier": self.calculate_platform_multiplier(
                    trend.get("platform_count", 1)
                ),
                "longevity_factor": self.calculate_longevity_factor(
                    trend.get("first_seen", ""),
                    trend.get("last_seen", "")
                ),
                "marketing_penalty": self.calculate_marketing_penalty(
                    trend.get("keyword", ""),
                    trend.get("is_marketing", False)
                )
            }
            
            processed.append(trend_copy)
        
        # 按 RealScore 降序排序
        processed.sort(key=lambda x: x["real_score"], reverse=True)
        
        return processed


# 全局实例
real_score_calculator = RealScoreCalculator()
