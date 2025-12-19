"""
TrueTrend CN - FastAPI 应用入口
去伪存真：穿透商业营销和假热搜的迷雾，挖掘中国互联网真正自发的年度记忆
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import trends

# 创建 FastAPI 应用
app = FastAPI(
    title="TrueTrend CN",
    description="年度网络热词分析 API - 去伪存真，挖掘真实的民间记忆",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS (允许前端跨域访问)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(trends.router)


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "TrueTrend CN",
        "version": "1.0.0",
        "description": "去伪存真 - 年度网络热词分析",
        "docs": "/docs",
        "endpoints": {
            "trends": "/api/trends",
            "lifecycle": "/api/trends/{keyword}/lifecycle",
            "timeline": "/api/trends/timeline"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
