# -*- coding: utf-8 -*-
"""生成 MiniCPM-V 封面用数据图：35B 参数 → 3GB 内存对比（深色极客风，配 A 风格封面）。

输出: outputs/gen_minicpm_memory.png (1200x890, 4:3 适配封面截图卡)
设计: 深色底 + 两组内存对比横条（同级模型 ~21GB vs MiniCPM-V 3GB）+ 中央 35B→3GB 大数字
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 890
BG = "#0D1117"
CARD = "#161B22"
LINE = "#30363D"
WHITE = "#F0F6FC"
GRAY = "#8B949E"
GREEN = "#7EE787"
RED = "#FF7B72"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([8, 8, W - 8, H - 8], radius=20, fill=CARD, outline=LINE, width=2)

    # 顶部标签
    f_tag = font(FONT_MONO, 30)
    d.text((56, 44), "$ MiniCPM-V 4.5 memory footprint", font=f_tag, fill=GRAY)

    # 中央大数字：35B -> 3GB
    f_big = font(FONT_BOLD, 150)
    f_unit = font(FONT_BOLD, 44)
    d.text((56, 120), "35B", font=f_big, fill=WHITE)
    w35 = d.textlength("35B", font=f_big)
    d.text((56 + w35 + 16, 210), "参数", font=f_unit, fill=GRAY)
    ax = 56 + w35 + 130
    d.text((ax, 150), "→", font=font(FONT_BOLD, 110), fill=GREEN)
    d.text((ax + 130, 120), "3GB", font=f_big, fill=GREEN)
    w3 = d.textlength("3GB", font=f_big)
    d.text((ax + 130 + w3 + 16, 210), "内存", font=f_unit, fill=GRAY)

    # 分隔线
    d.line([(56, 330), (W - 56, 330)], fill=LINE, width=2)
    f_sec = font(FONT_BOLD, 34)
    d.text((56, 356), "跑起来要占的内存", font=f_sec, fill=WHITE)

    # 对比条 1：同级稠密模型 ~21GB
    f_lbl = font(FONT_BOLD, 34)
    f_val = font(FONT_MONO, 36)
    bar_x, bar_w_max = 56, W - 56 - 200
    d.text((bar_x, 430), "同级 7B 稠密模型", font=f_lbl, fill=GRAY)
    d.text((bar_x, 478), "~21 GB", font=f_val, fill=RED)
    y1 = 530
    d.rounded_rectangle([bar_x, y1, bar_x + bar_w_max, y1 + 54], radius=12, fill="#3A1D24")
    d.rounded_rectangle([bar_x, y1, bar_x + bar_w_max, y1 + 54], radius=12, outline=RED, width=2)
    # 斜纹填充表示"太重"
    for i in range(0, bar_w_max, 40):
        d.line([(bar_x + i, y1 + 54), (bar_x + i + 30, y1)], fill="#5A2A33", width=6)

    # 对比条 2：MiniCPM-V 3GB
    d.text((bar_x, 620), "MiniCPM-V 4.5", font=f_lbl, fill=WHITE)
    d.text((bar_x, 668), "3 GB", font=f_val, fill=GREEN)
    y2 = 720
    bar2_w = int(bar_w_max * 3 / 21)
    d.rounded_rectangle([bar_x, y2, bar_x + bar_w_max, y2 + 54], radius=12, fill="#12261C")
    d.rounded_rectangle([bar_x, y2, bar_x + bar2_w, y2 + 54], radius=12, fill=GREEN)

    # 底部结论
    f_bot = font(FONT_BOLD, 36)
    d.text((56, 812), "iPhone 本地跑 · 不联网 · 不上传", font=f_bot, fill=GREEN)

    img.save("outputs/gen_minicpm_memory.png")
    print("saved: outputs/gen_minicpm_memory.png", img.size)


if __name__ == "__main__":
    main()
