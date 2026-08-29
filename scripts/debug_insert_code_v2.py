#!/usr/bin/env python3
"""调试插入代码：先换行，再点击代码按钮内部元素。"""
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

        # 聚焦正文
        await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          for (const pm of pms) {
            const ph = pm.getAttribute('data-placeholder') || '';
            if (ph.indexOf('标题') < 0) { pm.focus(); return; }
          }
        }""")
        await page.wait_for_timeout(500)

        # 输入普通文本
        await page.keyboard.type("测试代码插入：")
        await page.wait_for_timeout(500)

        # 按回车换行
        print("按回车换行")
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(500)

        # 打印代码按钮的内部结构
        btn_html = await page.evaluate("""() => {
          const btn = document.querySelector('.edui-for-insertcode');
          return btn ? btn.innerHTML.substring(0, 500) : 'NOT_FOUND';
        }""")
        print(f"代码按钮内部HTML: {btn_html}")

        # 方法1：点击代码按钮内部的edui-button-body
        print("\n方法1：点击edui-button-body")
        clicked1 = await page.evaluate("""() => {
          const btn = document.querySelector('.edui-for-insertcode .edui-button-body');
          if (btn) { btn.click(); return 'CLICKED_BODY'; }
          return 'NOT_FOUND_BODY';
        }""")
        print(f"点击结果: {clicked1}")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(SKILL_ROOT / "outputs" / "debug2_01_method1.png"))

        # 检查ProseMirror内容
        pm1 = await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          let target=null;
          for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
          return target ? target.innerHTML.substring(0, 500) : 'NO_PM';
        }""")
        print(f"方法1后ProseMirror: {pm1}")

        # 如果方法1不行，试试方法2：点击坐标(1285, 66)
        if 'code' not in pm1.lower() and 'pre' not in pm1.lower():
            print("\n方法2：用坐标点击代码按钮")
            await page.mouse.click(1285, 66)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=str(SKILL_ROOT / "outputs" / "debug2_02_method2.png"))

            pm2 = await page.evaluate("""() => {
              const pms = document.querySelectorAll('.ProseMirror');
              let target=null;
              for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
              return target ? target.innerHTML.substring(0, 500) : 'NO_PM';
            }""")
            print(f"方法2后ProseMirror: {pm2}")

        # 输入代码
        print("\n输入代码内容")
        await page.keyboard.type("pip install playwright")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SKILL_ROOT / "outputs" / "debug2_03_after_input.png"))

        # 点击任意位置退出
        await page.mouse.click(500, 500)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SKILL_ROOT / "outputs" / "debug2_04_final.png"))

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
