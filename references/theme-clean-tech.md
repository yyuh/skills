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
大编号字号：   36px
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
<p style="font-size:15px;color:#666666;line-height:2.1;margin:32px 16px 32px;">
  <span leaf="">{{一句话导语：这个项目解决了什么问题 / 这条新闻为什么值得看}}</span>
</p>
```

---

## 组件 3 大编号模块（01/02/03）

> 用大号橙色数字把长文切成独立模块。每个模块结构：编号→小标题→正文→截图→项目地址。

```html
<section style="margin:40px 16px 0;">
  <!-- 大编号 -->
  <p style="font-size:36px;font-weight:800;color:#FF6B35;line-height:1;margin:0 0 8px;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;">
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

## 组件 5 代码块（公众号原生）

> 项目地址和命令行用公众号原生代码块样式（灰底圆角）。

```html
<section style="background:#F5F5F5;border-radius:6px;padding:12px 16px;margin:12px 0;overflow-x:auto;">
  <p style="font-size:13px;color:#333333;font-family:Menlo,Monaco,'Courier New',monospace;line-height:1.6;margin:0;word-break:break-all;">
    <span leaf="">{{代码/URL/命令}}</span>
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
<section style="margin:40px 16px 24px;text-align:center;">
  <p style="font-size:14px;color:#999999;line-height:1.6;margin:0;">
    <span leaf="">点击下方卡片，关注硅基研究员</span>
  </p>
</section>
```

---

## 组件 9 作者签名

```html
<section style="margin:24px 16px 0;padding-top:20px;border-top:1px solid #EEEEEE;">
  <p style="font-size:13px;color:#999999;line-height:1.6;margin:0;text-align:right;">
    <span leaf="">硅基研究员 · 专注AI工具与开源项目</span>
  </p>
</section>
```

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
- ❌ 段落不超过3行（手机屏幕），超过就拆段
- ❌ 不用背景色块包裹正文

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
