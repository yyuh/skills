#!/usr/bin/env python3
"""调试插入代码的完整流程。"""
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

        # 步骤1：聚焦正文，输入一段普通文本
        print("步骤1：聚焦正文，输入普通文本")
        await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          for (const pm of pms) {
            const ph = pm.getAttribute('data-placeholder') || '';
            if (ph.indexOf('标题') < 0) { pm.focus(); return; }
          }
        }""")
        await page.wait_for_timeout(500)
        await page.keyboard.type("测试代码插入：")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(SKILL_ROOT / "outputs" / "debug_01_text.png"))

        # 步骤2：点击代码按钮
        print("步骤2：点击代码按钮")
        await page.evaluate("""() => {
          const btn = document.querySelector('.edui-for-insertcode');
          if (btn) btn.click();
        }""")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(SKILL_ROOT / "outputs" / "debug_02_after_click.png"))

        # 检查当前焦点元素
        focus_info = await page.evaluate("""() => {
          const el = document.activeElement;
          return {
            tag: el ? el.tagName : 'none',
            cls: el ? (el.className || '').substring(0, 80) : '',
            id: el ? el.id : '',
            html: el ? el.outerHTML.substring(0, 200) : ''
          };
        }""")
        print(f"当前焦点: {focus_info}")

        # 检查ProseMirror里是否有代码块
        pm_info = await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          let target=null;
          for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
          if (!target) return 'NO_PM';
          return {
            html: target.innerHTML.substring(0, 500),
            text: target.innerText.substring(0, 200),
            childCount: target.children.length
          };
        }""")
        print(f"ProseMirror内容: {pm_info}")

        # 步骤3：输入代码
        print("步骤3：输入代码内容")
        await page.keyboard.type("pip install playwright")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SKILL_ROOT / "outputs" / "debug_03_after_input.png"))

        # 步骤4：点击任意位置退出
        print("步骤4：点击任意位置退出")
        await page.mouse.click(500, 500)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SKILL_ROOT / "outputs" / "debug_04_final.png"))

        # 最终检查
        final = await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          let target=null;
          for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
          if (!target) return 'NO_PM';
          const codeBlocks = target.querySelectorAll('pre, code, [class*="code"], [class*="Code"]');
          return {
            textLength: target.innerText.length,
            codeBlocksCount: codeBlocks.length,
            html: target.innerHTML.substring(0, 800),
            text: target.innerText.substring(0, 300)
          };
        }""")
        print(f"\n最终检查: {final}")

        print("\n===== 调试完成，浏览器保持10秒后关闭 =====")
        await page.wait_for_timeout(10000)
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(main())
