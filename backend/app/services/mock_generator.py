"""
TrueTrend CN - 模拟数据生成器
生成带有真实感的年度热词数据，用于前端开发和演示
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from ..models.schemas import Platform, Sentiment, TrendDataPoint


# ============================================================
# 模拟热词数据库 - 2024 年中国互联网记忆
# ============================================================

MOCK_KEYWORDS = {
    # 社会事件类 - 跨平台传播
    "城中村改造": {"sentiment": Sentiment.NEUTRAL, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BAIDU], "base_heat": 8500},
    "延迟退休": {"sentiment": Sentiment.ANGRY, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI, Platform.BAIDU], "base_heat": 9200},
    "35岁危机": {"sentiment": Sentiment.SAD, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI], "base_heat": 7800},
    "烂尾楼": {"sentiment": Sentiment.ANGRY, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.DOUYIN, Platform.BAIDU], "base_heat": 8900},
    "考公上岸": {"sentiment": Sentiment.NEUTRAL, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI], "base_heat": 7200},
    "县城婆罗门": {"sentiment": Sentiment.ANGRY, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 6800},
    
    # 网络文化类
    "city不city": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 9500},
    "遥遥领先": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.ZHIHU, Platform.DOUYIN, Platform.BAIDU], "base_heat": 8800},
    "显眼包": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 7500},
    "i人e人": {"sentiment": Sentiment.NEUTRAL, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 8200},
    "发疯文学": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 7000},
    "多巴胺穿搭": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 6500},
    "特种兵旅游": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.DOUYIN, Platform.ZHIHU], "base_heat": 8100},
    "电子榨菜": {"sentiment": Sentiment.NEUTRAL, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.ZHIHU], "base_heat": 5800},
    "脆皮大学生": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 6200},
    "搭子文化": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.DOUYIN], "base_heat": 5500},
    
    # 科技类
    "ChatGPT": {"sentiment": Sentiment.NEUTRAL, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI, Platform.BAIDU], "base_heat": 9800},
    "Sora": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI], "base_heat": 7800},
    "国产大模型": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI, Platform.BAIDU], "base_heat": 7200},
    "鸿蒙系统": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI, Platform.BAIDU], "base_heat": 6800},
    
    # 娱乐类 (部分可能是营销，用于测试过滤)
    "繁花": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 8500},
    "庆余年2": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 8200},
    "黑神话悟空": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI, Platform.DOUYIN, Platform.BAIDU], "base_heat": 9900},
    
    # 疑似营销类 (用于测试过滤算法)
    "XX新品发布会": {"sentiment": Sentiment.NEUTRAL, "platforms": [Platform.WEIBO], "base_heat": 9000, "is_marketing": True},
    "XX代言人官宣": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO], "base_heat": 8500, "is_marketing": True},
    "双十一预售": {"sentiment": Sentiment.NEUTRAL, "platforms": [Platform.WEIBO, Platform.DOUYIN], "base_heat": 9500, "is_marketing": True},
    "618大促": {"sentiment": Sentiment.NEUTRAL, "platforms": [Platform.WEIBO, Platform.DOUYIN], "base_heat": 9200, "is_marketing": True},
    "XX生日快乐": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO], "base_heat": 8800, "is_marketing": True},
    
    # 更多真实热词
    "挖呀挖": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.DOUYIN, Platform.BILIBILI], "base_heat": 7800},
    "淄博烧烤": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI, Platform.DOUYIN, Platform.BAIDU], "base_heat": 9600},
    "哈尔滨冰雪": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI, Platform.DOUYIN, Platform.BAIDU], "base_heat": 9400},
    "南方小土豆": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 8600},
    "尔滨": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 8400},
    "科目三舞蹈": {"sentiment": Sentiment.HAPPY, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 8000},
    "命运的齿轮": {"sentiment": Sentiment.NEUTRAL, "platforms": [Platform.WEIBO, Platform.BILIBILI, Platform.DOUYIN], "base_heat": 5500},
    "孔乙己文学": {"sentiment": Sentiment.SAD, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI], "base_heat": 7600},
    "全职儿女": {"sentiment": Sentiment.SAD, "platforms": [Platform.WEIBO, Platform.ZHIHU], "base_heat": 6800},
    "断亲": {"sentiment": Sentiment.SAD, "platforms": [Platform.WEIBO, Platform.ZHIHU], "base_heat": 5900},
    "精神离职": {"sentiment": Sentiment.NEUTRAL, "platforms": [Platform.WEIBO, Platform.ZHIHU, Platform.BILIBILI], "base_heat": 6100},
    "45度人生": {"sentiment": Sentiment.SAD, "platforms": [Platform.WEIBO, Platform.ZHIHU], "base_heat": 5700},
}


class MockDataGenerator:
    """
    模拟数据生成器
    生成带有时间戳、平台来源和热度的 JSON 数据
    """
    
    def __init__(self, year: int = 2024):
        self.year = year
        self.start_date = datetime(year, 1, 1)
        self.end_date = datetime(year, 12, 31)
    
    def _generate_lifecycle(
        self, 
        keyword: str, 
        platforms: List[Platform],
        base_heat: float
    ) -> List[Dict[str, Any]]:
        """
        生成一个词的生命周期数据
        模拟从诞生到消亡的热度变化
        """
        # 随机生成诞生日期 (在年度内)
        birth_offset = random.randint(0, 300)
        birth_date = self.start_date + timedelta(days=birth_offset)
        
        # 生命周期长度 (3-60 天)
        lifecycle_days = random.randint(3, 60)
        
        # 峰值出现在生命周期的前 1/3 到 1/2
        peak_day = random.randint(lifecycle_days // 3, lifecycle_days // 2)
        
        data_points = []
        
        for day in range(lifecycle_days):
            current_date = birth_date + timedelta(days=day)
            if current_date > self.end_date:
                break
                
            # 计算热度曲线 (使用简单的抛物线模型)
            if day <= peak_day:
                # 上升期: 指数增长
                progress = day / peak_day
                heat = base_heat * (progress ** 1.5)
            else:
                # 下降期: 指数衰减
                decay_progress = (day - peak_day) / (lifecycle_days - peak_day)
                heat = base_heat * (1 - decay_progress ** 0.8)
            
            # 添加随机波动
            heat *= random.uniform(0.85, 1.15)
            heat = max(100, heat)  # 最低热度
            
            # 为每个平台生成数据点
            for platform in platforms:
                # 不同平台的热度有差异
                platform_factor = random.uniform(0.7, 1.3)
                data_points.append({
                    "keyword": keyword,
                    "timestamp": current_date.isoformat(),
                    "platform": platform.value,
                    "heat_score": round(heat * platform_factor, 2)
                })
        
        return data_points
    
    def generate_all_trends(self) -> List[Dict[str, Any]]:
        """
        生成所有热词的完整数据
        返回包含所有热词详细信息的列表
        """
        all_data = []
        
        for keyword, info in MOCK_KEYWORDS.items():
            platforms = info["platforms"]
            base_heat = info["base_heat"]
            sentiment = info["sentiment"]
            is_marketing = info.get("is_marketing", False)
            
            # 生成生命周期数据
            lifecycle_data = self._generate_lifecycle(keyword, platforms, base_heat)
            
            if not lifecycle_data:
                continue
            
            # 聚合统计
            timestamps = [dp["timestamp"] for dp in lifecycle_data]
            heat_scores = [dp["heat_score"] for dp in lifecycle_data]
            
            first_seen = min(timestamps)
            last_seen = max(timestamps)
            peak_idx = heat_scores.index(max(heat_scores))
            peak_time = timestamps[peak_idx]
            
            all_data.append({
                "keyword": keyword,
                "platforms": [p.value for p in platforms],
                "platform_count": len(platforms),
                "raw_heat_score": sum(heat_scores),
                "sentiment": sentiment.value,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "peak_time": peak_time,
                "is_marketing": is_marketing,
                "lifecycle_data": lifecycle_data
            })
        
        return all_data
    
    def generate_timeline_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        生成时间轴数据
        按月份分组
        """
        all_trends = self.generate_all_trends()
        timeline = {}
        
        for trend in all_trends:
            # 使用峰值时间来分配月份
            peak_time = datetime.fromisoformat(trend["peak_time"])
            month_key = peak_time.strftime("%Y-%m")
            
            if month_key not in timeline:
                timeline[month_key] = []
            
            timeline[month_key].append(trend)
        
        # 每月按热度排序
        for month in timeline:
            timeline[month].sort(key=lambda x: x["raw_heat_score"], reverse=True)
        
        return timeline
