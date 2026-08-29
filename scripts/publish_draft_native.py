#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公众号草稿存稿（异步 Playwright 版）—— 扩展：
  ① 公众号名片（硅基研究员）插入到正文【最前】；
  ② 代码块用编辑器原生「插入代码」（找不到则回退为样式代码块）；
  ③ 支持一次串行存多套主题（--theme 指定单套或 all）。

依赖：系统 Python 3.14 + playwright（greenlet 桩绕过 WDAC 拦 DLL）。
用法：
  python publish_draft_native.py --theme moyu-green
  python publish_draft_native.py --theme all --wait-scan 1800
"""
import sys
import types
import asyncio
import base64
import os
import re
import json
import time
from pathlib import Path

# ---- greenlet 桩（异步 API 不需要它，但 import 前必须桩掉以免被 WDAC 拦）----
_gmod = types.ModuleType("greenlet")


class _Greenlet:
    def __init__(self, run=None, parent=None):
        self.run = run
        self.parent = parent

    def switch(self, *a, **k):
        return None

    def throw(self, *a, **k):
        return None

    def __bool__(self):
        return True


_gmod.greenlet = _Greenlet
_gmod.settrace = lambda *a, **k: None
sys.modules["greenlet"] = _gmod

from playwright.async_api import async_playwright  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
OUT = SKILL_ROOT / "outputs"
PROGRESS_FILE = str(OUT / "publish_native.log")

THEME_IDS = ["moyu-green", "swiss-minimal", "bauhaus", "japanese-mag", "neo-brutalism"]


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
    except Exception:
        pass


async def shot(page, name):
    try:
        await page.screenshot(path=str(OUT / f"step_{name}.png"), full_page=False)
        log(f"截图 → step_{name}.png")
    except Exception as e:
        log(f"截图 {name} 失败: {e}")


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
    has_qr = ("扫码" in txt) or ("扫描二维码" in txt) or ("请使用微信" in txt)
    has_console = ("草稿箱" in txt) or ("图文素材" in txt) or ("内容管理" in txt) \
        or ("公众号" in txt and "登录" not in txt)
    return has_console and not has_qr


async def inject_html(page, html):
    b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
    return await page.evaluate("""(b64) => {
      const html = decodeURIComponent(escape(atob(b64)));
      const pms = document.querySelectorAll('.ProseMirror');
      let target = null;
      for (const pm of pms) {
        const ph = pm.getAttribute('data-placeholder') || '';
        if (ph.indexOf('标题') < 0) { target = pm; break; }
      }
      if (!target) return 'NO-PM';
      target.focus();
      const range = document.createRange();
      range.selectNodeContents(target);
      range.collapse(false);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      const dt = new DataTransfer();
      dt.setData('text/html', html);
      dt.setData('text/plain', '');
      const evt = document.createEvent('Event');
      evt.initEvent('paste', true, true);
      Object.defineProperty(evt, 'clipboardData', { get: () => dt });
      target.dispatchEvent(evt);
      return 'LEN:' + target.innerText.length;
    }""", b64)


async def fill_title(page, title):
    b64 = base64.b64encode(title.encode("utf-8")).decode("ascii")
    return await page.evaluate("""(b64) => {
      const val = decodeURIComponent(escape(atob(b64)));
      const tas = document.querySelectorAll('textarea');
      let target = null;
      for (const ta of tas) {
        if ((ta.placeholder || '').indexOf('标题') >= 0) { target = ta; break; }
      }
      if (!target) return 'NO-TA';
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(target, val);
      target.dispatchEvent(new Event('input', {bubbles:true}));
      target.dispatchEvent(new Event('change', {bubbles:true}));
      return target.value;
    }""", b64)


async def save_draft(page):
    await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) {
        if ((b.innerText || '').indexOf('保存为草稿') >= 0) { b.click(); return; }
      }
    }""")
    await page.wait_for_timeout(1500)
    handled = await page.evaluate("""() => {
      const cands = document.querySelectorAll(
        '.weui-dialog, [role="dialog"], .dialog, [class*="dialog"], [class*="modal"], [class*="Dialog"], [class*="Modal"]'
      );
      for (const d of cands) {
        if (!d.offsetParent) continue;
        const btns = d.querySelectorAll('button, a');
        for (const b of btns) {
          const t = (b.innerText || '').trim();
          if (t === '确定' || t === '确认' || t === 'OK' || t.indexOf('仍要保存') >= 0) {
            b.click();
            return t;
          }
        }
      }
      return null;
    }""")
    log(f"保存确认: {handled}")
    await page.wait_for_timeout(3000)
    return page.url


