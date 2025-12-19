"""
TrueTrend CN - GitHub 微博热搜存档获取器

从 justjavac/weibo-trending-hot-search 仓库获取历史微博热搜数据
数据范围: 2020-11-24 至今
更新频率: 每小时
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import Counter
import httpx


@dataclass
class HotSearchItem:
    """热搜条目"""
    title: str
    url: str
    date: str  # YYYY-MM-DD


@dataclass
class YearlyTrendItem:
    """年度热词统计"""
    keyword: str
    total_appearances: int      # 总出现次数
    days_on_list: int          # 上榜天数
    peak_date: str             # 峰值日期
    first_seen: str            # 首次出现
    last_seen: str             # 最后出现
    avg_appearances_per_day: float
    burst_score: float = 0.0   # 爆发度分数 (新增)
    peak_intensity: int = 0    # 峰值强度 (单日最高出现次数)


# ============================================================
# 黑名单: 过滤掉游戏、综艺、电视剧、常规栏目等日常热搜
# ============================================================

BLACKLIST_KEYWORDS = {
    # 游戏
    "王者荣耀", "原神", "第五人格", "阴阳师", "和平精英", "英雄联盟", "lol",
    "恋与深空", "恋与制作人", "光与夜之恋", "代号鸢", "明日方舟", "崩坏",
    "永夜星河", "世界之外", "逆水寒", "剑网3", "梦幻西游", "天涯明月刀",
    "蛋仔派对", "金铲铲", "云顶之弈", "绝区零", "鸣潮", "黑神话悟空",
    
    # 电竞赛事
    "KPL", "WTT", "CBA", "LPL", "S赛", "MSI", "世冠", "挑战者杯",
    "英超", "西甲", "德甲", "意甲", "法甲", "欧冠", "中超", "亚锦赛",
    "欧洲杯", "世界杯", "亚运会", "全运会",
    
    # 综艺节目
    "你好星期六", "披荆斩棘", "乘风破浪", "奔跑吧", "极限挑战",
    "大侦探", "花儿与少年", "向往的生活", "快乐大本营", "天天向上",
    "声生不息", "歌手", "我是歌手", "中国好声音", "创造营",
    "青春有你", "偶像练习生", "登陆计划", "种地吧", "半熟男女",
    
    # 电视剧 (热播剧名 2024-2025)
    "春色寄情人", "花间令", "承欢记", "惜花芷", "边水往事", "锦绣中国年",
    "新生", "春花焰", "好东西", "冰雪春天", "长相思", "繁花",
    "庆余年", "玫瑰的故事", "墨雨云间", "度华年", "小日子", "狐妖小红娘",
    "唐朝诡事录", "莲花楼", "与凤行", "柳舟记", "九尾狐传", "默杀",
    "人民军队淬火向前", "文化中国团圆年", "小龙糕",
    # 2025年热播剧
    "白月梵星", "仙台有树", "白色橄榄树", "六姊妹", "值得爱", "雁回时",
    "天地剑心", "敖光", "敖丙", "藕饼", "扫毒风暴", "盛世天下",
    "以法之名", "一笑随歌", "临江仙", "入青云", "得闲谨制", "凡人歌",
    "浪浪山小妖怪", "要久久爱", "爱你", "蛇小姐", "小蛇糕",
    # 更多2025剧集
    "难哄", "赴山海", "棋士", "仙逆", "无限暖暖", "大奉打更人",
    "射雕", "石矶娘娘", "红房子", "桃花映江山", "四喜", "B萌",
    
    # 电影/动画
    "疯狂动物城", "票房", "周处除三害", "哪吒", "热辣滚烫",
    
    # 星座/日常
    "白桃星座", "星座", "天气", "天气预报", "早安",
    
    # 股市 (每天都有)
    "A股", "股市", "大盘", "涨停", "跌停", "金价",
    
    # 固定栏目
    "学习新语", "改革", "新时代", "私藏浪漫", "九重紫",
    "感悟总书记", "读懂全会", "习近平", "总书记",
    
    # 手机/科技产品
    "小米15", "小米14", "华为", "iPhone", "Mate",
}

# 正则黑名单: 匹配特定模式
BLACKLIST_PATTERNS = [
    r"^.*vs.*$",                    # 对战类标题
    r"^跟着.*探寻.*$",              # 固定栏目
    r"^.*恋综.*$",                  # 恋爱综艺
    r"^.*收视率.*$",                # 收视率相关
    r"^.*预告.*$",                  # 预告片
    r"^.*首播.*$",                  # 首播相关
    r"^.*大结局.*$",                # 大结局
    r"^.*定档.*$",                  # 定档相关
    r"^.*官宣.*$",                  # 官宣相关  
    r"^电影.*$",                    # 电影开头
    r"^.*之行$",                    # XX之行
    r"^.*中国年.*$",                # 节日栏目
]


def is_blacklisted(keyword: str) -> bool:
    """检查关键词是否在黑名单中"""
    import re
    
    # 精确匹配
    keyword_lower = keyword.lower()
    for bl in BLACKLIST_KEYWORDS:
        if bl.lower() in keyword_lower:
            return True
    
    # 正则匹配
    for pattern in BLACKLIST_PATTERNS:
        if re.match(pattern, keyword, re.IGNORECASE):
            return True
    
    return False


def calculate_burst_score(
    total_appearances: int,
    days_on_list: int,
    peak_intensity: int,
    lifespan_days: int
) -> float:
    """
    计算爆发度分数 - 用于识别年度热点事件
    
    核心逻辑:
    - 真正的热点事件会连续多天高频出现
    - 单次上榜的话题可能只是普通新闻
    - 长期断续出现的话题可能是游戏/综艺等
    
    公式:
    爆发度 = (总出现次数 × 上榜天数权重) / 生命周期惩罚
    
    - 上榜天数权重: 3-10天的事件得分最高
    - 生命周期惩罚: 跨度过长(>30天)说明是断续话题
    """
    import math
    
    if days_on_list == 0:
        return 0.0
    
    # 基础分 = 总出现次数
    base_score = total_appearances
    
    # 上榜天数权重: 3-10天的事件最可能是热点事件
    # 1天: 0.3, 2天: 0.6, 3-10天: 1.0, >10天: 递减
    if days_on_list == 1:
        days_weight = 0.3
    elif days_on_list == 2:
        days_weight = 0.6
    elif days_on_list <= 10:
        days_weight = 1.0
    else:
        days_weight = 1.0 / math.log(days_on_list, 5)  # 超过10天逐渐降低
    
    # 集中度权重: 出现密集程度
    concentration = total_appearances / days_on_list
    
    # 生命周期惩罚: 跨度超过30天的话题降权
    if lifespan_days <= 14:
        lifespan_penalty = 1.0
    elif lifespan_days <= 30:
        lifespan_penalty = 0.8
    elif lifespan_days <= 60:
        lifespan_penalty = 0.5
    else:
        lifespan_penalty = 0.3
    
    # 最终得分
    burst_score = base_score * days_weight * concentration * lifespan_penalty
    
    return round(burst_score, 2)


class GitHubArchiveFetcher:
    """
    GitHub 微博热搜存档获取器
    
    数据源: https://github.com/justjavac/weibo-trending-hot-search
    文件路径: /raw/YYYY-MM-DD.json
    """
    
    BASE_URL = "https://raw.githubusercontent.com/justjavac/weibo-trending-hot-search/master/raw"
    
    # 数据可用的最早日期
    MIN_DATE = datetime(2020, 11, 24)
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, List[Dict]] = {}  # 简单内存缓存
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """关闭连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def fetch_day_data(self, date: str) -> List[HotSearchItem]:
        """
        获取单日热搜数据
        
        Args:
            date: 日期字符串 YYYY-MM-DD
            
        Returns:
            热搜条目列表
        """
        # 检查缓存
        if date in self._cache:
            return [HotSearchItem(title=item["title"], url=item["url"], date=date) 
                    for item in self._cache[date]]
        
        client = await self._get_client()
        url = f"{self.BASE_URL}/{date}.json"
        
        try:
            response = await client.get(url)
            
            if response.status_code == 404:
                print(f"[GitHubArchive] {date} 数据不存在")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # 缓存数据
            self._cache[date] = data
            
            return [HotSearchItem(title=item["title"], url=item["url"], date=date) 
                    for item in data]
            
        except Exception as e:
            print(f"[GitHubArchive] 获取 {date} 数据失败: {e}")
            return []
    
    async def fetch_date_range(
        self, 
        start_date: str, 
        end_date: str,
        progress_callback: Optional[callable] = None
    ) -> List[HotSearchItem]:
        """
        获取日期范围内的热搜数据
        
        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            progress_callback: 进度回调函数
            
        Returns:
            热搜条目列表
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_items = []
        current = start
        total_days = (end - start).days + 1
        processed = 0
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            items = await self.fetch_day_data(date_str)
            all_items.extend(items)
            
            processed += 1
            if progress_callback:
                progress_callback(processed, total_days, date_str)
            
            current += timedelta(days=1)
            
            # 避免请求过快
            await asyncio.sleep(0.1)
        
        return all_items
    
    async def fetch_month_data(self, year: int, month: int) -> List[HotSearchItem]:
        """
        获取整月热搜数据
        """
        start_date = f"{year}-{month:02d}-01"
        
        # 计算月末日期
        if month == 12:
            end_date = f"{year}-12-31"
        else:
            next_month = datetime(year, month + 1, 1)
            last_day = next_month - timedelta(days=1)
            end_date = last_day.strftime("%Y-%m-%d")
        
        print(f"[GitHubArchive] 获取 {year}年{month}月 数据...")
        return await self.fetch_date_range(start_date, end_date)
    
    async def fetch_year_data(self, year: int) -> List[HotSearchItem]:
        """
        获取全年热搜数据
        """
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        # 确保不超过当前日期
        today = datetime.now()
        if datetime.strptime(end_date, "%Y-%m-%d") > today:
            end_date = today.strftime("%Y-%m-%d")
        
        # 确保不早于最早可用日期
        if datetime.strptime(start_date, "%Y-%m-%d") < self.MIN_DATE:
            start_date = self.MIN_DATE.strftime("%Y-%m-%d")
        
        print(f"[GitHubArchive] 获取 {year}年 数据 ({start_date} ~ {end_date})...")
        
        def progress(current, total, date):
            if current % 30 == 0 or current == total:
                print(f"  进度: {current}/{total} ({date})")
        
        return await self.fetch_date_range(start_date, end_date, progress)
    
    def aggregate_yearly_stats(
        self, 
        items: List[HotSearchItem],
        filter_blacklist: bool = True,
        sort_by: str = "burst"  # "burst" | "total" | "days"
    ) -> List[YearlyTrendItem]:
        """
        统计年度热词排行
        
        Args:
            items: 热搜条目列表
            filter_blacklist: 是否过滤黑名单 (游戏/综艺/赛事等)
            sort_by: 排序方式 - burst(爆发度), total(出现次数), days(上榜天数)
            
        Returns:
            年度热词统计列表
        """
        from datetime import datetime
        
        # 统计每个关键词的出现信息
        keyword_stats: Dict[str, Dict] = {}
        
        for item in items:
            keyword = item.title
            date = item.date
            
            # 过滤黑名单
            if filter_blacklist and is_blacklisted(keyword):
                continue
            
            if keyword not in keyword_stats:
                keyword_stats[keyword] = {
                    "total_appearances": 0,
                    "dates": set(),
                    "first_seen": date,
                    "last_seen": date,
                    "date_counts": Counter(),
                }
            
            stats = keyword_stats[keyword]
            stats["total_appearances"] += 1
            stats["dates"].add(date)
            stats["date_counts"][date] += 1
            
            if date < stats["first_seen"]:
                stats["first_seen"] = date
            if date > stats["last_seen"]:
                stats["last_seen"] = date
        
        # 生成统计结果
        results = []
        for keyword, stats in keyword_stats.items():
            peak_date, peak_intensity = stats["date_counts"].most_common(1)[0]
            days_on_list = len(stats["dates"])
            
            # 计算生命周期天数
            first_dt = datetime.strptime(stats["first_seen"], "%Y-%m-%d")
            last_dt = datetime.strptime(stats["last_seen"], "%Y-%m-%d")
            lifespan_days = (last_dt - first_dt).days + 1
            
            # 计算爆发度
            burst_score = calculate_burst_score(
                total_appearances=stats["total_appearances"],
                days_on_list=days_on_list,
                peak_intensity=peak_intensity,
                lifespan_days=lifespan_days
            )
            
            results.append(YearlyTrendItem(
                keyword=keyword,
                total_appearances=stats["total_appearances"],
                days_on_list=days_on_list,
                peak_date=peak_date,
                first_seen=stats["first_seen"],
                last_seen=stats["last_seen"],
                avg_appearances_per_day=round(stats["total_appearances"] / max(days_on_list, 1), 2),
                burst_score=burst_score,
                peak_intensity=peak_intensity,
            ))
        
        # 根据排序方式排序
        if sort_by == "burst":
            results.sort(key=lambda x: x.burst_score, reverse=True)
        elif sort_by == "days":
            results.sort(key=lambda x: x.days_on_list, reverse=True)
        else:  # total
            results.sort(key=lambda x: x.total_appearances, reverse=True)
        
        return results


# ============================================================
# 便捷函数
# ============================================================

async def get_yearly_hot_words(year: int, limit: int = 100) -> Dict[str, Any]:
    """
    获取年度热词榜
    
    Args:
        year: 年份
        limit: 返回数量限制
        
    Returns:
        年度热词数据
    """
    fetcher = GitHubArchiveFetcher()
    
    try:
        # 获取全年数据
        items = await fetcher.fetch_year_data(year)
        
        if not items:
            return {
                "year": year,
                "trends": [],
                "total_count": 0,
                "error": "无法获取数据",
            }
        
        # 统计排行 (默认按爆发度排序，过滤游戏综艺等)
        stats = fetcher.aggregate_yearly_stats(items, filter_blacklist=True, sort_by="burst")
        
        # 转换为字典格式
        trends = [
            {
                "keyword": s.keyword,
                "burst_score": s.burst_score,
                "peak_intensity": s.peak_intensity,
                "total_appearances": s.total_appearances,
                "days_on_list": s.days_on_list,
                "peak_date": s.peak_date,
                "first_seen": s.first_seen,
                "last_seen": s.last_seen,
                "avg_appearances_per_day": s.avg_appearances_per_day,
            }
            for s in stats[:limit]
        ]
        
        return {
            "year": year,
            "trends": trends,
            "total_count": len(stats),
            "total_items": len(items),
            "generated_at": datetime.now().isoformat(),
        }
        
    finally:
        await fetcher.close()


async def get_monthly_hot_words(year: int, month: int, limit: int = 50) -> Dict[str, Any]:
    """
    获取月度热词榜
    """
    fetcher = GitHubArchiveFetcher()
    
    try:
        items = await fetcher.fetch_month_data(year, month)
        
        if not items:
            return {
                "year": year,
                "month": month,
                "trends": [],
                "total_count": 0,
            }
        
        stats = fetcher.aggregate_yearly_stats(items)
        
        trends = [
            {
                "keyword": s.keyword,
                "total_appearances": s.total_appearances,
                "days_on_list": s.days_on_list,
                "peak_date": s.peak_date,
            }
            for s in stats[:limit]
        ]
        
        return {
            "year": year,
            "month": month,
            "trends": trends,
            "total_count": len(stats),
            "generated_at": datetime.now().isoformat(),
        }
        
    finally:
        await fetcher.close()


async def get_daily_archive(date: str) -> Dict[str, Any]:
    """
    获取单日热搜存档
    
    Args:
        date: 日期 YYYY-MM-DD
    """
    fetcher = GitHubArchiveFetcher()
    
    try:
        items = await fetcher.fetch_day_data(date)
        
        return {
            "date": date,
            "items": [{"title": item.title, "url": item.url} for item in items],
            "total_count": len(items),
        }
        
    finally:
        await fetcher.close()


# ============================================================
# CLI 测试
# ============================================================

if __name__ == "__main__":
    import sys
    
    async def main():
        if len(sys.argv) < 2:
            print("用法:")
            print("  python github_archive.py day 2024-01-01")
            print("  python github_archive.py month 2024 1")
            print("  python github_archive.py year 2024")
            return
        
        cmd = sys.argv[1]
        
        if cmd == "day" and len(sys.argv) >= 3:
            date = sys.argv[2]
            result = await get_daily_archive(date)
            print(f"\n📅 {date} 热搜 ({result['total_count']} 条):")
            for i, item in enumerate(result["items"][:20], 1):
                print(f"  {i:2}. {item['title']}")
        
        elif cmd == "month" and len(sys.argv) >= 4:
            year = int(sys.argv[2])
            month = int(sys.argv[3])
            result = await get_monthly_hot_words(year, month)
            print(f"\n📊 {year}年{month}月 热词榜 (Top 20):")
            for i, trend in enumerate(result["trends"][:20], 1):
                print(f"  {i:2}. {trend['keyword']} ({trend['total_appearances']} 次, {trend['days_on_list']} 天)")
        
        elif cmd == "year" and len(sys.argv) >= 3:
            year = int(sys.argv[2])
            result = await get_yearly_hot_words(year, limit=30)
            print(f"\n🏆 {year}年度热词榜 (Top 30):")
            for i, trend in enumerate(result["trends"][:30], 1):
                print(f"  {i:2}. {trend['keyword']}")
                print(f"      出现 {trend['total_appearances']} 次 | 上榜 {trend['days_on_list']} 天 | 峰值 {trend['peak_date']}")
        
        else:
            print("无效命令")
    
    asyncio.run(main())
