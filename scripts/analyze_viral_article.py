#!/usr/bin/env python3
"""公众号爆款文章分析（纯标准库）。

输入一篇公众号爆款文章（URL 或粘贴全文），输出结构化拆解：
爆款点 / 标题套路 / 结构 / 开头钩子 / 可复用模板 / 风险提示。

用法：
  python analyze_viral_article.py --url "文章URL"          # 用 WebFetch 交给宿主抓，本脚本给拆解模板
  python analyze_viral_article.py --text "粘贴全文"         # 直接分析粘贴的文本
  python analyze_viral_article.py --url xxx --save 输出.md  # 保存拆解报告

说明：本脚本自身不做网络抓取（抓取走宿主 WebFetch 避开 Playwright/DLL 坑），
核心价值是**固定的拆解维度**，让每个选题分析口径一致、可复用。
"""
import sys
import argparse
from pathlib import Path

# 公众号爆款拆解维度（口径单一来源，供宿主 Agent 逐项填写）
DIMENSIONS = [
    ("标题", "原标题是什么？属于哪类标题公式（数字反差/悬念/身份共鸣/对立冲突/热点借势）"),
    ("爆款点", "核心爆点是什么？戳中了读者哪个痛点/情绪/利益点"),
    ("开头钩子", "前3行怎么钩住人？(提问/反常识/场景代入/数据冲击)"),
    ("结构骨架", "章节顺序是什么？用了什么结构（清单体/观点体/故事体/对比体）"),
    ("数据支撑", "用了哪些数据/案例/引用？可信度如何？"),
    ("写作风格", "语气/人称/段落节奏？有没有活人感、口语感"),
    ("可复用模板", "这篇的骨架能否抽象成模板复用？模板长什么样"),
    ("风险提示", "有没有标题党/夸大/侵权/敏感风险？"),
]

TITLE_FORMULAS = [
    "数字反差（X个…/从…到…）",
    "悬念钩子（为什么…/竟然…）",
    "身份共鸣（写给…/普通人…）",
    "对立冲突（别再…/都错了）",
    "热点借势（结合某热点事件）",
    "干货承诺（速查/指南/清单）",
    "反常识（越…越…/其实…）",
    "情绪宣泄（气死/爽/焦虑）",
]

def render_report(title, raw):
    lines = []
    lines.append(f"# 公众号爆款文章拆解报告")
    lines.append("")
    lines.append(f"> 分析对象：{title}")
    lines.append("")
    lines.append("## 一、标题公式判断")
    lines.append("")
    lines.append("可能的标题公式（可多选）：")
    for f in TITLE_FORMULAS:
        lines.append(f"- [ ] {f}")
    lines.append("")
    lines.append("## 二、逐维度拆解")
    lines.append("")
    for name, desc in DIMENSIONS:
        lines.append(f"### {name}")
        lines.append(f"*（{desc}）*")
        lines.append("")
        lines.append("> 待填写")
        lines.append("")
    lines.append("## 三、可复用选题结论")
    lines.append("")
    lines.append("- 本篇值得模仿的点：")
    lines.append("- 我们能借鉴的选题方向：")
    lines.append("- 差异化空间（我们账号能比它做得更好的是什么）：")
    lines.append("")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(description="公众号爆款文章拆解")
    ap.add_argument("--url", help="爆款文章 URL（宿主用 WebFetch 抓取后再跑 --text 填入正文）")
    ap.add_argument("--text", help="爆款文章全文/要点")
    ap.add_argument("--save", help="保存拆解报告到文件")
    args = ap.parse_args()

    if args.url:
        print(f"已登记 URL: {args.url}")
        print(">>> 请宿主 Agent 用 WebFetch 抓取该 URL 正文，然后用 --text 传入正文重跑本脚本，得到完整拆解。")
        print(">>> 抓取避开 Playwright（本机 WDAC 拦 DLL），一律走 WebFetch。")
        if args.save:
            Path(args.save).write_text(render_report(args.url, ""), encoding="utf-8")
            print(f"报告模板已保存: {args.save}")
        return

    if args.text:
        title = args.text.strip().split("\n")[0][:40] if args.text.strip() else "未命名"
        report = render_report(title, args.text)
        if args.save:
            Path(args.save).write_text(report, encoding="utf-8")
            print(f"✅ 拆解报告已保存: {args.save}")
            print("   报告含 8 个拆解维度，请宿主 Agent 结合文章内容逐项填写。")
        else:
            print(report)
        return

    print("用法: python analyze_viral_article.py --url <URL> 或 --text <全文> [--save 输出.md]")
    print("本脚本给出统一的爆款拆解维度（口径单一来源），供每次选题分析保持一致。")
    sys.exit(0)

if __name__ == "__main__":
    main()
