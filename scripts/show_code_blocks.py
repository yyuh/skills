#!/usr/bin/env python3
"""插入10个网址代码块，浏览器保持打开不关闭。"""
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

async def insert_code_block(page, code_text):
    # 确保焦点在正文
    await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      for (const pm of pms) {
        const ph = pm.getAttribute('data-placeholder') || '';
        if (ph.indexOf('标题') < 0) { pm.focus(); return; }
      }
    }""")
    await page.wait_for_timeout(200)
    # 光标移到正文末尾
    await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      let target=null;
      for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
      if (target) {
        target.focus();
        const range = document.createRange();
        range.selectNodeContents(target);
        range.collapse(false);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
      }
    }""")
    await page.wait_for_timeout(200)
    # 按回车换行
    await page.keyboard.press('Enter')
    await page.wait_for_timeout(300)
    # 点击代码按钮
    await page.evaluate("""() => {
      const btn = document.querySelector('.edui-for-insertcode .edui-button-body');
      if (btn) btn.click();
    }""")
    await page.wait_for_timeout(1500)
    # 输入代码
    await page.keyboard.type(code_text)
    await page.wait_for_timeout(500)
    # 光标移到代码块后面
    await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      let target=null;
      for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
      if (target) {
        const codeBlocks = target.querySelectorAll('.code-snippet');
        if (codeBlocks.length > 0) {
          const lastBlock = codeBlocks[codeBlocks.length - 1];
          let next = lastBlock.nextElementSibling;
          if (next) {
            const range = document.createRange();
            range.selectNodeContents(next);
            range.collapse(true);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            next.focus();
          }
        }
      }
    }""")
    await page.wait_for_timeout(300)

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

        # 处理原创声明对话框
        await page.evaluate("""() => {
          const radios = document.querySelectorAll('input[type="radio"]');
          for (const r of radios) {
            if (r.value === '0' || r.name === 'copyright_type') { r.click(); break; }
          }
        }""")
        await page.wait_for_timeout(500)
        await page.evaluate("""() => {
          const btns = document.querySelectorAll('a.btn, button');
          for (const b of btns) {
            if ((b.innerText||'').indexOf('确定') >= 0) { b.click(); break; }
          }
        }""")
        await page.wait_for_timeout(1000)

        # 聚焦正文，输入开头
        await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          for (const pm of pms) {
            const ph = pm.getAttribute('data-placeholder') || '';
            if (ph.indexOf('标题') < 0) { pm.focus(); return; }
          }
        }""")
        await page.wait_for_timeout(500)
        await page.keyboard.type("参考链接（共10个，全部用原生代码块）：")
        await page.wait_for_timeout(300)

        # 插入10个网址
        for i, url in enumerate(URLS):
            print(f"插入第 {i+1} 个: {url}")
            await insert_code_block(page, url)

        # 检查结果
        result = await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          let target=null;
          for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
          if (!target) return 'NO_PM';
          const codeBlocks = target.querySelectorAll('.code-snippet');
          return { codeBlocksCount: codeBlocks.length, textLength: target.innerText.length };
        }""")
        print(f"\n完成！代码块数量={result['codeBlocksCount']}")
        print("浏览器保持打开，你可以查看效果。按Ctrl+C结束。")

        # 保持浏览器打开
        while True:
            await page.wait_for_timeout(60000)

if __name__ == "__main__":
    asyncio.run(main())
