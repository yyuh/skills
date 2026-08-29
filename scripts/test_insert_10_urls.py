#!/usr/bin/env python3
"""测试插入10个网址，每个用原生代码模块。"""
import sys
import types
import asyncio
import time
import re
from pathlib import Path

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

# 10个测试网址
URLS = [
    "https://github.com/obra/superpowers",
    "https://github.com/trending?since=daily",
    "https://mp.weixin.qq.com",
    "https://www.python.org",
    "https://playwright.dev",
    "https://openai.com",
    "https://github.com/features/copilot",
    "https://huggingface.co",
    "https://arxiv.org",
    "https://www.npmjs.com",
]

async def click_code_btn(page):
    """点击工具栏代码按钮"""
    return await page.evaluate("""() => {
      // 方法1：找title含"代码"的按钮
      const btns = document.querySelectorAll('[id^="edui"], .edui-btn, [class*="toolbar"] button, [class*="toolbar"] [role=button], .edui-for-code');
      for (const b of btns) {
        const title = b.getAttribute('title') || b.getAttribute('aria-label') || '';
        if (title.indexOf('代码') >= 0 || title.indexOf('code') >= 0) {
          b.click();
          return {method: 'title', title: title};
        }
      }
      // 方法2：找包含 </> 文本的元素
      const all = document.querySelectorAll('*');
      for (const el of all) {
        if (el.children.length === 0 && (el.innerText || '').trim() === '</>') {
          el.click();
          return {method: 'text'};
        }
      }
      // 方法3：找code相关的class
      const codeEls = document.querySelectorAll('[class*="code"], [class*="Code"], [data-command*="code"]');
      for (const el of codeEls) {
        if (el.offsetParent) { el.click(); return {method: 'class'}; }
      }
      return {method: 'not_found'};
    }""")

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
            await page.goto(editor_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)

        await page.screenshot(path=str(SKILL_ROOT / "outputs" / "urls_01_blank.png"))
        print("已打开空白文章页")

        # 聚焦正文
        await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          for (const pm of pms) {
            const ph = pm.getAttribute('data-placeholder') || '';
            if (ph.indexOf('标题') < 0) { pm.focus(); return; }
          }
        }""")
        await page.wait_for_timeout(1000)

        # 插入10个网址
        for i, url in enumerate(URLS):
            print(f"\n--- 插入第 {i+1} 个网址: {url} ---")

            # 点击代码按钮
            r = await click_code_btn(page)
            print(f"  点击代码按钮: {r}")
            await page.wait_for_timeout(1500)

            # 输入网址
            await page.keyboard.type(url)
            await page.wait_for_timeout(500)

            # 点击任意位置退出编辑
            await page.mouse.click(500, 500 + i * 30)
            await page.wait_for_timeout(1000)

            # 按回车换行，准备下一个
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(500)

            if i == 0:
                await page.screenshot(path=str(SKILL_ROOT / "outputs" / "urls_02_first.png"))
            if i == 4:
                await page.screenshot(path=str(SKILL_ROOT / "outputs" / "urls_03_mid.png"))

        await page.screenshot(path=str(SKILL_ROOT / "outputs" / "urls_04_final.png"))

        # 检查结果
        result = await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          let target=null;
          for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
          if (!target) return 'NO_PM';
          const codeBlocks = target.querySelectorAll('pre, code, [class*="code"], [class*="Code"]');
          return {
            textLength: target.innerText.length,
            codeBlocksCount: codeBlocks.length,
            text: target.innerText.substring(0, 300)
          };
        }""")
        print(f"\n最终检查: {result}")

        print("\n===== 测试完成，浏览器保持15秒后关闭 =====")
        await page.wait_for_timeout(15000)
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(main())
