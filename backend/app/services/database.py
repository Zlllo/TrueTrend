"""
TrueTrend CN - 数据库模型
使用 SQLAlchemy 定义帖子和评论表结构
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# 数据库 URL (开发阶段使用 SQLite)
DATABASE_URL = "sqlite+aiosqlite:///./truetrend.db"

# 创建异步引擎
engine = create_async_engine(DATABASE_URL, echo=False)

# 创建会话工厂
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 声明基类
Base = declarative_base()


class Post(Base):
    """帖子/视频/问题表"""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False)  # weibo/zhihu/bilibili
    post_id = Column(String(50), nullable=False)   # 平台原始 ID
    keyword = Column(String(100), nullable=False)  # 关联热词
    title = Column(Text)
    content = Column(Text)
    author = Column(String(100))
    url = Column(String(500))
    heat_score = Column(Integer, default=0)
    created_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联评论
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Post {self.platform}:{self.post_id} '{self.title[:20]}...'>"


class Comment(Base):
    """评论表"""
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    comment_id = Column(String(50))                # 平台原始评论 ID
    content = Column(Text, nullable=False)
    author = Column(String(100))
    likes = Column(Integer, default=0)
    sentiment = Column(String(20))                 # happy/sad/angry/neutral
    sentiment_score = Column(Float)                # 0.0 - 1.0
    created_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联帖子
    post = relationship("Post", back_populates="comments")
    
    def __repr__(self):
        return f"<Comment {self.comment_id} '{self.content[:30]}...'>"


class CrawlTask(Base):
    """采集任务表"""
    __tablename__ = "crawl_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(100), nullable=False)
    platform = Column(String(20))                  # 可为空表示全平台
    status = Column(String(20), default="pending") # pending/running/completed/failed
    posts_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    def __repr__(self):
        return f"<CrawlTask {self.keyword} [{self.status}]>"


# ============================================================
# 数据库操作函数
# ============================================================

async def init_db():
    """初始化数据库 (创建表)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[Database] 数据库初始化完成")


async def get_session() -> AsyncSession:
    """获取数据库会话"""
    async with async_session() as session:
        yield session


async def add_post(session: AsyncSession, post_data: dict) -> Post:
    """添加帖子"""
    post = Post(**post_data)
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post


async def add_comments(session: AsyncSession, post_id: int, comments_data: list) -> int:
    """批量添加评论"""
    comments = [Comment(post_id=post_id, **data) for data in comments_data]
    session.add_all(comments)
    await session.commit()
    return len(comments)


async def get_comments_by_keyword(
    session: AsyncSession, 
    keyword: str, 
    limit: int = 100
) -> list:
    """根据热词查询评论"""
    from sqlalchemy import select
    
    stmt = (
        select(Comment)
        .join(Post)
        .where(Post.keyword == keyword)
        .order_by(Comment.likes.desc())
        .limit(limit)
    )
    
    result = await session.execute(stmt)
    return result.scalars().all()
