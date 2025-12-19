"""
TrueTrend CN - B站评论爬虫
获取 B站 热词相关视频及其评论

API 参考:
- 搜索: https://api.bilibili.com/x/web-interface/search/all/v2?keyword={keyword}
- 评论: https://api.bilibili.com/x/v2/reply/main?oid={aid}&type=1
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx


@dataclass
class BilibiliVideo:
    """B站视频数据"""
    aid: int              # av 号
    bvid: str             # BV 号
    title: str
    author: str
    play: int             # 播放量
    danmaku: int          # 弹幕数
    pubdate: int          # 发布时间戳
    description: str
    url: str


@dataclass
class BilibiliComment:
    """B站评论数据"""
    rpid: int             # 评论 ID
    content: str
    author: str
    likes: int
    rcount: int           # 回复数
    ctime: int            # 评论时间戳


class BilibiliCommentsCrawler:
    """
    B站评论爬虫
    
    流程: 搜索视频 → 获取视频评论 → 返回结构化数据
    """
    
    # B站 API
    SEARCH_API = "https://api.bilibili.com/x/web-interface/search/type"
    REPLY_API = "https://api.bilibili.com/x/v2/reply/main"
    
    # 热门视频 API (备用)
    POPULAR_API = "https://api.bilibili.com/x/web-interface/popular"
    
    # 完整的请求头 (绕过反爬)
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://search.bilibili.com/",
        "Origin": "https://search.bilibili.com",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }
    
    def __init__(self, cookie: Optional[str] = None):
        self.cookie = cookie
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            headers = self.HEADERS.copy()
            if self.cookie:
                headers["Cookie"] = self.cookie
            # 添加基础 Cookie (buvid3 是必须的)
            if "Cookie" not in headers:
                headers["Cookie"] = "buvid3=random-uuid-for-truetrend"
            self._client = httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True)
        return self._client
    
    async def close(self):
        """关闭连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def search_videos(self, keyword: str, limit: int = 20) -> List[BilibiliVideo]:
        """
        搜索关键词相关视频
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
        """
        client = await self._get_client()
        
        try:
            # 使用 search/type API
            params = {
                "keyword": keyword,
                "search_type": "video",
                "page": 1,
                "pagesize": min(limit, 30),
                "order": "totalrank",  # 综合排序
            }
            
            response = await client.get(self.SEARCH_API, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("code") != 0:
                print(f"[BilibiliCrawler] 搜索失败: {data.get('message')}")
                # 尝试使用热门视频作为备用
                return await self._get_popular_videos(limit)
            
            videos = []
            # search/type API 直接返回视频列表
            video_results = data.get("data", {}).get("result", [])
            
            if not video_results:
                print("[BilibiliCrawler] 搜索无结果，使用热门视频")
                return await self._get_popular_videos(limit)
            
            for item in video_results[:limit]:
                try:
                    videos.append(BilibiliVideo(
                        aid=item.get("aid", 0),
                        bvid=item.get("bvid", ""),
                        title=self._clean_html(item.get("title", "")),
                        author=item.get("author", ""),
                        play=item.get("play", 0),
                        danmaku=item.get("danmaku", 0),
                        pubdate=item.get("pubdate", 0),
                        description=item.get("description", ""),
                        url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    ))
                except Exception as e:
                    print(f"[BilibiliCrawler] 解析视频失败: {e}")
                    continue
            
            return videos
            
        except Exception as e:
            print(f"[BilibiliCrawler] 搜索请求失败: {e}")
            # 尝试使用热门视频作为备用
            return await self._get_popular_videos(limit)
    
    async def _get_popular_videos(self, limit: int = 10) -> List[BilibiliVideo]:
        """获取热门视频作为备用数据源"""
        client = await self._get_client()
        
        try:
            params = {"pn": 1, "ps": min(limit, 20)}
            response = await client.get(self.POPULAR_API, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("code") != 0:
                return []
            
            videos = []
            for item in data.get("data", {}).get("list", [])[:limit]:
                videos.append(BilibiliVideo(
                    aid=item.get("aid", 0),
                    bvid=item.get("bvid", ""),
                    title=item.get("title", ""),
                    author=item.get("owner", {}).get("name", ""),
                    play=item.get("stat", {}).get("view", 0),
                    danmaku=item.get("stat", {}).get("danmaku", 0),
                    pubdate=item.get("pubdate", 0),
                    description=item.get("desc", ""),
                    url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                ))
            
            print(f"[BilibiliCrawler] 使用热门视频: {len(videos)} 个")
            return videos
            
        except Exception as e:
            print(f"[BilibiliCrawler] 热门视频获取失败: {e}")
            return []
    
    async def get_video_comments(
        self, 
        aid: int, 
        limit: int = 100,
        sort: int = 2  # 0=时间 1=点赞 2=回复
    ) -> List[BilibiliComment]:
        """
        获取视频评论
        
        Args:
            aid: 视频 av 号
            limit: 返回数量限制
            sort: 排序方式
        """
        client = await self._get_client()
        comments = []
        next_cursor = 0
        
        while len(comments) < limit:
            try:
                params = {
                    "oid": aid,
                    "type": 1,  # 1=视频
                    "mode": sort,
                    "next": next_cursor,
                    "ps": min(20, limit - len(comments)),
                }
                
                response = await client.get(self.REPLY_API, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if data.get("code") != 0:
                    break
                
                replies = data.get("data", {}).get("replies", [])
                
                if not replies:
                    break
                
                for reply in replies:
                    try:
                        comments.append(BilibiliComment(
                            rpid=reply.get("rpid", 0),
                            content=reply.get("content", {}).get("message", ""),
                            author=reply.get("member", {}).get("uname", ""),
                            likes=reply.get("like", 0),
                            rcount=reply.get("rcount", 0),
                            ctime=reply.get("ctime", 0),
                        ))
                    except Exception:
                        continue
                
                # 获取下一页游标
                cursor = data.get("data", {}).get("cursor", {})
                if cursor.get("is_end", True):
                    break
                next_cursor = cursor.get("next", 0)
                
                # 避免请求过快
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"[BilibiliCrawler] 获取评论失败: {e}")
                break
        
        return comments[:limit]
    
    async def crawl_keyword_comments(
        self, 
        keyword: str,
        video_limit: int = 10,
        comment_limit_per_video: int = 50
    ) -> Dict[str, Any]:
        """
        完整流程: 搜索视频 → 获取评论
        
        Args:
            keyword: 热词
            video_limit: 搜索视频数量
            comment_limit_per_video: 每个视频的评论数量
        """
        print(f"[BilibiliCrawler] 开始采集: {keyword}")
        
        # 1. 搜索相关视频
        videos = await self.search_videos(keyword, video_limit)
        print(f"[BilibiliCrawler] 找到 {len(videos)} 个视频")
        
        # 2. 获取每个视频的评论
        all_results = {
            "keyword": keyword,
            "platform": "bilibili",
            "videos": [],
            "total_comments": 0,
            "crawled_at": datetime.now().isoformat(),
        }
        
        for video in videos:
            comments = await self.get_video_comments(video.aid, comment_limit_per_video)
            
            video_data = {
                "aid": video.aid,
                "bvid": video.bvid,
                "title": video.title,
                "author": video.author,
                "play": video.play,
                "url": video.url,
                "pubdate": datetime.fromtimestamp(video.pubdate).isoformat() if video.pubdate else None,
                "comments": [
                    {
                        "rpid": c.rpid,
                        "content": c.content,
                        "author": c.author,
                        "likes": c.likes,
                        "ctime": datetime.fromtimestamp(c.ctime).isoformat() if c.ctime else None,
                    }
                    for c in comments
                ]
            }
            
            all_results["videos"].append(video_data)
            all_results["total_comments"] += len(comments)
            
            print(f"  - {video.title[:30]}... ({len(comments)} 条评论)")
            
            # 避免请求过快
            await asyncio.sleep(1)
        
        print(f"[BilibiliCrawler] 采集完成: {all_results['total_comments']} 条评论")
        
        return all_results
    
    def _clean_html(self, text: str) -> str:
        """清除 HTML 标签"""
        import re
        return re.sub(r'<[^>]+>', '', text)


# ============================================================
# 便捷函数
# ============================================================

async def crawl_bilibili_comments(keyword: str, video_limit: int = 10) -> Dict[str, Any]:
    """便捷函数: 采集 B站 关键词相关评论"""
    crawler = BilibiliCommentsCrawler()
    try:
        return await crawler.crawl_keyword_comments(keyword, video_limit)
    finally:
        await crawler.close()
