#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复公众号排版 HTML 文本节点里的半角引号 → 全角引号。

只处理标签之间的文本（>text<），不碰 HTML 属性引号。
- 双引号 "xxx" → “xxx”（中文正文里几乎一定是中文引号）
- 单引号 'xxx' → ‘xxx’：仅当引号内部含中文字符才转，
  避免误伤英文撇号（it's、don't）与纯英文引号（'hello'）
用法：python fix_quotes.py <html文件路径>
"""
import os
import re
import sys

# 中文字符范围（用于判断单引号是否该转全角）
CJK = re.compile(r"[\u4e00-\u9fff]")


def main():
    if len(sys.argv) < 2:
        print("用法: python fix_quotes.py <html文件路径>")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"✗ 找不到文件: {path}")
        sys.exit(1)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            html = f.read()
    except OSError as e:
        print(f"✗ 无法读取文件: {path}（{e}）")
        sys.exit(1)

    count = [0]

    def fix_text(m):
        text = m.group(1)
        # 成对替换 "xxx" → “xxx”
        new = re.sub(r'"([^"]*)"', "\u201c\\1\u201d", text)
        # 成对单引号 'xxx' → ‘xxx’：先保护英文撇号（it's/don't/'90s），
        # 再对内部含中文的成对单引号转全角，最后还原撇号
        protected = re.sub(r"(?<=[A-Za-z0-9])'|'(?=[A-Za-z0-9])",
                           "\x01", new)
        new = re.sub(r"'([^']*[\u4e00-\u9fff][^']*)'",
                     "\u2018\\1\u2019", protected)
        new = new.replace("\x01", "'")
        if new != text:
            count[0] += len(re.findall(r"[\u201c\u2018]", new))
        return ">" + new + "<"

    html = re.sub(r">([^<>]+)<", fix_text, html)

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    except OSError as e:
        print(f"✗ 无法写入文件（只读或被占用）: {path}（{e}）")
        sys.exit(1)

    print(f"已替换 {count[0]} 对半角引号 → 全角：{path}")


if __name__ == "__main__":
    main()
