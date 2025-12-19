"""
TrueTrend CN - Pydantic 数据模型
定义 API 请求/响应的数据结构
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Sentiment(str, Enum):
    """情绪类型枚举"""
    ANGRY = "angry"       # 愤怒 - 红色
    HAPPY = "happy"       # 开心 - 绿色
    SAD = "sad"           # 忧郁 - 蓝色
    NEUTRAL = "neutral"   # 中性 - 灰色


class Platform(str, Enum):
    """数据来源平台"""
    WEIBO = "weibo"       # 微博
    ZHIHU = "zhihu"       # 知乎
    BILIBILI = "bilibili" # B站
    DOUYIN = "douyin"     # 抖音
    BAIDU = "baidu"       # 百度


class TrendDataPoint(BaseModel):
    """单个时间点的热度数据"""
    timestamp: datetime
    heat_score: float
    platform: Platform


class TrendItem(BaseModel):
    """一个热词的完整信息"""
    keyword: str = Field(..., description="热词关键字")
    platforms: List[Platform] = Field(..., description="出现的平台列表")
    raw_heat_score: float = Field(..., description="原始热度分数")
    real_score: float = Field(..., description="经过客观性算法加权后的分数")
    sentiment: Sentiment = Field(..., description="主要情绪倾向")
    first_seen: datetime = Field(..., description="首次出现时间")
    peak_time: datetime = Field(..., description="热度峰值时间")
    last_seen: datetime = Field(..., description="最后出现时间")
    is_marketing: bool = Field(default=False, description="是否疑似营销内容")
    platform_count: int = Field(..., description="出现平台数量")


class LifecyclePoint(BaseModel):
    """生命周期曲线上的一个点"""
    timestamp: datetime
    heat_score: float
    phase: str = Field(..., description="阶段: birth/rise/peak/decline/death")


class LifecycleData(BaseModel):
    """一个热词的生命周期数据"""
    keyword: str
    data_points: List[LifecyclePoint]
    birth_date: datetime
    peak_date: datetime
    death_date: Optional[datetime] = None
    total_days: int


class TrendResponse(BaseModel):
    """热词列表 API 响应"""
    trends: List[TrendItem]
    total_count: int
    generated_at: datetime


class TimelineMonth(BaseModel):
    """时间轴上一个月的数据"""
    month: str  # "2024-01"
    top_trends: List[TrendItem]


class TimelineResponse(BaseModel):
    """时间轴 API 响应"""
    timeline: List[TimelineMonth]
    year: int
