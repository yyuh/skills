# 公众号排版组件库 —— 清爽技术风（逛逛GitHub风）

> **使用说明**：本组件库为「清爽技术风」主题（Clean Tech），仿照"逛逛GitHub"排版风格。所有组件使用**内联样式**，可直接复制粘贴到微信公众号编辑器。
>
> **设计风格**：黑白灰为主 + 单一强调色橙色 #FF6B35 + 大量留白 + 大编号模块分隔。无花哨装饰、无撞色、无粗黑边框。信息层级极其明确：标题→导语→大编号→小标题→正文→截图。
>
> **公众号平台限制须知**：
> - ❌ 不支持 `<style>`/`<script>`、CSS class/id、`position:fixed/absolute`、`float`、`@media`/`@keyframes`、`display:grid`
> - ✅ 支持内联 `style`、`display:flex`（有限）、`linear-gradient`、`border-radius`、`box-shadow`、`<section>/<p>/<span>/<strong>/<img>` 等基础标签
>
> **WeChat 兼容铁律**：装饰性空元素内部放 `<span leaf=""><br></span>`；不要把 font-size 打在 strong 上；不用 position:absolute；无内容区域整块删掉。
>
> **清爽三原则**：
> 1. **黑白灰为主**——正文深灰 #333，次要文字中灰 #666，背景纯白，禁用多种颜色混搭
> 2. **单一强调色**——全片只用橙色 #FF6B35，用于大编号、关键词高亮、链接，其他位置不用
> 3. **截图裸放**——截图直接嵌在段落下方，不加边框、不加圆角、不加阴影、不加说明文字

---

## 设计变量速查表

```
背景色：       #FFFFFF（纯白）
强调色橙：     #FF6B35（仅用于编号/关键词/链接）
标题色：       #111111（近黑，标题）
正文色：       #333333（正文）
次要文字：     #666666（说明/注释/导语）
浅灰文字：     #999999（辅助/时间）
分割线：       #EEEEEE（1px 实线，不做渐变）
正文字号：     15px
行高：         1.8
段间距：       16px
大编号字号：   48px
小标题字号：   17px
最大宽度：     677px
内容区边距：   0 16px
```

字体栈：`-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif`

---

## 组件 1 全局容器

```html
<section style="max-width:677px;margin:0 auto;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;color:#333333;line-height:2.1;letter-spacing:0.3px;overflow-x:hidden;">

  <!-- 所有组件放在这里 -->

</section>
```

---

## 组件 2 开头导语（一句话概括）

> 文章开头用一句话概括核心，不加装饰符号，前后各空一行。

```html
<p style="font-size:16px;color:#111111;font-weight:700;line-height:1.8;margin:0 16px 8px;">
  <span leaf="">{{核心卖点，一行讲完，不加解释}}</span>
</p>
```

---

## 组件 3 大编号模块（01/02/03）

> 用大号橙色数字把长文切成独立模块。每个模块结构：编号→小标题→正文→截图→项目地址。

```html
<section style="margin:40px 16px 0;">
  <!-- 大编号 -->
  <p style="font-size:48px;font-weight:900;color:#FF6B35;line-height:1;margin:0 0 8px;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;">
    <span leaf="">01</span>
  </p>

  <!-- 小标题 -->
  <p style="font-size:17px;font-weight:700;color:#111111;line-height:1.5;margin:0 0 20px;">
    <span leaf="">{{小标题：一句话说清这个项目是干嘛的}}</span>
  </p>

  <!-- 正文段落（每段不超过3行） -->
  <p style="font-size:15px;color:#333333;line-height:2.1;margin:0 0 20px;">
    <span leaf="">{{正文段落1}}</span>
  </p>
  <p style="font-size:15px;color:#333333;line-height:2.1;margin:0 0 20px;">
    <span leaf="">{{正文段落2}}</span>
  </p>

  <!-- 截图（裸放，不加边框圆角阴影） -->
  <p style="margin:24px 0;text-align:center;">
    <img src="{{截图URL}}" style="max-width:100%;height:auto;border-radius:0;" />
  </p>

  <!-- 项目地址（橙色高亮，单独一行） -->
  <p style="font-size:14px;color:#FF6B35;line-height:1.6;margin:16px 0 0;word-break:break-all;">
    <span leaf="">{{项目地址URL}}</span>
  </p>
</section>
```

---

## 组件 4 关键词高亮

> 正文中的关键词用橙色加粗，不用背景色块。

