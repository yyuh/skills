# gzh-publish

公众号文章自动化发布 Skill —— 从选题、排版到存入草稿箱的完整流水线。

## 功能特性

- **多风格排版**：内置 6 套公众号排版风格（新丑撞色、摸鱼绿、瑞士极简、包豪斯几何、日式杂志、粗野主义），一键生成带样式的正文 HTML
- **完整发布流水线**：标题 + 正文 + 封面 + 账号名片 + 原创声明，一键存入公众号草稿箱
- **原生代码块**：命令行、网址、仓库地址自动插入公众号原生代码模块（灰色背景 + 行号）
- **GitHub 热榜选题**：自动抓取 GitHub Trending，生成深度解读文章
- **合规校验**：发布前自动校验 HTML 结构、引号、组件规范
- **登录态缓存**：一次扫码，长期复用，无需每次登录

## 快速开始

### 环境要求

- Windows 10/11
- Python 3.14+（系统 Python，非 WorkBuddy 托管 Python）
- Playwright + Chromium（已内置）

### 使用方式

```bash
# 1. 生成排版后的正文 HTML（用新丑撞色风格）
# （在 Skill 流程中自动完成，此处仅示意）

# 2. 完整发布（标题 + 正文 + 封面 + 名片 → 草稿箱）
py -3.14 scripts/publish_full.py 正文.html --title "文章标题" --cover 封面.jpg

# 3. 仅存正文+标题（不含封面和名片）
py -3.14 scripts/publish_draft_async.py 正文.html --title "文章标题"

# 4. 校验 HTML 合规性
py -3.14 scripts/validate_gzh_html.py 正文.html
```

首次运行会弹出浏览器，扫码登录公众号后自动缓存登录态（`.gzh-profile-dir/`），后续无需重复扫码。

## 工作流程

```
用户下达任务
    ↓
检查公众号登录态 → 未登录则停止，等用户扫码
    ↓
生成/获取文章内容（原创写作 / GitHub 热榜 / 用户提供）
    ↓
选择排版风格，生成带样式的正文 HTML
    ↓
生成与风格一致的封面图（2.35:1）
    ↓
打开公众号编辑器 → 填标题 → 注入正文
    ↓
插入原生代码块（命令行/网址/仓库地址）
    ↓
上传封面 → 设置为文章封面 → 删除正文临时图
    ↓
插入账号名片到文章底部
    ↓
处理原创声明对话框 → 保存草稿
    ↓
完成，用户在手机草稿箱查看并手动发布
```

## 目录结构

```
gzh-publish/
├── SKILL.md                          # Skill 主文档（使用说明 + 踩坑记录）
├── README.md                         # 项目说明（本文件）
├── .gitignore
├── scripts/
│   ├── publish_full.py               # ⭐ 完整发布流水线（封面+名片+原创对话框）
│   ├── publish_draft.py              # 存稿（同步版）
│   ├── publish_draft_async.py        # 存稿（异步版+greenlet桩，绕开WDAC）
│   ├── publish_draft_card_bottom.py  # 名片置底版
│   ├── add_cover_to_draft.py         # 给已有草稿添加封面
│   ├── insert_profile_card.py        # 插入账号名片
│   ├── validate_gzh_html.py          # HTML 合规校验
│   ├── wrap_preview.py               # 生成预览页（手动复制兜底）
│   ├── fix_quotes.py                 # 半角引号→全角
│   ├── extract_docx.py               # docx → Markdown
│   ├── component_lint.py             # 组件库源头检查
│   ├── fetch_ai_news.py              # 抓 AI 媒体首页选题
│   ├── rescale_fonts.py              # 字体缩放
│   └── build_five_styles.py          # 多风格预览页
├── references/
│   ├── theme-index.md                # 主题索引（单一来源）
│   ├── theme-moyu-green.md           # 摸鱼绿
│   ├── theme-neo-brutalism.md        # 新丑撞色
│   ├── theme-swiss-minimal.md        # 瑞士极简
│   ├── theme-bauhaus.md              # 包豪斯几何
│   ├── theme-japanese-mag.md         # 日式杂志
│   ├── common-components.md          # 通用增量组件库
│   ├── format-normalize.md           # 输入归一化规则
│   └── publish-sop.md                # 存稿+名片+封面操作细节
└── assets/
    └── preview-template.html         # 预览页外壳模板
```

## 排版风格

| 风格 | 特点 | 适用场景 |
|------|------|----------|
| 新丑撞色 | 高饱和对比色、粗边框、错位排版 | 科技资讯、工具推荐、热点解读 |
| 摸鱼绿 | 清新绿色、柔和留白、轻松语气 | 职场话题、生活方式、轻科普 |
| 瑞士极简 | 大量留白、网格排版、无衬线字体 | 深度分析、行业报告、方法论 |
| 包豪斯几何 | 几何图形、三原色、结构化布局 | 设计思维、创意工具、艺术相关 |
| 日式杂志 | 竖排元素、精致排版、和式美学 | 文化评论、生活美学、读书笔记 |
| 粗野主义 | 粗黑边框、原始质感、强冲击力 | 观点文、批判文、先锋话题 |

## 注意事项

### Windows 策略机环境

如果运行报 `greenlet` / `_socket` 被「应用程序控制策略已阻止」，是 Windows WDAC/AppLocker 拦截了 Playwright 底层 DLL。**解法**：统一用异步版脚本（`publish_draft_async.py` / `publish_full.py`），它们在 import 前打了纯 Python greenlet 桩，绕开被拦 DLL。

### 登录态过期

`.gzh-profile-dir/` 里的 cookie 一般 1–2 周过期，过期后脚本会提示重新扫码。

### 封面比例

公众号封面统一用 2.35:1 宽屏比例（如 1280×545），不要用方形。

### 代码块

命令行、网址、仓库地址必须用公众号原生代码模块（灰色背景+行号），不能用普通文本或 HTML `<pre>`。插入流程见 `SKILL.md`。

## License

MIT
