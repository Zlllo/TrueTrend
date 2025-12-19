"""
TrueTrend CN - 热词 API 路由
提供热词排行、生命周期数据等接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from ..services.mock_generator import MockDataGenerator
from ..services.real_score import real_score_calculator
from ..models.schemas import (
    TrendResponse, 
    TrendItem, 
    LifecycleData, 
    LifecyclePoint,
    TimelineResponse,
    TimelineMonth,
    Platform,
    Sentiment
)

router = APIRouter(prefix="/api/trends", tags=["trends"])

# 初始化模拟数据生成器
mock_generator = MockDataGenerator(year=2024)


def _convert_to_trend_item(trend_data: dict) -> TrendItem:
    """将原始数据转换为 TrendItem 模型"""
    return TrendItem(
        keyword=trend_data["keyword"],
        platforms=[Platform(p) for p in trend_data["platforms"]],
        raw_heat_score=trend_data["raw_heat_score"],
        real_score=trend_data.get("real_score", 0),
        sentiment=Sentiment(trend_data["sentiment"]),
        first_seen=datetime.fromisoformat(trend_data["first_seen"]),
        peak_time=datetime.fromisoformat(trend_data["peak_time"]),
        last_seen=datetime.fromisoformat(trend_data["last_seen"]),
        is_marketing=trend_data.get("is_marketing", False),
        platform_count=trend_data["platform_count"]
    )


@router.get("", response_model=TrendResponse)
async def get_trends(
    limit: int = Query(default=50, ge=1, le=100, description="返回数量限制"),
    include_marketing: bool = Query(default=False, description="是否包含营销内容"),
    min_platforms: int = Query(default=1, ge=1, le=5, description="最少出现平台数")
):
    """
    获取年度热词排行榜
    
    返回经过 RealScore 算法加权后的热词列表，默认过滤营销内容
    """
    # 生成模拟数据
    raw_trends = mock_generator.generate_all_trends()
    
    # 应用 RealScore 算法
    processed_trends = real_score_calculator.process_all_trends(raw_trends)
    
    # 过滤
    filtered = processed_trends
    
    if not include_marketing:
        filtered = [t for t in filtered if not t.get("is_marketing", False)]
    
    if min_platforms > 1:
        filtered = [t for t in filtered if t["platform_count"] >= min_platforms]
    
    # 限制返回数量
    filtered = filtered[:limit]
    
    # 转换为响应模型
    trend_items = [_convert_to_trend_item(t) for t in filtered]
    
    return TrendResponse(
        trends=trend_items,
        total_count=len(trend_items),
        generated_at=datetime.now()
    )


@router.get("/{keyword}/lifecycle", response_model=LifecycleData)
async def get_keyword_lifecycle(keyword: str):
    """
    获取某个热词的生命周期数据
    
    返回从诞生到消亡的完整热度曲线
    """
    # 生成模拟数据
    raw_trends = mock_generator.generate_all_trends()
    
    # 查找指定关键词
    target_trend = None
    for trend in raw_trends:
        if trend["keyword"] == keyword:
            target_trend = trend
            break
    
    if not target_trend:
        raise HTTPException(status_code=404, detail=f"热词 '{keyword}' 未找到")
    
    lifecycle_raw = target_trend.get("lifecycle_data", [])
    
    if not lifecycle_raw:
        raise HTTPException(status_code=404, detail=f"热词 '{keyword}' 没有生命周期数据")
    
    # 聚合每日数据 (跨平台)
    daily_heat = {}
    for point in lifecycle_raw:
        date = point["timestamp"][:10]  # 只取日期部分
        if date not in daily_heat:
            daily_heat[date] = 0
        daily_heat[date] += point["heat_score"]
    
    # 转换为生命周期点
    sorted_dates = sorted(daily_heat.keys())
    max_heat = max(daily_heat.values())
    max_date = [d for d, h in daily_heat.items() if h == max_heat][0]
    
    data_points = []
    for i, date in enumerate(sorted_dates):
        heat = daily_heat[date]
        
        # 判断阶段
        if i < len(sorted_dates) * 0.2:
            phase = "birth"
        elif date < max_date:
            phase = "rise"
        elif date == max_date:
            phase = "peak"
        elif i > len(sorted_dates) * 0.8:
            phase = "death"
        else:
            phase = "decline"
        
        data_points.append(LifecyclePoint(
            timestamp=datetime.fromisoformat(date),
            heat_score=heat,
            phase=phase
        ))
    
    return LifecycleData(
        keyword=keyword,
        data_points=data_points,
        birth_date=datetime.fromisoformat(sorted_dates[0]),
        peak_date=datetime.fromisoformat(max_date),
        death_date=datetime.fromisoformat(sorted_dates[-1]) if len(sorted_dates) > 1 else None,
        total_days=len(sorted_dates)
    )


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    year: int = Query(default=2024, ge=2020, le=2030)
):
    """
    获取年度时间轴数据
    
    按月份分组，显示每月的热门话题
    """
    # 更新生成器年份
    generator = MockDataGenerator(year=year)
    timeline_data = generator.generate_timeline_data()
    
    # 应用 RealScore
    timeline_months = []
    
    for month_key in sorted(timeline_data.keys()):
        trends = timeline_data[month_key]
        processed = real_score_calculator.process_all_trends(trends)
        
        # 过滤营销并取前 5 名
        non_marketing = [t for t in processed if not t.get("is_marketing", False)][:5]
        
        trend_items = [_convert_to_trend_item(t) for t in non_marketing]
        
        timeline_months.append(TimelineMonth(
            month=month_key,
            top_trends=trend_items
        ))
    
    return TimelineResponse(
        timeline=timeline_months,
        year=year
    )


@router.get("/debug/score-breakdown")
async def get_score_breakdown(keyword: str):
    """
    调试接口：查看某个热词的分数计算过程
    """
    raw_trends = mock_generator.generate_all_trends()
    processed = real_score_calculator.process_all_trends(raw_trends)
    
    for trend in processed:
        if trend["keyword"] == keyword:
            return {
                "keyword": keyword,
                "raw_heat_score": trend["raw_heat_score"],
                "real_score": trend["real_score"],
                "breakdown": trend.get("score_breakdown", {}),
                "platforms": trend["platforms"],
                "is_marketing": trend.get("is_marketing", False)
            }
    
    raise HTTPException(status_code=404, detail=f"热词 '{keyword}' 未找到")


# ============================================================
# Phase 2: 实时数据接口
# ============================================================

from ..services.fetchers import get_fetcher_manager
from ..services.sentiment_analyzer import get_sentiment_analyzer, SentimentType


@router.get("/live")
async def get_live_trends(
    limit: int = Query(default=30, ge=1, le=100, description="返回数量限制"),
    platforms: Optional[str] = Query(default=None, description="指定平台，逗号分隔 (weibo,zhihu,bilibili)"),
    use_cache: bool = Query(default=True, description="是否使用缓存 (5分钟有效)")
):
    """
    🔴 实时获取多平台热搜数据
    
    从微博、知乎、B站实时爬取热搜，合并相同热词，应用情感分析
    
    注意: 首次调用可能较慢 (需要网络请求), 后续使用缓存
    """
    try:
        manager = get_fetcher_manager()
        analyzer = get_sentiment_analyzer()
        
        # 获取并合并数据
        merged_data = await manager.fetch_and_merge(
            limit_per_platform=limit,
            use_cache=use_cache
        )
        
        # 过滤指定平台
        if platforms:
            platform_list = [p.strip() for p in platforms.split(",")]
            merged_data = [
                item for item in merged_data
                if any(p in item["platforms"] for p in platform_list)
            ]
        
        # 应用情感分析
        for item in merged_data:
            sentiment_result = analyzer.analyze(item["keyword"])
            item["sentiment"] = sentiment_result.sentiment.value
            item["sentiment_confidence"] = sentiment_result.confidence
        
        # 应用 RealScore 算法
        for item in merged_data:
            # 添加必要字段用于 RealScore 计算
            item["is_marketing"] = False  # 实时数据默认非营销
            
            real_score = real_score_calculator.calculate_real_score(item)
            item["real_score"] = real_score
        
        # 按 RealScore 排序
        merged_data.sort(key=lambda x: x.get("real_score", 0), reverse=True)
        
        return {
            "source": "live",
            "trends": merged_data[:limit],
            "total_count": len(merged_data),
            "generated_at": datetime.now().isoformat(),
            "cache_used": use_cache,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"实时数据获取失败: {str(e)}"
        )


@router.get("/live/{platform}")
async def get_live_platform_trends(
    platform: str,
    limit: int = Query(default=50, ge=1, le=100)
):
    """
    获取单个平台的实时热搜
    
    Args:
        platform: weibo / zhihu / bilibili
    """
    valid_platforms = ["weibo", "zhihu", "bilibili"]
    
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"无效平台，可选: {', '.join(valid_platforms)}"
        )
    
    try:
        manager = get_fetcher_manager()
        analyzer = get_sentiment_analyzer()
        
        data = await manager.fetch_single_platform(platform, limit)
        
        # 添加情感分析
        for item in data:
            sentiment_result = analyzer.analyze(item["keyword"])
            item["sentiment"] = sentiment_result.sentiment.value
            item["sentiment_confidence"] = sentiment_result.confidence
        
        return {
            "platform": platform,
            "trends": data,
            "total_count": len(data),
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取 {platform} 数据失败: {str(e)}"
        )


@router.post("/analyze-sentiment")
async def analyze_sentiment_api(texts: List[str]):
    """
    情感分析 API
    
    输入一组文本，返回情感分析结果
    """
    if not texts:
        raise HTTPException(status_code=400, detail="texts 不能为空")
    
    if len(texts) > 100:
        raise HTTPException(status_code=400, detail="单次最多分析 100 条文本")
    
    analyzer = get_sentiment_analyzer()
    results = []
    
    for text in texts:
        result = analyzer.analyze(text)
        results.append({
            "text": text[:100],  # 截断长文本
            "sentiment": result.sentiment.value,
            "confidence": result.confidence,
            "method": result.method
        })
    
    return {
        "results": results,
        "total": len(results)
    }


# ============================================================
# Phase 3: 评论采集 API
# ============================================================

from ..services.crawlers import BilibiliCommentsCrawler, ZhihuCommentsCrawler, WeiboCommentsCrawler


@router.get("/comments/{keyword}")
async def get_keyword_comments(
    keyword: str,
    platform: str = Query(default="bilibili", description="平台: bilibili, zhihu, weibo"),
    video_limit: int = Query(default=5, ge=1, le=20, description="视频/问题/帖子数量"),
    comment_limit: int = Query(default=30, ge=1, le=100, description="每项评论数")
):
    """
    获取热词相关评论
    
    支持 B站、知乎、微博 三个平台
    """
    analyzer = get_sentiment_analyzer()
    
    try:
        if platform == "bilibili":
            crawler = BilibiliCommentsCrawler()
            try:
                result = await crawler.crawl_keyword_comments(
                    keyword, 
                    video_limit=video_limit, 
                    comment_limit_per_video=comment_limit
                )
            finally:
                await crawler.close()
            
            # 对评论进行情感分析
            for video in result.get("videos", []):
                for comment in video.get("comments", []):
                    sentiment_result = analyzer.analyze(comment["content"])
                    comment["sentiment"] = sentiment_result.sentiment.value
                    comment["sentiment_score"] = sentiment_result.confidence
        
        elif platform == "zhihu":
            # 自动加载持久化的 Cookie
            cookie = None
            try:
                cookie = await get_browser_auth().get_cookies("zhihu")
                if cookie:
                    print("[ZhihuCrawler] 已加载持久化的登录 Cookie")
            except Exception as e:
                print(f"[ZhihuCrawler] Cookie 加载失败: {e}")
            
            crawler = ZhihuCommentsCrawler(cookie=cookie)
            try:
                result = await crawler.crawl_keyword_comments(
                    keyword, 
                    question_limit=video_limit, 
                    answer_limit=3,
                    comment_limit=comment_limit
                )
            finally:
                await crawler.close()
            
            # 对评论进行情感分析
            for question in result.get("questions", []):
                for answer in question.get("answers", []):
                    for comment in answer.get("comments", []):
                        sentiment_result = analyzer.analyze(comment["content"])
                        comment["sentiment"] = sentiment_result.sentiment.value
                        comment["sentiment_score"] = sentiment_result.confidence
        
        elif platform == "weibo":
            # 自动加载持久化的 Cookie
            cookie = None
            try:
                cookie = await get_browser_auth().get_cookies("weibo")
                if cookie:
                    print("[WeiboCrawler] 已加载持久化的登录 Cookie")
            except Exception as e:
                print(f"[WeiboCrawler] Cookie 加载失败: {e}")
            
            crawler = WeiboCommentsCrawler(cookie=cookie)
            try:
                result = await crawler.crawl_keyword_comments(
                    keyword, 
                    post_limit=video_limit, 
                    comment_limit_per_post=comment_limit
                )
            finally:
                await crawler.close()
            
            # 对评论进行情感分析
            for post in result.get("posts", []):
                for comment in post.get("comments", []):
                    sentiment_result = analyzer.analyze(comment["content"])
                    comment["sentiment"] = sentiment_result.sentiment.value
                    comment["sentiment_score"] = sentiment_result.confidence
        
        else:
            raise HTTPException(
                status_code=400,
                detail="支持的平台: bilibili, zhihu, weibo"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"评论采集失败: {str(e)}"
        )


@router.get("/comments/{keyword}/sentiment")
async def get_comments_sentiment_stats(
    keyword: str,
    platform: str = Query(default="bilibili", description="平台: bilibili, zhihu")
):
    """
    获取热词评论的情感统计
    
    返回各情感类别的数量和占比
    """
    analyzer = get_sentiment_analyzer()
    sentiment_counts = {"happy": 0, "sad": 0, "angry": 0, "neutral": 0}
    total = 0
    
    try:
        if platform == "bilibili":
            crawler = BilibiliCommentsCrawler()
            try:
                result = await crawler.crawl_keyword_comments(keyword, video_limit=5, comment_limit_per_video=30)
            finally:
                await crawler.close()
            
            for video in result.get("videos", []):
                for comment in video.get("comments", []):
                    sentiment_result = analyzer.analyze(comment["content"])
                    sentiment_counts[sentiment_result.sentiment.value] += 1
                    total += 1
        
        elif platform == "zhihu":
            crawler = ZhihuCommentsCrawler()
            try:
                result = await crawler.crawl_keyword_comments(keyword, question_limit=5, answer_limit=3, comment_limit=30)
            finally:
                await crawler.close()
            
            for question in result.get("questions", []):
                for answer in question.get("answers", []):
                    for comment in answer.get("comments", []):
                        sentiment_result = analyzer.analyze(comment["content"])
                        sentiment_counts[sentiment_result.sentiment.value] += 1
                        total += 1
        
        else:
            raise HTTPException(status_code=400, detail="支持的平台: bilibili, zhihu")
        
        # 计算占比
        stats = {
            sentiment: {
                "count": count,
                "percentage": round(count / total * 100, 1) if total > 0 else 0
            }
            for sentiment, count in sentiment_counts.items()
        }
        
        return {
            "keyword": keyword,
            "platform": platform,
            "total_comments": total,
            "sentiment_distribution": stats,
            "dominant_sentiment": max(sentiment_counts, key=sentiment_counts.get) if total > 0 else "neutral"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"统计失败: {str(e)}")


# ============================================================
# Phase 3.5: 登录认证 API
# ============================================================

from ..services.browser_auth import get_browser_auth, PLAYWRIGHT_AVAILABLE


@router.get("/auth/status")
async def get_auth_status():
    """
    获取各平台的登录状态
    
    返回微博和知乎的登录信息
    """
    if not PLAYWRIGHT_AVAILABLE:
        return {
            "error": "Playwright 未安装",
            "install_command": "pip install playwright && playwright install chromium"
        }
    
    auth = get_browser_auth()
    return {
        "platforms": auth.get_login_status(),
        "browser_data_dir": str(auth._get_state_path("").parent)
    }


@router.post("/auth/login/{platform}")
async def trigger_login(platform: str):
    """
    触发扫码登录
    
    注意: 这会在服务器端弹出浏览器窗口
    仅适用于本地开发环境
    """
    if platform not in ["weibo", "zhihu"]:
        raise HTTPException(status_code=400, detail="支持的平台: weibo, zhihu")
    
    if not PLAYWRIGHT_AVAILABLE:
        raise HTTPException(
            status_code=500, 
            detail="Playwright 未安装，请运行: pip install playwright && playwright install chromium"
        )
    
    auth = get_browser_auth(headless=False)
    
    try:
        success = await auth.login_with_qr(platform, timeout=180)
        
        if success:
            return {
                "status": "success",
                "message": f"{platform} 登录成功",
                "cookie_available": True
            }
        else:
            return {
                "status": "failed",
                "message": f"{platform} 登录超时或失败",
                "cookie_available": False
            }
    finally:
        await auth.close()


@router.get("/auth/cookies/{platform}")
async def get_platform_cookies(platform: str):
    """
    获取平台的 Cookie (用于调试)
    """
    if platform not in ["weibo", "zhihu"]:
        raise HTTPException(status_code=400, detail="支持的平台: weibo, zhihu")
    
    auth = get_browser_auth()
    cookie = await auth.get_cookies(platform)
    
    if cookie:
        # 只返回部分 Cookie 用于确认
        preview = cookie[:100] + "..." if len(cookie) > 100 else cookie
        return {
            "platform": platform,
            "has_cookie": True,
            "cookie_preview": preview,
            "cookie_length": len(cookie)
        }
    else:
        return {
            "platform": platform,
            "has_cookie": False,
            "message": "未登录，请先调用 POST /auth/login/{platform}"
        }


# ============================================================
# GitHub 存档 API (历史热搜数据)
# ============================================================

@router.get("/yearly/{year}")
async def get_yearly_trends(
    year: int,
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制")
):
    """
    获取年度热词榜
    
    数据来源: GitHub justjavac/weibo-trending-hot-search
    可用范围: 2020-11-24 至今
    """
    from ..services.github_archive import get_yearly_hot_words
    
    if year < 2020 or year > datetime.now().year:
        raise HTTPException(
            status_code=400,
            detail=f"可用年份: 2020 ~ {datetime.now().year}"
        )
    
    try:
        result = await get_yearly_hot_words(year, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取年度数据失败: {str(e)}")


@router.get("/monthly/{year}/{month}")
async def get_monthly_trends(
    year: int,
    month: int,
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制")
):
    """
    获取月度热词榜
    
    数据来源: GitHub justjavac/weibo-trending-hot-search
    """
    from ..services.github_archive import get_monthly_hot_words
    
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="月份必须在 1-12 之间")
    
    if year < 2020 or year > datetime.now().year:
        raise HTTPException(
            status_code=400,
            detail=f"可用年份: 2020 ~ {datetime.now().year}"
        )
    
    try:
        result = await get_monthly_hot_words(year, month, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取月度数据失败: {str(e)}")


@router.get("/archive/{date}")
async def get_daily_archive(date: str):
    """
    获取单日热搜存档
    
    Args:
        date: 日期格式 YYYY-MM-DD
        
    数据来源: GitHub justjavac/weibo-trending-hot-search
    """
    from ..services.github_archive import get_daily_archive as fetch_daily
    
    # 验证日期格式
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")
    
    # 验证日期范围
    min_date = datetime(2020, 11, 24)
    if parsed_date < min_date:
        raise HTTPException(status_code=400, detail="数据最早可追溯至 2020-11-24")
    if parsed_date > datetime.now():
        raise HTTPException(status_code=400, detail="日期不能超过今天")
    
    try:
        result = await fetch_daily(date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取存档失败: {str(e)}")

