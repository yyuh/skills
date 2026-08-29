#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一缩放公众号 HTML / 组件库里的 font-size，使正文在手机上一行约 15 个汉字。

规则：
- 对所有 style="..." 里的 font-size:Npx 乘以 FACTOR（默认 1.47），四舍五入，上限 CAP。
- 跳过含等宽字体（monospace，代码块）的 style —— 代码保持原尺寸。
- 跳过 font-size:0（红绿灯圆点等隐藏文字）。
- 仅处理 px 单位，不动 width/height/letter-spacing/line-height。

用法：
  python scripts/rescale_fonts.py 文件1 [文件2 ...]
  python scripts/rescale_fonts.py --factor 1.47 --cap 44 文件
"""
import sys
import re

FACTOR = 1.47
CAP = 44


def scale_text(text: str) -> str:
    def repl_style(m):
        style = m.group(1)
        if "monospace" in style or "font-size:0" in style:
            return m.group(0)
        def repl_fs(fm):
            n = int(fm.group(1))
            if n == 0:
                return fm.group(0)
            new = min(round(n * FACTOR), CAP)
            return f"font-size:{new}px"
        new_style = re.sub(r"font-size:(\d+)px", repl_fs, style)
        return f'style="{new_style}"'

    return re.sub(r'style="([^"]*)"', repl_style, text)


def main():
    global FACTOR, CAP
    args = sys.argv[1:]
    factor = FACTOR
    cap = CAP
    files = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--factor":
            factor = float(args[i + 1]); i += 2; continue
        if a == "--cap":
            cap = int(args[i + 1]); i += 2; continue
        files.append(a); i += 1

    if not files:
        print("用法: python rescale_fonts.py [--factor 1.47] [--cap 44] 文件 ...")
        sys.exit(1)

    FACTOR, CAP = factor, cap

    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"[跳过] {path}: 读取失败 {e}")
            continue
        new = scale_text(text)
        if new != text:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            # 统计改动处
            before = len(re.findall(r"font-size:(\d+)px", text))
            after = len(re.findall(r"font-size:(\d+)px", new))
            print(f"[已写] {path}: 处理 {before} 处 font-size")
        else:
            print(f"[无变化] {path}")


if __name__ == "__main__":
    main()
