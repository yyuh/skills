---
name: "gzh-publish-pipeline"
description: "公众号排版+校验+预览+存草稿 全自包含流水线。把任意文章转成公众号合规富文本并自动存入草稿箱；不依赖 AppSecret/认证，走 UI 自动化。收到排版/发布/存草稿需求即触发。跨 Agent 通用（Claude Code / Codex / Cursor / OpenClaw 等装上依赖即可跑）。"
---

# 公众号排版 + 存稿流水线（自包含合并版）

把任意形式文章（纯文本 / Markdown / Word / PDF / 链接）转成公众号合规 HTML，并自动存入微信公众号草稿箱。**本 skill 是单文件目录自包含**：排版组件库、校验脚本、预览脚本、Playwright 存稿脚本、主题配方全在这里，拷贝到任何支持 `SKILL.md` 的工具的 skills 目录即可使用，不依赖本机其他路径。

> 公众号未认证、没有 AppSecret 也能用——存稿走浏览器 UI 自动化（Playwright 点击 + ProseMirror 富文本注入），不调任何微信接口。

## 何时触发

用户发来一篇文章/素材且没特殊说明（如「只排版不要存」「改一下」），默认执行完整流水线：排版 + 校验 + 预览 + 存草稿箱。用户说「只排版」「不存稿」时只做到预览页交付。

## 环境准备（首次 / 换机器必看）

依赖：Python 3.10+，以及 `playwright` + `websocket-client`（仅 THUQX/CDP 备用通道需要）。

```bash
pip install playwright websocket-client
playwright install chromium
```

- **Windows 中文环境**：Python 脚本 stdout 遇 emoji 会 GBK 崩溃，跑校验/预览/存稿时务必设 `PYTHONIOENCODING=utf-8`、`PYTHONUTF8=1`。
- **登录态**：存稿脚本用 `launch_persistent_context(user_data_dir=skill根/.gzh-profile-dir)` 复用登录态。首次运行（或 cookie 过期）加 `--headful` 参数，会弹出浏览器让你手机微信扫码，登录后 cookie 持久化进 `.gzh-profile-dir`，之后不带 `--headful` 也能复用。`.gzh-profile-dir` 是 per-机器 per-微信账号的，**换机器需重新扫码**（属正常）。
- **封面图**：本流程不自动传封面，存稿后需在公众号后台手动上传（草稿列表点开该草稿 → 封面区 → 上传）。

## 六个固定决策

1. **排版主题（两风格轮换）**：用户没指定时**默认轮换**——上篇用摸鱼绿 `moyu-green`，本篇用红白色系 `red-white`，下篇再回摸鱼绿，如此交替。题材映射仅用于用户明确「自动排」时：
   - 教程/干货/清单/工具盘点/测评/内刊手记/系统说明 → 摸鱼绿 moyu-green（默认）
   - 观点/深度分析/设计评论/随笔禅意 → 红白色系 red-white
   - 主题索引单一来源：`references/theme-index.md`
2. **存草稿箱**：默认执行，不打断用户。登录失效 → 提示用户用 `--headful` 扫码（本 skill 输出提示，由宿主 Agent 通道发送）。
3. **作者名**：`{{作者名}}` 占位（默认「硅基研究员」），简介一句。
4. **标题**：由 Agent 起/优化。主标题疑问句含关键词+数字 ≤22 字无特殊符号；副标题给具体价值；正文每段 ≤ 手机 5 行。
5. **文末公众号名片**：所有文章末尾必须插入公众号账号名片（正文最末尾）。操作路径见 `references/publish-sop.md`。
6. **三连卡规范**：点赞=大拇指 / 推荐=爱心 / 转发=弯箭头，图标上文字下（SVG）。旧「在看/星标」字样一律替换为「推荐/转发」。模板见 `references/theme-*.md` footer-cta 组件。

## 执行流程（7 步）

1. **输入归一化** → 非 Markdown 先按 `references/format-normalize.md` 转 Markdown（docx 用 `scripts/extract_docx.py`，PDF 分页读取清噪，纯文本语义推断结构）。
2. **选主题** → 读 `references/theme-index.md` 按题材选（见决策 1，默认轮换）。
3. **排版** → 读所选主题组件库 `references/theme-{标识}.md` + 通用库 `references/common-components.md`，按「文章类型 → 组件组合配方表」装配纯 `<section>` HTML。HTML 一律从组件库取，不凭记忆手写。
4. **校验（强制）** → `scripts/validate_gzh_html.py <生成的.html>`，ERROR 清零 + 半角标点 WARNING 清零才算完成。半角引号用 `scripts/fix_quotes.py <生成的.html>` 一键转全角后再复验。
5. **生成预览** → `scripts/wrap_preview.py <干净正文.html>`，产出带「复制到公众号」按钮的 `_预览.html`。
6. **起标题 + 签名** → 按决策 4 起标题；`{{作者名}}`→实际作者名；文末放签名段 + 三连卡。
7. **存草稿箱** → `scripts/publish_draft.py <正文.html> --title "标题"`（Playwright 方案，见下）。

## 半角引号修复

