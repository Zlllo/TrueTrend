"""
TrueTrend CN - 知乎评论爬虫
获取知乎热词相关问题及其回答评论

API 参考:
- 搜索: https://www.zhihu.com/api/v4/search_v3?q={keyword}&t=general
- 回答: https://www.zhihu.com/api/v4/questions/{qid}/answers
- 评论: https://www.zhihu.com/api/v4/answers/{aid}/root_comments
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx


@dataclass
class ZhihuQuestion:
    """知乎问题数据"""
    id: int
    title: str
    url: str
    answer_count: int
    follower_count: int = 0


@dataclass
class ZhihuAnswer:
    """知乎回答数据"""
    id: int
    question_id: int
    author: str
    content: str
    voteup_count: int
    comment_count: int
    created_time: int


@dataclass
class ZhihuComment:
    """知乎评论数据"""
    id: int
    content: str
    author: str
    likes: int
    created_time: int


class ZhihuCommentsCrawler:
    """
    知乎评论爬虫
    
    流程: 搜索问题 → 获取回答 → 获取评论
    """
    
    # 知乎 API
    SEARCH_API = "https://www.zhihu.com/api/v4/search_v3"
    QUESTION_API = "https://www.zhihu.com/api/v4/questions/{qid}/feeds"
    ANSWERS_API = "https://www.zhihu.com/api/v4/questions/{qid}/answers"
    COMMENTS_API = "https://www.zhihu.com/api/v4/answers/{aid}/root_comments"
    
    # 热榜 API (备用)
    HOT_LIST_API = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.zhihu.com/",
        "X-Requested-With": "fetch",
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
            self._client = httpx.AsyncClient(
                headers=headers, 
                timeout=30.0,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """关闭连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def search_questions(self, keyword: str, limit: int = 10) -> List[ZhihuQuestion]:
        """
        搜索关键词相关问题
        使用知乎网页版搜索 API
        """
        client = await self._get_client()
        
        try:
            # 使用网页版搜索 API (更稳定)
            search_url = "https://www.zhihu.com/api/v4/search_v3"
            
            params = {
                "gk_version": "gz-gaokao",
                "t": "general",
                "q": keyword,
                "correction": 1,
                "offset": 0,
                "limit": min(limit, 20),
                "filter_fields": "",
                "lc_idx": 0,
                "show_all_topics": 0,
            }
            
            # 添加必要的请求头
            headers = {
                "x-requested-with": "fetch",
                "x-zse-93": "101_3_3.0",
            }
            
            response = await client.get(search_url, params=params, headers=headers)
            
            # 如果搜索失败，尝试使用问题搜索 API
            if response.status_code != 200:
                print(f"[ZhihuCrawler] 搜索 API 返回 {response.status_code}，尝试话题搜索")
                return await self._search_by_topic(keyword, limit)
            
            data = response.json()
            
            questions = []
            for item in data.get("data", []):
                try:
                    obj = item.get("object", {})
                    obj_type = obj.get("type", "")
                    
                    # 处理问题类型
                    if obj_type == "question":
                        question = obj.get("question", obj)
                        questions.append(ZhihuQuestion(
                            id=question.get("id", 0),
                            title=question.get("title", ""),
                            url=f"https://www.zhihu.com/question/{question.get('id', '')}",
                            answer_count=question.get("answer_count", 0),
                            follower_count=question.get("follower_count", 0),
                        ))
                    
                    # 处理回答类型 (提取其问题)
                    elif obj_type == "answer":
                        question = obj.get("question", {})
                        if question.get("id"):
                            questions.append(ZhihuQuestion(
                                id=question.get("id", 0),
                                title=question.get("title", ""),
                                url=f"https://www.zhihu.com/question/{question.get('id', '')}",
                                answer_count=question.get("answer_count", 0),
                            ))
                except Exception:
                    continue
            
            # 去重
            seen_ids = set()
            unique_questions = []
            for q in questions:
                if q.id not in seen_ids:
                    seen_ids.add(q.id)
                    unique_questions.append(q)
            
            if not unique_questions:
                print(f"[ZhihuCrawler] 搜索无结果，尝试话题搜索")
                return await self._search_by_topic(keyword, limit)
            
            print(f"[ZhihuCrawler] 搜索到 {len(unique_questions)} 个相关问题")
            return unique_questions[:limit]
            
        except Exception as e:
            print(f"[ZhihuCrawler] 搜索失败: {e}")
            return await self._search_by_topic(keyword, limit)
    
    async def _search_by_topic(self, keyword: str, limit: int = 10) -> List[ZhihuQuestion]:
        """使用话题搜索作为备用"""
        client = await self._get_client()
        
        try:
            # 话题搜索 API
            url = f"https://www.zhihu.com/api/v4/search/suggest"
            params = {"q": keyword}
            
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                print(f"[ZhihuCrawler] 话题搜索也失败，使用热榜")
                return await self._get_hot_questions(limit)
            
            data = response.json()
            questions = []
            
            for item in data.get("suggest", []):
                if item.get("type") == "topic":
                    topic_id = item.get("id")
                    # 获取话题下的问题
                    topic_questions = await self._get_topic_questions(topic_id, limit)
                    questions.extend(topic_questions)
                    if len(questions) >= limit:
                        break
            
            if questions:
                print(f"[ZhihuCrawler] 话题搜索找到 {len(questions)} 个问题")
                return questions[:limit]
            
            return await self._get_hot_questions(limit)
            
        except Exception as e:
            print(f"[ZhihuCrawler] 话题搜索失败: {e}")
            return await self._get_hot_questions(limit)
    
    async def _get_topic_questions(self, topic_id: int, limit: int = 5) -> List[ZhihuQuestion]:
        """获取话题下的热门问题"""
        client = await self._get_client()
        
        try:
            url = f"https://www.zhihu.com/api/v4/topics/{topic_id}/feeds/top_question"
            params = {"limit": limit}
            
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            questions = []
            
            for item in data.get("data", []):
                target = item.get("target", {})
                if target.get("type") == "question":
                    questions.append(ZhihuQuestion(
                        id=target.get("id", 0),
                        title=target.get("title", ""),
                        url=f"https://www.zhihu.com/question/{target.get('id', '')}",
                        answer_count=target.get("answer_count", 0),
                    ))
            
            return questions
            
        except Exception:
            return []
    
    async def _get_hot_questions(self, limit: int = 10) -> List[ZhihuQuestion]:
        """获取热榜问题作为备用"""
        client = await self._get_client()
        
        try:
            params = {"limit": min(limit, 50)}
            response = await client.get(self.HOT_LIST_API, params=params)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            questions = []
            
            for item in data.get("data", [])[:limit]:
                target = item.get("target", {})
                questions.append(ZhihuQuestion(
                    id=target.get("id", 0),
                    title=target.get("title", ""),
                    url=f"https://www.zhihu.com/question/{target.get('id', '')}",
                    answer_count=target.get("answer_count", 0),
                ))
            
            print(f"[ZhihuCrawler] 使用热榜: {len(questions)} 个问题")
            return questions
            
        except Exception as e:
            print(f"[ZhihuCrawler] 热榜获取失败: {e}")
            return []
    
    async def get_question_answers(
        self, 
        question_id: int, 
        limit: int = 5
    ) -> List[ZhihuAnswer]:
        """获取问题的热门回答"""
        client = await self._get_client()
        
        try:
            url = self.ANSWERS_API.format(qid=question_id)
            params = {
                "include": "content,voteup_count,comment_count",
                "offset": 0,
                "limit": min(limit, 20),
                "sort_by": "default",  # 默认排序 (热门)
            }
            
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            answers = []
            
            for item in data.get("data", [])[:limit]:
                try:
                    answers.append(ZhihuAnswer(
                        id=item.get("id", 0),
                        question_id=question_id,
                        author=item.get("author", {}).get("name", "匿名用户"),
                        content=self._clean_html(item.get("content", ""))[:500],
                        voteup_count=item.get("voteup_count", 0),
                        comment_count=item.get("comment_count", 0),
                        created_time=item.get("created_time", 0),
                    ))
                except Exception:
                    continue
            
            return answers
            
        except Exception as e:
            print(f"[ZhihuCrawler] 获取回答失败: {e}")
            return []
    
    async def get_answer_comments(
        self, 
        answer_id: int, 
        limit: int = 20
    ) -> List[ZhihuComment]:
        """获取回答的评论"""
        client = await self._get_client()
        
        try:
            url = self.COMMENTS_API.format(aid=answer_id)
            params = {
                "order": "normal",  # 热门排序
                "limit": min(limit, 20),
                "offset": 0,
            }
            
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            comments = []
            
            for item in data.get("data", [])[:limit]:
                try:
                    comments.append(ZhihuComment(
                        id=item.get("id", 0),
                        content=item.get("content", ""),
                        author=item.get("author", {}).get("name", "匿名用户"),
                        likes=item.get("like_count", 0),
                        created_time=item.get("created_time", 0),
                    ))
                except Exception:
                    continue
            
            return comments
            
        except Exception as e:
            print(f"[ZhihuCrawler] 获取评论失败: {e}")
            return []
    
    async def crawl_keyword_comments(
        self, 
        keyword: str,
        question_limit: int = 5,
        answer_limit: int = 3,
        comment_limit: int = 20
    ) -> Dict[str, Any]:
        """
        完整流程: 搜索问题 → 获取回答 → 获取评论
        """
        print(f"[ZhihuCrawler] 开始采集: {keyword}")
        
        # 1. 搜索相关问题
        questions = await self.search_questions(keyword, question_limit)
        print(f"[ZhihuCrawler] 找到 {len(questions)} 个问题")
        
        all_results = {
            "keyword": keyword,
            "platform": "zhihu",
            "questions": [],
            "total_comments": 0,
            "crawled_at": datetime.now().isoformat(),
        }
        
        for question in questions:
            # 2. 获取回答
            answers = await self.get_question_answers(question.id, answer_limit)
            
            question_data = {
                "id": question.id,
                "title": question.title,
                "url": question.url,
                "answer_count": question.answer_count,
                "answers": [],
            }
            
            for answer in answers:
                # 3. 获取评论
                comments = await self.get_answer_comments(answer.id, comment_limit)
                
                answer_data = {
                    "id": answer.id,
                    "author": answer.author,
                    "voteup_count": answer.voteup_count,
                    "content_preview": answer.content[:200] + "..." if len(answer.content) > 200 else answer.content,
                    "comments": [
                        {
                            "id": c.id,
                            "content": c.content,
                            "author": c.author,
                            "likes": c.likes,
                            "created_time": datetime.fromtimestamp(c.created_time).isoformat() if c.created_time else None,
                        }
                        for c in comments
                    ]
                }
                
                question_data["answers"].append(answer_data)
                all_results["total_comments"] += len(comments)
                
                await asyncio.sleep(0.5)  # 避免请求过快
            
            all_results["questions"].append(question_data)
            print(f"  - {question.title[:30]}... ({len(answers)} 回答)")
            
            await asyncio.sleep(0.5)
        
        print(f"[ZhihuCrawler] 采集完成: {all_results['total_comments']} 条评论")
        
        return all_results
    
    def _clean_html(self, text: str) -> str:
        """清除 HTML 标签"""
        import re
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


# ============================================================
# 便捷函数
# ============================================================

async def crawl_zhihu_comments(
    keyword: str, 
    question_limit: int = 5,
    cookie: Optional[str] = None,
    auto_load_cookie: bool = True
) -> Dict[str, Any]:
    """
    便捷函数: 采集知乎关键词相关评论
    
    Args:
        keyword: 搜索关键词
        question_limit: 问题数量限制
        cookie: 手动传入的 Cookie
        auto_load_cookie: 是否自动从 browser_auth 加载持久化的 Cookie
    """
    # 自动加载持久化的 Cookie
    if cookie is None and auto_load_cookie:
        try:
            from ..browser_auth import get_browser_auth
            auth = get_browser_auth()
            cookie = await auth.get_cookies("zhihu")
            if cookie:
                print("[ZhihuCrawler] 已加载持久化的登录 Cookie")
        except Exception as e:
            print(f"[ZhihuCrawler] 无法加载 Cookie: {e}")
    
    crawler = ZhihuCommentsCrawler(cookie=cookie)
    try:
        return await crawler.crawl_keyword_comments(keyword, question_limit)
    finally:
        await crawler.close()
