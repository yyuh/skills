#!/usr/bin/env python3
"""给已有草稿补一张正文插图（原位替换「图片占位符N」文字，ProseMirror 安全方式）。

适用场景：publish_full_v2.py 存稿时某张正文图剪贴板失败（如源文件损坏），
草稿已存但占位符文字还在。本脚本打开该草稿 → 找到占位符段落 → 选中 → 剪贴板粘贴 → 等 mmbiz → 保存。

用法：
  python fix_body_image_in_draft.py --appmsgid 100006250 --image "og.png" --placeholder 1
"""
import sys
import re
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_full_v2 import (  # noqa: E402
    log, shot, is_logged_in, close_original_dialog,
    copy_image_to_clipboard_retry, copy_image_via_page, save_draft,
    SKILL_ROOT,
)
from playwright.async_api import async_playwright  # noqa: E402


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--appmsgid", required=True, help="草稿的 appmsgid")
    ap.add_argument("--image", required=True, help="要插入的图片路径")
    ap.add_argument("--placeholder", type=int, default=1, help="占位符编号（默认1，即「图片占位符1」）")
    ap.add_argument("--channel", default="msedge", help="浏览器 channel（默认 msedge）")
    ap.add_argument("--profile-dir", default=".gzh-profile-dir")
    ap.add_argument("--wait-scan", type=int, default=600)
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()

    profile_dir = Path(args.profile_dir)
    if not profile_dir.is_absolute():
        profile_dir = SKILL_ROOT / profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)

    img_path = Path(args.image)
    if not img_path.is_absolute():
        img_path = SKILL_ROOT / img_path
    if not img_path.is_file():
        log(f"ERR: 找不到图片: {img_path}")
        sys.exit(1)

    placeholder = f"图片占位符{args.placeholder}"
    log(f"==== 修补草稿 {args.appmsgid}：在「{placeholder}」处插入 {img_path.name} ====")

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
        await shot(page, "fix_body_00_opened")
        await close_original_dialog(page)

        # 1) 找到占位符并选中整个段落
        found = await page.evaluate(f"""() => {{
          const pms = document.querySelectorAll('.ProseMirror');
          for (const pm of pms) {{
            if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')>=0) continue;
            const all = pm.querySelectorAll('span, p');
            for (const el of all) {{
              if (el.textContent && el.textContent.indexOf('{placeholder}') >= 0) {{
                el.focus();
                const range = document.createRange();
                range.selectNodeContents(el);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
                return 'FOUND';
              }}
            }}
          }}
          return 'NOT_FOUND';
        }}""")
        if found != 'FOUND':
            log(f"ERR: 未找到占位符 {placeholder}（可能已被替换或文本不同）")
            await shot(page, "fix_body_99_noanchor")
            await ctx.close()
            sys.exit(2)
        log(f"已定位并选中: {placeholder}")
        await page.wait_for_timeout(500)

        # 2) 剪贴板（重试 + 浏览器 fallback）
        ok = copy_image_to_clipboard_retry(str(img_path))
        if not ok:
            log("win32clipboard失败，尝试浏览器剪贴板")
            ok = await copy_image_via_page(page, str(img_path))
        if not ok:
            log("ERR: 剪贴板复制图片失败（所有方式）")
            await ctx.close()
            sys.exit(3)

        # 3) Ctrl+V 粘贴（替换选中的占位符文字）
        await page.keyboard.press('Control+V')

        # 4) 轮询等 mmbiz
        pasted = False
        for i in range(30):
            await page.wait_for_timeout(1000)
            r = await page.evaluate("""() => {
              const pms = document.querySelectorAll('.ProseMirror');
              for (const pm of pms) {
                if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')>=0) continue;
                const imgs = pm.querySelectorAll('img');
                for (const img of imgs) {
                  const s = img.src || img.getAttribute('data-src') || '';
                  if ((s.indexOf('mmbiz') >= 0 || s.indexOf('qpic') >= 0) && img.getBoundingClientRect().width > 50) return 'OK';
                }
              }
              return 'WAIT';
            }""")
            if r == 'OK':
                log(f"插图已粘贴成功 ({i+1}秒)")
                pasted = True
                break
        if not pasted:
            log("ERR: 粘贴失败（30秒内未见mmbiz图片）")
            await shot(page, "fix_body_99_paste_fail")
            await ctx.close()
            sys.exit(4)

        await page.wait_for_timeout(1000)
        # 5) 保存
        url = await save_draft(page)
        log(f"保存URL: {url}")
        await shot(page, "fix_body_01_saved")
        log("DONE: 草稿已修补并保存")

        await page.wait_for_timeout(3000)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
