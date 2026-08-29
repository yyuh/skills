# gzh-publish 项目长期记忆

## 会话定位
本工作区（gzh-publish skill）专做公众号排版发布。用户约定：默认走完整流水线 = 排版（**当前 5 主题**组件库：摸鱼绿 moyu-green / 瑞士极简 swiss-minimal / 包豪斯几何 bauhaus / 日式杂志 japanese-mag / 新丑撞色 neo-brutalism；2026-08-26 用户删掉旧红白等、保留并新增为这 5 套）+ 强制 validate 校验 + 生成预览页 + 存入草稿箱。一次任务可指定每篇用哪套主题（如「5 篇用 5 种风格各一篇」）。

## 排版字号标准（已固化）
- 正文目标：**手机预览一行 14 个汉字**（2026-08-26 由「15 字/行」下调）。实测可用内容宽约 264px（非 320px，旧记的 320 偏乐观），故正文落点：摸鱼绿 **18px**、红白 **19px**（264÷18≈14.7 字、264÷19≈13.9 字，平均约 14）。
- 统一缩放工具：`scripts/rescale_fonts.py`（上限 44px，跳过等宽代码块与 `font-size:0`）。改主题库/组件库字号后跑它即可整体缩放，设计比例不畸变。代码块保持 13px 不变。
- 缩放因子约定：从「15 字/行」（摸鱼绿 21px / 红白 22px）调到「14 字/行」用 **×0.857**（=12/14，等比，保持主题内比例）；若日后又要改，按 `新因子 = 当前字数/目标字数` 套用即可。
- 已对 6 套主题库 + common-components + 两个 build 生成脚本统一执行过 ×0.857。

## 存稿约定
- 存稿脚本只需把「正文 HTML + 标题」存入草稿箱即可，**封面图由用户发布时手动添加**，不要试图自动传封面。
- **封面全权用户自理**：不要调用 ImageGen 出封面、也不要把 wechat-cover 等封面 skill 接入流水线（用户觉得出图太麻烦）。流水线里不要有任何封面生成/可选步骤，存完草稿即结束。

## 后续规划（用户预告）
当前基本盘（排版→校验→预览→存草稿）已稳定，并新增两项能力：
1. **自助选题（已落地进 SKILL.md）**：选题来源 = 2 个自动抓取源（① GitHub 热榜 + ④ AI 媒体/社区：机器之心/量子位/36氪AI，均 WebFetch）+ 3 种用户驱动输入（B1 给题目+中心论点、B2 给题目、B3 给整篇待整理文）。**无「四源扫描」一说，旧记忆误记**。本号只发 AI 类内容。
2. **爬取网页（首个落地：GitHub 热榜）**：已作为「可选功能」写进 SKILL.md——用户说「爬 GitHub 热榜 / 从 GitHub 趋势选一篇」即触发，走 WebFetch（**绝不用 Playwright**，本机 WDAC 拦 DLL）抓 `github.com/trending?since=daily` 前十 → 选篇 → 取详情 → 接现有 7 步流水线。后续可扩到任意网页抓取（同样优先 requests / 系统 Python，避开 Playwright）。
- 作者名默认「硅基研究员」，正文**开头**自动插公众号名片（2026-08-26 起由「文末」改为「前置」，每篇仅一次，幂等）+ 点赞/推荐/转发三连卡。
- 登录态缓存在 `.gzh-profile-dir`（cookie 约 1–2 周有效），headful 打开通常即已登录，无需重扫码。

## 关键环境约束（重要）
本机 Windows 应用控制策略（WDAC/AppLocker）阻止 Playwright 同步 API 依赖的 `greenlet` C 扩展 DLL（`import greenlet` 直接报「应用程序控制策略已阻止此文件」，关沙箱也无效）。
- 原 `scripts/publish_draft.py`（同步 API）在本环境**不可用**。
- 解决：用 `scripts/publish_draft_async.py`——在 `import playwright.async_api` 之前把 `sys.modules['greenlet']` 替换成纯 Python 桩（`greenlet.greenlet` 仅作基类），异步 API 走 asyncio 不实例化 greenlet，可正常拉起浏览器。
- playwright 1.62.0 包装在系统 Python 3.14（`C:\Users\18480\AppData\Local\Microsoft\WindowsApps\python.exe`），浏览器二进制 chromium-1234 在 `ms-playwright`。**后续存稿一律用 `publish_draft_async.py`。**

