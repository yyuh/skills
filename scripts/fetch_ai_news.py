#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_ai_news.py —— 公众号「自助选题」AI 媒体抓取源（对标 GitHub 热榜 WebFetch 逻辑）

用途：抓取 AI 垂类媒体首页，抽取候选文章（标题 + 链接），去重按特征排序，输出 top N 供 Agent/用户选篇。

设计约束（本机 Windows 应用控制策略 WDAC/AppLocker）：
- 用系统 Python 3.14（C:/Users/18480/AppData/Local/Microsoft/WindowsApps/python.exe），不用 managed Python（其 _socket 被拦）。
- 纯标准库 urllib + html.parser，不装第三方包、不碰 Playwright（Playwright 的 greenlet DLL 被拦）。
- 仅做"选题源扫描"，详情正文仍由 Agent 用 WebFetch 二次抓取（同 GitHub 流程）。

用法：
  python fetch_ai_news.py                 # 抓全部默认源，每源 top 8
  python fetch_ai_news.py --source qbitai # 只抓量子位
  python fetch_ai_news.py --top 5         # 每源 top 5
  python fetch_ai_news.py --list          # 列出可用源后退出
"""
import sys
import argparse
import urllib.request
import urllib.error
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from collections import OrderedDict

# ---- 默认 AI 媒体源（可增删；按本号只发 AI 类内容定位）----
AI_OUTLETS = OrderedDict([
    ("jiqizhixin", {"name": "机器之心", "url": "https://www.jiqizhixin.com/"}),
    ("qbitai",     {"name": "量子位",   "url": "https://www.qbitai.com/"}),
    ("36kr",       {"name": "36氪AI",  "url": "https://36kr.com/"}),
])

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 候选文章链接特征（命中其一即加分）
ARTICLE_HINTS = ("/p/", "/article", "/post", "/news", "/a/", "/story", "/item",
                 "/ai", "/tech", "/2024", "/2025", "/2026")


class LinkExtractor(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self._in_a = False
        self._cur_attrs = None
        self._buf = []
        self.links = []  # (text, href)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._in_a = True
            self._cur_attrs = dict(attrs)
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "a" and self._in_a:
            text = "".join(self._buf).strip()
            href = self._cur_attrs.get("href", "") if self._cur_attrs else ""
            if text and href:
                self.links.append((text, href))
            self._in_a = False
            self._cur_attrs = None

    def handle_data(self, data):
        if self._in_a:
            self._buf.append(data)


def fetch_html(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    # 编码探测：先 http header，再 utf-8，再 gbk
    enc = resp.headers.get_content_charset()
    if not enc:
        for probe in ("utf-8", "gbk", "gb18030"):
            try:
                return raw.decode(probe)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")
    try:
        return raw.decode(enc)
    except (LookupError, UnicodeDecodeError):
        return raw.decode("utf-8", errors="replace")


def score(text, href):
    """越高越像正文文章链接。"""
    s = 0
    t = text.strip()
    # 标题长度：中文资讯标题多在 8~40 字
    n = len(t)
    if 8 <= n <= 40:
        s += 3
    elif 5 <= n < 8 or 40 < n <= 60:
        s += 1
    # 链接像文章
    low = href.lower()
    if any(h in low for h in ARTICLE_HINTS):
        s += 2
    # 同一域名内（排除外链/导航）
    if urlparse(href).netloc == "" or urlparse(href).netloc in urlparse(base_url_for(href)).netloc:
        s += 1
    # 含数字（文章 id / 日期）
    if any(ch.isdigit() for ch in low):
        s += 1
    return s


def base_url_for(href):
    # 仅用于同域判断的占位；真实 base 在调用处传入
    return href


def scan_source(key, top):
    info = AI_OUTLETS[key]
    base = info["url"]
    try:
        html = fetch_html(base)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        print(f"  [!] {info['name']} 抓取失败：{e}", file=sys.stderr)
        return []
    p = LinkExtractor(base)
    try:
        p.feed(html)
    except Exception as e:  # noqa
        print(f"  [!] {info['name']} 解析异常：{e}", file=sys.stderr)
        return []
    seen = set()
    cands = []
    for text, href in p.links:
        abs_href = urljoin(base, href)
        parsed = urlparse(abs_href)
        if parsed.scheme not in ("http", "https"):
            continue
        # 必须同域（避免站外友链/广告）
        if parsed.netloc and parsed.netloc != urlparse(base).netloc:
            continue
        t = text.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        sc = score(t, abs_href)
        if sc >= 4:  # 过滤纯导航短链
            cands.append((sc, t, abs_href))
    cands.sort(key=lambda x: x[0], reverse=True)
    return cands[:top]


def main():
    ap = argparse.ArgumentParser(description="AI 媒体热点抓取（选题源）")
    ap.add_argument("--source", help="只抓指定源：" + "/".join(AI_OUTLETS.keys()))
    ap.add_argument("--top", type=int, default=8, help="每源返回条数（默认 8）")
    ap.add_argument("--list", action="store_true", help="列出可用源后退出")
    args = ap.parse_args()

    if args.list:
        for k, v in AI_OUTLETS.items():
            print(f"  {k:12s} {v['name']:8s} {v['url']}")
        return

    keys = [args.source] if args.source else list(AI_OUTLETS.keys())
    for k in keys:
        if k not in AI_OUTLETS:
            print(f"[!] 未知源：{k}（可用：{'/'.join(AI_OUTLETS.keys())}）", file=sys.stderr)
            continue
        info = AI_OUTLETS[k]
        print(f"\n===== {info['name']} ({info['url']}) =====")
        cands = scan_source(k, args.top)
        if not cands:
            print("  （无候选）")
            continue
        for i, (sc, t, url) in enumerate(cands, 1):
            print(f"  {i:2d}. [{sc}] {t}")
            print(f"      {url}")


if __name__ == "__main__":
    main()
