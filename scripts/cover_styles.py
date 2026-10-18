# -*- coding: utf-8 -*-
"""公众号封面 3 种候选风格（替代旧的「纯色块+左图右文」模板）。

风格:
  A 深色极客风: 近黑底 + 终端装饰条 + 白色大标题(数字强调色) + 右侧截图卡(细边框)
  B 杂志海报风: 米白底 + 超大黑标题 + 荧光笔高亮 + 硬阴影截图卡
  C 渐变霓虹风: 深蓝紫渐变 + 发光标题 + 发光边框截图卡

用法: python cover_styles.py <截图.png> <主标题> <数字行> <kicker> <输出前缀>
示例: python cover_styles.py outputs/og_vs.png "开源版ElevenLabs" "6.8万星 · 646种语言" "GitHub 热榜项目实测" outputs/cov_vs_sample
"""
import sys
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1280, 545
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"


def load_font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.truetype(FONT_BOLD, size)


def fit_font(draw, text, start_size, min_size, max_w, path=FONT_BOLD):
    """从 start_size 递减直到文本宽度 <= max_w，返回 (font, size)"""
    size = start_size
    while size > min_size:
        f = load_font(path, size)
        if draw.textlength(text, font=f) <= max_w:
            return f, size
        size -= 2
    return load_font(path, min_size), min_size


def text_w(draw, text, font):
    return draw.textlength(text, font=font)


