#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同一篇文章渲染成 5 套主题（摸鱼绿/瑞士极简/包豪斯/日式杂志/新丑撞色）。

产出：
  outputs/排版_{主题中文}({id}).html   —— 带样式代码块的正文（用于校验+预览+手动兜底）
  outputs/.seg_{id}.json                —— {segments:[... prose html ...], codes:[{lang,code}...]}
                                          供改造后的存稿脚本原生插入代码 + 名片置顶使用

正文一律从组件库取，全角标点，所有 CJK 文字包 <span leaf="">。
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 文章正文（单一来源，5 套主题共用；仅换主题 chrome / 强调样式）
# 约定：段落里 **加粗** = 主题强调； `行内代码` = 行内代码。标点全角。
# ---------------------------------------------------------------------------
TITLE = "本地大模型接进工作流：30行Python当故障助手"
TOP = "AI 实战 · 硬件向"
DATE = "2026.08"

INTRO = [
    "很多做硬件的朋友觉得 AI 离自己很远：要注册、要付费、数据还要上传云端。"
    "其实你桌上那台电脑，用本地大模型就能跑通一套故障排查助手。",
    "我本地跑着 Qwen3.5-9B（通过 QClaw 起的 llama-server），只要一行 Python 就能问它问题。"
    "下面把这套接进工作流的方法讲清楚。",
]

CHAPTERS = [
    {
        "num": "PART 01", "en": "WHY LOCAL", "title": "为什么是本地模型",
        "before": [
            "选本地模型有三个实在理由：**隐私不出本机**、**断网也能用**、**零调用成本**。"
            "维修记录、电路参数这些敏感信息，不该往外传。",
            "像电动车控制器的故障现象描述，本地模型足够理解并给出结构化判断，"
            "不需要动辄几十亿参数的云端大模型。",
        ],
        "after": [],
        "code": None,
    },
    {
        "num": "PART 02", "en": "CALL THE API", "title": "三步调通本地 API",
        "before": [
            "本地模型走 OpenAI 兼容接口，地址就是 `http://127.0.0.1:19110/v1/chat/completions`。"
            "先封装一个最小的 ask 函数：",
        ],
        "after": [
            "注意 temperature 设低一点（0.3），让输出更稳；max_tokens 给够，否则长 JSON 会被截断。",
        ],
        "code": {
            "lang": "python",
            "code": (
"import requests\n\n"
"URL = \"http://127.0.0.1:19110/v1/chat/completions\"\n"
"HEADERS = {\"Content-Type\": \"application/json\",\n"
"           \"Authorization\": \"Bearer llama-server\"}\n\n"
"def ask(symptom: str) -> str:\n"
"    resp = requests.post(URL, headers=HEADERS, json={\n"
"        \"model\": \"Qwen3.5-9B\",\n"
"        \"messages\": [{\"role\": \"user\", \"content\": symptom}],\n"
"        \"temperature\": 0.3,\n"
"        \"max_tokens\": 500,\n"
"    })\n"
"    return resp.json()[\"choices\"][0][\"message\"][\"content\"]"
            ),
        },
    },
    {
        "num": "PART 03", "en": "STRUCTURED", "title": "让它返回结构化结果",
        "before": [
            "故障助手最有用的不是聊天，而是**能直接拿来用的 JSON**。在提示词里约束输出格式，"
            "模型就会乖乖返回：",
        ],
        "after": [
            "这样一行 `json.loads` 就能拿到「可能原因」和「优先排查」，直接进你的维修单系统。",
        ],
        "code": {
            "lang": "python",
            "code": (
"import json\n\n"
"PROMPT = \"\"\"你是电动车控制器维修助手。\n"
"根据用户描述的故障现象，输出 JSON：\n"
"{\\\"可能原因\\\": [...], \\\"优先排查\\\": \\\"...\\\"}\n"
"只输出 JSON，不要解释。\"\"\"\n\n"
"def diagnose(symptom: str) -> dict:\n"
"    out = ask(PROMPT + \"\\n现象：\" + symptom)\n"
"    return json.loads(out)   # 本地模型直接返回 JSON\n\n"
"print(diagnose(\"通电无反应，指示灯不亮\"))"
            ),
        },
    },
    {
        "num": "PART 04", "en": "TOOL USE", "title": "加上 Function Calling，让它真能查",
        "before": [
            "光靠记忆不够。给它挂一个**查维修记录**的工具，模型觉得需要时自己会调用：",
        ],
        "after": [
            "这就是一个最小可用的 Agent：模型先决定要不要查，查完把结果回灌再给结论。",
        ],
        "code": {
            "lang": "python",
            "code": (
"tools = [{\n"
"    \"type\": \"function\",\n"
"    \"function\": {\n"
"        \"name\": \"查维修记录\",\n"
"        \"description\": \"按型号查询历史维修记录\",\n"
"        \"parameters\": {\n"
"            \"type\": \"object\",\n"
"            \"properties\": {\"型号\": {\"type\": \"string\"}},\n"
"            \"required\": [\"型号\"],\n"
"        },\n"
"    },\n"
"}]\n\n"
"def agent(symptom: str):\n"
"    msg = ask_with_tools(symptom, tools)   # 1) 模型决定要不要调工具\n"
"    if msg.tool_calls:\n"
"        rec = 查维修记录(msg.tool_calls[0][\"型号\"])\n"
"        return ask(\"结合记录给结论：\" + rec)   # 2) 回灌再答\n"
"    return msg.content"
            ),
        },
    },
    {
        "num": "PART 05", "en": "ON BENCH", "title": "落地到维修台",
        "before": [
            "实际用下来，把「型号 + 现象」喂进去，十秒出一份排查清单，新手照着做就能上手。"
            "老师傅也能用它做二次确认。",
            "关键是整套跑在你自己机器上，**不依赖任何外部服务**，产线、出差、没网的环境都能用。",
        ],
        "after": [],
        "code": None,
    },
]

