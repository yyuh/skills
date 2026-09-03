#!/usr/bin/env python3
"""给已有公众号草稿添加公众号名片并置底。

用法：
  python add_card_to_draft.py --appmsgid 100000686 --card-name "硅基研究员"
"""
import sys
import types
import asyncio
import time
import re
import argparse
from pathlib import Path

# ---- greenlet 桩（绕开 WDAC 拦 DLL）----
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
PROGRESS_FILE = str(SKILL_ROOT / "outputs" / "add_card_progress.log")

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n"); f.flush()
    except Exception:
        pass

async def shot(page, name):
    path = str(SKILL_ROOT / "outputs" / f"addcard_{name}.png")
    try:
        await page.screenshot(path=path, full_page=False)
        log(f"截图→{name}")
    except Exception as e:
        log(f"截图失败:{e}")

async def is_logged_in(page):
    try:
        url = page.url or ""
    except Exception:
        url = ""
    if "cgi-bin" in url and "connect" not in url and "qrconnect" not in url:
        return True
    try:
        txt = await page.inner_text("body", timeout=5000)
    except Exception:
        return False
    has_console = ("新的创作" in txt) or (
        ("首页" in txt) and ("内容管理" in txt)
    )
    has_login_page = ("微信扫一扫" in txt) or ("使用账号登录" in txt) or ("扫码登录" in txt)
    return has_console and not has_login_page

async def close_original_dialog(page):
    has = await page.evaluate("""() => {
      const cands = document.querySelectorAll('.weui-dialog, [role="dialog"], [class*="dialog"], [class*="Dialog"], [class*="modal"], [class*="Modal"]');
      for (const d of cands) {
        if (d.offsetParent && d.innerText && d.innerText.indexOf('原创') >= 0) return true;
      }
      return false;
    }""")
    if not has:
        log("无原创对话框，跳过")
        return
    log("处理原创对话框...")
    await page.evaluate("""() => {
      const cands = document.querySelectorAll('.weui-dialog, [role="dialog"], [class*="dialog"], [class*="Dialog"]');
      for (const d of cands) {
        if (!d.offsetParent || !d.innerText || d.innerText.indexOf('原创') < 0) continue;
        // 选「无需声明」单选
        const radios = d.querySelectorAll('input[type="radio"], .weui-check, [class*="radio"]');
        for (const r of radios) {
          const label = r.closest('label') || r.parentElement;
          if (label && label.innerText && label.innerText.indexOf('无需') >= 0) {
            r.click(); r.checked = true; break;
          }
        }
        // 点「确定」
        const btns = d.querySelectorAll('button, a');
        for (const b of btns) {
          const t = (b.innerText||'').trim();
          if (t === '确定' || t === '确认') { b.click(); return; }
        }
      }
    }""")
    await page.wait_for_timeout(1500)
    log("原创对话框已处理")

async def insert_profile_card(page, card_name):
    """插入公众号名片并置底"""
    log(f"插入名片: {card_name}...")
    await close_original_dialog(page)
    # 点击「更多」→「账号名片」
    clicked = await page.evaluate("""() => {
      const cands = Array.from(document.querySelectorAll('button, [role=button], div, span, a'));
      for (const el of cands) {
        const t = (el.innerText || '').trim();
        if (t === '账号名片') { el.click(); return 'CLICKED'; }
      }
      return 'NOT_FOUND';
    }""")
    log(f"点击账号名片: {clicked}")
    await page.wait_for_timeout(2000)
    # 输入账号名称
    await page.evaluate(f"""() => {{
      const ins = Array.from(document.querySelectorAll('input'));
      for (const i of ins) {{
        const ph = i.getAttribute('placeholder')||'';
        if (ph.indexOf('账号名称') >= 0 || ph.indexOf('账号ID') >= 0) {{
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
          setter.call(i, '{card_name}');
          i.dispatchEvent(new Event('input',{{bubbles:true}}));
          i.dispatchEvent(new Event('change',{{bubbles:true}}));
          i.focus();
          return 'INPUT';
        }}
      }}
      return 'NO_INPUT';
    }}""")
    await page.wait_for_timeout(1500)
    await page.keyboard.press('Enter')
    await page.wait_for_timeout(3000)
    # 先点「最近使用」触发搜索结果渲染
    await page.evaluate("""() => {
      const items = document.querySelectorAll('li.profile_history_item, [class*="history_item"], [class*="recent"]');
      for (const it of items) { if (it.offsetParent) { it.click(); return 'CLICKED_HISTORY'; } }
      return 'NO_HISTORY';
    }""")
    await page.wait_for_timeout(2000)
    # 点击搜索结果卡片（选简介含「一个AI研究员的日常记录」的）
    await page.evaluate(f"""() => {{
      const cards = Array.from(document.querySelectorAll('.wx_profile_card, [class*="profile_card"], [class*="account_card"]'));
      for (const c of cards) {{
        if (c.innerText.indexOf('{card_name}') >= 0 && c.innerText.indexOf('AI研究员') >= 0) {{ c.click(); return 'CARD'; }}
      }}
      for (const c of cards) {{
        if (c.innerText.indexOf('{card_name}') >= 0) {{ c.click(); return 'CARD_FALLBACK'; }}
      }}
      return 'NOT_FOUND';
    }}""")
    await page.wait_for_timeout(1500)
    # 点击插入按钮
    await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) { if ((b.innerText||'').trim() === '插入') { b.click(); return 'INSERTED'; } }
      return 'NO_BTN';
    }""")
    await page.wait_for_timeout(2000)
    # 名片置底
    await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      let target=null;
      for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
      if (target) {
        const wrp = target.querySelector('section.mp_profile_iframe_wrp') || target.querySelector('.mp_profile_iframe_wrp');
        if (wrp) target.appendChild(wrp);
      }
    }""")
    await page.wait_for_timeout(1000)
    log("名片已插入并置底")

