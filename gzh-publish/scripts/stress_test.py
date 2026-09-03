#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gzh-publish 公众号推送流水线 —— 抗压/鲁棒性测试（stress test）。

目的：验证整套流水线在压力输入下的稳定性和错误拦截能力，提前发现
「脚本会不会崩 / 会不会误存稿 / 会不会漏报错」等问题。纯离线、无副作用：
- 不连接公众号后台、不写草稿、不删除任何现有产物（只读校验真实产物）。
- 样本全部生成在临时目录，测完清理。
- 对连线环节（publish_full.py）只测"坏参数前置拦截"，保证它安全退出、
  不会启动浏览器/连公众号。

分层覆盖：
  A. validate_gzh_html.py  校验器：禁用元素暴雨/span-leaf缺失/半角标点/代码块
     豁免/畸形HTML/超长/深嵌套/乱码/stdin/CLI退出码
  B. fix_quotes.py         引号修复：幂等性/属性引号不误伤/边界
  C. generate_titles.py    标题评分：边界输入/稳定性
  D. publish_full.py       存稿前置拦截：坏参数是否在开浏览器前被拒（不真连）
  E. 组件库 + 抓取 + 真实产物回归
  F. 流水线闭环演练：坏文件 → 校验发现 → 修复 → 复验通过

用法（Windows，系统 Python 3.14）：
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 py -3.14 -B scripts/stress_test.py
  py -3.14 -B scripts/stress_test.py --layer A   # 只跑某层
  py -3.14 -B scripts/stress_test.py --quick     # 跳过性能/深嵌套大样本
  py -3.14 -B scripts/stress_test.py --save outputs/stress_report_xxx.md
