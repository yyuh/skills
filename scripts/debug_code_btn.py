#!/usr/bin/env python3
"""调试：找到公众号编辑器的代码按钮。"""
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
        await page.wait_for_timeout(1000)

        # 打印工具栏所有按钮信息
        info = await page.evaluate("""() => {
          const results = [];
          // 找所有可能的工具栏按钮
          const all = document.querySelectorAll('[id^="edui"], .edui-btn, [class*="toolbar"] *, [class*="edui"] *');
          const seen = new Set();
          for (const el of all) {
            if (el.children.length > 0) continue;
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;
            if (rect.y > 150) continue; // 只看工具栏区域
            const id = el.id || '';
            const cls = el.className || '';
            const title = el.getAttribute('title') || '';
            const text = (el.innerText || '').trim();
            const dataCmd = el.getAttribute('data-command') || '';
            const key = id + '|' + cls + '|' + title + '|' + text;
            if (seen.has(key)) continue;
            seen.add(key);
            results.push({
              tag: el.tagName,
              id: id.substring(0, 30),
              cls: (typeof cls === 'string' ? cls.substring(0, 50) : ''),
              title: title,
              text: text,
              dataCmd: dataCmd,
              x: Math.round(rect.x),
              y: Math.round(rect.y),
              w: Math.round(rect.width),
              h: Math.round(rect.height)
            });
          }
          return results;
        }""")

        print("=== 工具栏按钮列表 ===")
        for i, b in enumerate(info):
            print(f"{i:2d}. {b['tag']:6s} id={b['id']:30s} cls={b['cls']:50s} title={b['title']:15s} text={b['text']:10s} cmd={b['dataCmd']:15s} pos=({b['x']},{b['y']}) size={b['w']}x{b['h']}")

        # 特别找代码相关的
        print("\n=== 代码相关元素 ===")
        code_info = await page.evaluate("""() => {
          const results = [];
          const all = document.querySelectorAll('*');
          for (const el of all) {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;
            if (rect.y > 150) continue;
            const html = el.outerHTML.substring(0, 200);
            if (html.indexOf('code') >= 0 || html.indexOf('Code') >= 0 || html.indexOf('</>') >= 0) {
              results.push({
                tag: el.tagName,
                id: (el.id || '').substring(0, 30),
                cls: (el.className || '').substring(0, 80),
                html: html,
                x: Math.round(rect.x),
                y: Math.round(rect.y)
              });
            }
          }
          return results;
        }""")
        for i, b in enumerate(code_info):
            print(f"{i}. {b['tag']} id={b['id']} cls={b['cls']} pos=({b['x']},{b['y']})")
            print(f"   html={b['html']}")

        await page.wait_for_timeout(5000)
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(main())
