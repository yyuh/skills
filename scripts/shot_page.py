"""抓取网页真实截图（用于公众号正文插图）。

用法：shot_page.py <url> <out.png> [--wait 4] [--clip top|full] [--width 1440]
"""
import os
import sys
import argparse
from playwright.sync_api import sync_playwright

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--wait", type=float, default=4.0)
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--scroll", type=int, default=0)
    a = ap.parse_args()

    with sync_playwright() as p:
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        launch_args = {"headless": True, "args": ["--disable-blink-features=AutomationControlled"]}
        if proxy and any(host in a.url for host in ("huggingface", "meta.com", "openai", "github.com")):
            launch_args["proxy"] = {"server": proxy}
        b = p.chromium.launch(**launch_args)
        ctx = b.new_context(viewport={"width": a.width, "height": a.height},
                            device_scale_factor=2,
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        pg = ctx.new_page()
        pg.goto(a.url, wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_timeout(int(a.wait * 1000))
        if a.scroll:
            pg.mouse.wheel(0, a.scroll)
            pg.wait_for_timeout(1500)
        pg.screenshot(path=a.out, full_page=a.full)
        print("saved", a.out, pg.title()[:80])
        b.close()

if __name__ == "__main__":
    main()
