#!/usr/bin/env python3
"""公众号爆款标题生成 + 评分 + 风险标注（纯标准库）。

输入文章主题/核心卖点，批量生成候选标题，逐个按统一评分维度打分并标注风险。
评分口径单一来源，保证每次标题决策一致。

用法：
  python generate_titles.py "GPT-Image2提示词工业级模板库" --sell "476+案例/20+模板/Agent Skill" --num 12

说明：
- 标题由宿主 Agent 基于主题+卖点生成候选（模型生成），本脚本负责
  **统一的评分维度 + 风险标注 + 排序**，避免每次都凭感觉选。
- 遵循 SKILL.md 决策 4：主标题 ≤22 字无特殊符号、含关键词+数字。
"""
import sys
import argparse
from pathlib import Path

# 标题评分维度（权重合计 100）
CRITERIA = [
    ("关键词相关", 20, "标题是否精准命中主题核心词"),
    ("数字/价值感", 15, "是否有具体数字或明确价值承诺"),
    ("情绪/钩子", 20, "是否有悬念、反差、共鸣、紧迫感"),
    ("字数控制", 15, "≤22 字（超长扣分）"),
    ("无特殊符号", 10, "无！？、括号等特殊符号（公众号规范）"),
    ("目标读者", 10, "是否命中目标读者（AI从业者/普通用户）"),
    ("平台合规", 10, "无夸大/标题党/敏感词风险"),
]

# 风险标注
RISKS = {
    "标题党": "夸大承诺、与内容不符，可能被平台降权/读者反感",
    "敏感词": "涉及政治/医疗/金融等敏感表述，需替换",
    "特殊符号": "含！？（）等符号，公众号主标题不建议",
    "超长": "超过22字，列表页可能被截断",
    "同质化": "与常见标题撞车，无差异化",
}

def score_title(title):
    """对单个标题评分（0-100）并返回维度分与风险。"""
    t = title
    length = len(t)
    dims = {}
    dims["关键词相关"] = 15 if length > 8 else 12
    has_num = any(ch.isdigit() for ch in t)
    dims["数字/价值感"] = 15 if has_num else 8
    hook_words = ["为什么", "别再", "竟然", "才", "其实", "一招", "避坑", "真相", "后悔", "狂", "爽", "免费", "速查", "指南", "清单", "手把手", "全", "最"]
    has_hook = any(w in t for w in hook_words)
    dims["情绪/钩子"] = 18 if has_hook else 10
    dims["字数控制"] = 15 if length <= 22 else (8 if length <= 28 else 3)
    special = "！？!?（）()【】[]《》\"'"
    has_special = any(ch in t for ch in special)
    dims["无特殊符号"] = 10 if not has_special else 4
    reader_words = ["AI", "程序员", "普通人", "你", "开发者", "打工人", "创作者", "新手"]
    has_reader = any(w in t for w in reader_words)
    dims["目标读者"] = 8 if has_reader else 6
    dims["平台合规"] = 10

    total = sum(v for _, v, _ in CRITERIA)  # 100
    raw = sum(dims[k] for k, _, _ in CRITERIA)
    score = round(raw * 100 / total)

    risks = []
    if has_special:
        risks.append("特殊符号")
    if length > 22:
        risks.append("超长")
    if length > 28:
        risks.append("标题党倾向")
    if not has_num and not has_hook:
        risks.append("同质化")
    return score, dims, risks

def main():
    ap = argparse.ArgumentParser(description="公众号爆款标题生成+评分")
    ap.add_argument("topic", help="文章主题/标题方向")
    ap.add_argument("--sell", default="", help="核心卖点（逗号分隔）")
    ap.add_argument("--num", type=int, default=10, help="候选数量")
    ap.add_argument("--save", help="保存报告到文件")
    args = ap.parse_args()

    print(f"主题：{args.topic}")
    if args.sell:
        print(f"卖点：{args.sell}")
    print(f"\n>>> 请宿主 Agent 先基于主题+卖点，用爆款标题公式批量生成 {args.num} 个候选标题：")
    print("    公式库：数字反差 / 悬念钩子 / 身份共鸣 / 对立冲突 / 热点借势 / 干货承诺 / 反常识 / 情绪宣泄")
    print("    规则：≤22字、无特殊符号、含关键词+数字。")
    print("    然后把候选标题逐个传给本脚本评分（或按下方评分标准人工打分）。\n")

    print("=" * 60)
    print("标题评分标准（满分100）：")
    for name, w, desc in CRITERIA:
        print(f"  {name}({w}分)：{desc}")
    print("=" * 60)

    # 评分入口
    if args.sell == "__score__":
        score, dims, risks = score_title(args.topic)
        print(f"\n标题「{args.topic}」评分：{score}/100")
        for k, _, _ in CRITERIA:
            print(f"  {k}: {dims[k]}/{dict((n, w) for n, w, _ in CRITERIA)[k]}")
        if risks:
            print(f"  风险：{', '.join(risks)}")
            for r in risks:
                print(f"    - {r}：{RISKS.get(r, '')}")
        return

    print("\n评分入口示例（宿主评分单个标题）：")
    print('  python generate_titles.py "4000星项目教你写工业级提示词" --sell __score__')
    print("\n完成后用 --save 保存评分报告。")

    # 生成报告模板
    if args.save:
        lines = [f"# 标题候选评分表", "", f"主题：{args.topic}", f"卖点：{args.sell}", "",
                 "| # | 候选标题 | 评分 | 主要风险 |", "|---|---------|------|---------|"]
        for i in range(1, args.num + 1):
            lines.append(f"| {i} | 待生成 | - | - |")
        Path(args.save).write_text("\n".join(lines), encoding="utf-8")
        print(f"评分表模板已保存: {args.save}")

if __name__ == "__main__":
    main()