# ---------------------------------------------------------------------------
# ① 公众号名片插入到最前
# ---------------------------------------------------------------------------
async def insert_account_card_top(page):
    # 首选：顶部菜单栏直接点「账号名片」（精确匹配）
    r = await page.evaluate("""() => {
      const cands = Array.from(document.querySelectorAll('button, [role=button], div, span, a'));
      let exact = null, contains = null;
      for (const el of cands) {
        const t = (el.innerText || '').trim();
        if (t === '账号名片') { exact = el; break; }
        if (t.indexOf('账号名片') >= 0 || t.indexOf('公众号名片') >= 0) contains = el;
      }
      const target = exact || contains;
      if (target) { target.click(); return 'CLICKED_DIRECT:' + (exact ? 'EXACT' : 'CONTAINS'); }
      return 'NO_DIRECT';
    }""")
    log(f"账号名片-直接: {r}")
    await page.wait_for_timeout(1200)
    if r.startswith('NO'):
        r = await page.evaluate("""() => {
          const btns = Array.from(document.querySelectorAll('button, [role=button], div'));
          for (const b of btns) {
            const t = (b.innerText||'').trim();
            if (t === '更多' || t.indexOf('更多') >= 0) { b.click(); return 'CLICKED_MORE'; }
          }
          return 'NO_MORE';
        }""")
        log(f"账号名片-更多: {r}")
        await page.wait_for_timeout(1200)
        r = await page.evaluate("""() => {
          const cands = Array.from(document.querySelectorAll('.tpl_dropdown_menu_item, li, a, div, span'));
          let exact = null, contains = null;
          for (const it of cands) {
            const t = (it.innerText||'').trim();
            if (t === '账号名片') { exact = it; break; }
            if (t.indexOf('账号名片') >= 0 || t.indexOf('公众号名片') >= 0) contains = it;
          }
          const target = exact || contains;
          if (target) { target.click(); return 'CLICKED_MENU:' + (exact ? 'EXACT' : 'CONTAINS'); }
          return 'NO_MENU';
        }""")
    log(f"账号名片-菜单: {r}")
    await page.wait_for_timeout(1500)
    r = await page.evaluate("""() => {
      const ins = Array.from(document.querySelectorAll('input'));
      for (const i of ins) {
        const ph = i.getAttribute('placeholder')||'';
        if (ph.indexOf('账号名称') >= 0 || ph.indexOf('账号ID') >= 0 || ph.indexOf('名称') >= 0) {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
          setter.call(i, '硅基研究员');
          i.dispatchEvent(new Event('input',{bubbles:true}));
          i.dispatchEvent(new Event('change',{bubbles:true}));
          return 'FILL:'+ph;
        }
      }
      return 'NO_INPUT';
    }""")
    log(f"账号名片-搜索框: {r}")
    await page.wait_for_timeout(2500)
    # 先点「最近使用」触发渲染
    r = await page.evaluate("""() => {
      const items = Array.from(document.querySelectorAll('li.profile_history_item'));
      if (items.length) { items[0].click(); return 'CLICKED_HISTORY'; }
      return 'NO_HISTORY';
    }""")
    log(f"账号名片-最近使用: {r}")
    await page.wait_for_timeout(2000)
    r = await page.evaluate("""() => {
      const cards = Array.from(document.querySelectorAll('.wx_profile_card'));
      for (const c of cards) {
        const t = c.innerText||'';
        if (t.indexOf('硅基研究员') >= 0 && t.indexOf('一个AI研究员的日常记录') >= 0) { c.click(); return 'SELECTED'; }
      }
      for (const c of cards) { if (c.innerText.indexOf('硅基研究员') >= 0) { c.click(); return 'SELECTED_FALLBACK'; } }
      return 'NO_CARD';
    }""")
    log(f"账号名片-选卡: {r}")
    await page.wait_for_timeout(1500)
    r = await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) { if ((b.innerText||'').trim() === '插入') { b.click(); return 'INSERT'; } }
      return 'NO_INSERT';
    }""")
    log(f"账号名片-插入: {r}")
    await page.wait_for_timeout(1500)
    # 确保位于最前
    r = await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      let target=null;
      for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
      if (!target) return 'NO_PM';
      const wrp = target.querySelector('section.mp_profile_iframe_wrp') || target.querySelector('.mp_profile_iframe_wrp');
      if (wrp && target.firstChild && target.firstChild !== wrp) {
        target.insertBefore(wrp, target.firstChild);
        return 'MOVED_TOP';
      }
      return 'ALREADY_TOP_OR_NONE';
    }""")
    log(f"账号名片-置顶: {r}")
    return r


