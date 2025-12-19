"""
TrueTrend CN - 浏览器认证模块
实现扫码登录 + Cookie 持久化策略

参考 BettaFish 项目的 "先登录，后持久化" 方案:
1. 首次运行弹出二维码，用户扫码登录
2. 登录成功后保存浏览器状态到本地
3. 后续运行自动加载状态，无需重复登录
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[BrowserAuth] Playwright 未安装，请运行: pip install playwright && playwright install chromium")


# 浏览器状态存储目录
BROWSER_DATA_DIR = Path(__file__).parent.parent.parent.parent / "browser_data"


class BrowserAuth:
    """
    浏览器认证管理器
    
    支持微博、知乎的扫码登录和状态持久化
    """
    
    # 平台登录页面
    LOGIN_URLS = {
        "weibo": "https://passport.weibo.com/sso/signin?entry=miniblog&source=miniblog",
        "zhihu": "https://www.zhihu.com/signin",
    }
    
    # 登录成功检测 URL 特征 (任意匹配即成功)
    LOGIN_SUCCESS_PATTERNS = {
        "weibo": [
            "weibo.com/u/",
            "weibo.com/home", 
            "weibo.cn/",
            "weibo.com/newlogin",
            "weibo.com/ajax",
            "my.weibo.com",
            "d.weibo.com",
        ],
        "zhihu": [
            "zhihu.com/people/", 
            "www.zhihu.com/",
            "zhihu.com/question",
            "zhihu.com/hot",
        ],
    }
    
    # 登录页面 URL 特征 (离开这些页面表示可能登录成功)
    LOGIN_PAGE_PATTERNS = {
        "weibo": ["passport.weibo.com", "login.sina.com.cn"],
        "zhihu": ["zhihu.com/signin", "zhihu.com/sign"],
    }
    
    def __init__(self, headless: bool = False):
        """
        Args:
            headless: 是否无头模式 (首次登录建议 False 以显示二维码)
        """
        self.headless = headless
        self._browser: Optional[Browser] = None
        self._contexts: Dict[str, BrowserContext] = {}
        
        # 确保数据目录存在
        BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_state_path(self, platform: str) -> Path:
        """获取平台状态文件路径"""
        return BROWSER_DATA_DIR / f"{platform}_state.json"
    
    def is_logged_in(self, platform: str) -> bool:
        """检查平台是否已登录 (状态文件是否存在)"""
        state_path = self._get_state_path(platform)
        return state_path.exists()
    
    async def _init_browser(self):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装")
        
        if self._browser is None:
            playwright = await async_playwright().start()
            # 使用 Firefox 避免 macOS Sonoma + Chromium 兼容性问题
            self._browser = await playwright.firefox.launch(
                headless=self.headless,
            )
    
    async def close(self):
        """关闭浏览器"""
        for ctx in self._contexts.values():
            await ctx.close()
        self._contexts.clear()
        
        if self._browser:
            await self._browser.close()
            self._browser = None
    
    async def login_with_qr(self, platform: str, timeout: int = 120) -> bool:
        """
        扫码登录
        
        Args:
            platform: 平台名称 (weibo / zhihu)
            timeout: 等待扫码的超时时间 (秒)
            
        Returns:
            是否登录成功
        """
        if platform not in self.LOGIN_URLS:
            raise ValueError(f"不支持的平台: {platform}")
        
        print(f"\n{'='*50}")
        print(f"[BrowserAuth] 开始 {platform.upper()} 扫码登录")
        print(f"{'='*50}")
        
        await self._init_browser()
        
        # 创建新的浏览器上下文
        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        
        page = await context.new_page()
        
        try:
            # 打开登录页面
            await page.goto(self.LOGIN_URLS[platform], wait_until="networkidle")
            
            print(f"\n📱 请使用 {platform.upper()} APP 扫描浏览器中的二维码")
            print(f"⏰ 等待时间: {timeout} 秒\n")
            
            # 等待登录成功
            success = await self._wait_for_login(page, platform, timeout)
            
            if success:
                # 对于微博，需要访问移动端页面以获取 m.weibo.cn 的 cookie
                # 参考 BettaFish: 登录成功后重定向到手机端的网站，再保存 cookie
                if platform == "weibo":
                    print("[BrowserAuth] 正在获取移动端 Cookie...")
                    await page.goto("https://m.weibo.cn", wait_until="networkidle")
                    await asyncio.sleep(2)
                    # 再访问 API 确保 cookie 完整
                    await page.goto("https://m.weibo.cn/api/config", wait_until="networkidle")
                    await asyncio.sleep(1)
                
                # 保存浏览器状态
                state_path = self._get_state_path(platform)
                await context.storage_state(path=str(state_path))
                
                print(f"\n✅ {platform.upper()} 登录成功！")
                print(f"📁 状态已保存到: {state_path}")
                
                return True
            else:
                print(f"\n❌ {platform.upper()} 登录超时或失败")
                print(f"最后 URL: {page.url}")
                return False
                
        except Exception as e:
            print(f"\n❌ 登录过程出错: {e}")
            return False
        finally:
            await context.close()
    
    async def _wait_for_login(self, page: Page, platform: str, timeout: int) -> bool:
        """等待登录成功"""
        success_patterns = self.LOGIN_SUCCESS_PATTERNS.get(platform, [])
        login_page_patterns = self.LOGIN_PAGE_PATTERNS.get(platform, [])
        
        start_time = asyncio.get_event_loop().time()
        last_url = ""
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            current_url = page.url
            
            # 打印 URL 变化
            if current_url != last_url:
                print(f"[检测] URL 变化: {current_url[:60]}...")
                last_url = current_url
            
            # 方法1: 检查是否匹配成功模式
            for pattern in success_patterns:
                if pattern in current_url:
                    print(f"[检测] ✓ 匹配成功模式: {pattern}")
                    await asyncio.sleep(2)
                    return True
            
            # 方法2: 检查是否离开了登录页面
            on_login_page = any(p in current_url for p in login_page_patterns)
            if not on_login_page and "passport" not in current_url and "signin" not in current_url.lower():
                # 已离开登录页面，可能登录成功
                print(f"[检测] ✓ 已离开登录页面")
                await asyncio.sleep(2)
                return True
            
            await asyncio.sleep(1)
        
        return False
    
    async def get_authenticated_context(self, platform: str) -> Optional[BrowserContext]:
        """
        获取已认证的浏览器上下文
        
        如果之前已登录，会自动加载保存的状态
        """
        if platform in self._contexts:
            return self._contexts[platform]
        
        state_path = self._get_state_path(platform)
        
        if not state_path.exists():
            print(f"[BrowserAuth] {platform} 未登录，请先调用 login_with_qr()")
            return None
        
        await self._init_browser()
        
        # 加载保存的状态
        context = await self._browser.new_context(
            storage_state=str(state_path),
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        
        self._contexts[platform] = context
        print(f"[BrowserAuth] 已加载 {platform} 登录状态")
        
        return context
    
    async def get_cookies(self, platform: str) -> Optional[str]:
        """
        获取平台的 Cookie 字符串 (用于 httpx 请求)
        """
        state_path = self._get_state_path(platform)
        
        if not state_path.exists():
            return None
        
        import json
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        cookies = state.get("cookies", [])
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        
        return cookie_str
    
    async def refresh_login(self, platform: str) -> bool:
        """
        刷新登录状态 (重新扫码)
        """
        state_path = self._get_state_path(platform)
        
        # 删除旧状态
        if state_path.exists():
            state_path.unlink()
        
        # 清除缓存的上下文
        if platform in self._contexts:
            await self._contexts[platform].close()
            del self._contexts[platform]
        
        # 重新登录
        return await self.login_with_qr(platform)
    
    def get_login_status(self) -> Dict[str, Any]:
        """获取所有平台的登录状态"""
        status = {}
        
        for platform in ["weibo", "zhihu"]:
            state_path = self._get_state_path(platform)
            
            if state_path.exists():
                mtime = datetime.fromtimestamp(state_path.stat().st_mtime)
                status[platform] = {
                    "logged_in": True,
                    "state_file": str(state_path),
                    "last_updated": mtime.isoformat(),
                }
            else:
                status[platform] = {
                    "logged_in": False,
                    "state_file": None,
                    "last_updated": None,
                }
        
        return status


# ============================================================
# 全局实例和便捷函数
# ============================================================

_browser_auth: Optional[BrowserAuth] = None


def get_browser_auth(headless: bool = False) -> BrowserAuth:
    """获取全局浏览器认证管理器"""
    global _browser_auth
    if _browser_auth is None:
        _browser_auth = BrowserAuth(headless=headless)
    return _browser_auth


async def login_platform(platform: str) -> bool:
    """便捷函数: 登录指定平台"""
    auth = get_browser_auth(headless=False)  # 显示浏览器以扫码
    return await auth.login_with_qr(platform)


async def get_platform_cookies(platform: str) -> Optional[str]:
    """便捷函数: 获取平台 Cookie"""
    auth = get_browser_auth()
    return await auth.get_cookies(platform)


# ============================================================
# CLI 入口
# ============================================================

async def main():
    """命令行入口: 交互式登录"""
    import sys
    
    print("\n" + "="*50)
    print("TrueTrend CN - 平台扫码登录工具")
    print("="*50 + "\n")
    
    auth = get_browser_auth(headless=False)
    
    # 显示当前状态
    status = auth.get_login_status()
    print("当前登录状态:")
    for platform, info in status.items():
        icon = "✅" if info["logged_in"] else "❌"
        print(f"  {icon} {platform}: {'已登录' if info['logged_in'] else '未登录'}")
    
    print("\n请选择要登录的平台:")
    print("  1. 微博 (weibo)")
    print("  2. 知乎 (zhihu)")
    print("  3. 全部登录")
    print("  4. 退出")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    try:
        if choice == "1":
            await auth.login_with_qr("weibo")
        elif choice == "2":
            await auth.login_with_qr("zhihu")
        elif choice == "3":
            await auth.login_with_qr("weibo")
            await auth.login_with_qr("zhihu")
        elif choice == "4":
            print("退出")
        else:
            print("无效选项")
    finally:
        await auth.close()


if __name__ == "__main__":
    asyncio.run(main())
