#!/usr/bin/env python3
"""打开公众号空白文章页，保持浏览器不关闭，用于学习插入代码模块。"""
import sys
import types
import asyncio
import time
import re
from pathlib import Path

# greenlet 桩
_gmod = types.ModuleType("greenlet")
class _Greenlet:
    def __init__(self, run=None, parent=None):
        self.run = run; self.parent = parent
    def switch(self, *a, **k): return None
    def throw(self, *a, **k): return None
    def __bool__(self): return True
_gmod.greenlet = _Greenlet
_gmod.settrace = lambda *a, **k: None
sys.modules["greenlet"] = _gmod

from playwright.async_api import async_playwright

SKILL_ROOT = Path(__file__).resolve().parent.parent

async def main():
    profile_dir = SKILL_ROOT / ".gzh-profile-dir"
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

        # 获取token并打开空白文章
        token = None
        m = re.search(r"token=(\d+)", page.url or "")
        if m: token = m.group(1)
        if not token:
            for pg in ctx.pages:
                m = re.search(r"token=(\d+)", pg.url or "")
                if m: token = m.group(1); break

        if token:
            editor_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg"
                          f"?t=media/appmsg_edit_v2&action=edit&isNew=1"
                          f"&type=10&lang=zh_CN&token={token}")
            print(f"打开空白文章: {editor_url}")
            await page.goto(editor_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)
        else:
            print("未获取到token，请手动点击新建文章")

        print("\n===== 浏览器已打开空白文章页 =====")
        print("请在浏览器中操作，教我插入代码模块")
        print("学习完成后，按 Ctrl+C 结束脚本")

        # 保持浏览器打开
        while True:
            await page.wait_for_timeout(5000)
            # 每5秒截图一次，方便记录操作
            try:
                await page.screenshot(path=str(SKILL_ROOT / "outputs" / "learn_code.png"), full_page=False)
            except Exception:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n脚本结束")