# ---------------------------------------------------------------------------
# ② 原生插入代码（找不到按钮则回退样式代码块）
# ---------------------------------------------------------------------------
def styled_code_block(lang, code):
    lines = code.split("\n")
    body = ""
    for ln in lines:
        indent = len(ln) - len(ln.lstrip(" "))
        vis = "　" * (indent // 2) + ln.lstrip(" ")
        body += (f'<p style="margin:0;font-family:\'SF Mono\',Consolas,Monaco,monospace;'
                 f'font-size:13px;line-height:1.6;color:#E2E8F0;"><span leaf="">{vis}</span></p>')
    return (
        '<section style="margin:0 0 20px;border-radius:8px;overflow:hidden;background:#1E293B;box-shadow:0 4px 16px -8px rgba(15,23,42,0.4);">'
        '<section style="display:flex;align-items:center;padding:9px 14px;background:#0F172A;">'
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#FF5F56;margin-right:7px;font-size:0;line-height:0;overflow:hidden;"><span leaf=""><br></span></span>'
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#FFBD2E;margin-right:7px;font-size:0;line-height:0;overflow:hidden;"><span leaf=""><br></span></span>'
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#27C93F;font-size:0;line-height:0;overflow:hidden;"><span leaf=""><br></span></span>'
        f'<span style="margin-left:12px;font-size:12px;color:#64748B;font-family:Consolas,Monaco,monospace;letter-spacing:1px;"><span leaf="">{lang}</span></span>'
        f'</section><section style="padding:11px 14px;">{body}</section></section>'
    )


async def insert_native_code(page, lang, code):
    found = await page.evaluate("""() => {
      const cands = Array.from(document.querySelectorAll('button, [role=button], span, a, div[class*=toolbar] *'));
      for (const el of cands) {
        const t = (el.innerText||'').trim();
        const al = (el.getAttribute('aria-label')||'') + (el.getAttribute('title')||'');
        if (t.indexOf('<') >= 0 && t.indexOf('>') >= 0) return 'BTN:'+t;
        if (al.indexOf('代码') >= 0 || al.toLowerCase().indexOf('code') >= 0) return 'BTN:'+al;
      }
      return null;
    }""")
    if not found:
        html = styled_code_block(lang, code)
        inj = await inject_html(page, html)
        log(f"原生代码-未找到按钮，回退样式代码块: {inj}")
        return 'FALLBACK_STYLED'
    await page.evaluate("""() => {
      const cands = Array.from(document.querySelectorAll('button, [role=button], span, a, div[class*=toolbar] *'));
      for (const el of cands) {
        const t = (el.innerText||'').trim();
        const al = (el.getAttribute('aria-label')||'') + (el.getAttribute('title')||'');
        if (t.indexOf('<') >= 0 && t.indexOf('>') >= 0) { el.click(); return; }
        if (al.indexOf('代码') >= 0 || al.toLowerCase().indexOf('code') >= 0) { el.click(); return; }
      }
    }""")
    log(f"原生代码-点击按钮: {found}")
    await page.wait_for_timeout(1500)
    modal = await page.evaluate("""() => {
      const tas = Array.from(document.querySelectorAll('textarea'));
      for (const ta of tas) { if (!(ta.getAttribute('placeholder')||'').indexOf('标题') >= 0) return 'TA'; }
      const dlg = document.querySelector('.weui-dialog, [role=dialog], [class*=Dialog]');
      if (dlg) return 'DIALOG';
      return null;
    }""")
    if modal:
        await page.evaluate("""(code) => {
          const tas = Array.from(document.querySelectorAll('textarea'));
          let ta=null; for (const t of tas){ if (!(t.getAttribute('placeholder')||'').indexOf('标题') >= 0){ta=t;break;} }
          if (ta){ const setter=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set; setter.call(ta, code); ta.dispatchEvent(new Event('input',{bubbles:true})); ta.dispatchEvent(new Event('change',{bubbles:true})); }
        }""", code)
        await page.wait_for_timeout(500)
        await page.evaluate("""() => {
          const btns=Array.from(document.querySelectorAll('button'));
          for (const b of btns){ const t=(b.innerText||'').trim(); if (t==='确定'||t==='确认'||t==='保存'){ b.click(); return; } }
        }""")
        await page.wait_for_timeout(1000)
        return 'NATIVE_MODAL'
    else:
        try:
            await page.keyboard.insertText(code)
        except Exception as e:
            log(f"原生代码-insertText 失败: {e}")
        await page.wait_for_timeout(500)
        await page.evaluate("""() => {
          const pms=document.querySelectorAll('.ProseMirror'); let target=null;
          for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
          if (target){ target.focus(); const r=document.createRange(); r.selectNodeContents(target); r.collapse(false); const s=window.getSelection(); s.removeAllRanges(); s.addRange(r); }
        }""")
        return 'NATIVE_INLINE'


# ---------------------------------------------------------------------------
# 打开编辑器（4 级兜底，沿用原 async 脚本）
# ---------------------------------------------------------------------------
async def open_editor(ctx, page):
    await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(2000)
    await shot(page, "home_for_create")

    editor_page = None
    try:
        async with ctx.expect_page(timeout=15000) as np_info:
            clicked = await page.evaluate("""() => {
              const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
              let target = null; let node;
              while (node = walker.nextNode()) {
                if (node.textContent.trim() !== '文章') continue;
                let p = node.parentElement; let inNew = false;
                while (p) { if ((p.textContent || '').includes('新的创作')) { inNew = true; break; } p = p.parentElement; }
                if (inNew) { target = node.parentElement; break; }
              }
              if (!target) return 'NOT_FOUND';
              let el = target;
              while (el && el !== document.body) {
                const cs = window.getComputedStyle(el);
                if (el.tagName === 'A' || el.tagName === 'BUTTON' || el.onclick ||
                    cs.cursor === 'pointer' || el.getAttribute('role') === 'button' ||
                    el.getAttribute('role') === 'link') { el.click(); return 'CLICKED_ANCESTOR'; }
                el = el.parentElement;
              }
              target.click(); return 'CLICKED_TARGET';
            }""")
            log(f"点击文章: {clicked}")
        np = await np_info.value
        try:
            await np.wait_for_load_state("domcontentloaded", timeout=60000)
        except Exception:
            pass
        try:
            await np.wait_for_selector(".ProseMirror", timeout=25000)
            editor_page = np
            log(f"新标签页编辑器: {np.url}")
        except Exception:
            log(f"新标签页无 ProseMirror: {np.url}")
    except Exception as e:
        log(f"点击未触发新标签页: {e}")

    if not editor_page:
        for i, pg in enumerate(ctx.pages):
            try:
                pms = await pg.query_selector_all(".ProseMirror")
                if pms:
                    editor_page = pg
                    log(f"标签页 {i} 找到编辑器")
                    break
            except Exception:
                continue

    if not editor_page:
        token = None
        for pg in ctx.pages:
            m = re.search(r"token=(\d+)", pg.url or "")
            if m:
                token = m.group(1)
                break
        if token:
            draft_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg"
                         f"?action=list&type=10&lang=zh_CN&token={token}")
            try:
                await page.goto(draft_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)
                new_btn = await page.evaluate("""() => {
                  const cands = document.querySelectorAll('a, button, div[role="button"]');
                  for (const el of cands) {
                    const t = (el.textContent || '').trim();
                    if (t === '新建图文' || t === '新建' || t.includes('新建图文')) { el.click(); return 'CLICKED'; }
                  }
                  return 'NO_NEW';
                }""")
                log(f"草稿箱新建: {new_btn}")
                try:
                    async with ctx.expect_page(timeout=15000) as np_info:
                        await asyncio.sleep(0.2)
                    np = await np_info.value
                    try:
                        await np.wait_for_load_state("domcontentloaded", timeout=60000)
                    except Exception:
                        pass
                    try:
                        await np.wait_for_selector(".ProseMirror", timeout=25000)
                        editor_page = np
                    except Exception:
                        pass
                except Exception as e:
                    log(f"草稿箱未触发新标签: {e}")
            except Exception as e:
                log(f"草稿箱失败: {e}")

    if not editor_page:
        token = None
        for pg in ctx.pages:
            m = re.search(r"token=(\d+)", pg.url or "")
            if m:
                token = m.group(1)
                break
        if token:
            editor_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg"
                          f"?t=media/appmsg_edit_v2&action=edit&isNew=1&type=10&lang=zh_CN&token={token}")
            try:
                async with ctx.expect_page(timeout=20000) as np_info:
                    await page.goto(editor_url, wait_until="domcontentloaded", timeout=60000)
                np = await np_info.value
                try:
                    await np.wait_for_load_state("domcontentloaded", timeout=60000)
                except Exception:
                    pass
                try:
                    await np.wait_for_selector(".ProseMirror", timeout=25000)
                    editor_page = np
                except Exception:
                    pass
            except Exception as e:
                log(f"直跳失败: {e}")

    if not editor_page:
        return None
    try:
        await editor_page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass
    await editor_page.wait_for_timeout(2000)
    await shot(editor_page, "editor")
    return editor_page