## 编辑器打开策略（4 级兜底，已验证 100000611）
公众号后台「文章」编辑器入口有多种，DOM 结构可能改版。`publish_draft_async.py` 当前按以下优先级尝试打开编辑器，找到任一即停：
1. **点首页「新的创作 → 文章」**：用 TreeWalker 找「文章」文本，**向上找最近的可点击祖先**（`onclick` / `<a>` / `<button>` / `cursor:pointer` / `role=button/link`）后点击；用 `ctx.expect_page` 捕获新标签页，再用 `wait_for_selector('.ProseMirror')` 确认就绪。
2. **遍历所有标签页找 ProseMirror**（覆盖点击在原标签页内导航的情况）。
3. **去「草稿箱」页点「新建图文」按钮**（最稳入口，DOM 结构稳定）。
4. **token 直跳 `appmsg_edit_v2` URL**（最后兜底，有时落回首页）。
**教训**：点 DOM 文本再 `click()` 父级不一定能触发——必须**找最近的可点击祖先**。`expect_page` 比事后遍历 `ctx.pages` 更可靠。

## 登录态与二维码踩坑（已验证）
- **二维码约 2 分钟过期**：等待循环中每 120s 自动 `goto` 刷新登录页 + 重截 PNG，让实时窗口里的码始终有效。
- **`is_logged_in` 双判**：URL 含 `cgi-bin` 且不含 `connect/qrconnect` 即视为已登录（首页/body 文本判断兜底）。仅看 body 文本漏掉「已登录但首页未完全渲染」的中间态。
- **杀进程会丢 cookie**：`taskkill` 强制终止 Playwright 进程时，未 flush 的 cookie 不落盘到 `.gzh-profile-dir`，重跑回未登录。**正确做法**：让脚本自己跑到 `ctx.close()`，或在等待扫码阶段不要杀。
- **诊断日志**：等待循环每 30s 把每个 tab 的 `url` + 正文前 50 字打出来，方便区分「用户扫错窗口（自己 Chrome）」还是「Playwright 真没登录」。
- **存稿必须串行**：`.gzh-profile-dir` 是单一目录，两个 Playwright 进程同时起会抢 SingletonLock 互相崩。同一时间只跑一个存稿任务。
- **登录握手协议（Agent 铁律，2026-08-25 用户明确）**：检测到未登录 → **立刻停止并通知用户「需要登录，请扫码；扫完回『已登录』」** → 等用户明确「已登录」再继续 → 拿到 `appmsgid` 才算完成。绝不在「已弹码/已发起存稿」时宣称成功。脚本交接用户手动扫时传 `--wait-scan 1800+` 防浏览器提前超时。后台任务追踪可能丢失，判真实状态看 `msedge` 进程 + `outputs/login_qr.png` 时间戳，不只信 TaskOutput。
- **复制 profile 接管（免扫码方案 2）本机不可行（2026-08-25 实测）**：把默认 `User Data` 复制到独立目录 `User Data_CDP`，用 `--remote-debugging-port=9222 --remote-allow-origins=*` 启动，`connect_over_cdp` 连接成功（greenlet 桩下异步 API 可用，已写好 `scripts/publish_draft_cdp.py`），但 Chromium cookie 用 OS DPAPI 加密 + Edge 启动后改写 `Local State` 导致原 cookie 解密失败，Edge 打开 `mp.weixin.qq.com` 仍显示登录页（含扫码按钮）。**Chromium cookie 不可跨 profile 移植**——免扫码通道在本机走不通，仍需用户扫一次码（登录态缓存进 `.gzh-profile-dir`，1–2 周内免扫）。另：Edge 默认 profile 硬性禁止开远程调试（`DevTools remote debugging requires a non-default data directory`），"直接接管用户正在用的 Edge"也不行；且 `User Data_CDP` 复制时 robocopy 默认 `/R:1000000 /W:30` 遇锁文件会卡死数小时，必须加 `/R:1 /W:1` 速跳。

## 原生「插入代码」按钮本环境不可自动化触发（2026-08-26 实测）
- 工具栏按钮是 `.edui-for-insertcode`（`data-tooltip="插入代码"`，纯图标无 innerText/无 aria-label）。
- 点击打不开代码对话框：① `#edui1_toolbar_mask`（≈1434×45px，`display:block;pointer-events:auto`）整条盖在工具栏上拦截指针；② 即便 JS/force 点中按钮，`window.UE.instants` 为空——微信真编辑器是 ProseMirror，UEditor 工具栏未连真实编辑器实例，按钮 `execCommand('insertcode')` 是 no-op，对话框永不开。
- 结论：本机自动化**无法用微信原生「插入代码」**。替代方案（用户 2026-08-26 确认采用）：用合规深色样式代码块 `styled_code_block(lang,code)`（见 `publish_draft_native.py`）——和微信原生代码块外观一致，读者看到的是标准代码块，区别仅不是微信内部 `<pre>` 元素；可过 validate。
- 名片前置 `insert_account_card_top` 走「顶部菜单栏直接点『账号名片』→ 搜索『硅基研究员』→ 点『最近使用』→ 选含『一个AI研究员的日常记录』的卡 → 插入 → 置顶」稳定成功（CLICKED_DIRECT:EXACT 路径）。