CONCLUSION = [
    "本地大模型不是玩具。把它接进工作流，你得到的不是一个聊天框，而是一个随叫随到的**领域助手**。",
    "上面三十行出头，已经能跑。下一步可以接更多工具：查数据手册、读 PDF 图纸、写维修报告。"
    "动手试试，比想十遍有用。",
]

CTA_TEXT = "既然看到这里了，如果觉得有用，随手点个赞、推荐、转发三连吧。"

# ---------------------------------------------------------------------------
# 行内处理：**加粗** / `代码`
# ---------------------------------------------------------------------------
def inline(text, em_fn, code_fn):
    out = []
    i = 0
    buf = ""
    while i < len(text):
        if text[i] == "*" and text[i:i+2] == "**":
            j = text.find("**", i+2)
            if j != -1:
                out.append(em_fn(buf))
                buf = ""
                out.append(em_fn(text[i+2:j]))
                i = j+2
                continue
        if text[i] == "`":
            j = text.find("`", i+1)
            if j != -1:
                out.append(em_fn(buf))   # 普通文字也走 em 包裹（内层无加粗）
                buf = ""
                out.append(code_fn(text[i+1:j]))
                i = j+1
                continue
        buf += text[i]
        i += 1
    out.append(em_fn(buf))
    return "".join(out)


def para_wrap(style, inner):
    return f'<p style="{style}"><span leaf="">{inner}</span></p>'