```html
<p style="font-size:15px;color:#333333;line-height:2.1;margin:0 0 20px;">
  <span leaf="">{{前文}}</span>
  <strong style="color:#FF6B35;font-weight:700;"><span leaf="">{{关键词}}</span></strong>
  <span leaf="">{{后文}}</span>
</p>
```

---

## 组件 5 代码块（深色，真实终端风）

> 项目地址和命令行用深色代码块（真实终端观感）。多行命令每行一个 `<p style="margin:0">`，行距靠 line-height 控制；长行自动换行不溢出。

```html
<section style="background:#1E293B;border-radius:8px;padding:12px 16px;margin:12px 0;overflow-x:auto;">
  <p style="font-size:13px;color:#E2E8F0;font-family:Menlo,Monaco,'Courier New',monospace;line-height:1.7;margin:0 0 6px;word-break:break-all;">
    <span leaf="">{{代码/URL/命令 第1行}}</span>
  </p>
  <p style="font-size:13px;color:#E2E8F0;font-family:Menlo,Monaco,'Courier New',monospace;line-height:1.7;margin:0;word-break:break-all;">
    <span leaf="">{{第2行}}</span>
  </p>
</section>
```

---

## 组件 6 步骤列表

> 实操步骤用简洁数字列表，不用花哨卡片。

```html
<section style="margin:24px 0;">
  <p style="font-size:15px;color:#333333;line-height:2.1;margin:0 0 8px;">
    <strong style="color:#FF6B35;font-weight:700;"><span leaf="">1.</span></strong>
    <span leaf="">{{第一步说明}}</span>
  </p>
  <p style="font-size:15px;color:#333333;line-height:2.1;margin:0 0 8px;">
    <strong style="color:#FF6B35;font-weight:700;"><span leaf="">2.</span></strong>
    <span leaf="">{{第二步说明}}</span>
  </p>
  <p style="font-size:15px;color:#333333;line-height:2.1;margin:0 0 8px;">
    <strong style="color:#FF6B35;font-weight:700;"><span leaf="">3.</span></strong>
    <span leaf="">{{第三步说明}}</span>
  </p>
</section>
```

---

## 组件 7 分割线

> 1px 浅灰实线，不做渐变不做装饰。

```html
<section style="margin:32px 0;border-top:1px solid #EEEEEE;">
  <span leaf=""><br></span>
</section>
```

---

## 组件 8 结尾引导关注

> 统一一句话引导，不加二维码大图，不加"求转发"话术。

```html
<section style="margin:40px 16px 0;">
  <p style="font-size:48px;font-weight:900;color:#FF6B35;line-height:1;margin:0 0 8px;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;">
    <span leaf="">04</span>
  </p>
  <p style="font-size:17px;font-weight:700;color:#111111;line-height:1.5;margin:0 0 12px;">
    <span leaf="">点击下方卡片，关注硅基研究员，每天一个 AI 资讯</span>
  </p>
</section>
```

> 编号顺延：正文最后一节是 03，引导关注就用 04；正文到 02 就用 03。编号样式与正文模块完全一致。

---

## 组件 9 作者签名

```html
<section style="margin:24px 16px 0;padding-top:20px;border-top:1px solid #EEEEEE;">
  <p style="font-size:13px;color:#999999;line-height:1.6;margin:0;text-align:right;">
    <span leaf="">点击下方卡片，关注硅基研究员，每天一个 AI 资讯</span>
  </p>
</section>
```

---

## 组件 10 引流卡（已取消，2026-09-27 用户指示）

> ~~每篇正文末尾放品牌引流卡图~~。**引流卡已取消**：正文不再放任何品牌卡图，关注引导由结尾引导文字（组件 8）+ 结尾公众号名片承担。插图数量 = 正文插图 3~4 张真实截图，无固定尾图。

---

## 文章结构配方表

| 文章类型 | 组件组合顺序 |
|---------|-------------|
| GitHub项目推荐（单项目） | 容器 → 导语 → 大编号01(小标题+正文+截图+项目地址) → 步骤(可选) → 分割线 → 结尾 → 签名 |
| GitHub项目推荐（多项目） | 容器 → 导语 → 大编号01 → 大编号02 → 大编号03 → 分割线 → 结尾 → 签名 |
| AI新闻解读 | 容器 → 导语 → 大编号01(核心事实) → 大编号02(误区/判断) → 大编号03(建议/动作) → 分割线 → 结尾 → 签名 |
| 单项目深度评测 | 容器 → 导语 → 大编号01(是什么) → 大编号02(怎么用) → 大编号03(优缺点) → 分割线 → 结尾 → 签名 |

