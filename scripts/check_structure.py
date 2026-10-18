# -*- coding: utf-8 -*-
"""公众号正文结构体检：把「写得好不好」里能机器判的部分量化出来。

为什么需要：封面解决了「点不点」，结构决定「读不读完」。排版校验只管合规（标签/引号/密度），
管不了阅读节奏——小节过长、全篇没一个加粗金句、结尾没有提问，这些都会被漏掉。

检查项（对照 references/rewrite-rules.md）：
  1. 字数区间（500–2000，超 2000 或不足 500 报警）
  2. 小节数（3–5）与单节字数（≤380，超了建议拆分）
  3. 段落最长字数（≤150，手机三行以内）
  4. 加粗金句数（正文级 font-weight:700 且 ≤20 字，要求 ≥2 处）
  5. 图片占位数（3–4）
  6. 代码块数（有实操内容时 ≥1）
  7. 结尾三件套：封闭式提问 / 行动指令 / 固定关注语
  8. 开头钩子：前 120 字是否出现具体数字

用法:
  python scripts/check_structure.py "outputs/xxx_排版(clean-tech).html" [...]
  python scripts/check_structure.py outputs/*_排版*.html --json
"""
import argparse
import glob
import json
import os
import re
import sys

FIXED_CTA = "点击下方卡片，关注硅基研究员"


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def text_of(html):
    return re.sub(r"\s+", "", strip_tags(html))


def parse(path):
    html = open(path, encoding="utf-8", errors="ignore").read()
    body = html[html.find("<body"):] if "<body" in html else html
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", body, flags=re.S)

    full = text_of(body)
    paras = [p for p in re.findall(r"<p[^>]*>(.*?)</p>", body, flags=re.S)]

    def ptext(p):
        return re.sub(r"\s+", "", strip_tags(p))

    # 代码块：深色底或 pre
    code_blocks = len(re.findall(r"background(?:-color)?:\s*#1E293B|<pre", body))

    # 段落 = 完整 <p ...>内容</p>（样式写在开标签上，必须连标签一起看）
    plist = list(re.finditer(r"<p([^>]*)>(.*?)</p>", body, flags=re.S))

    def ptext(m):
        return re.sub(r"\s+", "", strip_tags(m.group(2)))

    # 小节标题：font-weight:700 + font-size 16–18px
    sec_titles = []
    for m in plist:
        attr = m.group(1)
        if re.search(r"font-weight:\s*(?:700|bold)", attr) and re.search(r"font-size:\s*1[6-8]px", attr):
            t = ptext(m)
            # 文末关注引导也用同样的加粗样式，不算正文小节
            if t and "图片占位符" not in t and FIXED_CTA not in t:
                sec_titles.append(t)
    n_sec = len(sec_titles)

    # 正文加粗金句：weight 700 但字号不是小节标题那种（15px 左右），且 ≤20 字
    gold = []
    for m in plist:
        attr = m.group(1)
        if re.search(r"font-weight:\s*(?:700|bold)", attr) and not re.search(r"font-size:\s*1[6-8]px", attr):
            t = ptext(m)
            if 0 < len(t) <= 20:
                gold.append(t)

    # 按小节切分正文，算每节字数（用开标签样式定位）
    marks = [m.start() for m in plist
             if re.search(r"font-weight:\s*(?:700|bold)", m.group(1))
             and re.search(r"font-size:\s*1[6-8]px", m.group(1))
             and FIXED_CTA not in ptext(m)]
    sec_lens = []
    if marks:
        sec_lens.append(("(开头)", len(text_of(body[:marks[0]]))))
        for i, start in enumerate(marks):
            end = marks[i + 1] if i + 1 < len(marks) else len(body)
            label = sec_titles[i] if i < len(sec_titles) else f"第{i + 1}节"
            sec_lens.append((label, len(text_of(body[start:end]))))
    else:
        sec_lens.append(("(全文)", len(full)))

    plens = [len(ptext(m)) for m in plist if ptext(m)]
    imgs = len(re.findall(r"图片占位符", body))

    # 结尾检测
    tail = full[-260:]
    has_cta = FIXED_CTA in full
    has_question = bool(re.search(r"[？?]", tail))
    has_action = bool(re.search(
        r"(评论区|点关注|关注我|后台回复|加我|收藏|点下方|建议你|现在就去|转发|留言|试试|跑一遍|试一下)", tail))

    # 开头数字
    head120 = full[:120]
    has_num = bool(re.search(r"\d", head120))

    # 长段落
    long_paras = sum(1 for l in plens if l > 150)

    return dict(
        file=os.path.basename(path),
        chars=len(full),
        n_sec=n_sec,
        sec_titles=sec_titles,
        sec_lens=sec_lens,
        max_para=max(plens) if plens else 0,
        long_paras=long_paras,
        gold=gold,
        imgs=imgs,
        code_blocks=code_blocks,
        has_cta=has_cta,
        has_question=has_question,
        has_action=has_action,
        head_has_num=has_num,
    )


