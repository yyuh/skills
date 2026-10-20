#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按页面上的锚点文字滚动截图（比盲滚像素可靠）。

用法：
    python shot_at.py <url> <out.png> --text "计费" [--offset 0]
    python shot_at.py <url> <out.png> --y 5200

原理：在页面里找 textContent 完全等于/包含 --text 的标题元素，scrollIntoView 到顶部附近，
再截当前视口。适合截官方文档里某个小节（计费表、参数表）。
"""
import argparse
import asyncio
import os
import sys
import types

# 本机 WDAC 拦 greenlet C 扩展，先打纯 Python 桩（异步 API 不需要它）
_gmod = types.ModuleType("greenlet")


class _Greenlet:
    def switch(self, *a, **k):
        return None

    def throw(self, *a, **k):
        return None


_gmod.greenlet = _Greenlet
sys.modules["greenlet"] = _gmod

from playwright.async_api import async_playwright  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""


def find_js(text):
    return """
    (text) => {
      const all = Array.from(document.querySelectorAll('h1,h2,h3,h4,p,td,span'));
      let best = null;
      for (const el of all) {
        const t = (el.innerText || '').trim();
        if (!t) continue;
        if (t === text) { best = el; break; }
        if (!best && t.indexOf(text) >= 0 && t.length < text.length + 40) best = el;
      }
      if (!best) return null;
      best.scrollIntoView({block: 'start'});
      const r = best.getBoundingClientRect();
      return {y: r.top + window.scrollY, tag: best.tagName, text: best.innerText.slice(0, 60)};
    }
    """


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--text", default="")
    ap.add_argument("--y", type=int, default=-1)
    ap.add_argument("--offset", type=int, default=-90)
    ap.add_argument("--wait", type=float, default=5.0)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--no-proxy", action="store_true",
                    help="直连不走代理（github.com 等被代理拦的站点用这个）")
    a = ap.parse_args()

    kw = dict(headless=True, args=["--disable-blink-features=AutomationControlled"])
    if PROXY and not a.no_proxy:
        kw["proxy"] = {"server": PROXY}

    async with async_playwright() as p:
        b = await p.chromium.launch(**kw)
        ctx = await b.new_context(viewport={"width": a.width, "height": a.height},
                                  user_agent=UA, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto(a.url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(int(a.wait * 1000))

        if a.text:
            hit = await page.evaluate(find_js(a.text), a.text)
            print("anchor:", hit)
            if hit:
                await page.evaluate(f"window.scrollTo(0, {max(0, int(hit['y']) + a.offset)})")
                await page.wait_for_timeout(900)
        elif a.y >= 0:
            await page.evaluate(f"window.scrollTo(0, {a.y})")
            await page.wait_for_timeout(900)

        await page.screenshot(path=a.out)
        print("saved", a.out)
        await b.close()


if __name__ == "__main__":
    asyncio.run(main())