# ---------------------------------------------------------------------------
# 主题配置
# ---------------------------------------------------------------------------
THEMES = {
    "moyu-green": {
        "cn": "摸鱼绿", "id": "moyu-green",
        "container": 'max-width:677px;margin:0 auto;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,\'PingFang SC\',\'Hiragino Sans GB\',\'Microsoft YaHei\',sans-serif;color:#374151;line-height:1.75;letter-spacing:0.5px;overflow-x:hidden;',
        "para": 'margin-bottom:16px;font-size:18px;line-height:1.9;text-align:justify;',
        "accent": "#059669", "accent_soft_bg": "#ECFDF5", "accent_soft_border": "#A7F3D0",
        "code_bar": "#059669",
        "em": lambda t: f'<strong style="color:#059669;"><span leaf="">{t}</span></strong>',
        "code_inline": lambda t: f'<span style="background:#F3F4F6;color:#1F2937;padding:2px 6px;border-radius:4px;font-size:16px;font-weight:600;"><span leaf="">{t}</span></span>',
        "header": lambda: (
            '<section style="margin:0 0 32px;background:#fff;border:1.5px solid rgba(5,150,105,0.15);border-radius:20px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.06);width:100%;">'
            '<section style="padding:32px 28px 28px;">'
            '<section style="display:flex;align-items:center;gap:8px;margin-bottom:28px;">'
            '<span style="width:6px;height:6px;background:#059669;border-radius:50%;"><span leaf=""><br></span></span>'
            f'<span style="font-size:14px;font-weight:700;letter-spacing:3px;color:#059669;"><span leaf="">{TOP}</span></span>'
            '<section style="flex:1;height:1px;overflow:hidden;background:linear-gradient(to right,rgba(5,150,105,0.12),transparent);"><span leaf=""><br></span></section>'
            f'<span style="font-size:13px;color:#D1D5DB;font-weight:600;"><span leaf="">{DATE}</span></span>'
            '</section>'
            '<section>'
            '<p style="font-size:30px;font-weight:900;color:#111827;margin:0;line-height:1.05;letter-spacing:-2px;">'
            '<span leaf="">本地大模型接进</span><span style="color:#059669;"><span leaf="">工作流</span></span></p>'
            '<p style="font-size:30px;font-weight:900;color:#059669;margin:0 0 16px;line-height:1.05;letter-spacing:-2px;"><span leaf="">30 行 Python 当故障助手</span></p>'
            '<section style="width:48px;height:3px;background:linear-gradient(to right,#059669,#34D399);border-radius:2px;margin-bottom:12px;"><span leaf=""><br></span></section>'
            f'<p style="font-size:16px;color:#9CA3AF;margin:0;line-height:1.7;letter-spacing:0.5px;"><span leaf="">不上云、不花钱、离线也能跑，把本地千问变成你的维修台助手</span></p>'
            '</section></section>'
            '<section style="background:linear-gradient(135deg,#059669,#10B981);padding:12px 28px;display:flex;align-items:center;justify-content:space-between;">'
            '<p style="font-size:15px;color:rgba(255,255,255,0.9);margin:0;font-weight:600;letter-spacing:0.5px;"><span leaf="">硅基研究员</span></p>'
            '<section style="display:flex;gap:4px;">'
            '<span style="background:rgba(255,255,255,0.2);padding:1px 6px;border-radius:3px;font-size:10px;color:#fff;font-weight:600;"><span leaf="">AI 实战</span></span>'
            '<span style="background:rgba(255,255,255,0.2);padding:1px 6px;border-radius:3px;font-size:10px;color:#fff;font-weight:600;"><span leaf="">硬件向</span></span>'
            '</section></section></section>'
        ),
        "chapter": lambda num, en, title: (
            '<section style="margin-top:48px;margin-bottom:32px;padding:0 20px;">'
            '<section style="display:flex;align-items:center;gap:16px;margin-bottom:24px;">'
            '<section style="text-align:center;flex-shrink:0;">'
            f'<p style="margin:0;font-size:35px;font-weight:900;color:#059669;line-height:1;letter-spacing:-2px;"><span leaf="">{num.replace("PART ","")}</span></p>'
            '<p style="margin:0;font-size:10px;font-weight:700;color:#D1D5DB;letter-spacing:2px;"><span leaf="">PART</span></p>'
            '</section>'
            '<span style="width:1px;height:36px;background:#E5E7EB;flex-shrink:0;"><span leaf=""><br></span></span>'
            '<section>'
            f'<p style="margin:0 0 1px;font-size:21px;font-weight:900;color:#111827;letter-spacing:0.3px;"><span leaf="">{title}</span></p>'
            f'<p style="margin:0;font-size:14px;font-weight:600;color:#9CA3AF;letter-spacing:1.5px;"><span leaf="">{en}</span></p>'
            '</section></section></section>'
        ),
        "quote": lambda t: (
            '<section style="background:#F9FAFB;border:1px dashed #D1D5DB;border-radius:8px;padding:12px 16px;margin-bottom:24px;text-align:justify;">'
            f'<p style="font-size:16px;color:#374151;margin:0;line-height:1.6;"><span leaf="">{t}</span></p></section>'
        ),
        "end": lambda: "",
        "cta": True,
    },
    "swiss-minimal": {
        "cn": "瑞士极简", "id": "swiss-minimal",
        "container": 'max-width:677px;margin:0 auto;background:#FFFFFF;font-family:\'Helvetica Neue\',Helvetica,Arial,-apple-system,\'PingFang SC\',sans-serif;color:#1A1A1A;line-height:1.8;letter-spacing:0.5px;overflow-x:hidden;padding:40px 28px;',
        "para": 'margin-bottom:20px;font-size:14px;color:#1A1A1A;line-height:1.8;text-align:left;',
        "accent": "#E63946", "accent_soft_bg": "#fff", "accent_soft_border": "#EEE",
        "code_bar": "#E63946",
        "em": lambda t: f'<strong style="font-weight:900;"><span leaf="">{t}</span></strong>',
        "code_inline": lambda t: f'<span style="background:#F3F4F6;color:#1F2937;padding:2px 6px;border-radius:4px;font-size:13px;font-weight:700;"><span leaf="">{t}</span></span>',
        "header": lambda: (
            '<section style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:40px;padding-bottom:16px;border-bottom:1px solid #000;">'
            '<section><p style="font-size:10px;letter-spacing:2px;color:#000;font-weight:700;text-transform:uppercase;margin:0;line-height:1.4;"><span leaf="">SILICON RESEARCH</span></p></section>'
            f'<section style="text-align:right;"><p style="font-size:10px;letter-spacing:1px;color:#666;margin:0;line-height:1.4;"><span leaf="">ISSUE 07</span></p>'
            f'<p style="font-size:10px;letter-spacing:1px;color:#999;margin:4px 0 0;line-height:1.4;"><span leaf="">{DATE}</span></p></section></section>'
            '<section style="margin-bottom:8px;">'
            '<p style="font-size:42px;font-weight:900;line-height:1.05;letter-spacing:-1px;color:#000;margin:0;"><span leaf="">本地大模型</span></p>'
            '<p style="font-size:42px;font-weight:900;line-height:1.05;letter-spacing:-1px;color:#000;margin:0;"><span leaf="">接进工作流</span></p></section>'
            '<p style="font-size:13px;color:#666;line-height:1.6;margin:0 0 40px;max-width:320px;"><span leaf="">不上云、不花钱、离线也能跑，把本地千问变成你的维修台助手</span></p>'
        ),
        "chapter": lambda num, en, title: (
            '<section style="margin-top:40px;margin-bottom:16px;">'
            f'<p style="font-size:11px;font-weight:900;color:#E63946;letter-spacing:2px;margin:0 0 8px;"><span leaf="">{num}</span></p>'
            f'<p style="font-size:22px;font-weight:900;color:#000;margin:0;line-height:1.3;"><span leaf="">{title}</span></p></section>'
        ),
        "quote": lambda t: (
            '<section style="margin:36px 0;padding:20px 0;border-top:2px solid #000;border-bottom:1px solid #000;">'
            f'<p style="font-size:20px;font-weight:900;line-height:1.4;letter-spacing:-0.5px;color:#000;margin:0;"><span leaf="">{t}</span></p></section>'
        ),
        "end": lambda: (
            '<section style="margin-top:48px;padding-top:16px;border-top:1px solid #000;display:flex;justify-content:space-between;">'
            '<p style="font-size:9px;color:#999;letter-spacing:1px;margin:0;"><span leaf="">硅基研究员</span></p>'
            '<p style="font-size:9px;color:#999;letter-spacing:1px;margin:0;"><span leaf="">— END —</span></p></section>'
        ),
        "cta": True,
    },
    "bauhaus": {
        "cn": "包豪斯几何", "id": "bauhaus",
        "container": 'max-width:677px;margin:0 auto;background:#F1EDE4;font-family:\'Helvetica Neue\',Arial,-apple-system,\'PingFang SC\',sans-serif;color:#1A1A1A;line-height:1.75;letter-spacing:0.5px;overflow-x:hidden;',
        "para": 'margin-bottom:16px;font-size:14px;color:#444;line-height:1.8;',
        "accent": "#E63946", "accent_soft_bg": "#1A1A1A", "accent_soft_border": "#F4D35E",
        "code_bar": "#E63946",
        "em": lambda t: f'<strong style="color:#E63946;"><span leaf="">{t}</span></strong>',
        "code_inline": lambda t: f'<span style="background:#fff;color:#E63946;padding:2px 6px;border:1px solid #1A1A1A;border-radius:2px;font-size:13px;font-weight:700;"><span leaf="">{t}</span></span>',
        "header": lambda: (
            '<section style="background:#1A1A1A;padding:36px 24px;overflow:hidden;">'
            '<section style="display:inline-block;width:80px;height:80px;background:#E63946;border-radius:50%;margin-bottom:16px;"><span leaf=""><br></span></section>'
            f'<p style="font-size:10px;letter-spacing:3px;color:#F4D35E;margin:0 0 14px;font-weight:700;"><span leaf="">FORM FOLLOWS FUNCTION · N°07</span></p>'
            '<p style="font-size:28px;font-weight:900;color:#fff;line-height:1.2;margin:0;letter-spacing:-0.5px;">'
            '<span style="color:#E63946;"><span leaf="">本地大模型</span></span>'
            '<span leaf="">接进</span>'
            '<span style="color:#F4D35E;"><span leaf="">工作流</span></span></p></section>'
            '<section style="padding:28px 24px;">'
        ),
        "chapter": lambda num, en, title: (
            '<section style="display:flex;gap:16px;margin-bottom:24px;align-items:flex-start;">'
            '<section style="width:36px;height:36px;background:#E63946;border-radius:50%;flex-shrink:0;margin-top:2px;"><span leaf=""><br></span></section>'
            '<section style="flex:1;">'
            f'<p style="font-size:18px;font-weight:900;margin:0 0 8px;color:#1A1A1A;"><span leaf="">{title}</span></p>'
        ),
        "chapter_close": True,
        "quote": lambda t: (
            '<section style="margin:24px 0;padding:20px;background:#1A1A1A;color:#fff;border-left:6px solid #F4D35E;">'
            f'<p style="font-size:17px;font-weight:700;line-height:1.6;margin:0;color:#fff;"><span leaf="">{t}</span></p></section>'
        ),
        "end": lambda: (
            '<section style="padding:20px 24px;background:#1A1A1A;color:#999;font-size:11px;letter-spacing:2px;text-align:center;"><span leaf="">硅基研究员 · BAUHAUS SERIES</span></section>'
        ),
        "cta": True,
    },
    "japanese-mag": {
        "cn": "日式杂志", "id": "japanese-mag",
        "container": 'max-width:677px;margin:0 auto;background:#FAFAF8;font-family:-apple-system,BlinkMacSystemFont,\'Hiragino Sans\',\'PingFang SC\',\'Microsoft YaHei\',sans-serif;color:#3A3A3A;line-height:2;letter-spacing:0.5px;overflow-x:hidden;',
        "para": 'font-size:13px;color:#555;line-height:2.2;margin-bottom:14px;text-align:justify;',
        "accent": "#B89070", "accent_soft_bg": "#FAFAF8", "accent_soft_border": "#B89070",
        "code_bar": "#B89070",
        "em": lambda t: f'<strong style="color:#2A2A2A;font-weight:600;"><span leaf="">{t}</span></strong>',
        "code_inline": lambda t: f'<span style="background:#F3EFE9;color:#B89070;padding:1px 5px;border-radius:3px;font-size:12px;font-weight:600;"><span leaf="">{t}</span></span>',
        "header": lambda: (
            '<section style="padding:32px 28px 0;display:flex;justify-content:space-between;align-items:flex-start;">'
            '<p style="font-size:9px;letter-spacing:3px;color:#999;text-transform:uppercase;margin:0;font-weight:600;"><span leaf="">ISSUE 07</span></p>'
            f'<p style="font-size:9px;letter-spacing:2px;color:#BBB;margin:0;"><span leaf="">{DATE} · 夏</span></p></section>'
            '<section style="padding:28px 28px 24px;">'
            '<p style="font-size:11px;letter-spacing:4px;color:#B89070;margin-bottom:16px;font-weight:600;"><span leaf="">暮 ら し の 手 帖</span></p>'
            '<p style="font-size:26px;font-weight:700;line-height:1.5;color:#2A2A2A;margin-bottom:16px;letter-spacing:2px;"><span leaf="">本地大模型接进工作流</span></p>'
            '<p style="font-size:18px;color:#666;font-weight:400;line-height:1.6;margin-bottom:0;"><span leaf="">三十行 Python，把本地千问变成维修台助手</span></p>'
            '<p style="font-size:12px;color:#999;line-height:1.9;margin:16px 0 0;"><span leaf="">不上云、不花钱、离线也能跑</span></p></section>'
        ),
        "chapter": lambda num, en, title: (
            '<section style="padding:24px 28px;">'
            f'<p style="font-size:10px;letter-spacing:3px;color:#B89070;margin-bottom:8px;font-weight:600;"><span leaf="">{num}</span></p>'
            f'<p style="font-size:16px;font-weight:700;color:#2A2A2A;margin:0 0 12px;line-height:1.5;"><span leaf="">{title}</span></p>'
        ),
        "chapter_close": True,
        "quote": lambda t: (
            '<section style="margin:0 28px 20px;padding-left:16px;border-left:2px solid #B89070;">'
            f'<p style="font-size:14px;color:#444;line-height:2;margin:0;font-style:italic;"><span leaf="">{t}</span></p></section>'
        ),
        "end": lambda: (
            '<section style="padding:20px 28px 32px;text-align:center;">'
            '<p style="font-size:10px;color:#CCC;letter-spacing:4px;margin:0;"><span leaf="">— 終 —</span></p></section>'
        ),
        "cta": True,
    },
    "neo-brutalism": {
        "cn": "新丑撞色", "id": "neo-brutalism",
        "container": 'max-width:677px;margin:0 auto;background:#FFF5E6;font-family:\'Arial Black\',\'Helvetica Neue\',Arial,-apple-system,\'PingFang SC\',sans-serif;color:#000;line-height:1.5;overflow-x:hidden;',
        "para": 'padding:0 20px 20px;',
        "para_inner": 'font-size:13px;color:#333;line-height:1.8;margin-bottom:12px;font-family:Arial,Helvetica,sans-serif;',
        "accent": "#FFE500", "accent_soft_bg": "#FFE500", "accent_soft_border": "#000",
        "code_bar": "#000",
        "em": lambda t: f'<span style="background:#FFE500;font-weight:700;padding:0 3px;"><span leaf="">{t}</span></span>',
        "code_inline": lambda t: f'<span style="background:#FF6B9D;color:#000;padding:0 3px;border:2px solid #000;font-weight:700;font-family:Arial,sans-serif;font-size:12px;"><span leaf="">{t}</span></span>',
        "header": lambda: (
            '<section style="background:#3B82F6;padding:10px 20px;border-bottom:3px solid #000;">'
            f'<p style="font-size:10px;letter-spacing:2px;color:#fff;font-weight:900;margin:0;text-transform:uppercase;"><span leaf="">★ NEO-BRUTALISM · ISSUE 07 ★</span></p></section>'
            '<section style="padding:24px 20px 16px;">'
            '<p style="font-size:32px;font-weight:900;line-height:1.05;color:#000;margin:0 0 8px;letter-spacing:-1px;">'
            '<span style="background:#FF6B9D;padding:2px 6px;"><span leaf="">本地大模型</span></span><span leaf="">接进</span></p>'
            '<p style="font-size:32px;font-weight:900;line-height:1.05;color:#000;margin:0 0 12px;letter-spacing:-1px;">'
            '<span leaf="">工作流，</span><span style="color:#3B82F6;"><span leaf="">30 行 Python</span></span><span leaf="">当故障助手</span></p></section>'
        ),
        "chapter": lambda num, en, title: (
            '<section style="padding:0 20px 20px;">'
            f'<p style="font-size:14px;font-weight:900;color:#000;margin:0 0 12px;"><span leaf="">{title}</span></p>'
        ),
        "chapter_close": True,
        "quote": lambda t: (
            '<section style="margin:0 20px 20px;padding:16px;background:#3B82F6;border:3px solid #000;box-shadow:6px 6px 0 #000;">'
            f'<p style="font-size:16px;font-weight:900;color:#fff;line-height:1.4;margin:0;font-style:italic;"><span leaf="">{t}</span></p></section>'
        ),
        "end": lambda: (
            '<section style="background:#000;padding:14px 20px;text-align:center;border-top:3px solid #000;">'
            '<p style="font-size:10px;color:#FFE500;letter-spacing:2px;margin:0;font-weight:900;"><span leaf="">★ 硅基研究员 · NEO-BRUTALISM ★</span></p></section>'
        ),
        "cta": True,
        "para_wrap_special": True,
    },
}

