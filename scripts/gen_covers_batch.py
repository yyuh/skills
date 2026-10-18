# -*- coding: utf-8 -*-
"""批量生成 5 篇文章的 A 风格（深色极客）封面，每篇按内容选图/强调色。

封面图选择原则（2026-10-17 用户要求：不要一刀切，按文章内容来）:
  1. VoiceStudio   → vs_clone.png        真实界面截图（界面含 LANGUAGE 646，佐证标题）
  2. AI科学家      → sas_rnaseq.png      项目工作流图（真实项目资产，非 OG 卡）
  3. rea 逆向      → og_rea.png          GitHub 项目卡（CLI 工具无界面）
  4. MiniCPM       → gen_minicpm_memory.png  自生成数据图（35B→3GB 内存对比）
  5. 苹果千问      → ap_1.jpg            彭博社报道截图（新闻实证）

输出: outputs/cov_<key>.png（1280x545，安全区合规：文字在 x384~912）
"""
import os
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cover_styles import style_dark  # noqa: E402

ARTICLES = [
    dict(key="voicestudio", img="outputs/vs_clone.png",
         title="开源版ElevenLabs", numline="6.8万星 · 646种语言",
         kicker="GitHub 热榜项目实测", accent="#7EE787",
         repo="debpalash/VoiceStudio"),
    dict(key="sciskills", img="outputs/sas_rnaseq.png",
         title="AI助手变AI科学家", numline="5万星 · 177个技能",
         kicker="GitHub 热榜项目实测", accent="#56D4DD",
         repo="scientific-agent-skills"),
    dict(key="rea", img="outputs/og_rea.png",
         title="让AI帮你逆向工程", numline="261k星 · App底层全看光",
         kicker="GitHub 热榜项目实测", accent="#FFA657",
         repo="morluto/rea"),
    dict(key="minicpm", img="outputs/gen_minicpm_memory.png",
         title="35B塞进3G内存", numline="iPhone断网秒答 · 国产开源",
         kicker="面壁智能 · 端侧实测", accent="#B48EFF",
         repo="OpenBMB/MiniCPM-V"),
    dict(key="appleqwen", img="outputs/ap_1.jpg",
         title="苹果智能接入千问", numline="库克确认 · 月底就能试",
         kicker="AI 新闻实测", accent="#6EA8FF",
         repo="Apple Intelligence + Qwen"),
]


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    for a in ARTICLES:
        shot = Image.open(a["img"]).convert("RGB")
        img = style_dark(shot, a["title"], a["numline"], a["kicker"], a["accent"], a["repo"])
        out = f"outputs/cov_{a['key']}.png"
        img.save(out)
        print("saved:", out, img.size)


if __name__ == "__main__":
    main()