---

## 禁止事项

- ❌ 禁用高饱和撞色（粉/蓝/黄三色搭配）
- ❌ 禁用粗黑边框、硬阴影、圆角卡片装饰
- ❌ 禁用贴纸风元素、动态分割线、无意义图标
- ❌ 禁用多种强调色（全片只有橙色 #FF6B35 一种强调色）
- ❌ 截图不加边框、不加圆角、不加阴影、不加说明文字
- ❌ 插图不带其他媒体水印（不要带公众号名称、版权标识等来源水印）
- ❌ 插图不加下标/图注（不要在图片下面加"图1：xxx"这类标注）
- ❌ 段落不超过3行（手机屏幕），超过就拆段
- ❌ 不用背景色块包裹正文
- ❌ 三连卡（点赞/推荐/转发）已取消，正文不放置任何三连卡组件
- ❌ 引流卡（品牌卡图）已取消（2026-09-27），正文不放任何尾图卡
- ❌ 信息卡/提示卡每篇最多 1 个，正文回归素段落，不要卡片堆砌

---

## 封面规范（2026-09-14 三次更新：逛逛GitHub风）

> 核心原则：纯黑底 + 左边视觉元素 + 右边巨大白字。仿照"逛逛GitHub"封面风格，干净但有视觉元素。

### 封面结构（左右布局）

| 区域 | 占比 | 内容 |
|------|------|------|
| **底板** | 100% | 纯黑 `#000000`，不用渐变不用纹理 |
| **左边视觉元素** | 1/3宽度 | 3D卡通图标 / 品牌Logo / 真实产品截图，要醒目可爱 |
| **右边大字** | 1/2宽度 | 4-6个字，极粗黑体白色，占封面1/3高度 |
| **角落水印** | 左上角 | 极小灰色"硅基研究员" |

### 三种封面模式（按优先级排序）

**模式B：真实产品Logo+大字（首选，读者一眼认出）**
- 纯黑底 + 左边**真实存在的产品/项目Logo** + 右边巨大白字
- 优先用真实产品图标：Codex、Claude Code、ChatGPT、GitHub Octocat、QQ、微信、Chrome、微软、苹果、谷歌等
- 讲什么产品就放什么产品的图标，不要用抽象图形代替
- 示例：讲Codex就放Codex图标 + 右边白字"网页版白嫖"；讲Claude Code就放Claude图标 + 右边白字"越权警告"
- Logo获取：从官网/维基百科下载真实Logo PNG，不要AI生成（AI生成的Logo不像）

**模式C：纯截图（次选，最真实）**
- 直接放GitHub项目主页截图 / 产品官网截图 / 应用界面截图，不加文字叠加
- 适用于：项目主页很有特色的、新闻类产品发布、界面本身就是看点的
- 截图要干净：去掉浏览器边框、地址栏、侧边栏，只保留核心内容区域

**模式A：3D概念图标+大字（兜底，没有对应产品时才用）**
- 纯黑底 + 左边3D概念图标 + 右边巨大白字
- 只有当文章主题是抽象概念（省钱/效率/安全/灵感），没有具体产品图标可放时，才用AI生成3D概念图标
- 示例：左边3D钱袋子（带橙色向下箭头）+ 右边白字"账单砍半"
- 图标要有冲击力，不要太软太可爱

### 封面生成 Prompt 模板

```
Wide banner cover, 2.35:1. Pure black #000000 background. 
Left side: {3D卡通图标/品牌Logo描述}, cute cartoon style, taking up 1/3 width. 
Right side: extremely large bold white Chinese text "{4-6字钩子词}", heavy black sans-serif font, very thick strokes, taking up 1/2 width. 
Maximum contrast between black and white. No other elements, no decoration, no gradients. Clean like a tech magazine cover. Chinese characters must be perfectly rendered.
```

### 禁止
- ❌ 深灰蓝底、渐变底、纹理底
- ❌ 纯文字居中（太素，没有视觉元素）
- ❌ 多个元素堆砌（不要同时放箭头+截图+标题+副标题）
- ❌ 文字太小（必须占封面1/3高度以上）
- ❌ 抽象图形（细折线箭头、小几何图形）
- ❌ 解释性副标题
- ❌ AI生成乱码文字（OCR检查，有乱码重生成）
