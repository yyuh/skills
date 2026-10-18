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
    }
    for name, (fn, acc) in styles.items():
        out = f"{prefix}_{name}.png"
        img = fn(shot, title, numline, kicker, acc)
        img.save(out)
        print("saved:", out, img.size)


if __name__ == "__main__":
    main()
