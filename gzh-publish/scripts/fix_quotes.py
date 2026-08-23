#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复公众号排版 HTML 文本节点里的半角引号 → 全角引号。

只处理标签之间的文本（>text<），不碰 HTML 属性引号。
用法：python fix_quotes.py <html文件路径>
"""
import re
import sys


def main():
    if len(sys.argv) < 2:
        print("用法: python fix_quotes.py <html文件路径>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        html = f.read()

    count = [0]

    def fix_text(m):
        text = m.group(1)
        # 成对替换 "xxx" → “xxx”
        new = re.sub(r'"([^"]*)"', "\u201c\\1\u201d", text)
        if new != text:
            count[0] += len(re.findall(r"\u201c", new))
        return ">" + new + "<"

    html = re.sub(r">([^<>]+)<", fix_text, html)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"已替换 {count[0]} 对半角引号 → 全角：{path}")


if __name__ == "__main__":
    main()
