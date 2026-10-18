#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""⚠️ 已验证失败（2026-10-19），不要用它改稿正文 —— 只保留 --dry-run 探测能力。

失败原因：微信编辑器是 ProseMirror，直接 `innerHTML = ...` 只改了 DOM，没有进它内部
state。点"保存为草稿"时前端以 state 为准，正文会被旧内容整篇覆盖回去。
唯一真正生效的是随后的 Ctrl+V 贴图（真实键盘事件会进 state），
结果就是"图片是新的、文字是旧的"这种更糟的状态——5 篇草稿因此报废重做。

**改稿正确姿势**：用 publish_full_v2.py 重新存一篇新草稿，旧稿手动删。
（已试过：innerHTML 注入 + 拼回名片，字数/probe 全部显示"成功"，保存后仍然回滚，
所以不要相信注入后的字数校验，它只能证明 DOM 变了，不能证明会存下来。）

保留用途：--dry-run 读取草稿现状（字数 / 图数 / 名片数 / 开头文本），排查问题很方便。

用法：
  python replace_draft_body.py --appmsgid 100006294 --dry-run
"""
import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_full_v2 import (  # noqa: E402
    log, shot, is_logged_in, close_original_dialog,
    inject_html, paste_body_images, insert_card, save_draft,
    SKILL_ROOT,
)
from playwright.async_api import async_playwright  # noqa: E402

PROBE_JS = """() => {
  const pms = document.querySelectorAll('.ProseMirror');
  let pm = null;
  for (const p of pms) { if ((p.getAttribute('data-placeholder')||'').indexOf('标题') < 0) { pm = p; break; } }
  if (!pm) return {ok: false};
  const imgs = Array.from(pm.querySelectorAll('img')).filter(i => i.getBoundingClientRect().width > 40);
  const cards = pm.querySelectorAll('.mp_profile_iframe_wrp');
  return {ok: true, chars: pm.innerText.replace(/\\s/g, '').length,
          head: pm.innerText.replace(/\\s/g, '').slice(0, 160),
          imgs: imgs.length, cards: cards.length,
          mmbiz: Array.from(pm.querySelectorAll('img')).filter(i => ((i.src || i.getAttribute('data-src') || '').indexOf('mmbiz') >= 0)).length};
}"""

CARD_JS = """() => {
  const pms = document.querySelectorAll('.ProseMirror');
  let pm = null;
  for (const p of pms) { if ((p.getAttribute('data-placeholder')||'').indexOf('标题') < 0) { pm = p; break; } }
  if (!pm) return {first: '', last: '', n: 0};
  const cards = pm.querySelectorAll('.mp_profile_iframe_wrp');
  return {first: cards.length ? cards[0].outerHTML : '',
          last: cards.length ? cards[cards.length - 1].outerHTML : '',
          n: cards.length};
}"""


def plain_len(html):
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S)
    return len(re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", body)))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--appmsgid", required=True)
    ap.add_argument("--html")
    ap.add_argument("--images", nargs="*", default=[])
    ap.add_argument("--card", default="硅基研究员")
    ap.add_argument("--no-card", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--channel", default="msedge")
    ap.add_argument("--profile-dir", default=".gzh-profile-dir")
    ap.add_argument("--wait-scan", type=int, default=600)
    ap.add_argument("--headless", action="store_true")
    a = ap.parse_args()

    profile_dir = Path(a.profile_dir)
    if not profile_dir.is_absolute():
        profile_dir = SKILL_ROOT / profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)

    if not a.dry_run:
        if not a.html:
            log("ERR: 非 dry-run 必须给 --html")
            sys.exit(1)
        html_path = Path(a.html)
        if not html_path.is_absolute():
            html_path = SKILL_ROOT / html_path
        if not html_path.is_file():
            log(f"ERR: 找不到 HTML: {html_path}")
            sys.exit(1)
        new_html = html_path.read_text(encoding="utf-8")
        for p in a.images:
            if not (Path(p) if Path(p).is_absolute() else SKILL_ROOT / p).is_file():
                log(f"ERR: 找不到正文图: {p}")
                sys.exit(1)

    async with async_playwright() as p:
        launch_kwargs = dict(
            user_data_dir=str(profile_dir),
            headless=a.headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
        )
        if a.channel:
            launch_kwargs["channel"] = a.channel
        ctx = await p.chromium.launch_persistent_context(**launch_kwargs)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)

        if await is_logged_in(page):
            log("已登录")
        else:
            log("未登录，等待扫码...")
            qr = str(SKILL_ROOT / "outputs" / "login_qr.png")
            await page.screenshot(path=qr)
            log(f"QR-READY: {qr}")
            ok = False
            for _ in range(a.wait_scan // 2):
                await page.wait_for_timeout(2000)
                for pg in ctx.pages:
                    if await is_logged_in(pg):
                        page = pg
                        ok = True
                        break
                if ok:
                    break
            if not ok:
                log("ERR: 扫码超时")
                await ctx.close()
                sys.exit(1)
            log("登录成功")

        token = None
        for pg in [page] + list(ctx.pages):
            m = re.search(r"token=(\d+)", pg.url or "")
            if m:
                token = m.group(1)
                break
        if not token:
            log("ERR: 无法获取 token")
            await ctx.close()
            sys.exit(1)

        edit_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg"
                    f"?t=media/appmsg_edit&action=edit&type=77"
                    f"&appmsgid={a.appmsgid}&token={token}&lang=zh_CN")
        log(f"打开草稿: {a.appmsgid}")
        await page.goto(edit_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(9000)
        await close_original_dialog(page)
        await shot(page, "replace_00_opened")

        before = await page.evaluate(PROBE_JS)
        log(f"原稿: OK={before.get('ok')} 字数={before.get('chars')} "
            f"图={before.get('imgs')} 名片={before.get('cards')}")
        log(f"原稿开头: {before.get('head')}")
        if not before.get("ok"):
            log("ERR: 没找到正文编辑器")
            await ctx.close()
            sys.exit(2)

        if a.dry_run:
            cards = await page.evaluate(CARD_JS)
            probe = SKILL_ROOT / "outputs" / f"_card_probe_{a.appmsgid}.html"
            probe.write_text((cards.get("first") or "") + "\n\n<!--SPLIT-->\n\n"
                             + (cards.get("last") or ""), encoding="utf-8")
            log(f"名片 {cards.get('n')} 张，已存样本: {probe}")
            log("DRY-RUN: 探测完成，未注入、未保存")
            await ctx.close()
            return

        # 抓原名片节点，注入时一起拼回去：文案覆盖会把名片一起清掉，
        # 而 insert_card 依赖光标位置，插到哪不好控。
        cards = await page.evaluate(CARD_JS)
        payload = new_html
        if cards.get("n"):
            payload = (cards.get("first") or "") + new_html + (cards.get("last") or "")
            log(f"拼回原名片 {cards.get('n')} 张")

        want = plain_len(new_html)
        inj = await inject_html(page, payload)
        log(f"注入结果: {inj}（新正文纯文本 {want} 字 + 名片）")
        await page.wait_for_timeout(2500)

        after = await page.evaluate(PROBE_JS)
        got = after.get("chars") or 0
        log(f"注入后: 字数={got} 图={after.get('imgs')} 名片={after.get('cards')} "
            f"mmbiz图={after.get('mmbiz')}")
        # 名片文字会让总数偏大，所以只查下限：正文必须完整灌进去
        if not after.get("ok") or got < want * 0.95:
            log("ERR: 注入不完整，中止（未保存，草稿未改动）")
            await shot(page, "replace_99_bad")
            await ctx.close()
            sys.exit(3)
        if (before.get("cards") or 0) != (after.get("cards") or 0):
            log(f"WARN: 名片数变了 {before.get('cards')} → {after.get('cards')}，请复核")

        if a.images:
            await paste_body_images(page, a.images)
            await page.wait_for_timeout(2000)

        final = await page.evaluate(PROBE_JS)
        log(f"保存前: 字数={final.get('chars')} 图={final.get('imgs')} "
            f"名片={final.get('cards')}")

        url = await save_draft(page)
        log(f"保存URL: {url}")
        await shot(page, "replace_01_saved")

        m = re.search(r"appmsgid=(\d+)", url or "")
        log(f"DONE: appmsgid={m.group(1) if m else a.appmsgid}")
        await page.wait_for_timeout(3000)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
