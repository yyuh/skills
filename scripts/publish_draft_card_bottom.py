#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公众号草稿存稿 —— 公众号名片放在【正文最下面】。

与 publish_draft_native.py 的唯一区别：
  名片在「所有正文 + 代码块注入完之后」才插入，并强制 appendChild 到正文末尾。
其余（登录态、打开编辑器、ProseMirror 注入、代码块回退、标题、存草稿）完全复用
publish_draft_native 的实现，避免重复逻辑、降低出错面。

用法：
  python publish_draft_card_bottom.py --theme moyu-green
  python publish_draft_card_bottom.py --theme all --wait-scan 1800
"""
import sys
import json
import asyncio
from pathlib import Path

# ---- 复用原生脚本：greenlet 桩 + playwright + 全部公共函数 ----
import publish_draft_native as base

SKILL_ROOT = base.SKILL_ROOT
OUT = base.OUT
THEME_IDS = base.THEME_IDS
PROGRESS_FILE = str(OUT / "publish_card_bottom.log")

log = base.log
inject_html = base.inject_html
fill_title = base.fill_title
save_draft = base.save_draft
open_editor = base.open_editor
insert_native_code = base.insert_native_code
is_logged_in = base.is_logged_in


# ---------------------------------------------------------------------------
# 名片插入到【最下面】
# ---------------------------------------------------------------------------
async def insert_account_card_bottom(page):
    # 1) 顶部菜单栏直接点「账号名片」（精确匹配优先）
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
    log(f"账号名片(底)-直接: {r}")
    await page.wait_for_timeout(1200)
    # 2) 兜底：走「更多」菜单
    if r.startswith('NO'):
        r = await page.evaluate("""() => {
          const btns = Array.from(document.querySelectorAll('button, [role=button], div'));
          for (const b of btns) {
            const t = (b.innerText||'').trim();
            if (t === '更多' || t.indexOf('更多') >= 0) { b.click(); return 'CLICKED_MORE'; }
          }
          return 'NO_MORE';
        }""")
        log(f"账号名片(底)-更多: {r}")
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
    log(f"账号名片(底)-菜单: {r}")
    await page.wait_for_timeout(1500)
    # 3) 填搜索框（React setter + 派发事件）
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
    log(f"账号名片(底)-搜索框: {r}")
    await page.wait_for_timeout(2500)
    # 4) 点「最近使用」触发历史名片渲染
    r = await page.evaluate("""() => {
      const items = Array.from(document.querySelectorAll('li.profile_history_item'));
      if (items.length) { items[0].click(); return 'CLICKED_HISTORY'; }
      return 'NO_HISTORY';
    }""")
    log(f"账号名片(底)-最近使用: {r}")
    await page.wait_for_timeout(2000)
    # 5) 选卡（名称 + 简介双重匹配，防选错）
    r = await page.evaluate("""() => {
      const cards = Array.from(document.querySelectorAll('.wx_profile_card'));
      for (const c of cards) {
        const t = c.innerText||'';
        if (t.indexOf('硅基研究员') >= 0 && t.indexOf('一个AI研究员的日常记录') >= 0) { c.click(); return 'SELECTED'; }
      }
      for (const c of cards) { if (c.innerText.indexOf('硅基研究员') >= 0) { c.click(); return 'SELECTED_FALLBACK'; } }
      return 'NO_CARD';
    }""")
    log(f"账号名片(底)-选卡: {r}")
    await page.wait_for_timeout(1500)
    # 6) 点「插入」
    r = await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) { if ((b.innerText||'').trim() === '插入') { b.click(); return 'INSERT'; } }
      return 'NO_INSERT';
    }""")
    log(f"账号名片(底)-插入: {r}")
    await page.wait_for_timeout(1500)
    # 7) 强制置底：把名片外层 section 移动到 ProseMirror 正文最后一个子节点
    r = await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      let target=null;
      for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
      if (!target) return 'NO_PM';
      const wrp = target.querySelector('section.mp_profile_iframe_wrp') || target.querySelector('.mp_profile_iframe_wrp');
      if (wrp) { target.appendChild(wrp); return 'MOVED_BOTTOM'; }
      return 'ALREADY_BOTTOM_OR_NONE';
    }""")
    log(f"账号名片(底)-置底: {r}")
    return r


# ---------------------------------------------------------------------------
# 注入单篇：先正文 → 再名片（置底）
# ---------------------------------------------------------------------------
async def inject_article_bottom(page, seg):
    segments = seg["segments"]
    codes = seg["codes"]
    # 先注入全部正文 + 代码块
    for i, html in enumerate(segments):
        inj = await inject_html(page, html)
        log(f"注入段 {i}: {inj}")
        await page.wait_for_timeout(1200)
        if i < len(codes):
            r = await insert_native_code(page, codes[i]["lang"], codes[i]["code"])
            log(f"代码块 {i}: {r}")
            await page.wait_for_timeout(1200)
    # 正文结束后插入名片并置底
    await insert_account_card_bottom(page)
    await page.wait_for_timeout(1000)
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
    log("==== 名片置底 存稿脚本启动 ====")

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

    async with base.async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(SKILL_ROOT / ".gzh-profile-dir"),
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
                url = await inject_article_bottom(page, seg_files[tid])
            except Exception as e:
                log(f"ERR inject {tid}: {e}")
                url = ""
            log(f"{tid} SAVED-URL: {url}")
            results.append((tid, "OK" if "appmsgid=" in (url or "") else "WARN:" + str(url)))

        await ctx.close()

    log("==== 全部完成 ====")
    for tid, st in results:
        log(f"  {tid}: {st}")
    ok_any = any(st == "OK" for _, st in results)
    sys.exit(0 if ok_any else 1)


if __name__ == "__main__":
    asyncio.run(main())