`validate_gzh_html.py` 会把正文里的半角 `"` `'` 报为 WARNING。用 `scripts/fix_quotes.py` 把文本节点里的英文引号成对替换为中文全角「」/‘’，幂等（已是全角再跑 = 0 替换），安全：

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  python scripts/fix_quotes.py "outputs/xxx_排版_红白色系(red-white).html"
```

## 产物规范

- 纯 `<section>…</section>` 正文片段，从全局容器开始，不包 `<!DOCTYPE>/<html>/<head>/<body>`。
- 文件名：`{原文件名}_排版_{主题中文名}({英文标识}).html`；预览页 `{...}_预览.html`。
- 样式全部内联；所有文字节点用 `<span leaf="">文字</span>` 包裹；禁 `<style>/<script>/<div>/class/id/position:fixed/absolute/float/@media/@keyframes/grid/CSS变量/外部字体`。

## 存稿自动化（跨 Agent）

```bash
# 首次 / 登录态失效：有头模式扫码
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  python scripts/publish_draft.py 排版.html --title "文章标题" --headful
# 之后复用登录态（无头，全自动）
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  python scripts/publish_draft.py 排版.html --title "文章标题"
```

脚本自动完成：登录态探测（已登录直进，未登录提示扫码）→ 新建图文 → 富文本注入（base64+paste 事件，UTF-8 安全，大文件自动分块）→ 填标题 → 文末插公众号名片 → 保存草稿 → 验证 appmsgid。所有截图/日志写到 skill 根 `outputs/`，登录态缓存写到 skill 根 `.gzh-profile-dir/`。

浏览器自动化细节（ProseMirror 定位、受控组件 setter、名片弹窗选择器、三连卡注入）见 `references/publish-sop.md`——该文件记录了真实踩坑后的稳定路径，改脚本前必读。

## Gotchas（真实踩坑）

- **漏 `<span leaf>` 包裹**是最常见致命错——粘贴后样式整片丢失，靠校验脚本兜底。
- **下划线逐段落实**：每段标 1–3 个关键词短语（主题下划线 CSS 见 theme-index），不整段划线也不漏段。
- **章节编号严格按 `##` 顺序**，不跳号；结语编号变体只用于末章。
- **签名区有且仅末尾一个**，原文末尾已有签名段时并入，不重复生成。
- **图片自适应不铺满**：`<img>` 用 `max-width:100%;height:auto;display:block;margin:0 auto`，不用 `width:100%`。
- **代码块紧凑**：每行一个 `<p style="margin:0">`，禁 `white-space:pre`，缩进用全角空格 `　`。
- **标点全角**：正文中文标点全角，代码块/行内代码保持原样。
- **不用虚线框做强调**：小标题用左竖条/药丸标签（通用库 3a-3e），虚线框仅限主题库明确风格组件与待补素材占位。
- **占位图残留**：名片图等占位无真实 URL 时整行删掉。
- **登录态过期**：`.gzh-profile-dir` 里的 cookie 一般 1–2 周过期，过期后存稿脚本退出码 2（NEED-LOGIN），加 `--headful` 重新扫码即可，不必改任何代码。
- **CDP 备用通道（THUQX 思路）**：若 Playwright 持久化 context 在某环境拉不起浏览器，可改用 Edge/Chrome 的 `--remote-debugging-port=9222` + `websocket-client` 直连，定位 ProseMirror 后走 `ClipboardEvent('paste')` 注入富文本。关键认知：公众号编辑器含**多个 ProseMirror**（标题带 `data-placeholder` 含「标题」、正文不带），querySelector 取第一个会填错位置；React 受控输入须用 native value setter；富文本只能经 paste 事件进 ProseMirror。

## 目录结构

```
gzh-publish-pipeline/
├── SKILL.md
├── scripts/
│   ├── validate_gzh_html.py    # 合规校验（必跑）
│   ├── wrap_preview.py         # 生成预览页
│   ├── fix_quotes.py           # 半角引号→全角（WARNING 清零）
│   ├── extract_docx.py         # docx → Markdown
│   ├── component_lint.py       # 组件库源头检查
│   └── publish_draft.py        # Playwright 存稿（跨 Agent）
├── references/
│   ├── theme-index.md          # 主题索引（单一来源）
│   ├── theme-moyu-green.md     # 摸鱼绿
│   ├── theme-red-white.md       # 红白色系
│   ├── common-components.md    # 通用增量库
│   ├── format-normalize.md     # 输入归一化规则
│   └── publish-sop.md          # 存稿+名片+三连卡操作细节
├── assets/
│   └── preview-template.html   # 预览页外壳模板
├── outputs/                    # 运行时产物（预览/截图/日志，可删）
└── .gzh-profile-dir/           # 登录态缓存（首次 --headful 扫码生成，per 机器）
```

## 可移植性说明

- 所有脚本的相对路径（assets、outputs、登录态目录）均基于**脚本自身位置**解析，从任意 cwd 调用都能正确落位。
- 拷到 Codex / Claude Code / 其他支持 `SKILL.md` 的工具时，只需把整个 `gzh-publish-pipeline/` 目录放到该工具的 skills 目录下，安装依赖即可。
- 登录态 `.gzh-profile-dir` 不随 skill 分发（per-机器），首次使用 `--headful` 扫码一次。
- 主题库维护：改组件库 → `scripts/component_lint.py .` 扫源头 0 ERROR → 生成产物 → `validate_gzh_html.py` 扫产物 → 修 → 重复。新主题按「添加新主题规范」登记 theme-index.md。
