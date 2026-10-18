# -*- coding: utf-8 -*-
"""品牌 logo 素材库：抓取 simple-icons 官方 logo → 光栅化成白色透明 PNG → 供封面合成。

为什么单独一层：
  文章写到 DeepSeek/GPT/Kimi/Claude/千问 时，封面放对应品牌 logo 比随便一张截图更有识别度。
  但 SVG 不能在 PIL 里直接用，所以这里做一次性离线转换：把 24x24 的路径图变成 512px 白色
  字形 PNG 存在 assets/logos/ 下，封面脚本只依赖 PIL，不依赖浏览器（生成时零网络）。

用法:
  # 首次/新增品牌时抓取（需要外网 + playwright，用系统 Python 3.14 跑）
  python scripts/brand_logos.py --fetch deepseek kimi qwen openai
  python scripts/brand_logos.py --fetch-all
  # 查看已有品牌
  python scripts/brand_logos.py --list
  # 快速自检：把全部 logo 拼一张对照图
  python scripts/brand_logos.py --sheet

注意:
  - simple-icons 不同版本收录不同品牌（openai 在 v16 已被移除，回退 v13 取）。
  - 光栅化后统一存 512x512 白色字形 + 透明底，封面里靠 tint_logo() 上色。
"""
import argparse
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_DIR = os.path.join(ROOT, "assets", "logos")
SVG_DIR = os.path.join(LOGO_DIR, "svg")

# key -> (simple-icons slug, 展示名, 品牌主色)
BRANDS = {
    "deepseek":    ("deepseek",    "DeepSeek",     "#4D6BFE"),
    "openai":      ("openai",      "OpenAI",       "#10A37F"),
    "chatgpt":     ("openai",      "ChatGPT",      "#10A37F"),
    "claude":      ("claude",      "Claude",       "#D97757"),
    "anthropic":   ("anthropic",   "Anthropic",    "#D97757"),
    "kimi":        ("kimi",        "Kimi",         "#1783FF"),
    "moonshot":    ("moonshotai",  "Moonshot AI",  "#1783FF"),
    "qwen":        ("qwen",        "Qwen",         "#615CED"),
    "gemini":      ("googlegemini", "Gemini",      "#8E75B2"),
    "google":      ("google",      "Google",       "#4285F4"),
    "meta":        ("meta",        "Meta",         "#0866FF"),
    "metaai":      ("metaai",      "Meta AI",      "#0866FF"),
    "mistral":     ("mistralai",   "Mistral AI",   "#FA520F"),
    "bytedance":   ("bytedance",   "ByteDance",    "#325AB4"),
    "doubao":      ("bytedance",   "豆包",         "#325AB4"),
    "hunyuan":     ("tencenthy",   "腾讯混元",     "#0052D9"),
    "baidu":       ("baidu",       "百度",         "#2932E1"),
    "alibaba":     ("alibabacloud", "阿里云",      "#FF6A00"),
    "minimax":     ("minimax",     "MiniMax",      "#F23F5D"),
    "perplexity":  ("perplexity",  "Perplexity",   "#1FB8CD"),
    "huggingface": ("huggingface", "Hugging Face", "#FFD21E"),
    "github":      ("github",      "GitHub",       "#F0F6FC"),
    "apple":       ("apple",       "Apple",        "#F0F6FC"),
    "nvidia":      ("nvidia",      "NVIDIA",       "#76B900"),
    "ollama":      ("ollama",      "Ollama",       "#F0F6FC"),
    "langchain":   ("langchain",   "LangChain",    "#1C3C3C"),
    "suno":        ("suno",        "Suno",         "#F0F6FC"),
}

UNPKG = "https://unpkg.com/simple-icons@{}/icons/{}.svg"
# v16 是最新全集；openai 等少数品牌因商标政策被下线，回退旧版拿
VERSIONS = ["16", "13", "11"]