def fit_screenshot(img, box_w, box_h):
    iw, ih = img.size
    scale = min(box_w / iw, box_h / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    return img.resize((nw, nh), Image.LANCZOS)


def draw_numline_hl(draw, x, y, numline, font, hl_color, base_color):
    """画数字行，数字段用高亮色，其余用 base_color"""
    draw.text((x, y), numline, font=font, fill=base_color)
    for m in re.finditer(r"[0-9][0-9.,万B GTb]*[^\s·]*", numline):
        frag = m.group(0)
        off = text_w(draw, numline[:m.start()], font)
        draw.text((x + off, y), frag, font=font, fill=hl_color)


# ---------------------------------------------------------------- D 瑞士极简风
def style_swiss(screenshot, title, numline, kicker, accent="#E62E2E"):
    """白底大量留白 + 黑色超大标题 + 红色数字强调 + 右下小截图卡（细黑框）。"""
    bg = Image.new("RGB", (W, H), "#FAFAF8")
    d = ImageDraw.Draw(bg)

    # 左上黑徽章
    f_badge = load_font(FONT_BOLD, 22)
    bw = text_w(d, kicker, f_badge) + 40
    d.rectangle([56, 44, 56 + bw, 84], fill="#111111")
    d.text((56 + 20, 51), kicker, font=f_badge, fill="#FAFAF8")

    # 红色方点（瑞士经典元素）
    d.rectangle([56 + bw + 18, 56, 56 + bw + 38, 76], fill=accent)

    # 超大黑标题
    f_title, _ = fit_font(d, title, 108, 56, 700)
    d.text((56, 128), title, font=f_title, fill="#111111")

    # 数字行（数字段红色）
    f_num, _ = fit_font(d, numline, 56, 32, 700)
    draw_numline_hl(d, 56, 128 + f_title.size + 36, numline, f_num, accent, "#111111")

    # 右下小截图卡（细黑框 + 硬投影偏移）
    shot = fit_screenshot(screenshot, 420, 250)
    sw, sh = shot.size
    cx0, cy0 = W - 56 - sw - 28, H - 56 - sh - 28
    d.rectangle([cx0 + 10, cy0 + 10, cx0 + sw + 20 + 10, cy0 + sh + 20 + 10], fill="#111111")
    d.rectangle([cx0, cy0, cx0 + sw + 20, cy0 + sh + 20],
                fill="#FFFFFF", outline="#111111", width=2)
    bg.paste(shot, (cx0 + 10, cy0 + 10))

    # 底部细线 + 署名
    d.line([56, H - 60, W - 56, H - 60], fill="#111111", width=2)
    f_bot = load_font(FONT_BOLD, 20)
    d.text((56, H - 48), "硅基研究员", font=f_bot, fill="#111111")
    d.text((W - 56 - text_w(d, "AI · 开源 · 实测", f_bot), H - 48),
           "AI · 开源 · 实测", font=f_bot, fill="#111111")
    return bg


# ---------------------------------------------------------------- E 蓝图工程风
def style_blueprint(screenshot, title, numline, kicker, accent="#FFD23F"):
    """深蓝图底 + 白色网格 + 等宽字体 + 工程标注（FIG.01/准星角标）+ 黄色强调。"""
    bg = Image.new("RGB", (W, H), "#0F2B5C")
    d = ImageDraw.Draw(bg)

    # 白色细网格
    for gx in range(0, W, 40):
        d.line([(gx, 0), (gx, H)], fill="#1B3E7A", width=1)
    for gy in range(0, H, 40):
        d.line([(0, gy), (W, gy)], fill="#1B3E7A", width=1)

    # 四角准星标记
    for cx, cy in [(30, 30), (W - 30, 30), (30, H - 30), (W - 30, H - 30)]:
        d.line([(cx - 12, cy), (cx + 12, cy)], fill="#FFFFFF", width=2)
        d.line([(cx, cy - 12), (cx, cy + 12)], fill="#FFFFFF", width=2)

    f_mono = load_font(FONT_MONO, 20)
    f_zh = load_font(FONT_BOLD, 19)
    # 顶部工程标注行
    d.text((64, 46), "DWG-NO. GZH-2026", font=f_mono, fill="#9DB8E0")
    d.text((64 + text_w(d, "DWG-NO. GZH-2026", f_mono) + 12, 47), f"· {kicker}",
           font=f_zh, fill="#9DB8E0")
    d.text((W - 64 - text_w(d, "FIG.01", f_mono), 46), "FIG.01", font=f_mono, fill=accent)

    # 左列标题（等宽氛围 + 中文粗体）
    f_title, _ = fit_font(d, title, 84, 52, 640)
    d.text((64, 120), title, font=f_title, fill="#FFFFFF")
    f_num, _ = fit_font(d, numline, 52, 32, 640)
    draw_numline_hl(d, 64, 120 + f_title.size + 34, numline, f_num, accent, "#FFFFFF")

    # 标注引线（从标题区指向截图卡）
    d.line([(64, 120 + f_title.size + 120), (700, 240)], fill=accent, width=2)
    d.ellipse([696, 236, 704, 244], fill=accent)
    f_note = load_font(FONT_MONO, 18)
    d.text((420, 262), "REAL SCREENSHOT // VERIFIED", font=f_note, fill="#9DB8E0")

    # 右侧截图卡（白框 + 四角小准星）
    card_x0, card_y0, card_x1, card_y1 = 740, 110, W - 64, H - 110
    d.rectangle([card_x0, card_y0, card_x1, card_y1], fill="#FFFFFF", width=2)
    for mx, my in [(card_x0 + 12, card_y0 + 12), (card_x1 - 12, card_y0 + 12),
                   (card_x0 + 12, card_y1 - 12), (card_x1 - 12, card_y1 - 12)]:
        d.line([(mx - 8, my), (mx + 8, my)], fill=accent, width=3)
        d.line([(mx, my - 8), (mx, my + 8)], fill=accent, width=3)
    shot = fit_screenshot(screenshot, card_x1 - card_x0 - 32, card_y1 - card_y0 - 32)
    bg.paste(shot, (card_x0 + 16, card_y0 + 16))

    # 底部信息条（工程图标题栏）
    d.rectangle([0, H - 48, W, H], fill="#0A1F42")
    f_bot = load_font(FONT_BOLD, 20)
    d.text((64, H - 36), "硅基研究员", font=f_bot, fill="#9DB8E0")
    d.text((W - 64 - text_w(d, "SCALE 1:1 · AI · 开源 · 实测", f_bot), H - 36),
           "SCALE 1:1 · AI · 开源 · 实测", font=f_bot, fill="#9DB8E0")
    return bg


# ---------------------------------------------------------------- A 深色极客风
def style_dark(screenshot, title, numline, kicker, accent, repo=""):
    """样品原版布局（2026-10-17 用户指定「偏向 cov_vs_sample_A_dark 多一点」）：
    左列大文字 + 右侧大截图卡。注意：文字从 x=60 起，超出分享安全区(367~912)，
    分享裁切时左侧会少一截——用户明确偏好此视觉效果，保留。"""
    bg = Image.new("RGB", (W, H), "#0D1117")
    d = ImageDraw.Draw(bg)

    # 顶部终端装饰条
    for i, c in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        d.ellipse([48 + i * 26, 42, 48 + i * 26 + 14, 56], fill=c)
    f_mono = load_font(FONT_MONO, 20)
    d.text((132, 40), "github.com", font=f_mono, fill="#8B949E")
    f_zh = load_font(FONT_BOLD, 20)
    d.text((132 + text_w(d, "github.com", f_mono) + 14, 40),
           "· 开源项目实测", font=f_zh, fill="#8B949E")

    # 左侧文字列（大字号，不侵入右侧卡片）
    LEFT_MAX = 690
    f_kick, _ = fit_font(d, kicker, 27, 20, LEFT_MAX)
    d.text((64, 126), kicker, font=f_kick, fill=accent)

    f_title, _ = fit_font(d, title, 92, 56, LEFT_MAX)
    d.text((60, 184), title, font=f_title, fill="#F0F6FC")

    f_num, _ = fit_font(d, numline, 88, 52, LEFT_MAX)
    draw_numline_hl(d, 60, 300, numline, f_num, accent, "#F0F6FC")

    # 底部信息条
    d.rectangle([0, H - 56, W, H], fill="#161B22")
    f_bot = load_font(FONT_BOLD, 22)
    d.text((64, H - 42), "硅基研究员", font=f_bot, fill="#8B949E")
    d.text((W - 64 - text_w(d, "AI · 开源 · 实测", f_bot), H - 42),
           "AI · 开源 · 实测", font=f_bot, fill="#8B949E")

    # 右侧截图卡（大卡，细边框 + 圆角，无多余标注）
    card_x0, card_y0, card_x1, card_y1 = 760, 108, 1216, 452
    d.rounded_rectangle([card_x0, card_y0, card_x1, card_y1], radius=14,
                        fill="#161B22", outline="#30363D", width=2)
    shot = fit_screenshot(screenshot, card_x1 - card_x0 - 24, card_y1 - card_y0 - 24)
    bg.paste(shot, (card_x0 + 12, card_y0 + 12))
    return bg


# --------------------------------------------------- A2 深色极客风 · 品牌 logo 版
def _radial_glow(diam, rgb, alpha=95):
    """圆形径向渐变光晕（中心亮 → 边缘透明），用来给 logo 垫底。"""
    img = Image.new("RGBA", (diam, diam), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, steps = diam // 2, 40
    for i in range(steps, 0, -1):
        rr = int(r * i / steps)
        a = int(alpha * (1 - i / steps) ** 1.7)
        d.ellipse([r - rr, r - rr, r + rr, r + rr], fill=tuple(rgb) + (a,))
    return img.filter(ImageFilter.GaussianBlur(max(2, diam // 26)))


def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _glow_rgb(brand_hex, accent_hex):
    """品牌色太浅（Apple/GitHub 这种近白）时用强调色打光，否则一层灰雾。"""
    rgb = _hex_rgb(brand_hex)
    return _hex_rgb(accent_hex) if _lum(rgb) > 190 else rgb


def _brand_header(d, x, y, kicker, accent):
    """kicker 小字（封面顶部那行彩色小标）"""
    f, _ = fit_font(d, kicker, 27, 20, 690)
    d.text((x, y), kicker, font=f, fill=accent)
    return f.size


def style_dark_logo(brands, title, numline, kicker, accent,
                    topbar="品牌官方 logo · 实测", brand_note=""):
    """A 风格骨架 + 右侧卡片换成「品牌 logo 墙」。
    文章写到 DeepSeek / GPT / Kimi / Claude / 千问 时，用品牌标志代替模糊截图，
    识别度更高、也更不容易踩到别人家的版权截图。

    brands: ['deepseek'] 或 ['apple', 'qwen']（多品牌并排 + × 号）
    """
    import brand_logos as BL

    bg = Image.new("RGB", (W, H), "#0D1117")
    d = ImageDraw.Draw(bg)

    # 顶部终端装饰条
    for i, c in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        d.ellipse([48 + i * 26, 42, 48 + i * 26 + 14, 56], fill=c)
    f_mono = load_font(FONT_MONO, 20)
    d.text((132, 40), "silicon-lab", font=f_mono, fill="#8B949E")
    f_zh = load_font(FONT_BOLD, 20)
    d.text((132 + text_w(d, "silicon-lab", f_mono) + 14, 40), f"· {topbar}",
           font=f_zh, fill="#8B949E")

    # 左侧文字列（与 style_dark 完全一致，保持基线统一）
    LEFT_MAX = 690
    _brand_header(d, 64, 126, kicker, accent)

    f_title, _ = fit_font(d, title, 92, 56, LEFT_MAX)
    d.text((60, 184), title, font=f_title, fill="#F0F6FC")

    f_num, _ = fit_font(d, numline, 88, 52, LEFT_MAX)
    draw_numline_hl(d, 60, 300, numline, f_num, accent, "#F0F6FC")

    # 底部信息条
    d.rectangle([0, H - 56, W, H], fill="#161B22")
    f_bot = load_font(FONT_BOLD, 22)
    d.text((64, H - 42), "硅基研究员", font=f_bot, fill="#8B949E")
    d.text((W - 64 - text_w(d, "AI · 开源 · 实测", f_bot), H - 42),
           "AI · 开源 · 实测", font=f_bot, fill="#8B949E")

    # 右侧品牌卡
    card_x0, card_y0, card_x1, card_y1 = 760, 108, 1216, 452
    d.rounded_rectangle([card_x0, card_y0, card_x1, card_y1], radius=14,
                        fill="#161B22", outline="#30363D", width=2)

    cx = (card_x0 + card_x1) // 2
    cy = (card_y0 + card_y1) // 2 - 18
    n = max(1, len(brands))

    # 先算每个 logo 的位置（多品牌并排）
    if n == 1:
        px, gap = 196, 0
    else:
        px, gap = 116, 58
    total_w = px * n + gap * (n - 1)
    x0 = cx - total_w // 2
    slots = [(x0 + i * (px + gap) + px // 2, cy) for i in range(n)]

    # 光晕：单品牌一个大光斑，多品牌各自一个（品牌色太亮时改用强调色，避免糊成灰雾）
    card_mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(card_mask).rounded_rectangle([card_x0, card_y0, card_x1, card_y1],
                                                radius=14, fill=255)
    bg_rgba = bg.convert("RGBA")
    for i, b in enumerate(brands):
        gx, gy = slots[i]
        gd = 330 if n == 1 else 220
        bg_rgba.alpha_composite(_radial_glow(gd, _glow_rgb(BL.brand_color(b), accent),
                                             100 if n == 1 else 86),
                                (gx - gd // 2, gy - gd // 2 + 6))
    bg = Image.composite(bg_rgba.convert("RGB"), bg, card_mask)
    d = ImageDraw.Draw(bg)

    # logo 本体
    for i, b in enumerate(brands):
        lg = BL.tint_logo(b, px)
        bx, by = slots[i]
        bg.paste(lg, (bx - lg.width // 2, by - lg.height // 2), lg)
        if i < n - 1:
            f_x = load_font(FONT_BOLD, 30)
            gapx = bx + px // 2 + gap // 2
            d.text((gapx - text_w(d, "×", f_x) // 2, by - 18), "×", font=f_x, fill="#8B949E")

    if n == 1:
        f_name = load_font(FONT_MONO, 24)
        nm = BL.brand_label(brands[0])
        lab = BL.brand_color(brands[0])
        lab = "#8B949E" if _lum(_hex_rgb(lab)) > 200 else lab
        d.text((cx - text_w(d, nm, f_name) // 2, cy + 124), nm, font=f_name, fill=lab)
    else:
        f_name = load_font(FONT_MONO, 20)
        nm = "  ×  ".join(BL.brand_label(b) for b in brands)
        d.text((cx - text_w(d, nm, f_name) // 2, cy + 102), nm, font=f_name, fill="#8B949E")

    # 品牌卡左上角小标签
    f_tag = load_font(FONT_MONO, 17)
    d.text((card_x0 + 18, card_y0 + 14), "LOGO", font=f_tag, fill="#484F58")

    if brand_note:
        f_note = load_font(FONT_BOLD, 19)
        d.text((card_x0 + 18, card_y1 - 34), brand_note, font=f_note, fill="#6E7681")
    return bg


def style_dark_badge(screenshot, title, numline, kicker, accent, brands,
                     topbar="开源项目实测"):
    """A 风格 + 保留真实截图卡，把品牌 logo 做成圆形徽章压在卡片左上角。
    「有真图也要有品牌」时用这个：读者一眼认品牌，细节靠截图佐证。
    """
    import brand_logos as BL

    bg = style_dark(screenshot, title, numline, kicker, accent)
    # 覆盖顶部条文案（style_dark 里写死 github.com）
    d = ImageDraw.Draw(bg)
    d.rectangle([0, 28, 700, 70], fill="#0D1117")
    for i, c in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        d.ellipse([48 + i * 26, 42, 48 + i * 26 + 14, 56], fill=c)
    f_mono = load_font(FONT_MONO, 20)
    d.text((132, 40), "silicon-lab", font=f_mono, fill="#8B949E")
    f_zh = load_font(FONT_BOLD, 20)
    d.text((132 + text_w(d, "silicon-lab", f_mono) + 14, 40), f"· {topbar}",
           font=f_zh, fill="#8B949E")

    # 卡片左上角叠徽章（略出框，像 app icon）
    card_x0, card_y0 = 760, 108
    r = 40
    for i, b in enumerate(brands):
        bx = card_x0 + 8 + i * 74
        by = card_y0 + 8
        d.ellipse([bx - r - 4, by - r - 4, bx + r + 4, by + r + 4], fill="#0D1117")
        d.ellipse([bx - r - 4, by - r - 4, bx + r + 4, by + r + 4],
                  outline=BL.brand_color(b), width=3)
        lg = BL.tint_logo(b, 46)
        bg.paste(lg, (bx - lg.width // 2, by - lg.height // 2), lg)
    return bg


# ---------------------------------------------------------------- B 杂志海报风
def style_poster(screenshot, title, numline, kicker, accent):
    bg = Image.new("RGB", (W, H), "#F6F1E7")
    d = ImageDraw.Draw(bg)

    # 左上徽章：黑底白字
    f_badge = load_font(FONT_BOLD, 24)
    badge = "GitHub 热榜 · 实测"
    bw = text_w(d, badge, f_badge) + 36
    d.rectangle([56, 46, 56 + bw, 92], fill="#111111")
    d.text((56 + 18, 54), badge, font=f_badge, fill="#F6F1E7")

    # kicker 小字
    f_kick = load_font(FONT_BOLD, 26)
    d.text((60, 122), kicker, font=f_kick, fill="#8A8577")

    # 超大标题（自动缩放，不侵入右侧卡片区）
    LEFT_MAX = 716
    f_title, _ = fit_font(d, title, 104, 56, LEFT_MAX)
    d.text((56, 168), title, font=f_title, fill="#141414")

    # 数字行 + 荧光笔高亮块
    f_num, _ = fit_font(d, numline, 104, 52, LEFT_MAX)
    y = 292
    nw = text_w(d, numline, f_num)
    d.rectangle([50, y + 16, 50 + nw + 20, y + 126], fill=accent)
    draw_numline_hl(d, 60, y, numline, f_num, "#141414", "#141414")

    # 右下截图卡：白卡 + 硬阴影（错位黑矩形）
    card_x0, card_y0 = 800, 120
    shot = fit_screenshot(screenshot, 380, 250)
    sw, sh = shot.size
    pad = 14
    d.rectangle([card_x0 + 10, card_y0 + 10, card_x0 + sw + 2 * pad + 10, card_y0 + sh + 2 * pad + 10],
                fill="#141414")  # 硬阴影
    d.rectangle([card_x0, card_y0, card_x0 + sw + 2 * pad, card_y0 + sh + 2 * pad],
                fill="#FFFFFF", outline="#141414", width=2)
    bg.paste(shot, (card_x0 + pad, card_y0 + pad))

    # 底部细线 + 署名
    d.line([56, H - 64, W - 56, H - 64], fill="#141414", width=2)
    f_bot = load_font(FONT_BOLD, 22)
    d.text((56, H - 50), "硅基研究员", font=f_bot, fill="#141414")
    d.text((W - 56 - text_w(d, "AI 开源项目实测", f_bot), H - 50),
           "AI 开源项目实测", font=f_bot, fill="#8A8577")
    return bg


# ---------------------------------------------------------------- C 渐变霓虹风
def style_neon(screenshot, title, numline, kicker, accent):
    bg = Image.new("RGB", (W, H))
    top, bottom = (26, 27, 77), (10, 11, 38)
    for yy in range(H):
        t = yy / H
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        ImageDraw.Draw(bg).line([(0, yy), (W, yy)], fill=c)

    d = ImageDraw.Draw(bg)
    LEFT_MAX = 660
    f_kick, _ = fit_font(d, kicker, 26, 20, LEFT_MAX)
    d.text((64, 106), kicker, font=f_kick, fill="#9AA0FF")
    f_title, _ = fit_font(d, title, 96, 56, LEFT_MAX)
    f_num, _ = fit_font(d, numline, 92, 52, LEFT_MAX)

    # 发光层
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.text((60, 150), title, font=f_title, fill="#FFFFFF")
    gd.text((60, 272), numline, font=f_num, fill=accent + "FF")
    bg = Image.alpha_composite(bg.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(bg)

    # 清晰文字
    d.text((60, 150), title, font=f_title, fill="#FFFFFF")
    draw_numline_hl(d, 60, 272, numline, f_num, accent, "#B8BFFF")

    # 截图卡：发光边框
    card_x0, card_y0, card_x1, card_y1 = 800, 108, 1200, 448
    card_glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cgd = ImageDraw.Draw(card_glow)
    cgd.rounded_rectangle([card_x0, card_y0, card_x1, card_y1], radius=16,
                          outline=accent + "FF", width=4)
    bg = Image.alpha_composite(bg, card_glow.filter(ImageFilter.GaussianBlur(12)))
    d = ImageDraw.Draw(bg)
    shot = fit_screenshot(screenshot, card_x1 - card_x0 - 20, card_y1 - card_y0 - 20)
    bg.paste(shot, (card_x0 + 10, card_y0 + 10))
    d.rounded_rectangle([card_x0, card_y0, card_x1, card_y1], radius=16,
                        outline=accent, width=2)

    # 底部
    f_bot = load_font(FONT_BOLD, 22)
    d.text((64, H - 46), "硅基研究员", font=f_bot, fill="#8B90C0")
    return bg.convert("RGB")


def main():
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(1)
    shot_path, title, numline, kicker, prefix = sys.argv[1:6]

    shot = Image.open(shot_path).convert("RGB")
    styles = {
        "A_dark": (style_dark, "#7EE787"),
        "B_poster": (style_poster, "#FFD23F"),
        "C_neon": (style_neon, "#7C5CFF"),
        "D_swiss": (style_swiss, "#E62E2E"),
        "E_blueprint": (style_blueprint, "#FFD23F"),
    }
    for name, (fn, acc) in styles.items():
        out = f"{prefix}_{name}.png"
        img = fn(shot, title, numline, kicker, acc)
        img.save(out)
        print("saved:", out, img.size)


if __name__ == "__main__":
    main()