async def clear_summary(page):
    """清空摘要"""
    r = await page.evaluate("""() => {
      const tas = document.querySelectorAll('textarea');
      for (const ta of tas) {
        const ph = ta.getAttribute('placeholder') || '';
        if (ph.indexOf('摘要') >= 0 || ph.indexOf('选填') >= 0 || ph.indexOf('转发') >= 0) {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
          setter.call(ta, '');
          ta.dispatchEvent(new Event('input', {bubbles:true}));
          ta.dispatchEvent(new Event('change', {bubbles:true}));
          return 'CLEARED';
        }
      }
      return 'NOT_FOUND';
    }""")
    log(f"摘要清空: {r}")

async def save_draft(page):
    """保存草稿"""
    log("保存草稿...")
    await close_original_dialog(page)
    await clear_summary(page)
    await page.wait_for_timeout(1000)
    await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) {
        if ((b.innerText || '').indexOf('保存为草稿') >= 0) { b.click(); return; }
      }
    }""")
    await page.wait_for_timeout(3000)
    # 处理确认对话框
    await page.evaluate("""() => {
      const cands = document.querySelectorAll('.weui-dialog, [role="dialog"]');
      for (const d of cands) {
        if (!d.offsetParent) continue;
        const btns = d.querySelectorAll('button, a');
        for (const b of btns) {
          const t = (b.innerText||'').trim();
          if (t === '确定' || t === '确认') { b.click(); return; }
        }
      }
    }""")
    await page.wait_for_timeout(3000)
    return page.url

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--appmsgid", required=True, help="草稿的appmsgid")
    ap.add_argument("--card-name", default="硅基研究员")
    ap.add_argument("--profile-dir", default=".gzh-profile-dir")
    ap.add_argument("--wait-scan", type=int, default=600)
    args = ap.parse_args()

    profile_dir = Path(args.profile_dir)
    if not profile_dir.is_absolute():
        profile_dir = SKILL_ROOT / profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)

    try:
        Path(PROGRESS_FILE).write_text("", encoding="utf-8")
    except Exception:
        pass

    log("==== 启动补名片脚本 ====")

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)

        if await is_logged_in(page):
            log("已登录")
        else:
            log("未登录，等待扫码...")
            ok = False
            for i in range(args.wait_scan // 2):
                await page.wait_for_timeout(2000)
                for pg in ctx.pages:
                    if await is_logged_in(pg):
                        page = pg; ok = True; break
                if ok: break
            if not ok:
                log("ERR: 扫码超时")
                await ctx.close(); sys.exit(1)

        # 获取token
        token = None
        m = re.search(r"token=(\d+)", page.url or "")
        if m: token = m.group(1)
        if not token:
            for pg in ctx.pages:
                m = re.search(r"token=(\d+)", pg.url or "")
                if m: token = m.group(1); break
        if not token:
            log("ERR: 无法获取token")
            await ctx.close(); sys.exit(1)

        # 打开指定草稿
        edit_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg"
                    f"?t=media/appmsg_edit&action=edit&type=77"
                    f"&appmsgid={args.appmsgid}&token={token}&lang=zh_CN")
        log(f"打开草稿: {edit_url}")
        await page.goto(edit_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(8000)
        await shot(page, "00_draft_opened")

        await close_original_dialog(page)

        # 检查是否已有名片
        has_card = await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          for (const pm of pms) {
            if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')>=0) continue;
            if (pm.querySelector('.mp_profile_iframe_wrp, [class*="profile_iframe"]')) return true;
          }
          return false;
        }""")
        if has_card:
            log("草稿已有名片，跳过插入")
        else:
            await insert_profile_card(page, args.card_name)

        await shot(page, "05_before_save")

        # 保存
        url = await save_draft(page)
        log(f"保存URL: {url}")
        await shot(page, "06_final")
        log("DONE: 名片已添加并保存")

if __name__ == "__main__":
    asyncio.run(main())
