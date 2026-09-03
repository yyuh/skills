# 🚀 gzh-publish

> 公众号文章自动化发布 Skill —— 从选题、排版、封面到存入草稿箱的完整流水线。

## ✨ 功能特性

- 🎨 **5 套风格排版**：新丑撞色 / 瑞士极简 / 包豪斯几何 / 日式杂志 / 红白色系，按内容类型自动匹配（技术类三色轮换）
- 📦 **完整发布流水线**：选题 → 写文 → 排版 → 校验 → 封面 → 存草稿，一键自动化
- 🖼 **封面自动生成 + OCR 检查**：2.35:1 无文字封面，「从正文选择」流程 100% 匹配，检出文字自动重生成
- 💻 **原生代码块**：命令行、网址、仓库地址自动插入公众号原生代码模块（灰色背景 + 行号）
- 🔥 **GitHub 热榜选题**：自动抓取 GitHub Trending / AI 热点，按权重生成文章
- ✅ **合规校验**：发布前自动校验 HTML 结构、全角标点、组件规范（0 ERROR 0 WARNING）
- 🔐 **登录态缓存**：一次扫码，长期复用，无需每次登录

## 🚀 快速开始

### 📋 环境要求

- Windows 10/11
- Python 3.14+（系统 Python，非 WorkBuddy 托管 Python）
- Playwright + Chromium
- 首次使用需扫码登录微信公众平台（登录态缓存到 `.gzh-profile-dir/`，换机器需重新扫码）

### 🛠 安装

```bash
pip install playwright websocket-client
playwright install chromium
```

### 📝 使用

**方式一：手动单篇**（在支持 SKILL.md 的 AI 工具中）

把本 skill 目录路径交给 AI（豆包 / Claude / Codex / WorkBuddy 等），说一句「读这个 skill，写一篇关于 XX 的文章存到草稿箱」即可。

**方式二：全自动批量**（每日定时）

skill 内置内容权重（AI 80% / 理财 15% / 修心 5%）与批量生产规范，可配置定时任务每天自动生成 N 篇存入草稿箱。

### ⚙️ 核心脚本

```bash
# 存稿（封面+名片+原创对话框，唯一推荐）
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/publish_full.py 正文.html --title "标题" --cover "封面.png"

# 合规校验
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/validate_gzh_html.py 正文.html

# 半角引号→全角（WARNING 清零）
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/fix_quotes.py 正文.html

# 生成预览页
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/wrap_preview.py 正文.html
```

## 📂 目录结构

```
gzh-publish/
├── SKILL.md               # 主流程规范（入口）
├── references/            # 主题库 + 文风档案 + 操作细节
│   ├── theme-index.md     # 主题索引（单一来源）
│   ├── theme-neo-brutalism.md  # 新丑撞色
│   ├── theme-swiss-minimal.md  # 瑞士极简
│   ├── theme-bauhaus.md   # 包豪斯几何
│   ├── theme-japanese-mag.md   # 日式杂志
│   ├── theme-red-white.md # 红白色系
│   ├── my-voice.md        # 硅基研究员文风档案
│   └── ...
├── scripts/               # 校验/排版/存稿脚本
│   ├── publish_full.py    # ⭐ 完整发布流水线（封面+名片+存稿）
│   ├── validate_gzh_html.py
│   ├── fix_quotes.py
│   └── ...
└── assets/                # 预览页模板
```

## 🔒 安全说明

- `.gzh-profile-dir/`（登录态）、`outputs/`（产物）、`.workbuddy/`（本地记忆）均已加入 `.gitignore`，不会随仓库分发
- 本仓库只包含正式脚本与文档，不含开发调试脚本

## 📜 更新日志

- **2026-09-03**：封面 OCR 检查铁律、批量生产规范、红白色系主题、抗压测试脚本（85 用例）