def verdict(r):
    """返回 (ERROR 列表, WARN 列表)"""
    err, warn = [], []
    if r["chars"] < 500:
        err.append(f"字数 {r['chars']} < 500，信息量不足")
    if r["chars"] > 2000:
        err.append(f"字数 {r['chars']} > 2000，需拆分或删冗余")
    if not 3 <= r["n_sec"] <= 5:
        err.append(f"小节数 {r['n_sec']} 不在 3–5 之间")
    for label, n in r["sec_lens"]:
        if n > 380:
            warn.append(f"小节「{label}」{n} 字偏长（建议 ≤380，拆一节）")
    if r["max_para"] > 150:
        warn.append(f"最长段落 {r['max_para']} 字（手机超出 3 行，建议断句）")
    if len(r["gold"]) < 2:
        warn.append(f"加粗金句只有 {len(r['gold'])} 处（要求 ≥2）")
    if not 3 <= r["imgs"] <= 4:
        warn.append(f"正文配图 {r['imgs']} 张（要求 3–4 张）")
    if r["code_blocks"] == 0:
        warn.append("没有代码块（实操类文章至少 1 段命令行/配置）")
    if not r["has_question"]:
        warn.append("结尾没有封闭式提问（读者打字越少越愿意回）")
    if not r["has_action"]:
        warn.append("结尾缺行动指令（点关注/评论区/回复关键词）")
    if not r["has_cta"]:
        err.append("缺少固定关注语")
    if not r["head_has_num"]:
        warn.append("开头 120 字内没有具体数字，钩子偏弱")
    return err, warn


def print_report(r):
    err, warn = verdict(r)
    print("=" * 62)
    print(f"📄 {r['file']}")
    print(f"   字数 {r['chars']} | 小节 {r['n_sec']} | 段落最长 {r['max_para']} | "
          f"配图 {r['imgs']} | 代码块 {r['code_blocks']} | 金句 {len(r['gold'])}")
    for label, n in r["sec_lens"]:
        flag = " ⚠️" if n > 380 else ""
        print(f"     · {label[:26]:<28} {n:4d} 字{flag}")
    if r["gold"]:
        print("   金句:", " / ".join(r["gold"]))
    for e in err:
        print("   ❌", e)
    for w in warn:
        print("   ⚠️ ", w)
    if not err and not warn:
        print("   ✅ 结构合格")
    print(f"   结尾: 提问={'有' if r['has_question'] else '无'} "
          f"行动={'有' if r['has_action'] else '无'} 关注语={'有' if r['has_cta'] else '无'}")
    return len(err), len(warn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    paths = []
    for f in a.files:
        paths.extend(glob.glob(f))
    if not paths:
        print("没找到文件")
        sys.exit(1)

    total_e = total_w = 0
    results = []
    for p in paths:
        r = parse(p)
        results.append(r)
        if a.json:
            continue
        e, w = print_report(r)
        total_e += e
        total_w += w
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    print("=" * 62)
    print(f"合计: {len(paths)} 篇 | ERROR {total_e} | WARNING {total_w}")
    sys.exit(1 if total_e else 0)


if __name__ == "__main__":
    main()