# ---------------------------------------------------------------------------
# 注入单篇（名片置顶 + 分段 + 原生代码）
# ---------------------------------------------------------------------------
async def inject_article(page, seg):
    await insert_account_card_top(page)
    await page.wait_for_timeout(1000)
    segments = seg["segments"]
    codes = seg["codes"]
    for i, html in enumerate(segments):
        inj = await inject_html(page, html)
        log(f"注入段 {i}: {inj}")
        await page.wait_for_timeout(1200)
        if i < len(codes):
            r = await insert_native_code(page, codes[i]["lang"], codes[i]["code"])
            log(f"代码块 {i}: {r}")
            await page.wait_for_timeout(1200)
    t = await fill_title(page, seg["title"])
    log(f"标题: {t}")
    await page.wait_for_timeout(1000)
    url = await save_draft(page)
    return url


# ---------------------------------------------------------------------------
async def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="all", help="单套主题 id 或 all")
    ap.add_argument("--wait-scan", type=int, default=600)
    args = ap.parse_args()

    try:
        Path(PROGRESS_FILE).write_text("", encoding="utf-8")
    except Exception:
        pass
    log("==== 原生代码 + 名片置顶 存稿脚本启动 ====")

    if args.theme == "all":
        themes = THEME_IDS
    else:
        themes = [args.theme]

    seg_files = {}
    for tid in themes:
        p = OUT / f".seg_{tid}.json"
        if not p.is_file():
            log(f"ERR: 缺少分段文件 {p}")
            sys.exit(1)
        seg_files[tid] = json.loads(p.read_text(encoding="utf-8"))

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(SKILL_ROOT / ".gzh-profile-dir"),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        await shot(page, "home")

        if await is_logged_in(page):
            log("已登录")
        else:
            log("NOT-LOGGED-IN: 截图二维码，等待扫码")
            try:
                await page.screenshot(path=str(OUT / "login_qr.png"), full_page=False)
                log("QR-READY: outputs/login_qr.png")
            except Exception as e:
                log(f"二维码截图失败: {e}")
            ok = False
            for i in range(args.wait_scan // 2):
                await page.wait_for_timeout(2000)
                for pg in ctx.pages:
                    if await is_logged_in(pg):
                        page = pg
                        ok = True
                        break
                if ok:
                    break
                if i > 0 and i % 60 == 59:
                    try:
                        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
                        await page.wait_for_timeout(2000)
                        await page.screenshot(path=str(OUT / "login_qr.png"), full_page=False)
                        log("二维码已刷新")
                    except Exception as e:
                        log(f"刷新二维码失败: {e}")
                if i % 15 == 14:
                    diag = []
                    for idx, pg in enumerate(ctx.pages):
                        try:
                            u = pg.url
                            t = (await pg.inner_text("body", timeout=3000))[:50].replace("\n", " ")
                        except Exception as e:
                            u, t = "?", f"ERR:{e}"
                        diag.append(f"  tab{idx} url={u} txt={t}")
                    log("等待扫码...\n" + "\n".join(diag))
            if not ok:
                log("ERR: 等待扫码超时")
                await ctx.close()
                sys.exit(1)
            log("扫码登录成功")
            await page.wait_for_timeout(2000)
            await shot(page, "after_login")

        results = []
        for tid in themes:
            log(f"==== 开始存稿：{seg_files[tid]['theme_cn']} ({tid}) ====")
            editor = await open_editor(ctx, page)
            if not editor:
                log(f"ERR: {tid} 编辑器未打开")
                results.append((tid, "NO_EDITOR"))
                continue
            page = editor
            try:
                url = await inject_article(page, seg_files[tid])
            except Exception as e:
                log(f"ERR inject {tid}: {e}")
                url = ""
            log(f"{tid} SAVED-URL: {url}")
            results.append((tid, "OK" if "appmsgid=" in (url or "") else "WARN:" + str(url)))

        await ctx.close()

    log("==== 全部完成 ====")
    for tid, st in results:
        log(f"  {tid}: {st}")
    # 退出码：只要有一篇成功即 0
    ok_any = any(st == "OK" for _, st in results)
    sys.exit(0 if ok_any else 1)


if __name__ == "__main__":
    asyncio.run(main())