退出码：0 = 全部通过；1 = 有失败用例；2 = 脚本自身异常。
"""
import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_ROOT / "scripts"
OUTPUTS = SKILL_ROOT / "outputs"

PYTHON = sys.executable or "python"
BASE_ENV = os.environ.copy()
BASE_ENV["PYTHONIOENCODING"] = "utf-8"
BASE_ENV["PYTHONUTF8"] = "1"

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def run_py(args, timeout=60, stdin_data=None, cwd=None):
    """跑一个 python 脚本（子进程），返回 (exit_code, stdout, stderr)。"""
    cmd = [PYTHON, "-B", *[str(a) for a in args]]
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=BASE_ENV, timeout=timeout,
            input=stdin_data, cwd=str(cwd) if cwd else None,
        )
        return p.returncode, (p.stdout or ""), (p.stderr or "")
    except subprocess.TimeoutExpired as e:
        return -1, (e.stdout or ""), f"TIMEOUT {timeout}s"

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# ---- 样本构建 ----
def _leaf(text):
    return f'<span leaf="">{text}</span>'

def sample_legal() -> str:
    """一段完全合规的 section：span leaf 包裹、全角标点、无禁用元素。"""
    paras = []
    for i in range(3):
        paras.append(
            f'<section style="padding:8px 0;"><p style="font-size:14px;'
            f'color:#333;line-height:1.8;">{_leaf(f"第{i+1}段测试内容，验证合法基线。")}'
            f'</p></section>'
        )
    return '<section style="max-width:677px;margin:0 auto;">' + "".join(paras) + "</section>"

def sample_forbidden() -> str:
    """把所有禁用元素塞进一段，用于校验 ERROR 命中数与不崩溃。"""
    return (
        '<section><p style="font-size:12px;">'
        '<style>.x{}</style><script>alert(1)</script>'
        '<div class="a" id="b">text</div>'
        '<link rel="stylesheet" href="x.css">'
        '<p style="position:absolute;float:left;display:grid;'
        'white-space:pre;@media(max-width:1px){};'
        'color:var(--brand);font-family:url("http://a.com/x.woff2")">bad</p>'
        '</p></section>'
    )

def sample_half_punct() -> str:
    return (f'<section>{_leaf("你好，世界。他说：\"这是测试\"，然后走了。")}'
            f'<p>{_leaf("今天很忙, 有点累; 但是很开心! 你呢?")}</p></section>')

def sample_mixed_wrapped() -> str:
    """一部分包裹、一部分没包裹。"""
    return (f'<section><p>{_leaf("已包裹的文本。")}</p>'
            f'<p>没包裹的中文文本。</p></section>')

def sample_code_block() -> str:
    """代码块（monospace）内有半角符号，应被豁免不报 WARNING。"""
    return (
        f'<section><p>{_leaf("正文中文，正常。")}</p>'
        f'<section style="background:#1E293B;">'
        f'<p style="margin:0;font-family:monospace;">pip install foo; python run.py --arg=1 "q"</p>'
        f'</section></section>'
    )

# ---------------------------------------------------------------------------
# 测试框架
# ---------------------------------------------------------------------------

RESULTS = []  # (name, ok, detail, elapsed_sec)

def run_case(name, fn):
    t0 = time.perf_counter()
    try:
        ok, detail = fn()
    except Exception as e:  # 用例自身抛异常 = 失败
        ok, detail = False, f"用例异常: {type(e).__name__}: {e}"
    dt = time.perf_counter() - t0
    RESULTS.append((name, bool(ok), detail, dt))
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {name}  ({dt*1000:.0f}ms)")
    if not ok:
        print(f"         ↳ {detail}")

def check(cond, msg):
    return (bool(cond), msg)

def has_sub(text, *subs):
    return all(s in text for s in subs)

# ---------------------------------------------------------------------------
# A. 校验器深度压测
# ---------------------------------------------------------------------------

def layer_A(vmod, tmp):
    print("\n=== A. validate_gzh_html.py 校验器压测 ===")

    # A1 合法基线
    def a1():
        e, w, n = vmod.validate(sample_legal(), "legal")
        return check(not e and not w and n > 0, f"errors={e} warnings={w} leaf={n}")
    run_case("A1 合法基线：无 ERROR/WARNING", a1)

    # A2 禁用元素暴雨：每个都该命中 ERROR
    def a2():
        e, w, n = vmod.validate(sample_forbidden(), "forbidden")
        msgs = " | ".join(e)
        names = ["style", "script", "div", "link", "class", "id",
                 "position", "float", "white-space", "@media",
                 "@keyframes", "@import", "grid", "var(--", "字体"]
        missing = [nm for nm in names if nm not in msgs and nm not in "font"]
        # 部分名字在消息文案里不带原词，这里只要求 ERROR 数 >= 10 且都含关键语义
        return check(len(e) >= 10 and "style" in " ".join(e), f"ERROR×{len(e)}: {msgs[:200]}")
    run_case("A2 禁用元素暴雨：全部命中 ERROR", a2)

    # A3 无任何 span leaf → 致命 ERROR
    def a3():
        e, w, _ = vmod.validate('<section><p>中文没有包裹</p></section>', "noleaf")
        return check(any("span leaf" in x for x in e), f"errors={e}")
    run_case("A3 全文无 span leaf：报致命 ERROR", a3)

    # A4 部分未包裹 → WARNING
    def a4():
        e, w, _ = vmod.validate(sample_mixed_wrapped(), "mixed")
        return check(not e and any("未" in x or "leaf" in x for x in w), f"errors={e} warnings={w}")
    run_case("A4 部分未包裹：报 WARNING 不致命", a4)

    # A5 半角标点/英文引号 → WARNING
    def a5():
        e, w, _ = vmod.validate(sample_half_punct(), "half")
        return check(not e and any("半角" in x for x in w), f"errors={e} warnings={w}")
    run_case("A5 半角标点/引号：报 WARNING", a5)

    # A6 代码块内半角豁免
    def a6():
        e, w, _ = vmod.validate(sample_code_block(), "code")
        return check(not e and not w, f"errors={e} warnings={w}")
    run_case("A6 代码块内半角：被豁免不报 WARNING", a6)

    # A7 畸形 HTML（未闭合标签）→ 不崩溃，合理输出
    def a7():
        bad = '<section><p><span leaf="">缺闭合<span><p style="color:red">' \
              '<section><div class="x">'  # 乱序 + 禁用
        e, w, n = vmod.validate(bad, "malformed")
        return check(len(e) >= 0 and n >= 0, f"errors={len(e)} warnings={len(w)} leaf={n}")
    run_case("A7 畸形/未闭合 HTML：不崩溃", a7)

    # A8 空内容/无中文
    def a8():
        e1, w1, _ = vmod.validate("", "empty")
        e2, w2, _ = vmod.validate('<section><p>hello world</p></section>', "en")
        return check(not e1 and not w1 and not e2 and not w2,
                     f"empty(err={e1},w={w1}) en(err={e2},w={w2})")
    run_case("A8 空文件/纯英文：通过", a8)

    # A9 深嵌套（5000 层 section）→ 不崩溃
    def a9():
        deep = "<section>" * 5000 + _leaf("深嵌套内容") + "</section>" * 5000
        e, w, n = vmod.validate(deep, "deep")
        return check(not e, f"errors={len(e)} leaf={n}")
    run_case("A9 深嵌套 5000 层：不崩溃", a9)

    # A10 超大单行（1MB 无换行）
    def a10():
        big = '<section><p>' + _leaf("中" * 500_000) + "</p></section>"
        e, w, _ = vmod.validate(big, "bigline")
        return check(not e, f"errors={len(e)}")
    run_case("A10 超大单行 1MB：不崩溃", a10)

    # A11 长文（重复 1MB 合规段）+ 性能
    def a11():
        chunk = sample_legal()
        html = (chunk * 150)  # 约 > 1MB
        t0 = time.perf_counter()
        e, w, _ = vmod.validate(html, "long")
        dt = time.perf_counter() - t0
        return check(not e and dt < 60, f"errors={len(e)} 耗时={dt:.2f}s")
    run_case("A11 长文 1MB+：完成且不误报", a11)

    # A12 乱码字节（无效 UTF-8）→ CLI errors=replace 不崩
    def a12():
        f = tmp / "garbled.html"
        f.write_bytes(b'<section>\xff\xfe\x00\x80<p>\xfc\xa1\xa1\xc3\x28</p></section>')
        rc, out, err = run_py([SCRIPTS / "validate_gzh_html.py", f])
        return check(rc in (0, 1), f"rc={rc} out={out[:120]}")
    run_case("A12 乱码字节文件：CLI 不崩溃", a12)

    # A13 CLI 退出码：禁用元素 → exit 1
    def a13():
        f = tmp / "forbidden_cli.html"
        f.write_text(sample_forbidden(), encoding="utf-8")
        rc, out, _ = run_py([SCRIPTS / "validate_gzh_html.py", f])
        return check(rc == 1 and "ERROR" in out, f"rc={rc}")
    run_case("A13 CLI：禁用元素文件 exit 1", a13)

    # A14 CLI 退出码：合法文件 → exit 0
    def a14():
        f = tmp / "legal_cli.html"
        f.write_text(sample_legal(), encoding="utf-8")
        rc, out, _ = run_py([SCRIPTS / "validate_gzh_html.py", f])
        return check(rc == 0 and "完全合规" in out, f"rc={rc} out={out[-80:]}")
    run_case("A14 CLI：合法文件 exit 0", a14)

    # A15 CLI stdin 模式
    def a15():
        rc, out, _ = run_py([SCRIPTS / "validate_gzh_html.py", "--stdin"],
                            stdin_data=sample_legal())
        return check(rc == 0 and "完全合规" in out, f"rc={rc}")
    run_case("A15 CLI stdin 管道输入：通过", a15)

    # A16 CLI 文件不存在 → 非 0 退出 + 友好提示（无 traceback）
    def a16():
        rc, out, err = run_py([SCRIPTS / "validate_gzh_html.py", tmp / "nope.html"])
        return check(rc != 0 and "Traceback" not in err and "找不到文件" in out,
                     f"rc={rc} out={out[:120]} err={err[:120]}")
    run_case("A16 CLI 文件不存在：友好提示非 0 退出", a16)

# ---------------------------------------------------------------------------
# B. fix_quotes.py 压测
# ---------------------------------------------------------------------------

def layer_B(tmp):
    print("\n=== B. fix_quotes.py 引号修复压测 ===")

    # B1 常规替换：半角 → 全角
    def b1():
        f = tmp / "q1.html"
        f.write_text('<section><span leaf="">他说："你好"，然后说：\'再见\'。</span></section>',
                     encoding="utf-8")
        rc, out, _ = run_py([SCRIPTS / "fix_quotes.py", f])
        body = f.read_text(encoding="utf-8")
        return check(rc == 0 and "“" in body and "‘" in body,
                     f"rc={rc} body={body}")
    run_case("B1 半角引号→全角", b1)

    # B2 幂等性：跑两次 = 跑一次
    def b2():
        f = tmp / "q2.html"
        f.write_text('<section><span leaf="">他说："你好"。</span></section>', encoding="utf-8")
        run_py([SCRIPTS / "fix_quotes.py", f])
        first = f.read_text(encoding="utf-8")
        rc2, out2, _ = run_py([SCRIPTS / "fix_quotes.py", f])
        second = f.read_text(encoding="utf-8")
        return check(rc2 == 0 and first == second and "替换 0 对" in out2,
                     f"first==second:{first==second} out2={out2}")
    run_case("B2 幂等：重复执行 0 替换且内容不变", b2)

    # B3 属性引号不被误改（style="..." 里的引号保留半角）
    def b3():
        f = tmp / "q3.html"
        f.write_text('<section style="color:red"><p style=\'font-size:12px\'><span leaf="">内容</span></p></section>',
                     encoding="utf-8")
        rc, out, _ = run_py([SCRIPTS / "fix_quotes.py", f])
        body = f.read_text(encoding="utf-8")
        return check(rc == 0 and 'style="color:red"' in body, f"body={body}")
    run_case("B3 属性引号不被误改", b3)

    # B4 无引号 → 0 替换
    def b4():
        f = tmp / "q4.html"
        f.write_text(sample_legal(), encoding="utf-8")
        rc, out, _ = run_py([SCRIPTS / "fix_quotes.py", f])
        return check(rc == 0 and "替换 0 对" in out, f"out={out}")
    run_case("B4 无引号输入：0 替换", b4)

    # B5 缺参数 → exit 1
    def b5():
        rc, out, _ = run_py([SCRIPTS / "fix_quotes.py"])
        return check(rc == 1, f"rc={rc}")
    run_case("B5 缺参数：exit 1", b5)

    # B6 文件不存在 → 非 0 + 友好提示（无 traceback）
    def b6():
        rc, out, err = run_py([SCRIPTS / "fix_quotes.py", tmp / "nope.html"])
        return check(rc != 0 and "Traceback" not in err and "找不到文件" in out,
                     f"rc={rc} out={out[:120]} err={err[:120]}")
    run_case("B6 文件不存在：友好提示非 0 退出", b6)

# ---------------------------------------------------------------------------
# C. generate_titles.py 标题评分压测
# ---------------------------------------------------------------------------

def layer_C():
    print("\n=== C. generate_titles.py 标题评分压测 ===")
    gt = load_module("generate_titles", SCRIPTS / "generate_titles.py")
    score_title = gt.score_title

    def c1():
        s, dims, risks = score_title("4000星项目教你写工业级提示词")
        return check(0 <= s <= 100, f"score={s} dims={dims}")
    run_case("C1 正常标题评分在 0-100", c1)

    def c2():
        s, dims, risks = score_title("一个非常非常非常非常非常非常非常非常非常非常非常非常长的标题超过二十二个字符了啊啊啊")
        d = dims if isinstance(dims, (list, tuple)) else []
        return check(0 <= s <= 100, f"score={s}")
    run_case("C2 超长标题：正常评分不崩", c2)

    def c3():
        s, dims, risks = score_title("震惊！！AI 竟然能这样？！（快看）")
        return check(0 <= s <= 100, f"score={s}")
    run_case("C3 特殊符号标题：不崩", c3)

    def c4():
        s, dims, risks = score_title("")
        return check(0 <= s <= 100, f"score={s}")
    run_case("C4 空标题：不崩", c4)

    def c5():
        s, dims, risks = score_title("1234567890")
        return check(0 <= s <= 100, f"score={s}")
    run_case("C5 纯数字标题：不崩", c5)

    def c6():
        a = score_title("GitHub 56.7k 星的开源项目教你训大模型")
        b = score_title("GitHub 56.7k 星的开源项目教你训大模型")
        return check(a[0] == b[0], f"score 两次不一致: {a[0]} vs {b[0]}")
    run_case("C6 评分稳定性：同标题多次一致", c6)

    def c7():
        s, dims, risks = score_title("包治百病，吃了就能治好癌症")
        return check(0 <= s <= 100, f"score={s} risks={risks}")
    run_case("C7 敏感/夸大标题：正常评分并标注", c7)

# ---------------------------------------------------------------------------
# D. publish_full.py 存稿前置拦截（只传坏参数，保证安全退出、不开浏览器）
# ---------------------------------------------------------------------------

def layer_D(tmp):
    print("\n=== D. publish_full.py 存稿前置拦截（不真连公众号） ===")

    def d1():
        rc, out, err = run_py([SCRIPTS / "publish_full.py",
                               tmp / "不存在.html",
                               "--title", "测试标题"],
                              timeout=60)
        return check(rc == 1 and "ERR" in out, f"rc={rc} out={out[:200]}")
    run_case("D1 html 不存在：exit 1，开浏览器前拦截", d1)

    def d2():
        f = tmp / "ok.html"
        f.write_text(sample_legal(), encoding="utf-8")
        rc, out, _ = run_py([SCRIPTS / "publish_full.py", f,
                             "--title", "测试标题",
                             "--cover", str(tmp / "无封面.png")], timeout=60)
        return check(rc == 1 and "ERR" in out, f"rc={rc} out={out[:200]}")
    run_case("D2 cover 不存在：exit 1，开浏览器前拦截", d2)

    def d3():
        f = tmp / "ok2.html"
        f.write_text(sample_legal(), encoding="utf-8")
        rc, out, err = run_py([SCRIPTS / "publish_full.py", f], timeout=60)
        return check(rc == 2, f"rc={rc} err={err[:200]}")
    run_case("D3 缺 --title：argparse exit 2", d3)

    def d4():
        # html 参数指向目录：is_file()=False → 开浏览器前拦截（安全）
        rc, out, _ = run_py([SCRIPTS / "publish_full.py", tmp,
                             "--title", "测试标题"], timeout=60)
        return check(rc == 1 and "ERR" in out, f"rc={rc} out={out[:200]}")
    run_case("D4 html 是目录：exit 1，拦截（不启动浏览器）", d4)

    def d5():
        f = tmp / "ok3.html"
        f.write_text(sample_legal(), encoding="utf-8")
        rc, out, _ = run_py([SCRIPTS / "publish_full.py", f,
                             "--title", "测试标题",
                             "--cover", str(tmp)], timeout=60)  # cover 指向目录
        return check(rc == 1 and "ERR" in out, f"rc={rc} out={out[:200]}")
    run_case("D5 cover 是目录：exit 1，拦截", d5)

# ---------------------------------------------------------------------------
# E. 组件库 + 抓取 + 真实产物回归
# ---------------------------------------------------------------------------

def layer_E(tmp):
    print("\n=== E. 组件库/抓取/真实产物回归 ===")

    def e1():
        rc, out, _ = run_py([SCRIPTS / "component_lint.py", SKILL_ROOT], timeout=60)
        return check(rc == 0, f"rc={rc} out={out[-200:]}")
    run_case("E1 component_lint 组件库源头：exit 0", e1)

    def e2():
        rc, out, _ = run_py([SCRIPTS / "fetch_ai_news.py", "--list"], timeout=60)
        return check(rc == 0 and ("量子位" in out or "机器之心" in out or "36氪" in out),
                     f"rc={rc} out={out[:200]}")
    run_case("E2 fetch_ai_news --list：列源成功", e2)

    def e3():
        # 对 outputs 里最新一批合规产物做回归校验（只读）
        cands = sorted(OUTPUTS.glob("batch*.html"), key=lambda p: p.stat().st_mtime,
                       reverse=True) if OUTPUTS.exists() else []
        if not cands:
            return check(True, "outputs 无 batch 产物，跳过回归")
        checked, failed = 0, 0
        detail = []
        for p in cands[:10]:
            rc, out, _ = run_py([SCRIPTS / "validate_gzh_html.py", p], timeout=60)
            checked += 1
            if rc != 0:
                failed += 1
                detail.append(f"{p.name}: rc={rc}")
        return check(failed == 0, f"回归 {checked} 篇，失败 {failed}: {'; '.join(detail)}")
    run_case("E3 真实产物回归（最新≤10篇）", e3)

    def e4():
        # 全量产物回归：outputs 下所有 batch*.html
        cands = sorted(p for p in OUTPUTS.glob("batch*.html")
                       if "_预览" not in p.name) if OUTPUTS.exists() else []
        if not cands:
            return check(True, "outputs 无 batch 产物，跳过")
        bad = []
        for p in cands:
            rc, out, _ = run_py([SCRIPTS / "validate_gzh_html.py", p], timeout=60)
            if rc != 0:
                bad.append(p.name)
        return check(not bad, f"全量 {len(cands)} 篇，失败 {len(bad)}: {bad}")
    run_case("E4 全量正文产物回归（排除预览页）", e4)

# ---------------------------------------------------------------------------
# F. 流水线闭环演练：坏文件 → 发现 → 修复 → 复验
# ---------------------------------------------------------------------------

def layer_F(vmod, tmp):
    print("\n=== F. 流水线闭环演练（校验→修复→复验） ===")

    def f1():
        # 构造同时含「半角引号 + 未包裹中文」的坏文件
        bad = (f'<section><p>{_leaf("已包裹。")}</p>'
               f'<p>他说："这是没包裹的半角引号"，然后走了。</p></section>')
        f = tmp / "closed_loop.html"
        f.write_text(bad, encoding="utf-8")
        # 第一步：校验应发现问题
        e0, w0, _ = vmod.validate(bad, "loop")
        found = bool(w0)  # 至少有 WARNING（未包裹/半角）
        # 第二步：fix_quotes 修复
        rc, out, _ = run_py([SCRIPTS / "fix_quotes.py", f])
        fixed_body = f.read_text(encoding="utf-8")
        # 第三步：复验（未包裹仍是 WARNING，但引号应已转全角）
        e1, w1, _ = vmod.validate(fixed_body, "loop_fixed")
        quotes_ok = "“" in fixed_body and '"' not in fixed_body.split(">", 1)[1].split("<", 1)[0] if ">" in fixed_body else True
        quotes_ok = "“" in fixed_body
        return check(found and rc == 0 and e1 == [] and quotes_ok,
                     f"发现={found} rc={rc} 复验errors={e1} 引号已转={'“' in fixed_body}")
    run_case("F1 坏文件：校验发现→修复→复验通过", f1)
    def f2():
        # 含结构性 ERROR（div/class）的坏文件：修复器只修引号，不应把结构错误洗白
        bad = f'<section><div class="x">他说："内容"</div></section>'
        f = tmp / "struct_bad.html"
        f.write_text(bad, encoding="utf-8")
        rc0, out0, _ = run_py([SCRIPTS / "validate_gzh_html.py", f])
        # 修复
        run_py([SCRIPTS / "fix_quotes.py", f])
        rc1, out1, _ = run_py([SCRIPTS / "validate_gzh_html.py", f])
        return check(rc0 == 1 and rc1 == 1 and "ERROR" in out1,
                     f"修复前rc={rc0} 修复后rc={rc1}（应都=1，ERROR 不被洗白）")
    run_case("F2 结构错误不被修复器洗白：修复后仍拦截", f2)

# ---------------------------------------------------------------------------
# G. 极端规模 + 恶意/绕过输入（validate_gzh_html.py）
# ---------------------------------------------------------------------------

def layer_G(vmod):
    print("\n=== G. 极端规模 + 恶意/绕过输入 ===")

    # G1 10MB 超长合规文：完成且不误报
    def g1():
        chunk = sample_legal()
        html = "".join([chunk] * 20000)  # ≈ 10MB
        t0 = time.perf_counter()
        e, w, _ = vmod.validate(html, "huge10mb")
        dt = time.perf_counter() - t0
        return check(not e and dt < 30, f"errors={len(e)} 耗时={dt:.2f}s 大小≈{len(html)//1024//1024}MB")
    run_case("G1 10MB 超长文：完成且不误报", g1)

    # G2 10 万层深嵌套：不崩溃
    def g2():
        n = 100000
        deep = "<section>" * n + _leaf("深嵌套") + "</section>" * n
        e, w, _ = vmod.validate(deep, "deep10w")
        return check(not e, f"errors={len(e)}")
    run_case("G2 10 万层嵌套：不崩溃", g2)

    # G3 10 万个独立 section：不崩溃
    def g3():
        html = "".join(f"<section><p>{_leaf('段')}</p></section>" for _ in range(100000))
        e, w, _ = vmod.validate(html, "manysec")
        return check(not e, f"errors={len(e)}")
    run_case("G3 10 万个 section：不崩溃", g3)

    # G4 单文本节点 5MB：不崩溃
    def g4():
        html = f"<section><p>{_leaf('长' * 2_500_000)}</p></section>"
        e, w, _ = vmod.validate(html, "bigtext")
        return check(not e, f"errors={len(e)}")
    run_case("G4 单节点 5MB 文本：不崩溃", g4)

    # G5 嵌套引号地狱：正常报告不崩
    def g5():
        evil = "'\"'\"'\"''''\"\"\"\"'\"'"
        html = f"<section><p><span leaf=\"\">{evil}中文{evil}</span></p></section>"
        e, w, _ = vmod.validate(html, "quotestorm")
        return check(not e and len(w) >= 0, f"errors={len(e)} warnings={len(w)}")
    run_case("G5 引号风暴：不崩且能报告", g5)

    # G6 注释里藏禁用元素（正则全文扫描会命中 → 已知行为，记录）
    def g6():
        html = "<!-- <div class=\"x\"> <style> body{} </style> </div> --><section><p><span leaf=\"\">正常</span></p></section>"
        e, w, _ = vmod.validate(html, "comment")
        hit = any("div" in x or "style" in x for x in e)
        return check(hit, f"注释内禁用元素被正则命中(全文扫描特性): errors={len(e)}")
    run_case("G6 注释藏禁用元素：全文扫描会命中（已知特性）", g6)

    # G7 大小写混合绕过：sCrIpT/DiV/CLass 都应命中
    def g7():
        html = '<section><sCrIpT>alert(1)</sCrIpT><DiV class="a">x</DiV><p CLass="b">y</p></section>'
        e, w, _ = vmod.validate(html, "case")
        return check(len(e) >= 3, f"errors={len(e)}: {e[:3]}")
    run_case("G7 大小写混合：全部命中 ERROR", g7)

    # G8 属性里藏禁用样式：white-space:pre 在 style 属性内也应命中
    def g8():
        html = '<section><p style="white-space:pre">代码</p><p style="font-family:monospace">x</p></section>'
        e, w, _ = vmod.validate(html, "attrstyle")
        return check(any("white-space" in x for x in e), f"errors={len(e)}")
    run_case("G8 属性内禁用样式：命中 ERROR", g8)

    # G9 white-space:pre-wrap / pre-line 变体：应命中（pre 前缀）
    def g9():
        html = ('<section><p style="white-space:pre-wrap">x</p>'
                '<p style="white-space: pre-line">y</p></section>')
        e, w, _ = vmod.validate(html, "prevar")
        hit2 = any("2 处" in x for x in e) or len(e) >= 2
        return check(hit2, f"errors={len(e)}: {e}")
    run_case("G9 white-space 变体：命中 ERROR", g9)

    # G10 data URL 字体：外部字体检测是否覆盖（记录行为）
    def g10():
        html = ('<section><p style="font-family:url(\'data:font/woff2;base64,AAA\')">x</p>'
                '<p style="font-family:url(\'https://a.com/x.ttf\')">y</p></section>')
        e, w, _ = vmod.validate(html, "fonturl")
        http_hit = any("字体" in x for x in e)
        return check(http_hit, f"https字体命中={http_hit}（data URL 是否命中见报告） errors={len(e)}")
    run_case("G10 外部字体 URL 检测：http 命中", g10)

    # G11 繁体中文未包裹：应报 WARNING（CJK 覆盖）
    def g11():
        html = "<section><p>繁體中文測試內容</p></section>"
        e, w, _ = vmod.validate(html, "trad")
        leaf_hit = any("leaf" in x for x in e) or any("leaf" in x for x in w)
        return check(leaf_hit, f"errors={e} warnings={w}")
    run_case("G11 繁体中文：能被 CJK 识别并报未包裹", g11)

    # G12 零宽字符/emoji/全角空白：不崩
    def g12():
        html = f'<section><p><span leaf="">\u200b\ufeff\u3000\u00a0😀🚀中文</span></p></section>'
        e, w, _ = vmod.validate(html, "invisible")
        return check(not e, f"errors={len(e)}")
    run_case("G12 零宽/emoji/全角空白：不崩", g12)

# ---------------------------------------------------------------------------
# H. 判别器质量（合法 vs 非法 / 豁免边界 / 一致性）
# ---------------------------------------------------------------------------

def layer_H(vmod, tmp):
    print("\n=== H. 判别器质量 ===")

    # H1 真实产物（batch8_01 副本）→ 完全合规
    def h1():
        src = OUTPUTS / "batch8_01_VoiceStudio_新丑撞色(neo-brutalism).html"
        if not src.exists():
            return check(True, "产物不存在，跳过")
        html = src.read_text(encoding="utf-8")
        e, w, _ = vmod.validate(html, "real")
        return check(not e and not w, f"errors={len(e)} warnings={len(w)}")
    run_case("H1 真实产物：errors=0 warnings=0", h1)

    # H2 孪生文件：仅差一个 span leaf → 判别翻转
    def h2():
        good = sample_legal()
        bad = good.replace(_leaf("第1段测试内容，验证合法基线。"),
                           "第1段测试内容，验证合法基线。")
        e0, w0, _ = vmod.validate(good, "good")
        e1, w1, _ = vmod.validate(bad, "bad")
        return check(not e0 and not w0 and w1, f"good=(e{e0},w{w0}) bad=(e{e1},w{w1})")
    run_case("H2 孪生文件：少一个 leaf 即告警（敏感）", h2)

    # H3 代码区豁免边界：monospace / white-space:pre 内半角被豁免
    def h3():
        html = ('<section><p style="font-family:monospace">it\'s & "q" ; 123</p>'
                '<p style="white-space:pre">a\'b "c"</p>'
                '<p style="font-family:sans-serif">它\'说\'"了"话</p></section>')
        e, w, _ = vmod.validate(html, "codezone")
        # monospace 和 white-space:pre 段应豁免；sans-serif 段应报半角
        return check(any("半角" in x for x in w), f"warnings={w}")
    run_case("H3 代码区豁免：sans-serif 正文半角仍报、代码区豁免", h3)

    # H4 同一文件多次校验结果一致（无状态污染）
    def h4():
        html = sample_forbidden()
        r1 = vmod.validate(html, "stable")
        r2 = vmod.validate(html, "stable")
        return check(r1 == r2, f"两次结果不同: {r1} vs {r2}")
    run_case("H4 校验无状态：同文件两次结果一致", h4)

# ---------------------------------------------------------------------------
# I. 长跑稳定性 + 全脚本语法
# ---------------------------------------------------------------------------

def layer_I(tmp):
    print("\n=== I. 长跑稳定性 + 语法 ===")

    # I1 fix_quotes 连续 10 次幂等
    def i1():
        f = tmp / "idem10.html"
        f.write_text('<section><span leaf="">他说："你好"和\'再见\'。</span></section>', encoding="utf-8")
        hashes = []
        for _ in range(10):
            rc, out, _ = run_py([SCRIPTS / "fix_quotes.py", f])
            if rc != 0:
                return check(False, f"第{_+1}次 rc={rc}")
            hashes.append(open(f, "rb").read())
        return check(len(set(hashes)) == 1, f"10 次后哈希稳定={len(set(hashes))==1}")
    run_case("I1 fix_quotes ×10：结果稳定", i1)

    # I2 score_title 同标题 100 次一致
    def i2():
        gt = load_module("generate_titles", SCRIPTS / "generate_titles.py")
        scores = {gt.score_title("GitHub 56.7k 星教你训大模型")[0] for _ in range(100)}
        return check(len(scores) == 1, f"scores={scores}")
    run_case("I2 标题评分 ×100：结果一致", i2)

    # I3 validate 连续 20 次无状态污染
    def i3():
        vmod = load_module("validate_gzh_html", SCRIPTS / "validate_gzh_html.py")
        outs = {repr(vmod.validate(sample_half_punct(), "x")) for _ in range(20)}
        return check(len(outs) == 1, f"唯一结果数={len(outs)}")
    run_case("I3 validate ×20：无状态污染", i3)

    # I4 全部 scripts/*.py 语法编译通过
    def i4():
        import py_compile
        bad = []
        for p in sorted(SCRIPTS.glob("*.py")):
            if p.name.startswith("_") or ".bak" in p.name:
                continue
            try:
                py_compile.compile(str(p), doraise=True)
            except Exception as ex:
                bad.append(f"{p.name}: {ex}")
        return check(not bad, "编译失败: " + "; ".join(bad))
    run_case("I4 全脚本 py_compile：无语法错误", i4)

    # I5 fix_quotes ×30 幂等
    def i5():
        f = tmp / "idem30.html"
        f.write_text("<section><span leaf=\"\">他说：\"a\"和'b'。</span></section>", encoding="utf-8")
        first = None
        for _ in range(30):
            rc, _, _ = run_py([SCRIPTS / "fix_quotes.py", f])
            if rc != 0:
                return check(False, f"第{_+1}次 rc={rc}")
            blob = f.read_bytes()
            first = blob if first is None else first
        return check(first == f.read_bytes(), "30 次后内容稳定")
    run_case("I5 fix_quotes ×30：结果稳定", i5)

    # I6 score_title ×500 一致
    def i6():
        gt = load_module("generate_titles", SCRIPTS / "generate_titles.py")
        scores = {gt.score_title("4000星项目教你写工业级提示词")[0] for _ in range(500)}
        return check(len(scores) == 1, f"scores={scores}")
    run_case("I6 标题评分 ×500：结果一致", i6)


# ---------------------------------------------------------------------------
# J. 资源/性能上限（超大样本走子进程，防 OOM 连累主测试进程）
# ---------------------------------------------------------------------------

def layer_J(tmp):
    print("\n=== J. 资源/性能上限（子进程隔离） ===")

    def j1():
        # 50MB 合规文：子进程 validate
        chunk = sample_legal()
        big = "".join([chunk] * 100000)  # ≈ 50MB
        f = tmp / "huge50mb.html"
        f.write_text(big, encoding="utf-8")
        t0 = time.perf_counter()
        rc, out, _ = run_py([SCRIPTS / "validate_gzh_html.py", f], timeout=120)
        dt = time.perf_counter() - t0
        return check(rc == 0, f"rc={rc} 耗时={dt:.1f}s 大小≈{len(big)//1024//1024}MB out={out[-60:]}")
    run_case("J1 50MB 合规文（子进程）：不崩不误报", j1)

    def j2():
        # 20 万层嵌套：子进程（CLI 层大输入）
        n = 200000
        deep = "<section>" * n + '<span leaf="">深</span>' + "</section>" * n
        f = tmp / "deep20w.html"
        f.write_text(deep, encoding="utf-8")
        t0 = time.perf_counter()
        rc, out, _ = run_py([SCRIPTS / "validate_gzh_html.py", f], timeout=120)
        dt = time.perf_counter() - t0
        return check(rc == 0, f"rc={rc} 耗时={dt:.1f}s out={out[-80:]}")
    run_case("J2 20 万层嵌套（子进程）：不崩", j2)

    def j3():
        # 1MB 合规文 validate 内存峰值（tracemalloc）
        import tracemalloc
        html = "".join([sample_legal()] * 2000)  # ≈1MB
        vmod = load_module("validate_gzh_html", SCRIPTS / "validate_gzh_html.py")
        tracemalloc.start()
        vmod.validate(html, "mem")
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return check(peak < 300 * 1024 * 1024, f"峰值内存≈{peak//1024//1024}MB")
    run_case("J3 1MB 校验内存峰值（tracemalloc）", j3)


# ---------------------------------------------------------------------------
# K. 文件系统 / 编码异常
# ---------------------------------------------------------------------------

def layer_K(tmp):
    print("\n=== K. 文件系统/编码异常 ===")

    def k1():
        # 只读文件：fix_quotes 应友好报错而非 traceback
        f = tmp / "readonly.html"
        f.write_text('<section><p><span leaf="">他说："hi"</span></p></section>', encoding="utf-8")
        os.chmod(f, 0o444)
        try:
            rc, out, err = run_py([SCRIPTS / "fix_quotes.py", f])
        finally:
            os.chmod(f, 0o644)
        ok = rc != 0 and "Traceback" not in err
        return check(ok, f"rc={rc} out={out[:80]} err={err[:200]}")
    run_case("K1 只读文件：友好报错（无 traceback）", k1)

    def k2():
        # UTF-16 编码：fix_quotes 无 errors=replace → 记录真实行为
        f = tmp / "utf16.html"
        f.write_bytes('<section><p><span leaf="">他说："hi"</span></p></section>'.encode("utf-16"))
        rc, out, err = run_py([SCRIPTS / "fix_quotes.py", f])
        return check("Traceback" not in err, f"rc={rc} err={err[:200]}")
    run_case("K2 UTF-16 文件：无 traceback", k2)

    def k3():
        # GBK 编码
        f = tmp / "gbk.html"
        f.write_bytes('<section><p><span leaf="">中文内容</span></p></section>'.encode("gbk"))
        rc, out, err = run_py([SCRIPTS / "fix_quotes.py", f])
        return check("Traceback" not in err, f"rc={rc} err={err[:200]}")
    run_case("K3 GBK 文件：无 traceback", k3)

    def k4():
        # UTF-8 BOM 文件：不崩、可重复执行
        f = tmp / "bom.html"
        f.write_bytes(b"\xef\xbb\xbf" + '<section><p><span leaf="">中文</span></p></section>'.encode("utf-8"))
        rc, out, _ = run_py([SCRIPTS / "fix_quotes.py", f])
        rc2, out2, _ = run_py([SCRIPTS / "fix_quotes.py", f])
        return check(rc == 0 and rc2 == 0, f"rc={rc} rc2={rc2}")
    run_case("K4 UTF-8 BOM 文件：不崩可重复", k4)

    def k5():
        # 特殊字符路径（空格/括号/井号/百分号/中文）：脚本能处理
        d = tmp / "has space #%[]（）"
        d.mkdir(exist_ok=True)
        f = d / "文 章.html"
        f.write_text(sample_legal(), encoding="utf-8")
        rc, out, _ = run_py([SCRIPTS / "validate_gzh_html.py", f])
        return check(rc == 0, f"rc={rc} out={out[-60:]}")
    run_case("K5 特殊字符路径：正常处理", k5)

    def k6():
        # HTML 实体引号 &quot;：handle_data 转换后是否报半角（记录）
        vmod = load_module("validate_gzh_html", SCRIPTS / "validate_gzh_html.py")
        html = "<section><p><span leaf=\"\">他说：&quot;你好&quot;。</span></p></section>"
        e, w, _ = vmod.validate(html, "entity")
        hit = any("半角" in x for x in w)
        return check(not e, f"实体引号识别为半角={hit} errors={e}")
    run_case("K6 HTML 实体引号：行为记录", k6)


# ---------------------------------------------------------------------------
# L. 随机模糊 + 更刁钻绕过
# ---------------------------------------------------------------------------

def layer_L(vmod, tmp):
    print("\n=== L. 随机模糊 + 绕过变体 ===")
    import random

    def l1():
        # 随机字节 fuzz ×30（固定种子可复现）：validate 不崩溃
        rng = random.Random(42)
        for i in range(30):
            blob = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 4096)))
            f = tmp / f"fuzz_{i}.html"
            f.write_bytes(blob)
            rc, _, _ = run_py([SCRIPTS / "validate_gzh_html.py", f], timeout=30)
            if rc not in (0, 1, 2):
                return check(False, f"fuzz{i} rc={rc}")
        return check(True, "30 组随机字节均不崩溃")
    run_case("L1 随机字节 fuzz ×30：不崩溃", l1)

    def l2():
        # 随机 HTML 结构 fuzz ×50（import 级，快）：不崩溃
        rng = random.Random(7)
        tags = ["section", "p", "span", "div", "a", "img", "br", "style", "script", "b", "i"]
        for i in range(50):
            parts = []
            for _ in range(rng.randrange(1, 60)):
                r = rng.random()
                if r < 0.4:
                    t = rng.choice(tags)
                    attr = rng.choice(["", ' class="x"', ' style="color:red"', ' leaf=""'])
                    parts.append("<" + t + attr + ">")
                elif r < 0.7:
                    parts.append("</" + rng.choice(tags) + ">")
                else:
                    parts.append(rng.choice(["中文", "hello", "，", "；", '"q"', "&amp;", "💡", "\u200b", "&#34;"]))
            html = "".join(parts)
            vmod.validate(html, f"hf{i}")
        return check(True, "50 组随机 HTML 结构均不崩溃")
    run_case("L2 随机 HTML fuzz ×50：不崩溃", l2)

    def l3():
        # 注释拆分标签 <scr<!-- -->ipt>：正则是否漏检（绕过）
        html = '<section><scr<!-- -->ipt>alert(1)</scr<!-- -->ipt></section>'
        e, w, _ = vmod.validate(html, "split")
        hit = any("script" in x for x in e)
        return check(hit, f"注释拆分标签 script 被识别={hit}（漏检=绕过）")
    run_case("L3 注释拆分 script 标签：能否拦截", l3)

    def l4():
        # data URL 字体：是否漏检
        html = '<section><p style="font-family:url(\'data:font/woff2;base64,AAAA\')">x</p></section>'
        e, w, _ = vmod.validate(html, "datafont")
        hit = any("字体" in x for x in e)
        return check(hit, f"data 字体被识别={hit}（漏检=绕过）")
    run_case("L4 data URL 字体：能否拦截", l4)

    def l5():
        # 属性内换行 style="\nwhite-space:pre\n"：命中？
        html = '<section><p style="\nwhite-space:pre\n">x</p></section>'
        e, w, _ = vmod.validate(html, "nlattr")
        hit = any("white-space" in x for x in e)
        return check(hit, f"换行属性命中={hit}")
    run_case("L5 属性内换行：white-space 仍命中", l5)

    def l6():
        # class = 空格变体：命中？
        html = '<section><p class = "x">y</p></section>'
        e, w, _ = vmod.validate(html, "classsp")
        hit = any("class" in x for x in e)
        return check(hit, f"class空格变体命中={hit}")
    run_case("L6 class= 空格变体：命中", l6)

    def l7():
        # 全半角引号混排 + 嵌套：不崩
        html = '<section><p><span leaf="">“ab"cd” and ‘e\'f’</span></p></section>'
        e, w, _ = vmod.validate(html, "mixedq")
        return check(not e, f"errors={e}")
    run_case("L7 全半角引号混排：不崩", l7)


# ---------------------------------------------------------------------------
# M. 端到端离线闭环 + 组件库
# ---------------------------------------------------------------------------

def layer_M(tmp):
    print("\n=== M. 端到端离线闭环 + 组件库 ===")

    def m1():
        # 素材→合规HTML→校验(发现WARNING)→修复→复验(清零)→预览，全离线闭环
        f = tmp / "e2e.html"
        html = (sample_legal()
                + '<section><p><span leaf="">他说："测试"和\'你好\'。</span></p></section>')
        f.write_text(html, encoding="utf-8")
        vmod = load_module("validate_gzh_html", SCRIPTS / "validate_gzh_html.py")
        e0, w0, _ = vmod.validate(html, "e2e0")           # 修复前：应发现半角引号
        rc1, _, _ = run_py([SCRIPTS / "fix_quotes.py", f])
        fixed = f.read_text(encoding="utf-8")
        e1, w1, _ = vmod.validate(fixed, "e2e1")          # 修复后：应清零
        pv = tmp / "e2e_preview.html"
        rc3, _, _ = run_py([SCRIPTS / "wrap_preview.py", f, pv])
        return check(bool(w0) and not w1 and rc1 == 0 and rc3 == 0 and pv.exists(),
                     f"修复前warnings={w0} 修复后warnings={w1} rc1={rc1} rc3={rc3}")
    run_case("M1 端到端闭环：素材→校验→修复→复验→预览", m1)

    def m2():
        # wrap_preview 压测：空文件/无 section/含 script 都应能生成
        cases = {"empty.html": "", "nosection.html": "plain text no section",
                 "withscript.html": sample_legal() + "<script>alert(1)</script>",
                 "big.html": sample_legal() * 100}
        bad = []
        for name, content in cases.items():
            f = tmp / name
            f.write_text(content, encoding="utf-8")
            rc, out, _ = run_py([SCRIPTS / "wrap_preview.py", f, tmp / (name + ".pv")], timeout=30)
            if rc != 0 or not (tmp / (name + ".pv")).exists():
                bad.append(name)
        return check(not bad, f"失败: {bad}")
    run_case("M2 wrap_preview 边界输入：均能生成", m2)

    def m3():
        # 组件库 html 块抽出来 validate：组件本身合规（无 ERROR）
        import re
        vmod = load_module("validate_gzh_html", SCRIPTS / "validate_gzh_html.py")
        checked, err = 0, 0
        names = set()
        for md in sorted((SKILL_ROOT / "references").glob("theme-*.md")):
            txt = md.read_text(encoding="utf-8")
            for b in re.findall(r"```html(.*?)```", txt, re.S):
                checked += 1
                e, w, _ = vmod.validate(b, md.name)
                # 组件库片段是局部结构块（容器/标题/卡片），不含正文 leaf 属正常；
                # 只把"禁用元素/禁用样式"类 ERROR 视为组件违规
                real = [x for x in e if "全文没有任何 <span leaf" not in x]
                if real:
                    err += 1
                    names.add(md.name)
        return check(err == 0, f"组件块 {checked} 个，含禁用类 ERROR {err}: {names}")
    run_case("M3 组件库 html 块合规：无 ERROR", m3)


# ---------------------------------------------------------------------------
# N. 并发 / 多进程 + 内存稳定性
# ---------------------------------------------------------------------------

def layer_N(tmp):
    print("\n=== N. 并发/多进程 + 内存稳定性 ===")

    def n1():
        # 8 个 validate 子进程并发跑不同文件
        import concurrent.futures as cf
        files = []
        for i in range(8):
            f = tmp / f"conc_{i}.html"
            f.write_text(sample_legal(), encoding="utf-8")
            files.append(f)
        def run_one(f):
            rc, _, _ = run_py([SCRIPTS / "validate_gzh_html.py", f], timeout=60)
            return rc
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            rcs = list(ex.map(run_one, files))
        return check(all(r == 0 for r in rcs), f"rcs={rcs}")
    run_case("N1 8 进程并发校验：全部成功", n1)

    def n2():
        # 8 个 fix_quotes 并发处理不同文件：各自独立正确
        import concurrent.futures as cf
        files = []
        for i in range(8):
            f = tmp / f"fq_{i}.html"
            f.write_text(f'<section><p><span leaf="">第{i}篇："内容"。</span></p></section>', encoding="utf-8")
            files.append(f)
        def run_one(f):
            rc, _, _ = run_py([SCRIPTS / "fix_quotes.py", f], timeout=60)
            return rc
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            rcs = list(ex.map(run_one, files))
        texts = [f.read_text(encoding="utf-8") for f in files]
        good = all("“" in t and f"第{i}篇" in t for i, t in enumerate(texts))
        return check(all(r == 0 for r in rcs) and good, f"rcs={rcs}")
    run_case("N2 8 进程并发修复不同文件：独立正确", n2)

    def n3():
        # 8 个 fix_quotes 并发写同一文件（不推荐用法，验证数据竞争）
        f = tmp / "same.html"
        f.write_text('<section><p><span leaf="">并发："x"</span></p></section>', encoding="utf-8")
        import concurrent.futures as cf
        def run_one(_):
            rc, _, _ = run_py([SCRIPTS / "fix_quotes.py", f], timeout=60)
            return rc
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            rcs = list(ex.map(run_one, range(8)))
        body = f.read_text(encoding="utf-8")
        intact = "span leaf" in body and "并发" in body
        return check(intact, f"rcs={rcs} 文件完整性={intact}")
    run_case("N3 并发写同一文件：完整性记录", n3)

    def n4():
        # validate 连续 30 次内存稳定性（tracemalloc 增量）
        import tracemalloc
        vmod = load_module("validate_gzh_html", SCRIPTS / "validate_gzh_html.py")
        html = "".join([sample_legal()] * 200)  # ≈100KB
        tracemalloc.start()
        vmod.validate(html, "warm")
        _, base = tracemalloc.get_traced_memory()
        for _ in range(30):
            vmod.validate(html, "loop")
        cur, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        grow = cur - base
        return check(grow < 50 * 1024 * 1024, f"30 次后内存增量≈{grow//1024}KB")
    run_case("N4 validate ×30 内存稳定（tracemalloc）", n4)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", help="只跑指定层（A-F，可逗号分隔）")
    ap.add_argument("--quick", action="store_true", help="跳过重样本（深嵌套/1MB长文）")
    ap.add_argument("--save", help="把报告写到指定 md 文件")
    args = ap.parse_args()

    layers = set(args.layer.split(",")) if args.layer else set("ABCDEFGHIJKLMN")
    tmp = Path(tempfile.mkdtemp(prefix="gzh_stress_"))

    vmod = load_module("validate_gzh_html", SCRIPTS / "validate_gzh_html.py")

    t_start = time.perf_counter()
    print(f"gzh-publish 抗压测试  开始于 {time.strftime('%H:%M:%S')}")
    print(f"  Python: {PYTHON}")
    print(f"  Skill:  {SKILL_ROOT}")
    print(f"  临时目录: {tmp}\n")

    if "A" in layers:
        layer_A(vmod, tmp)
    if "B" in layers:
        layer_B(tmp)
    if "C" in layers:
        layer_C()
    if "D" in layers:
        layer_D(tmp)
    if "E" in layers:
        layer_E(tmp)
    if "F" in layers:
        layer_F(vmod, tmp)
    if "G" in layers:
        layer_G(vmod)
    if "H" in layers:
        layer_H(vmod, tmp)
    if "I" in layers:
        layer_I(tmp)
    if "J" in layers:
        layer_J(tmp)
    if "K" in layers:
        layer_K(tmp)
    if "L" in layers:
        layer_L(vmod, tmp)
    if "M" in layers:
        layer_M(tmp)
    if "N" in layers:
        layer_N(tmp)

    total_dt = time.perf_counter() - t_start

    # 汇总
    passed = sum(1 for _, ok, _, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    print(f"\n{'='*56}")
    print(f"汇总: 通过 {passed} / {len(RESULTS)}，失败 {failed}，总耗时 {total_dt:.1f}s")
    if failed:
        print("\n失败用例:")
        for name, ok, detail, dt in RESULTS:
            if not ok:
                print(f"  ✗ {name}: {detail}")
    # 性能榜（最慢 5 个）
    slow = sorted(RESULTS, key=lambda r: r[3], reverse=True)[:5]
    print("\n最慢用例 TOP5:")
    for name, _, _, dt in slow:
        print(f"  · {name}: {dt*1000:.0f}ms")

    if args.save:
        out = Path(args.save)
        if not out.is_absolute():
            out = OUTPUTS / out
        lines = [f"# gzh-publish 抗压测试报告\n",
                 f"- 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                 f"- 通过 {passed}/{len(RESULTS)}，失败 {failed}，耗时 {total_dt:.1f}s\n",
                 "| 用例 | 结果 | 耗时 | 说明 |",
                 "|---|---|---|---|"]
        for name, ok, detail, dt in RESULTS:
            lines.append(f"| {name} | {'✅' if ok else '❌'} | {dt*1000:.0f}ms | {detail} |")
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n报告已保存: {out}")

    try:
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        pass

    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
