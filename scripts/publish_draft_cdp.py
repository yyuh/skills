#!/usr/bin/env python3
"""公众号草稿存稿（Edge CDP 接管版，免扫码）。

前提：用户已用 --remote-debugging-port=9222 启动了一份带登录态的 Edge
（profile 复制自默认 User Data，因为 Edge 禁止对默认 profile 开调试）。
本脚本通过 connect_over_cdp 接管该 Edge，复用登录 cookie，跳过扫码。

用法：
  python publish_draft_cdp.py <正文.html> --title "标题"
"""
import sys
import types
import asyncio
import base64
import os
import time
import re
from pathlib import Path

# ---- greenlet 桩（异步 API 用不到，但保留以防 import 链触发同步路径）----
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
PROGRESS_FILE = str(SKILL_ROOT / "outputs" / "publish_progress_cdp.log")
CDP_URL = "http://127.0.0.1:9222"


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
    path = str(SKILL_ROOT / "outputs" / f"cdp_{name}.png")
    try:
        await page.screenshot(path=path, full_page=False)
        log(f"截图 → {path}")
    except Exception as e:
        log(f"截图 {name} 失败: {e}")
    return path


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


async def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--title", required=True)
    ap.add_argument("--cdp", default=CDP_URL)
    args = ap.parse_args()

    try:
        Path(PROGRESS_FILE).write_text("", encoding="utf-8")
    except Exception:
        pass

    log("==== 启动 Edge CDP 接管存稿（免扫码）====")
    if not Path(args.html).is_file():
        log(f"ERR: 找不到 HTML: {args.html}")
        sys.exit(1)
    html = Path(args.html).read_text(encoding="utf-8")
    log(f"正文已加载: {len(html)} 字符")

    async with async_playwright() as p:
        log(f"connect_over_cdp → {args.cdp}")
        try:
            browser = await p.chromium.connect_over_cdp(args.cdp)
        except Exception as e:
            log(f"ERR: 无法连接 CDP（Edge 未以调试端口启动？）: {e}")
            sys.exit(1)

        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()

        log("打开 https://mp.weixin.qq.com")
        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        await shot(page, "01_home")

        log("检测登录状态...")
        if not await is_logged_in(page):
            log("ERR: CDP 接管后仍未登录（profile 未带登录态？请改用 publish_draft_async.py 扫码版）")
            sys.exit(1)
        log("已登录（复用 Edge 登录态，无需扫码）")
        await page.wait_for_timeout(2000)
        await shot(page, "02_after_login")

        # ---- 进入编辑器 ----
        log("---- 进入编辑器 ----")
        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        await shot(page, "03_home_for_create")

        editor_page = None

        # 第一次尝试：点「新的创作 → 文章」
        try:
            async with context.expect_page(timeout=15000) as np_info:
                clicked = await page.evaluate("""() => {
                  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                  let target = null;
                  let node;
                  while (node = walker.nextNode()) {
                    if (node.textContent.trim() !== '文章') continue;
                    let p = node.parentElement;
                    let inNew = false;
                    while (p) {
                      if ((p.textContent || '').includes('新的创作')) { inNew = true; break; }
                      p = p.parentElement;
                    }
                    if (inNew) { target = node.parentElement; break; }
                  }
                  if (!target) return 'NOT_FOUND';
                  let el = target;
                  while (el && el !== document.body) {
                    const cs = window.getComputedStyle(el);
                    if (el.tagName === 'A' || el.tagName === 'BUTTON' ||
                        el.onclick || cs.cursor === 'pointer' ||
                        el.getAttribute('role') === 'button' || el.getAttribute('role') === 'link') {
                      el.click();
                      return 'CLICKED_ANCESTOR ' + el.tagName + '.' + (el.className || '').slice(0, 40);
                    }
                    el = el.parentElement;
                  }
                  target.click();
                  return 'CLICKED_TARGET';
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
                log(f"新标签页找到编辑器: {np.url}")
            except Exception:
                log(f"新标签页未出现 ProseMirror: {np.url}")
        except Exception as e:
            log(f"点击未触发新标签页: {e}")

        # 第二次尝试：遍历所有标签页
        if not editor_page:
            log("在所有标签页中查找 ProseMirror...")
            for i, pg in enumerate(context.pages):
                try:
                    pms = await pg.query_selector_all(".ProseMirror")
                    if pms:
                        editor_page = pg
                        log(f"在标签页 {i} 找到编辑器: {pg.url}")
                        break
                except Exception:
                    continue

        # 第三次尝试：草稿箱 → 新建图文
        if not editor_page:
            log("主页点击未触发编辑器，尝试走「草稿箱 → 新建图文」...")
            token = None
            m = re.search(r"token=(\d+)", page.url or "")
            if m:
                token = m.group(1)
            if not token:
                for pg in context.pages:
                    m = re.search(r"token=(\d+)", pg.url or "")
                    if m:
                        token = m.group(1)
                        break
            if token:
                draft_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg"
                             f"?action=list&type=10&lang=zh_CN&token={token}")
                log(f"打开草稿箱: {draft_url}")
                try:
                    await page.goto(draft_url, wait_until="networkidle", timeout=60000)
                    await page.wait_for_timeout(3000)
                    new_btn = await page.evaluate("""() => {
                      const cands = document.querySelectorAll('a, button, div[role="button"]');
                      for (const el of cands) {
                        const t = (el.textContent || '').trim();
                        if (t === '新建图文' || t === '新建' || t === '新的创作' ||
                            t.includes('新建图文') || t === '+ 新建图文') {
                          el.click();
                          return 'CLICKED: ' + t + ' (' + el.tagName + ')';
                        }
                      }
                      return 'NO_NEW_BTN';
                    }""")
                    log(f"草稿箱找新建按钮: {new_btn}")
                    try:
                        async with context.expect_page(timeout=15000) as np_info:
                            await asyncio.sleep(0.2)
                        np = await np_info.value
                        try:
                            await np.wait_for_load_state("domcontentloaded", timeout=60000)
                        except Exception:
                            pass
                        try:
                            await np.wait_for_selector(".ProseMirror", timeout=25000)
                            editor_page = np
                            log(f"草稿箱新建标签页找到编辑器: {np.url}")
                        except Exception:
                            log(f"草稿箱新建标签页未出现 ProseMirror: {np.url}")
                    except Exception as e:
                        log(f"草稿箱点击未触发新标签页: {e}")
                except Exception as e:
                    log(f"打开草稿箱失败: {e}")

        # 第四次尝试：token 直跳
        if not editor_page:
            log("草稿箱路径失败，最后尝试 token 直跳...")
            token = None
            m = re.search(r"token=(\d+)", page.url or "")
            if m:
                token = m.group(1)
            if not token:
                for pg in context.pages:
                    m = re.search(r"token=(\d+)", pg.url or "")
                    if m:
                        token = m.group(1)
                        break
            if token:
                editor_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg"
                              f"?t=media/appmsg_edit_v2&action=edit&isNew=1"
                              f"&type=10&lang=zh_CN&token={token}")
                log(f"直跳编辑器: {editor_url}")
                try:
                    async with context.expect_page(timeout=20000) as np_info:
                        await page.goto(editor_url, wait_until="domcontentloaded", timeout=60000)
                    np = await np_info.value
                    try:
                        await np.wait_for_load_state("domcontentloaded", timeout=60000)
                    except Exception:
                        pass
                    try:
                        await np.wait_for_selector(".ProseMirror", timeout=25000)
                        editor_page = np
                        log(f"直跳新标签页找到编辑器: {np.url}")
                    except Exception:
                        log(f"直跳新标签页未出现 ProseMirror: {np.url}")
                except Exception as e:
                    log(f"直跳失败: {e}")

        if not editor_page:
            log("ERR: 编辑器确实没打开，请看 outputs/cdp_04_editor.png")
            sys.exit(1)
        page = editor_page
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)
        await shot(page, "04_editor")
        log("TEST_OK: 编辑器已打开")

        # ---- 注入正文 + 标题 + 保存 ----
        log("注入正文...")
        try:
            inj = await inject_html(page, html)
            log(f"INJECT: {inj}")
        except Exception as e:
            log(f"INJECT-ERR: {e}")
        await page.wait_for_timeout(2000)
        log("填标题...")
        try:
            t = await fill_title(page, args.title)
            log(f"TITLE: {t}")
        except Exception as e:
            log(f"TITLE-ERR: {e}")
        await page.wait_for_timeout(2000)
        log("保存草稿...")
        try:
            url = await save_draft(page)
            log(f"SAVED-URL: {url}")
        except Exception as e:
            log(f"SAVE-ERR: {e}")
            url = ""
        await page.wait_for_timeout(2000)
        # 注意：不关闭 browser，保留用户 Edge 会话

    if url and "appmsgid=" in url:
        log("DONE: 已存入草稿箱")
        sys.exit(0)
    log("WARN: URL 未见 appmsgid，请人工检查草稿箱")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
