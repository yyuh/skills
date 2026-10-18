# -*- coding: utf-8 -*-
"""按文章涉及品牌生成封面（logo 版）。

原则（2026-10-18 用户要求）：封面插图跟着文章走——写到哪家就放哪家官方 logo，
DeepSeek / GPT / Kimi / Claude / 千问 都是现成素材，不再一律塞一张截图。

两种形态:
  logo 版  style_dark_logo  —— 右侧卡片 = 品牌 logo 墙（品牌色光晕 + 官方标志 + 名号）
  badge 版 style_dark_badge —— 保留真实截图，logo 做圆形徽章压在卡片左上角

brands 可用 key 见 scripts/brand_logos.py 的 BRANDS（deepseek / openai / claude /
kimi / moonshot / qwen / gemini / meta / mistral / bytedance / doubao / hunyuan /
baidu / alibaba / minimax / perplexity / huggingface / github / apple / nvidia ...）

输出: outputs/covb_<key>.png
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cover_styles import style_dark_logo, style_dark_badge  # noqa: E402

DEEPSEEK = dict(key="deepseek", brands=["deepseek"],
                title="反超Opus 5", numline="77.0分 · 只管编程",
                kicker="DeepSeek V4.1 Flash · 半夜偷发", accent="#4D6BFE",
                note="官方 logo · 模型卡实测", shot="outputs/news_ds_bench.png")

APPLEQWEN = dict(key="appleqwen", brands=["apple", "qwen"],
                 title="国行苹果智能批了", numline="10月底测试 · 12月转正",
                 kicker="苹果 × 阿里千问 · 库克确认", accent="#6EA8FF",
                 note="Apple × Qwen · 合规长跑两年", shot=None)

KIMI = dict(key="kimi", brands=["kimi"],
            title="百万字上下文全免费", numline="所有档位 · 免费也能用",
            kicker="Kimi K2.8 Preview · 9月11日", accent="#1783FF",
            note="官方 logo · 月之暗面", shot=None)

GPTSOL = dict(key="gpt6sol", brands=["openai"],
              title="比Astra快6倍", numline="10秒 → 1.5秒",
              kicker="GPT-6 Sol 隐藏版内测", accent="#10A37F",
              note="OpenAI · 快慢双模型", shot=None)

CLAUDE = dict(key="claude", brands=["claude"],
              title="逆向工程全自动", numline="261k星 · 底层看光",
              kicker="Claude Code 生态实测", accent="#D97757",
              note="Anthropic · 官方 logo", shot=None)


def gen(a, mode="logo"):
    if mode == "badge":
        if not a.get("shot"):
            return None
        shot = Image.open(a["shot"]).convert("RGB")
        return style_dark_badge(shot, a["title"], a["numline"], a["kicker"],
                                a["accent"], a["brands"])
    return style_dark_logo(a["brands"], a["title"], a["numline"], a["kicker"],
                           a["accent"], brand_note=a.get("note", ""))


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    jobs = [(DEEPSEEK, "logo"), (DEEPSEEK, "badge"), (APPLEQWEN, "logo"),
            (KIMI, "logo"), (GPTSOL, "logo"), (CLAUDE, "logo")]
    for a, mode in jobs:
        img = gen(a, mode)
        if img is None:
            print("skip (缺截图):", a["key"], mode)
            continue
        out = f"outputs/covb_{a['key']}_{mode}.png"
        img.save(out)
        print("saved:", out, img.size)


if __name__ == "__main__":
    main()
