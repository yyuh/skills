#!/usr/bin/env python3
"""公众号草稿存稿（异步 Playwright 版，绕过 greenlet DLL 拦截）。

本机有应用控制策略（WDAC/AppLocker）拦了 playwright 同步 API 依赖的
greenlet C 扩展 DLL。但 greenlet 仅在同步 API 运行时被实例化；异步 API
（asyncio）不实例化它。因此在 import playwright.async_api 之前，把
sys.modules['greenlet'] 替换为一个纯 Python 桩（greenlet.greenlet 仅作基类），
即可在无头/有头模式下拉起浏览器并完整跑存稿流程。

用法：
  python publish_draft_async.py <正文.html> --title "标题"
  python publish_draft_async.py <正文.html> --title "标题" --headless
"""
import sys
import types
import asyncio
import base64
import os
import time
import re
from pathlib import Path

# ---- 关键：在 import playwright 之前桩掉 greenlet（同步 API 专属，异步用不到）----
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
PROGRESS_FILE = str(SKILL_ROOT / "outputs" / "publish_progress_async.log")


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
    path = str(SKILL_ROOT / "outputs" / f"step_{name}.png")
    try:
        await page.screenshot(path=path, full_page=False)
        log(f"截图 → {path}")
    except Exception as e:
        log(f"截图 {name} 失败: {e}")
    return path


async def is_logged_in(page):
    # URL 层面：登录后位于 cgi-bin 后台区域（不含 connect/qr 登录页）即视为已登录
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
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--profile-dir", default=".gzh-profile-dir")
    ap.add_argument("--wait-scan", type=int, default=600,
                    help="未登录时轮询等待扫码的秒数，默认 600")
    args = ap.parse_args()

    profile_dir = Path(args.profile_dir)
    if not profile_dir.is_absolute():
        profile_dir = SKILL_ROOT / profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)

    try:
        Path(PROGRESS_FILE).write_text("", encoding="utf-8")
    except Exception:
        pass

    log("==== 启动异步存稿脚本（greenlet 桩绕过版）====")
    if not Path(args.html).is_file():
        log(f"ERR: 找不到 HTML: {args.html}")
        sys.exit(1)
    html = Path(args.html).read_text(encoding="utf-8")
    log(f"正文已加载: {len(html)} 字符")

    async with async_playwright() as p:
        log("启动持久化浏览器上下文（headful=%s）..." % (not args.headless))
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        log("打开 https://mp.weixin.qq.com")
        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        await shot(page, "01_home")

        log("检测登录状态...")
        if await is_logged_in(page):
            log("已登录，直接进入导航")
        else:
            log("NOT-LOGGED-IN: 未登录，截图二维码并等待扫码")
            qr_path = str(SKILL_ROOT / "outputs" / "login_qr.png")
            try:
                await page.screenshot(path=qr_path, full_page=False)
                log(f"QR-READY: {qr_path}")
            except Exception as e:
                log(f"二维码截图失败: {e}")
            ok = False
            qr_path = str(SKILL_ROOT / "outputs" / "login_qr.png")
            for i in range(args.wait_scan // 2):
                await page.wait_for_timeout(2000)
                # 遍历所有已打开的标签页：扫码登录可能发生在新标签页
                for pg in ctx.pages:
                    if await is_logged_in(pg):
                        page = pg
                        ok = True
                        break
                if ok:
                    break
                # 二维码约 2 分钟过期：每 120s 刷新一次（重截登录页+PNG），
                # 让窗口里的实时二维码始终有效，用户无需赶时间
                if i > 0 and i % 60 == 59:
                    try:
                        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
                        await page.wait_for_timeout(2000)
                        await page.screenshot(path=qr_path, full_page=False)
                        log("二维码已刷新（窗口实时码同步更新）")
                    except Exception as e:
                        log(f"刷新二维码失败: {e}")
                if i % 15 == 14:
                    # 诊断：把每个标签页的真实 URL + 正文片段打出来，方便核对到底登没登
                    diag = []
                    for idx, pg in enumerate(ctx.pages):
                        try:
                            u = pg.url
                            t = (await pg.inner_text("body", timeout=3000))[:50].replace("\n", " ")
                        except Exception as e:
                            u, t = "?", f"ERR:{e}"
                        diag.append(f"  tab{idx} url={u} txt={t}")
                    log(f"仍在等待扫码... ({(i+1)*2}s)\n" + "\n".join(diag))
            if not ok:
                log("ERR: 等待扫码超时，退出")
                await ctx.close()
                sys.exit(1)
            log("扫码登录成功")
            await page.wait_for_timeout(2000)
            await shot(page, "02_after_login")

        # ---- 进入编辑器 ----
        log("---- 进入编辑器 ----")
        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        await shot(page, "03_home_for_create")

        editor_page = None  # 最终确定使用的编辑器标签页

        # 第一次尝试：点「新的创作 → 文章」，用 expect_page 捕获可能的新标签页
        try:
            async with ctx.expect_page(timeout=15000) as np_info:
                clicked = await page.evaluate("""() => {
                  // 找「新的创作」下文本为「文章」的可点击卡片
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
                  // 向上找最近的可点击祖先（onclick / a / button / cursor:pointer / role=button）
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

        # 第二次尝试：遍历所有标签页找编辑器（点击可能在原标签页内导航）
        if not editor_page:
            log("在所有标签页中查找 ProseMirror...")
            for i, pg in enumerate(ctx.pages):
                try:
                    pms = await pg.query_selector_all(".ProseMirror")
                    if pms:
                        editor_page = pg
                        log(f"在标签页 {i} 找到编辑器: {pg.url}")
                        break
                except Exception:
                    continue

        # 第三次尝试：去「草稿箱」页点「新建图文」（最可靠的入口）
        if not editor_page:
            log("主页点击未触发编辑器，尝试走「草稿箱 → 新建图文」...")
            token = None
            m = re.search(r"token=(\d+)", page.url or "")
            if m:
                token = m.group(1)
            if not token:
                for pg in ctx.pages:
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
                    # 找「新建图文」/「新建」按钮
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
                        async with ctx.expect_page(timeout=15000) as np_info:
                            await asyncio.sleep(0.2)  # 让点击生效
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

        # 第四次尝试：token 直跳编辑器
        if not editor_page:
            log("草稿箱路径失败，最后尝试 token 直跳...")
            token = None
            m = re.search(r"token=(\d+)", page.url or "")
            if m:
                token = m.group(1)
            if not token:
                for pg in ctx.pages:
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
                        log(f"直跳新标签页找到编辑器: {np.url}")
                    except Exception:
                        log(f"直跳新标签页未出现 ProseMirror: {np.url}")
                except Exception as e:
                    log(f"直跳失败: {e}")

        if not editor_page:
            log("ERR: 编辑器确实没打开，请看 outputs/step_04_editor.png")
            await ctx.close()
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
        await ctx.close()

    if url and "appmsgid=" in url:
        log("DONE: 已存入草稿箱")
        sys.exit(0)
    log("WARN: URL 未见 appmsgid，请人工检查草稿箱")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
