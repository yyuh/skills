# 存稿自动化 + 名片 + 三连卡 操作细节

本文档记录真实踩坑后验证过的稳定路径。任何 Agent 在跑 `scripts/publish_draft.py` 或自行实现浏览器存稿前，必读本文档。

## 1. 登录态探测（先探测，失效才提醒扫码）

- 打开 `https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=77&createType=0&lang=zh_CN` 后先判断：
  - 页面出现「草稿箱」「新建」等入口 → 已登录，直接继续。
  - 页面出现二维码/「微信扫一扫」/「使用账号登录」→ 登录态失效，需用户扫码。
- 公众号后台 session 约 24h 有效；登录态存活期间连续排版多篇复用同一登录态，每篇不重复扫码。
- **编辑页 URL 必须显式带 token 参数**（如 `&token=1024637583`），否则即使已登录也显示「请重新登录」。token 从登录后 home 页 URL 获取。

## 2. 正文注入（富文本 paste 事件）

- 编辑器结构：`.ProseMirror` 共 2 个——标题框 placeholder 含「请在这里输入标题」，正文框 placeholder 为空。
- **正文 ProseMirror 定位**：遍历 `.ProseMirror`，取 `data-placeholder` 不含「标题」者。正文为空时**切勿按 innerText 长度选**（会误选标题框，导致 HTML 被转义成纯文本）。
- 注入方式：构造 `DataTransfer` → `setData('text/html', html)` → 自定义 paste 事件（`clipboardData` 用 `Object.defineProperty`）→ `target.dispatchEvent(evt)`。**不要直接 innerHTML 赋值**（ProseMirror 状态不同步）。
- **中文必须 `decodeURIComponent(escape(atob(b64)))` 还原**——只 `atob()` 会把 UTF-8 中文按 Latin-1 解析成乱码。
- 大文件分块：base64 后每段约 14-16KB（避免命令行/脚本超长），逐段注入（光标置尾即追加）。
- 分块边界断在标签属性中间没问题（ProseMirror 容错补全）；但可能残留裸 CSS 片段文本（如 `:14px;line-height:1.9;...">`），注入后需全文检索 `line-height` 裸文本节点清除。
- 误注入后刷新页面即可恢复干净编辑页，无脏数据残留。

## 3. 标题填入（React 受控组件）

- 标题框是 `textarea`（placeholder 含「标题」）。
- 用原生 setter：`Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set.call(ta, val)` 赋值，再派发 `input` + `change` 事件（bubbles:true）。直接 `ta.value = x` 不触发 React 状态更新。

## 4. 公众号名片插入（每篇必带）

操作路径（已多次验证）：
1. 点击工具栏「更多」按钮 → 展开 `.tpl_dropdown_menu_item` 列表 → 点击「账号名片」。
2. 弹窗 `.profile_dialog` 出现输入框（placeholder 含「账号名称或账号ID」）→ 原生 setter 填「硅基研究员」→ 派发 input/change。
3. 等待搜索渲染（networkidle）。**必须先点「最近使用」项 `li.profile_history_item` 触发搜索结果列表渲染**，否则只显示初始状态，无「插入」按钮或按钮 disabled。
4. 搜索结果里多个同名账号（理想汽车硅基研究所/江西硅基研究院等）**勿选错**：选中 `.wx_profile_card` 中 innerText 含「硅基研究员」且简介含「一个AI研究员的日常记录」的卡片，点击后 class 变 `wx_profile_card_selected`。
5. 点「插入」按钮 → 正文末尾出现 `<mp-common-profile data-nickname="硅基研究员" ...>`，外层包裹 `section.mp_profile_iframe_wrp`，对话框自动关闭。
6. **位置校验**：名片必须在正文最末尾。若不在，取 `profile.closest('.mp_profile_iframe_wrp, section[nodeleaf]')` 包裹层，`target.appendChild(wrp)` 移到末尾；验证 `target.children` 最后一个子节点是 wrp。

## 5. 三连卡（每篇必带，统一规范）

- 三项：点赞=大拇指 / 推荐=爱心 / 转发=弯箭头，**图标上文字下**（SVG），flex 居中 gap 24-28px，每项 40px 圆形浅底容器。
- 旧样式（在看/星标/左右排）一律改；正文「在看」→「推荐」、「星标」→「转发」。
- 注入方式同正文（base64 + paste 事件），光标 collapse 到 `.ProseMirror` 末尾再派发。
- 模板参考（摸鱼绿配色，可换主题色）：
  - 点赞：大拇指 SVG `M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3`
  - 推荐：爱心 SVG `M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z`
  - 转发：弯箭头 SVG `M4 18v-4a8 8 0 0 1 8-8h8` + `polyline 16 2 20 6 16 10`
- 完整三连卡 HTML 由主题库 footer-cta 组件提供，直接取用即可。

## 6. 保存草稿与验证

- 点「保存为草稿」按钮（按 innerText 含「保存为草稿」查找 button）。
- 保存成功标志：URL 由 `action=edit&isNew=1` 变为 `action=edit&appmsgid=<数字>`；历史版本区出现「MM-DD HH:MM 养乐多网页版 手动保存」（账号名可变）。
- 保存后告知用户「文章已存入草稿箱，确认没问题后手动发布」——**发布由用户手动，绝不代发**。

## 7. 已知环境坑

- **Windows GBK 终端**：Python stdout 输出 emoji（📋✓）会 UnicodeEncodeError。跑脚本设 `PYTHONIOENCODING=utf-8`、`PYTHONUTF8=1`，或把结果写文件再读。
- **PowerShell 内联 JS/中文**：复杂 JS 与中文命令禁内联直传（引号/括号被解析破坏），一律写 `.py/.js` 脚本落盘再执行。
- **file:// 协议**：预览页「复制到公众号」按钮在部分环境被浏览器安全策略拦截，可用 `python -m http.server` 起本地服务打开，或直接走脚本注入。
- **Vue/React 组件 `.click()` 无效**：必要时用 `new MouseEvent` 派发 mousedown→mouseup→click。
