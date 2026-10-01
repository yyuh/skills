#!/usr/bin/env python3
"""给**已存在**的草稿补设封面（不改正文、不重插名片）。

复用 publish_full.py 的封面流程：打开指定 appmsgid 的草稿 → 把封面图粘贴到
正文末尾（临时）→ 从正文选择设为封面 → 删除临时图 → 保存。

用法：
  python set_cover_to_draft.py --appmsgid 100003358 --cover "cover.png"
"""
import sys
import re
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_full import (  # noqa: E402
    log, shot, is_logged_in, close_original_dialog,
    insert_cover_temp, set_cover, remove_temp_cover, save_draft,
    SKILL_ROOT,
)
from playwright.async_api import async_playwright  # noqa: E402


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--appmsgid", required=True, help="草稿的 appmsgid")
    ap.add_argument("--cover", required=True, help="封面图路径")
    ap.add_argument("--channel", default="msedge", help="浏览器 channel（默认 msedge）")
    ap.add_argument("--profile-dir", default=".gzh-profile-dir")
    ap.add_argument("--wait-scan", type=int, default=600)
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()

    profile_dir = Path(args.profile_dir)
    if not profile_dir.is_absolute():
        profile_dir = SKILL_ROOT / profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)

    if not Path(args.cover).is_file():
        log(f"ERR: 找不到封面图: {args.cover}")
        sys.exit(1)

    log("==== 给已有草稿设置封面 ====")

    async with async_playwright() as p:
        launch_kwargs = dict(
            user_data_dir=str(profile_dir),
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
        )
        if args.channel:
            launch_kwargs["channel"] = args.channel
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
            for _ in range(args.wait_scan // 2):
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
        m = re.search(r"token=(\d+)", page.url or "")
        if m:
            token = m.group(1)
        if not token:
            for pg in ctx.pages:
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
                    f"&appmsgid={args.appmsgid}&token={token}&lang=zh_CN")
        log(f"打开草稿: {edit_url}")
        await page.goto(edit_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(9000)
        await shot(page, "cover_draft_00_opened")
        await close_original_dialog(page)

        pasted = await insert_cover_temp(page, args.cover)
        log(f"临时封面插入正文: {pasted}")
        cover_ok = False
        if pasted:
            for i in range(3):
                cover_ok = await set_cover(page, args.cover)
                await shot(page, f"cover_draft_01_set_{i}")
                if cover_ok:
                    break
                log(f"封面设置失败，重试 {i + 1}/3 ...")
                await close_original_dialog(page)
                await page.wait_for_timeout(1500)

        if not cover_ok:
            log("ERR: 封面设置失败")
            await shot(page, "cover_draft_99_fail")
            await ctx.close()
            sys.exit(2)

        await remove_temp_cover(page)
        await page.wait_for_timeout(1000)
        url = await save_draft(page)
        log(f"保存URL: {url}")
        await shot(page, "cover_draft_02_saved")
        log("DONE: 封面已设置并保存")

        await page.wait_for_timeout(3000)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