# ---------------------------------------------------------------------------
# 代码块（仅预览/校验用，深色 1a）
# ---------------------------------------------------------------------------
def code_block_styled(bar_color, lang, code):
    lines = code.split("\n")
    body = ""
    for ln in lines:
        indent = len(ln) - len(ln.lstrip(" "))
        vis = "　" * (indent // 2) + ln.lstrip(" ")
        body += (f'<p style="margin:0;font-family:\'SF Mono\',Consolas,Monaco,monospace;'
                 f'font-size:13px;line-height:1.6;color:#E2E8F0;"><span leaf="">{vis}</span></p>')
    return (
        '<section style="margin:0 0 20px;border-radius:8px;overflow:hidden;background:#1E293B;box-shadow:0 4px 16px -8px rgba(15,23,42,0.4);">'
        '<section style="display:flex;align-items:center;padding:9px 14px;background:#0F172A;">'
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#FF5F56;margin-right:7px;font-size:0;line-height:0;overflow:hidden;"><span leaf=""><br></span></span>'
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#FFBD2E;margin-right:7px;font-size:0;line-height:0;overflow:hidden;"><span leaf=""><br></span></span>'
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#27C93F;font-size:0;line-height:0;overflow:hidden;"><span leaf=""><br></span></span>'
        f'<span style="margin-left:12px;font-size:12px;color:#64748B;font-family:Consolas,Monaco,monospace;letter-spacing:1px;"><span leaf="">{lang}</span></span>'
        '</section>'
        f'<section style="padding:11px 14px;">{body}</section></section>'
    )


def three_link(theme):
    a, ab, abo = theme["accent"], theme["accent_soft_bg"], theme["accent_soft_border"]
    return (
        '<section style="background:radial-gradient(circle at center,#F9FAFB 0%,#FFFFFF 100%);border:1px solid #E5E7EB;border-radius:16px;padding:32px 20px;text-align:center;box-shadow:0 4px 12px rgba(0,0,0,0.03);margin:0 0 24px;">'
        f'<p style="font-size:16px;font-weight:bold;color:#111827;margin-bottom:20px;line-height:1.6;"><span leaf="">{CTA_TEXT}</span></p>'
        '<section style="display:flex;justify-content:center;gap:24px;margin-bottom:16px;">'
        '<section style="text-align:center;cursor:pointer;color:#4B5563;">'
        '<section style="width:40px;height:40px;display:flex;align-items:center;justify-content:center;margin:0 auto 6px;background:#fff;border-radius:12px;box-shadow:0 2px 4px rgba(0,0,0,0.05);border:1px solid #F3F4F6;">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>'
        '</section><span style="font-size:13px;font-weight:600;"><span leaf="">点赞</span></span></section>'
        '<section style="text-align:center;cursor:pointer;color:#4B5563;">'
        '<section style="width:40px;height:40px;display:flex;align-items:center;justify-content:center;margin:0 auto 6px;background:#fff;border-radius:12px;box-shadow:0 2px 4px rgba(0,0,0,0.05);border:1px solid #F3F4F6;">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>'
        '</section><span style="font-size:13px;font-weight:600;"><span leaf="">推荐</span></span></section>'
        f'<section style="text-align:center;cursor:pointer;color:{a};">'
        f'<section style="width:40px;height:40px;display:flex;align-items:center;justify-content:center;margin:0 auto 6px;background:{ab};border-radius:12px;box-shadow:0 2px 4px rgba(0,0,0,0.05);border:1px solid {abo};">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 18v-4a8 8 0 0 1 8-8h8"></path><polyline points="16 2 20 6 16 10"></polyline></svg>'
        f'</section><span style="font-size:13px;font-weight:600;"><span leaf="">转发</span></span></section>'
        '</section>'
        '<p style="font-size:13px;color:#9CA3AF;letter-spacing:1px;margin:0;"><span leaf="">THANKS FOR READING</span></p></section>'
    )


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------
def render(theme):
    t = THEMES[theme]
    em = t["em"]; ci = t["code_inline"]
    pstyle = t.get("para_inner", t["para"])
    if t.get("para_wrap_special"):
        def para(text):
            inner = inline(text, em, ci)
            return f'<section style="{t["para"]}"><p style="{pstyle}"><span leaf="">{inner}</span></p></section>'
    else:
        def para(text):
            inner = inline(text, em, ci)
            return para_wrap(t["para"], inner)

    styled = []          # 完整正文（含样式代码块）→ 校验+预览
    segments = []        # 纯 prose 片段 → 原生插入代码用
    codes = []

    buf = []             # 当前 segment 累积的 prose html

    def flush():
        if buf:
            segments.append("".join(buf))
            buf.clear()

    # 头部
    head = t["header"]()
    styled.append(head)
    buf.append(head)

    # 导语
    for p in INTRO:
        styled.append(para(p)); buf.append(para(p))

    # 章节
    for ch in CHAPTERS:
        ctitle = t["chapter"](ch["num"], ch["en"], ch["title"])
        styled.append(ctitle); buf.append(ctitle)
        for p in ch["before"]:
            styled.append(para(p)); buf.append(para(p))
        if ch["code"]:
            # 预览：样式代码块
            styled.append(code_block_styled(t["code_bar"], ch["code"]["lang"], ch["code"]["code"]))
            # 分段：flush 当前 prose，记 code，开新段
            flush()
            codes.append({"lang": ch["code"]["lang"], "code": ch["code"]["code"]})
        for p in ch["after"]:
            styled.append(para(p)); buf.append(para(p))
        if t.get("chapter_close"):
            close = '</section>'
            styled.append(close); buf.append(close)

    # 结语
    for p in CONCLUSION:
        styled.append(para(p)); buf.append(para(p))

    # 三连卡 + 结尾
    if t.get("cta"):
        cta = three_link(t)
        styled.append(cta); buf.append(cta)
    end = t["end"]()
    styled.append(end); buf.append(end)

    flush()

    # 拼正文容器
    body = "".join(styled)
    full = f'<section style="{t["container"]}">{body}</section>'
    return full, segments, codes


def main():
    for theme in THEMES:
        t = THEMES[theme]
        full, segments, codes = render(theme)
        fname = f'排版_{t["cn"]}({t["id"]}).html'
        (OUT / fname).write_text(full, encoding="utf-8")
        seg = {"segments": segments, "codes": codes,
               "title": TITLE, "theme_cn": t["cn"], "theme_id": t["id"]}
        (OUT / f".seg_{t['id']}.json").write_text(
            json.dumps(seg, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✓ {t['cn']}: 正文 {len(full)} 字符, 分段 {len(segments)}, 代码块 {len(codes)} → {fname}")


if __name__ == "__main__":
    main()
