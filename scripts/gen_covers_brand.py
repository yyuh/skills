# -*- coding: utf-8 -*-
"""按文章涉及品牌生成封面（logo 版）。

规则（2026-10-18 用户两次校准后定稿，简单说两句话）：
  - **AI 新闻类**：是谁的新闻就放谁的 logo——DeepSeek 发模型放鲸鱼、GPT-6 Sol 放 OpenAI、
    Kimi 放 K、Claude 出事放 Claude 星芒、苹果入华放 Apple × Qwen。
  - **GitHub 开源项目类**：照旧用真实截图（选项A~E），不放品牌 logo——项目不是「某家的新闻」，
    读者要看的是这个仓库/工具本身长什么样。
  - 有真图但也想露品牌的新闻，可用 badge 形态（截图 + logo 圆形徽章）。

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

# ---------------- 新闻类（放品牌 logo） ----------------
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
              title="安全对齐没兜住", numline="断网环境 · 结果连了网",
              kicker="Anthropic 自己承认 · 9月9日报告", accent="#D97757",
              note="Claude · 官方 logo", shot=None)

# ---------------- 开源项目类（照旧放截图，不走 logo 卡） ----------------
# 例：rea 逆向工程（261k 星）、VoiceStudio、MiniCPM —— 一律用真实界面/仓库卡/自生成数据图，
# 见 gen_covers_batch.py 的 style_dark 配置，不要套品牌 logo。



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