def _dl(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_svg(key):
    """下载品牌 SVG（多版本回退），返回本地路径；失败返回 None。"""
    if key not in BRANDS:
        print(f"[skip] 未登记品牌: {key}")
        return None
    slug = BRANDS[key][0]
    os.makedirs(SVG_DIR, exist_ok=True)
    out = os.path.join(SVG_DIR, slug + ".svg")
    if os.path.exists(out) and os.path.getsize(out) > 200:
        return out
    for v in VERSIONS:
        url = UNPKG.format(v, slug)
        try:
            data = _dl(url)
        except Exception as e:
            print(f"  [{slug}] v{v} 失败: {e}")
            continue
        if b"<svg" not in data[:400]:
            print(f"  [{slug}] v{v} 返回非 SVG")
            continue
        with open(out, "wb") as f:
            f.write(data)
        print(f"  [{slug}] OK v{v} {len(data)}B")
        return out
    print(f"[fail] {slug} 所有版本都拿不到")
    return None


RASTER_HTML = """<!doctype html><html><head><style>
html,body{{margin:0;padding:0;background:transparent}}
svg{{display:block;width:{size}px;height:{size}px}}
svg path,svg *{{fill:#fff!important}}
</style></head><body>{svg}</body></html>"""


def _install_greenlet_stub():
    """本机 WDAC 拦 greenlet 的 C 扩展 DLL，用纯 Python 桩顶上（同 publish_full_v2.py）。"""
    try:
        import greenlet  # noqa: F401
        return
    except Exception:
        pass
    import types
    mod = types.ModuleType("greenlet")

    class _Greenlet:
        def __init__(self, run=None, parent=None):
            self.run, self.parent = run, parent

        def switch(self, *a, **k):
            return None

        def throw(self, *a, **k):
            return None

        def __bool__(self):
            return True

    mod.greenlet = _Greenlet
    mod.settrace = lambda *a, **k: None
    sys.modules["greenlet"] = mod


def rasterize(svg_path, png_path, size=512):
    """用 chromium 把 SVG 渲成白色透明 PNG（playwright 只装在系统 Python 里）。"""
    _install_greenlet_stub()
    import asyncio
    from playwright.async_api import async_playwright

    svg = open(svg_path, "r", encoding="utf-8").read()
    # 去掉固定宽高，交给 CSS 控制尺寸
    for attr in (' width="24"', ' height="24"'):
        svg = svg.replace(attr, "")
    html = RASTER_HTML.format(size=size, svg=svg)

    async def _run():
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page(viewport={"width": size, "height": size})
            await pg.set_content(html)
            el = await pg.query_selector("svg")
            await el.screenshot(path=png_path, omit_background=True)
            await b.close()

    asyncio.run(_run())
    return png_path


def fetch_all(keys=None):
    keys = keys or list(BRANDS.keys())
    ok, fail = [], []
    for k in keys:
        print(f"[{k}]")
        svg = fetch_svg(k)
        if not svg:
            fail.append(k)
            continue
        slug = BRANDS[k][0]
        png = os.path.join(LOGO_DIR, slug + ".png")
        if os.path.exists(png) and os.path.getsize(png) > 1000:
            print(f"  [{slug}] PNG 已存在，跳过")
            ok.append(k)
            continue
        try:
            rasterize(svg, png)
            ok.append(k)
            print(f"  [{slug}] PNG {os.path.getsize(png)}B")
        except Exception as e:
            print(f"  [{slug}] 光栅化失败: {e}")
            fail.append(k)
    print(f"\n完成 {len(ok)} 个，失败 {len(fail)} 个: {fail}")
    return ok


# ------------------------------------------------------------------ 运行时接口
def logo_path(key):
    """取已缓存的白色字形 PNG 路径（大小写/别名兼容）。"""
    k = key.lower().strip()
    if k not in BRANDS:
        raise KeyError(f"未登记品牌 {key}，已登记: {', '.join(BRANDS)}")
    slug = BRANDS[k][0]
    p = os.path.join(LOGO_DIR, slug + ".png")
    if not os.path.exists(p):
        raise FileNotFoundError(f"缺少 logo 缓存 {p}，先跑 scripts/brand_logos.py --fetch {k}")
    return p


def brand_color(key):
    return BRANDS[key.lower().strip()][2]


def brand_label(key):
    return BRANDS[key.lower().strip()][1]


def tint_logo(key, px, color=None):
    """返回指定尺寸、指定颜色的 RGBA logo（默认品牌色）。"""
    from PIL import Image

    img = Image.open(logo_path(key)).convert("RGBA")
    w, h = img.size
    # 裁掉透明边，保证视觉尺寸一致
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    scale = px / max(img.size)
    img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))),
                     Image.LANCZOS)
    color = (color or brand_color(key)).lstrip("#")
    rgb = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    solid = Image.new("RGBA", img.size, rgb + (255,))
    solid.putalpha(img.split()[-1])
    return solid


def make_sheet(out_path=None):
    """把全部已缓存 logo 拼成对照图，方便肉眼确认没坏。"""
    from PIL import Image, ImageDraw

    keys = [k for k in BRANDS if os.path.exists(os.path.join(LOGO_DIR, BRANDS[k][0] + ".png"))]
    cell = 160
    cols = 6
    rows = (len(keys) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 26)), "#0D1117")
    d = ImageDraw.Draw(sheet)
    for i, k in enumerate(keys):
        x, y = (i % cols) * cell, (i // cols) * (cell + 26)
        try:
            lg = tint_logo(k, 96)
        except Exception as e:
            d.text((x + 10, y + 60), f"ERR {k}", fill="#FF7B72")
            print("sheet err", k, e)
            continue
        sheet.paste(lg, (x + (cell - lg.width) // 2, y + (cell - lg.height) // 2), lg)
        d.text((x + 8, y + cell + 4), k, fill="#8B949E")
    out_path = out_path or os.path.join(LOGO_DIR, "_sheet.png")
    sheet.save(out_path)
    print("sheet:", out_path, sheet.size, len(keys), "logos")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", nargs="*", help="抓取指定品牌")
    ap.add_argument("--fetch-all", action="store_true", help="抓取全部已登记品牌")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--sheet", action="store_true")
    a = ap.parse_args()
    os.makedirs(LOGO_DIR, exist_ok=True)

    if a.list:
        for k, (slug, name, color) in BRANDS.items():
            p = os.path.join(LOGO_DIR, slug + ".png")
            print(f"{k:14s} {slug:14s} {color:8s} {'有' if os.path.exists(p) else '缺':2s} {name}")
        return
    if a.fetch_all:
        fetch_all()
    elif a.fetch:
        fetch_all(a.fetch)
    if a.sheet:
        make_sheet()


if __name__ == "__main__":
    main()
