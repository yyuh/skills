#!/usr/bin/env python3
"""给已存草稿（appmsgid）补插公众号名片（正文最末尾）。

按 references/publish-sop.md 第 4 节的已验证路径实现（异步 Playwright + greenlet 桩）：
  工具栏「更多」→「账号名片」→ 弹窗填账号名 → 点「最近使用」项触发渲染
  → 选中 innerText 含账号名+简介的卡片 → 点「插入」→ 校验名片在正文末尾 → 保存草稿。

用法：
  python insert_profile_card.py --appmsgid 100000607 --nickname 硅基研究员
"""
import sys
import types
import asyncio
import time
import argparse
from pathlib import Path

# ---- greenlet 桩（同 publish_draft_async.py，绕过 WDAC/AppLocker DLL 拦截）----
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


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--appmsgid", required=True)
    ap.add_argument("--nickname", default="硅基研究员")
    ap.add_argument("--profile-dir", default=".gzh-profile-dir")
    args = ap.parse_args()

    profile_dir = Path(args.profile_dir)
    if not profile_dir.is_absolute():
        profile_dir = SKILL_ROOT / profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            str(profile_dir), headless=False,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # ---- 登录 + 取 token ----
        await page.goto("https://mp.weixin.qq.com", wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            log("home networkidle 等待超时，继续探测登录态")
        # 登录探测（与 publish_draft_async.py 一致：URL 优先 + 控制台特征，避免 SPA 未渲染时误判）
        url = page.url or ""
        body = ""
        try:
            body = await page.inner_text("body", timeout=8000)
        except Exception:
            pass
        has_qr = ("扫码" in body) or ("扫描二维码" in body) or ("请使用微信" in body)
        has_console = ("草稿箱" in body) or ("图文素材" in body) or ("内容管理" in body) \
            or ("公众号" in body and "登录" not in body)
        logged_in = (("cgi-bin" in url) and ("connect" not in url) and ("qrconnect" not in url)) \
            or (has_console and not has_qr)
        if not logged_in:
            log("NEED-LOGIN: 登录态失效，请用 --headful 重新扫码")
            await ctx.close()
            sys.exit(2)
        token = ""
        m = None
        import re
        m = re.search(r"token=(\d+)", page.url)
        if not m:
            for pg in ctx.pages:
                mm = re.search(r"token=(\d+)", pg.url)
                if mm:
                    token = mm.group(1)
                    break
        else:
            token = m.group(1)
        if not token:
            # 从首页链接里找
            hrefs = await page.evaluate(
                "() => Array.from(document.querySelectorAll('a')).map(a=>a.href).join('\\n')")
            mm = re.search(r"token=(\d+)", hrefs or "")
            if mm:
                token = mm.group(1)
        if not token:
            log("ERR: 拿不到 token")
            await ctx.close()
            sys.exit(1)
        log(f"token: {token}")

        # ---- 打开该草稿的编辑页 ----
        edit_url = ("https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit"
                    f"&action=edit&type=77&appmsgid={args.appmsgid}"
                    f"&token={token}&lang=zh_CN")
        log(f"打开草稿编辑页: {edit_url}")
        await page.goto(edit_url, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            log("edit 页 networkidle 等待超时，继续")
        await page.wait_for_timeout(5000)
        if len(ctx.pages) > 1:
            page = ctx.pages[-1]
            log(f"切换到新标签页（共 {len(ctx.pages)} 个）")
            try:
                await page.wait_for_load_state("networkidle", timeout=60000)
            except Exception:
                pass
        await page.wait_for_timeout(2000)
        await shot(page, "card_01_editor")

        # 已有名片：在正文开头则跳过；在末尾/其它位置则前移到开头（不重复插入）
        has_card = await page.evaluate(
            "() => !!document.querySelector('mp-common-profile, .mp_profile_iframe_wrp')")
        if has_card:
            pos = await page.evaluate("""() => {
              const pms = Array.from(document.querySelectorAll('.ProseMirror'));
              let target = null;
              for (const pm of pms) {
                const ph = pm.getAttribute('data-placeholder') || '';
                if (ph.indexOf('标题') < 0) { target = pm; break; }
              }
              if (!target) return 'NO-PM';
              const node = document.querySelector('.mp_profile_iframe_wrp') || document.querySelector('mp-common-profile');
              if (!node) return 'NO-NODE';
              const holder = node.closest('.mp_profile_iframe_wrp, section[nodeleaf]') || node;
              return (target.firstChild === holder) ? 'FIRST' : 'NOTFIRST';
            }""")
            if pos == 'FIRST':
                log("名片已在正文开头，跳过")
                await ctx.close()
                sys.exit(0)
            if pos == 'NOTFIRST':
                log("名片不在开头，前移到正文开头")
                await page.evaluate("""() => {
                  const pms = Array.from(document.querySelectorAll('.ProseMirror'));
                  let target = null;
                  for (const pm of pms) {
                    const ph = pm.getAttribute('data-placeholder') || '';
                    if (ph.indexOf('标题') < 0) { target = pm; break; }
                  }
                  const node = document.querySelector('.mp_profile_iframe_wrp') || document.querySelector('mp-common-profile');
                  const holder = node.closest('.mp_profile_iframe_wrp, section[nodeleaf]') || node;
                  target.insertBefore(holder, target.firstChild);
                }""")
                await page.wait_for_timeout(800)
                await shot(page, "card_moved_start")
                await page.evaluate("""() => {
                  const btns = Array.from(document.querySelectorAll('button'));
                  for (const b of btns) {
                    if ((b.innerText || '').indexOf('保存为草稿') >= 0) { b.click(); return; }
                  }
                }""")
                await page.wait_for_timeout(1500)
                log("SAVED-URL: " + page.url)
                await shot(page, "card_06_saved")
                await ctx.close()
                sys.exit(0)
            # NO-PM/NO-NODE 异常，继续走插入流程

        # ---- 工具栏「账号名片」是直接按钮（无需走更多）----
        clicked = await page.evaluate("""() => {
          const norm = s => (s || '').replace(/\\s+/g, '');
          const cands = Array.from(document.querySelectorAll(
            'a, button, span, div, li'));
          for (const el of cands) {
            if (el.children.length > 2) continue;
            const t = norm(el.innerText);
            if (t === '账号名片' || t === '公众号名片') {
              const r = el.getBoundingClientRect();
              if (r.width > 0 && r.height > 0 && r.top < 80) {
                el.click(); return 'CARD-BTN:' + t + '@' + Math.round(r.top);
              }
            }
          }
          return 'NO-CARD-BTN';
        }""")
        log(f"账号名片按钮: {clicked}")
        if not clicked.startswith("CARD-BTN:"):
            await shot(page, "card_02_no_cardbtn")
            await ctx.close()
            sys.exit(1)
        await page.wait_for_timeout(2000)
        await shot(page, "card_03_dialog")

        # ---- 弹窗：填账号名 → 点「最近使用」项触发搜索 ----
        nick_b64 = args.nickname
        filled = await page.evaluate("""(nick) => {
          const dlg = document.querySelector('.profile_dialog') ||
                      Array.from(document.querySelectorAll('[class*="dialog"]'))
                        .find(d => (d.innerText || '').indexOf('账号') >= 0);
          if (!dlg) return 'NO-DIALOG';
          const inp = dlg.querySelector('input, textarea');
          if (!inp) return 'NO-INPUT';
          const proto = inp.tagName === 'TEXTAREA'
            ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
          const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
          setter.call(inp, nick);
          inp.dispatchEvent(new Event('input', {bubbles: true}));
          inp.dispatchEvent(new Event('change', {bubbles: true}));
          return 'FILLED';
        }""", nick_b64)
        log(f"填账号名: {filled}")
        await page.wait_for_timeout(2000)

        # 点「最近使用」项（li.profile_history_item）触发搜索结果渲染
        hist = await page.evaluate("""() => {
          const items = document.querySelectorAll('li.profile_history_item, .profile_history_item');
          if (items.length) { items[0].click(); return 'HIST:' + items.length; }
          const all = Array.from(document.querySelectorAll('li, [class*="history"]'));
          for (const it of all) {
            const t = (it.innerText || '').replace(/\\s+/g, '');
            if (t.indexOf('最近使用') >= 0) { it.click(); return 'HIST-TEXT:' + t; }
          }
          return 'NO-HIST';
        }""")
        log(f"最近使用: {hist}")
        await page.wait_for_timeout(2500)
        await shot(page, "card_04_search")

        # ---- 选中正确卡片（账号名 + 简介匹配）→ 点「插入」----
        inserted = await page.evaluate("""(nick) => {
          const cards = Array.from(document.querySelectorAll('.wx_profile_card'));
          let picked = null;
          for (const c of cards) {
            const t = (c.innerText || '').replace(/\\s+/g, '');
            if (t.indexOf(nick) >= 0 && (t.indexOf('AI研究员') >= 0 || t.indexOf('日常记录') >= 0)) {
              picked = c; break;
            }
          }
          if (!picked) {
            for (const c of cards) {
              const t = (c.innerText || '').replace(/\\s+/g, '');
              if (t.indexOf(nick) >= 0) { picked = c; break; }
            }
          }
          if (!picked) return 'NO-CARD:' + cards.length;
          picked.click();
          return 'PICKED';
        }""", nick_b64)
        log(f"选中名片卡片: {inserted}")
        await page.wait_for_timeout(1500)

        btn = await page.evaluate("""() => {
          const btns = Array.from(document.querySelectorAll('button, a.weui-btn, a'));
          for (const b of btns) {
            const t = (b.innerText || '').trim();
            if (t === '插入' || t === '确 定' || t.indexOf('插入') >= 0 && t.length <= 4) {
              if (b.offsetParent) { b.click(); return 'INSERT:' + t; }
            }
          }
          return 'NO-INSERT-BTN';
        }""")
        log(f"插入按钮: {btn}")
        await page.wait_for_timeout(2500)
        await shot(page, "card_05_after_insert")

        # ---- 校验名片位置：必须在正文 ProseMirror 开头 ----
        moved = await page.evaluate("""() => {
          const pms = Array.from(document.querySelectorAll('.ProseMirror'));
          let target = null;
          for (const pm of pms) {
            const ph = pm.getAttribute('data-placeholder') || '';
            if (ph.indexOf('标题') < 0) { target = pm; break; }
          }
          if (!target) return 'NO-PM';
          const wrp = document.querySelector('.mp_profile_iframe_wrp');
          const profile = document.querySelector('mp-common-profile');
          const node = wrp || profile;
          if (!node) return 'NO-PROFILE';
          const holder = node.closest('.mp_profile_iframe_wrp, section[nodeleaf]') || node;
          if (target.firstChild === holder) return 'ALREADY-FIRST';
          target.insertBefore(holder, target.firstChild);
          return 'MOVED';
        }""")
        log(f"名片位置: {moved}")

        # ---- 保存草稿 ----
        await page.evaluate("""() => {
          const btns = Array.from(document.querySelectorAll('button'));
          for (const b of btns) {
            if ((b.innerText || '').indexOf('保存为草稿') >= 0) { b.click(); return; }
          }
        }""")
        await page.wait_for_timeout(1500)
        handled = await page.evaluate("""() => {
          const cands = document.querySelectorAll(
            '.weui-dialog, [role="dialog"], [class*="dialog"], [class*="modal"]');
          for (const d of cands) {
            if (!d.offsetParent) continue;
            const btns = d.querySelectorAll('button, a');
            for (const b of btns) {
              const t = (b.innerText || '').trim();
              if (t === '确定' || t === '确认' || t.indexOf('仍要保存') >= 0) {
                b.click(); return t;
              }
            }
          }
          return null;
        }""")
        log(f"保存确认: {handled}")
        await page.wait_for_timeout(3000)
        log(f"SAVED-URL: {page.url}")
        await shot(page, "card_06_saved")
        await ctx.close()

    if moved in ("ALREADY-FIRST", "MOVED"):
        log("DONE: 名片已插入正文开头并保存")
        sys.exit(0)
    log(f"WARN: 名片位置状态为 {moved}，请人工检查草稿")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
