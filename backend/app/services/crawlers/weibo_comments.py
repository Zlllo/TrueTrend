"""
TrueTrend CN - 微博评论爬虫 (BettaFish 方案)

参考 BettaFish 项目的实现方式：
1. 使用 Playwright 管理浏览器上下文和 Cookie
2. 使用移动端 API (m.weibo.cn)
3. 检查登录状态，失败则提示重新登录
4. 正确设置 Referer 等请求头

API 参考:
- 搜索: https://m.weibo.cn/api/container/getIndex?containerid=100103type=1&q={keyword}
- 评论: https://m.weibo.cn/comments/hotflow?id={mid}&mid={mid}
"""

import asyncio
import copy
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx


@dataclass
class WeiboPost:
    """微博帖子数据"""
    mid: str              # 微博 ID
    text: str             # 文本内容
    author: str           # 作者昵称
    author_id: str        # 作者 UID
    reposts: int          # 转发数
    comments: int         # 评论数
    likes: int            # 点赞数
    created_at: str       # 发布时间
    url: str


@dataclass
class WeiboComment:
    """微博评论数据"""
    id: str
    content: str
    author: str
    likes: int
    created_at: str


class WeiboCommentsCrawler:
    """
    微博评论爬虫 (BettaFish 方案)
    
    使用 Playwright 浏览器上下文进行请求，
    利用保存的登录状态绕过反爬限制
    """
    
    # 移动端 API 基础 URL
    HOST = "https://m.weibo.cn"
    
    # 移动端 User-Agent
    MOBILE_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    
    def __init__(self, cookie: Optional[str] = None):
        """
        Args:
            cookie: 微博登录 Cookie 字符串
        """
        self.cookie = cookie
        self._client: Optional[httpx.AsyncClient] = None
        self._headers = self._build_headers()
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "User-Agent": self.MOBILE_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://m.weibo.cn/",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://m.weibo.cn",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        return headers
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self._headers, 
                timeout=30.0,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """关闭连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def pong(self) -> bool:
        """
        检查登录状态 (参考 BettaFish)
        """
        client = await self._get_client()
        
        try:
            response = await client.get(f"{self.HOST}/api/config")
            
            if response.status_code != 200:
                print(f"[WeiboCrawler] pong 失败: HTTP {response.status_code}")
                return False
            
            data = response.json()
            
            if data.get("ok") == 1:
                login_status = data.get("data", {}).get("login", False)
                if login_status:
                    print("[WeiboCrawler] ✓ 登录状态有效")
                    return True
                else:
                    print("[WeiboCrawler] ✗ 未登录或登录已过期")
                    return False
            else:
                print(f"[WeiboCrawler] pong 返回异常: {data}")
                return False
                
        except Exception as e:
            print(f"[WeiboCrawler] pong 异常: {e}")
            return False
    
    async def search_posts(self, keyword: str, limit: int = 10) -> List[WeiboPost]:
        """
        搜索关键词相关微博 (参考 BettaFish get_note_by_keyword)
        """
        client = await self._get_client()
        posts = []
        page = 1
        
        while len(posts) < limit:
            try:
                # BettaFish 使用的 containerid 格式
                containerid = f"100103type=1&q={keyword}"
                
                params = {
                    "containerid": containerid,
                    "page_type": "searchall",
                    "page": page,
                }
                
                url = f"{self.HOST}/api/container/getIndex"
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    print(f"[WeiboCrawler] 搜索请求失败: HTTP {response.status_code}")
                    break
                
                data = response.json()
                
                ok_code = data.get("ok")
                if ok_code == 0:
                    msg = data.get("msg", "unknown error")
                    print(f"[WeiboCrawler] 搜索失败: {msg}")
                    break
                elif ok_code != 1:
                    print(f"[WeiboCrawler] 搜索异常: {data}")
                    break
                
                cards = data.get("data", {}).get("cards", [])
                
                if not cards:
                    break
                
                for card in cards:
                    card_type = card.get("card_type")
                    
                    # 处理微博卡片
                    if card_type == 9:
                        mblog = card.get("mblog", {})
                        post = self._parse_mblog(mblog)
                        if post:
                            posts.append(post)
                    
                    # 处理卡片组 (搜索结果有时是嵌套的)
                    elif card_type == 11:
                        card_group = card.get("card_group", [])
                        for sub_card in card_group:
                            if sub_card.get("card_type") == 9:
                                mblog = sub_card.get("mblog", {})
                                post = self._parse_mblog(mblog)
                                if post:
                                    posts.append(post)
                    
                    if len(posts) >= limit:
                        break
                
                page += 1
                await asyncio.sleep(1)  # 避免请求过快
                
            except Exception as e:
                print(f"[WeiboCrawler] 搜索异常: {e}")
                break
        
        return posts[:limit]
    
    def _parse_mblog(self, mblog: dict) -> Optional[WeiboPost]:
        """解析微博数据"""
        if not mblog or not mblog.get("mid"):
            return None
        
        try:
            user = mblog.get("user", {}) or {}
            return WeiboPost(
                mid=str(mblog.get("mid", "")),
                text=self._clean_html(mblog.get("text", "")),
                author=user.get("screen_name", ""),
                author_id=str(user.get("id", "")),
                reposts=mblog.get("reposts_count", 0),
                comments=mblog.get("comments_count", 0),
                likes=mblog.get("attitudes_count", 0),
                created_at=mblog.get("created_at", ""),
                url=f"https://m.weibo.cn/detail/{mblog.get('mid', '')}",
            )
        except Exception as e:
            print(f"[WeiboCrawler] 解析微博失败: {e}")
            return None
    
    async def get_post_comments(
        self, 
        mid: str, 
        limit: int = 50
    ) -> List[WeiboComment]:
        """
        获取微博评论 (参考 BettaFish get_note_comments)
        """
        client = await self._get_client()
        comments = []
        max_id = 0
        max_id_type = 0
        
        # 设置正确的 Referer (BettaFish 的做法)
        referer_url = f"https://m.weibo.cn/detail/{mid}"
        headers = copy.copy(self._headers)
        headers["Referer"] = referer_url
        
        while len(comments) < limit:
            try:
                params = {
                    "id": mid,
                    "mid": mid,
                    "max_id_type": max_id_type,
                }
                if max_id > 0:
                    params["max_id"] = max_id
                
                url = f"{self.HOST}/comments/hotflow"
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code != 200:
                    print(f"[WeiboCrawler] 评论请求失败: HTTP {response.status_code}")
                    break
                
                data = response.json()
                
                if data.get("ok") != 1:
                    break
                
                comment_data = data.get("data", {})
                comment_list = comment_data.get("data", [])
                
                if not comment_list:
                    break
                
                for item in comment_list:
                    try:
                        user = item.get("user", {}) or {}
                        comments.append(WeiboComment(
                            id=str(item.get("id", "")),
                            content=self._clean_html(item.get("text", "")),
                            author=user.get("screen_name", ""),
                            likes=item.get("like_count", 0),
                            created_at=item.get("created_at", ""),
                        ))
                    except Exception:
                        continue
                
                # 获取下一页游标
                max_id = comment_data.get("max_id", 0)
                max_id_type = comment_data.get("max_id_type", 0)
                
                if max_id == 0:
                    break
                
                await asyncio.sleep(1)  # 避免请求过快
                
            except Exception as e:
                print(f"[WeiboCrawler] 获取评论失败: {e}")
                break
        
        return comments[:limit]
    
    async def crawl_keyword_comments(
        self, 
        keyword: str,
        post_limit: int = 5,
        comment_limit_per_post: int = 30
    ) -> Dict[str, Any]:
        """
        完整流程: 搜索微博 → 获取评论
        """
        print(f"[WeiboCrawler] 开始采集: {keyword}")
        
        # 1. 检查登录状态
        if not await self.pong():
            print("[WeiboCrawler] ⚠️ 未登录，请先运行 python app/services/browser_auth.py 登录微博")
            return {
                "keyword": keyword,
                "platform": "weibo",
                "posts": [],
                "total_comments": 0,
                "crawled_at": datetime.now().isoformat(),
                "error": "需要登录微博，请运行: python app/services/browser_auth.py",
            }
        
        # 2. 搜索相关微博
        posts = await self.search_posts(keyword, post_limit)
        print(f"[WeiboCrawler] 找到 {len(posts)} 条微博")
        
        all_results = {
            "keyword": keyword,
            "platform": "weibo",
            "posts": [],
            "total_comments": 0,
            "crawled_at": datetime.now().isoformat(),
        }
        
        for post in posts:
            # 3. 获取评论
            comments = await self.get_post_comments(post.mid, comment_limit_per_post)
            
            post_data = {
                "mid": post.mid,
                "text": post.text[:200] + "..." if len(post.text) > 200 else post.text,
                "author": post.author,
                "reposts": post.reposts,
                "comments_count": post.comments,
                "likes": post.likes,
                "url": post.url,
                "created_at": post.created_at,
                "comments": [
                    {
                        "id": c.id,
                        "content": c.content,
                        "author": c.author,
                        "likes": c.likes,
                        "created_at": c.created_at,
                    }
                    for c in comments
                ]
            }
            
            all_results["posts"].append(post_data)
            all_results["total_comments"] += len(comments)
            
            text_preview = post.text[:30] if len(post.text) > 30 else post.text
            print(f"  - @{post.author}: {text_preview}... ({len(comments)} 条评论)")
            
            await asyncio.sleep(1)  # 避免请求过快
        
        print(f"[WeiboCrawler] 采集完成: {all_results['total_comments']} 条评论")
        
        return all_results
    
    def _clean_html(self, text: str) -> str:
        """清除 HTML 标签和表情"""
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除微博表情 [xxx]
        text = re.sub(r'\[[\u4e00-\u9fa5a-zA-Z]+\]', '', text)
        return text.strip()


# ============================================================
# 便捷函数
# ============================================================

async def crawl_weibo_comments(
    keyword: str, 
    post_limit: int = 5,
    cookie: Optional[str] = None,
    auto_load_cookie: bool = True
) -> Dict[str, Any]:
    """
    便捷函数: 采集微博关键词相关评论
    
    Args:
        keyword: 搜索关键词
        post_limit: 帖子数量限制
        cookie: 手动传入的 Cookie
        auto_load_cookie: 是否自动从 browser_auth 加载持久化的 Cookie
    """
    # 自动加载持久化的 Cookie
    if cookie is None and auto_load_cookie:
        try:
            from ..browser_auth import get_browser_auth
            auth = get_browser_auth()
            cookie = await auth.get_cookies("weibo")
            if cookie:
                print("[WeiboCrawler] 已加载持久化的登录 Cookie")
        except Exception as e:
            print(f"[WeiboCrawler] 无法加载 Cookie: {e}")
    
    crawler = WeiboCommentsCrawler(cookie=cookie)
    try:
        return await crawler.crawl_keyword_comments(keyword, post_limit)
    finally:
        await crawler.close()
