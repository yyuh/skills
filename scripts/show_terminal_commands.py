#!/usr/bin/env python3
"""插入10条终端命令行，用原生代码块，浏览器保持打开。"""
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

COMMANDS = [
    "pip install playwright",
    "npm install -g @vue/cli",
    "git clone https://github.com/obra/superpowers.git",
    "docker run -d -p 8080:80 nginx",
    "npx create-next-app@latest my-app",
    "brew install node",
    "python -m venv venv && source venv/bin/activate",
    "curl -fsSL https://get.docker.com | sh",
    "ssh-keygen -t ed25519 -C \"you@example.com\"",
    "pm2 start app.js --name my-api",
]

async def insert_code_block(page, code_text):
    await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      for (const pm of pms) {
        const ph = pm.getAttribute('data-placeholder') || '';
        if (ph.indexOf('标题') < 0) { pm.focus(); return; }
      }
    }""")
    await page.wait_for_timeout(200)
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
    await page.keyboard.press('Enter')
    await page.wait_for_timeout(300)
    await page.evaluate("""() => {
      const btn = document.querySelector('.edui-for-insertcode .edui-button-body');
      if (btn) btn.click();
    }""")
    await page.wait_for_timeout(1500)
    await page.keyboard.type(code_text)
    await page.wait_for_timeout(500)
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
        await page.keyboard.type("常用终端命令（共10条，全部用原生代码块）：")
        await page.wait_for_timeout(300)

        # 插入10条命令
        for i, cmd in enumerate(COMMANDS):
            print(f"插入第 {i+1} 条: {cmd}")
            await insert_code_block(page, cmd)

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
        print("浏览器保持打开，你可以查看效果。")

        while True:
            await page.wait_for_timeout(60000)

if __name__ == "__main__":
    asyncio.run(main())
