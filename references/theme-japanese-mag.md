# 公众号排版组件库 —— 日式杂志

> **使用说明**：本组件库为「日式杂志」主题（MUJI 风留白极简），所有组件使用**内联样式**，可直接复制粘贴到微信公众号编辑器。
>
> **设计风格**：大量留白 + 竖排感 + 日文小字 + 棕色调 + 汉字美学。「間/侘/寂」日式美学，MUJI 风格。适合生活美学、随笔、禅意、设计评论、个人感悟类文章。
>
> **公众号平台限制须知**：
> - ❌ 不支持 `<style>`/`<script>`、CSS class/id、`position:fixed/absolute`、`float`、`@media`/`@keyframes`、`display:grid`
> - ✅ 支持内联 `style`、`display:flex`（有限）、`linear-gradient`、`border-radius`、`box-shadow`、`<section>/<p>/<span>/<strong>/<img>` 等基础标签
>
> **WeChat 兼容铁律**：装饰性空元素内部放 `<span leaf=""><br></span>`；不要把 font-size 打在 strong 上；不用 position:absolute；无内容区域整块删掉。
>
> **竖排注意**：公众号对 `writing-mode:vertical-rl` 支持有限，本组件库用横向排版模拟竖排感（大字间距、日文小字标签、左侧竖线装饰），不使用真实竖排 CSS。

---

## 设计变量速查表

```
背景色：       #FAFAF8（米白）
主文字色：     #2A2A2A（近黑）
正文色：       #555555（深灰）
次要文字：     #999999（中灰）
辅助文字：     #BBBBBB（浅灰）
强调色：       #B89070（暖棕/焦糖色）
分隔线：       #EEEEEE（极浅灰）
竖线装饰：     #DDDDDD
正文字号：     13px（偏小，日式杂志感）
行高：         2.1（偏大，增加呼吸感）
字间距：       0.5px
最大宽度：     677px
内容区边距：   0 28px
上下留白：     32px（大量留白）
```

字体栈：`-apple-system,BlinkMacSystemFont,'Hiragino Sans','PingFang SC','Microsoft YaHei',sans-serif`

---

## 组件 1 全局容器（米白大留白）

```html
<section style="max-width:677px;margin:0 auto;background:#FAFAF8;font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans','PingFang SC','Microsoft YaHei',sans-serif;color:#3A3A3A;line-height:2;letter-spacing:0.5px;overflow-x:hidden;">

  <!-- 所有组件放在这里 -->

</section>
```

---

## 组件 2 顶部信息栏（左右分栏小标签）

```html
<section style="padding:32px 28px 0;display:flex;justify-content:space-between;align-items:flex-start;">
  <p style="font-size:9px;letter-spacing:3px;color:#999;text-transform:uppercase;margin:0;font-weight:600;">
    <span leaf="">{{期号，如 ISSUE 07}}</span>
  </p>
  <p style="font-size:9px;letter-spacing:2px;color:#BBB;margin:0;">
    <span leaf="">{{日期/季节，如 2026 · 夏}}</span>
  </p>
</section>
```

---

## 组件 3 标题区（日文小字 + 大标题 + 副标题）

> 日文/中文小字标签用暖棕色，大标题用近黑色，副标题用灰色。标题之间大间距。

```html
<section style="padding:28px 28px 24px;">
  <p style="font-size:11px;letter-spacing:4px;color:#B89070;margin-bottom:16px;font-weight:600;">
    <span leaf="">{{日文/中文标签，如 暮 ら し の 手 帖}}</span>
  </p>
  <p style="font-size:26px;font-weight:700;line-height:1.5;color:#2A2A2A;margin-bottom:16px;letter-spacing:2px;">
    <span leaf="">{{主标题第一行}}</span>
  </p>
  <p style="font-size:18px;color:#666;font-weight:400;line-height:1.6;margin-bottom:0;">
    <span leaf="">{{副标题/译文}}</span>
  </p>
  <p style="font-size:12px;color:#999;line-height:1.9;margin:16px 0 0;">
    <span leaf="">{{导语，一句话说明}}</span>
  </p>
</section>
```

---

## 组件 4 竖线装饰正文区（左侧竖线 + 正文）

> 日式杂志标志性设计：正文区左侧一条细竖线，正文靠右。

```html
<section style="padding:0 28px 24px;display:flex;gap:20px;">
  <section style="width:1px;background:#DDD;flex-shrink:0;">
    <span leaf=""><br></span>
  </section>
  <section style="flex:1;">
    <p style="font-size:13px;color:#555;line-height:2.2;margin-bottom:14px;text-align:justify;">
      <span leaf="">{{前半句}}</span>
      <strong style="color:#2A2A2A;font-weight:600;"><span leaf="">{{关键词}}</span></strong>
      <span leaf="">{{后半句}}</span>
    </p>
    <p style="font-size:13px;color:#555;line-height:2.2;margin:0;text-align:justify;">
      <span leaf="">{{第二段正文}}</span>
    </p>
  </section>
</section>
```

---

## 组件 5 居中金句（日文/中文 + 译文）

```html
<section style="padding:24px 28px;text-align:center;">
  <p style="font-size:16px;color:#3A3A3A;line-height:2;margin:0 0 10px;font-weight:300;">
    <span leaf="">{{金句，如 「足るを知る」}}</span>
  </p>
  <p style="font-size:11px;color:#999;margin:0;letter-spacing:2px;">
    <span leaf="">—— {{译文/注释，如 知足}}</span>
  </p>
</section>
```

---

## 组件 6 细分割线

```html
<section style="padding:0 28px;">
  <section style="height:1px;background:#EEE;">
    <span leaf=""><br></span>
  </section>
</section>
```

---

## 组件 7 章节标题（暖棕编号标签 + 标题）

```html
<section style="padding:24px 28px;">
  <p style="font-size:10px;letter-spacing:3px;color:#B89070;margin-bottom:8px;font-weight:600;">
    <span leaf="">{{编号标签，如 01 / 間 MA}}</span>
  </p>
  <p style="font-size:16px;font-weight:700;color:#2A2A2A;margin:0 0 12px;line-height:1.5;">
    <span leaf="">{{章节标题}}</span>
  </p>
  <p style="font-size:13px;color:#666;line-height:2.1;margin:0;text-align:justify;">
    <span leaf="">{{章节正文}}</span>
  </p>
</section>
```

---

## 组件 8 汉字三列数据（間/侘/寂）

> 日式杂志标志性组件：三个汉字大字 + 日文读音 + 中文释义。

```html
<section style="display:flex;gap:0;margin:0 28px 24px;border-top:1px solid #EEE;border-bottom:1px solid #EEE;">
  <section style="flex:1;padding:14px 8px;text-align:center;border-right:1px solid #EEE;">
    <p style="font-size:20px;font-weight:300;color:#B89070;margin:0;line-height:1;"><span leaf="">{{汉字1，如 間}}</span></p>
    <p style="font-size:9px;color:#BBB;margin:3px 0 0;letter-spacing:1px;"><span leaf="">{{读音，如 MA · 留白}}</span></p>
  </section>
  <section style="flex:1;padding:14px 8px;text-align:center;border-right:1px solid #EEE;">
    <p style="font-size:20px;font-weight:300;color:#B89070;margin:0;line-height:1;"><span leaf="">{{汉字2，如 侘}}</span></p>
    <p style="font-size:9px;color:#BBB;margin:3px 0 0;letter-spacing:1px;"><span leaf="">{{读音，如 WABI · 侘寂}}</span></p>
  </section>
  <section style="flex:1;padding:14px 8px;text-align:center;">
    <p style="font-size:20px;font-weight:300;color:#B89070;margin:0;line-height:1;"><span leaf="">{{汉字3，如 寂}}</span></p>
    <p style="font-size:9px;color:#BBB;margin:3px 0 0;letter-spacing:1px;"><span leaf="">{{读音，如 SABI · 古雅}}</span></p>
  </section>
</section>
```

---

## 组件 9 引用块（左边框 + 无背景）

```html
<section style="margin:0 28px 20px;padding-left:16px;border-left:2px solid #B89070;">
  <p style="font-size:14px;color:#444;line-height:2;margin:0 0 8px;font-style:italic;">
    <span leaf="">{{引用内容}}</span>
  </p>
  <p style="font-size:10px;color:#BBB;margin:0;letter-spacing:1px;">
    <span leaf="">— {{出处}}</span>
  </p>
</section>
```

---

## 组件 10 图片（无边框纯留白）

```html
<section style="margin:24px 28px;">
  <span leaf=""><img src="{{图片URL}}" style="max-width:100%;height:auto;display:block;margin:0 auto;"></span>
</section>
```

---

## 组件 11 END 结尾（日式「終」）

```html
<section style="padding:20px 28px 32px;text-align:center;">
  <p style="font-size:10px;color:#CCC;letter-spacing:4px;margin:0;">
    <span leaf="">— 終 —</span>
  </p>
</section>
```

---

## 完整文章模板骨架

```html
<section style="max-width:677px;margin:0 auto;background:#FAFAF8;font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans','PingFang SC','Microsoft YaHei',sans-serif;color:#3A3A3A;line-height:2;letter-spacing:0.5px;overflow-x:hidden;">
  <!-- 1. 顶部信息栏（组件2） -->
  <!-- 2. 标题区（组件3：日文小字+大标题+副标题） -->
  <!-- 3. 竖线装饰正文区（组件4 × N） -->
  <!-- 4. 居中金句（组件5，核心观点处） -->
  <!-- 5. 细分割线（组件6） -->
  <!-- 6. 章节标题（组件7）+ 正文 -->
  <!-- 7. 汉字三列数据（组件8） -->
  <!-- 8. 引用块（组件9） -->
  <!-- 9. 图片（组件10） -->
  <!-- 10. END结尾（组件11：「終」） -->
</section>
```

---

## 视觉层级与克制原则

- 全篇只用米白、灰、暖棕（#B89070）三色
- 暖棕仅用于标签、汉字、竖线装饰，不用于正文
- 大量留白是第一设计元素，间距宁大勿小
- 字号偏小（13px正文），行高偏大（2.1），营造呼吸感
- 字间距偏大（0.5px），模拟日式排版的疏朗感
- 不用圆角卡片、不用阴影、不用渐变、不用彩色
- 日文/中文小字标签是标志性元素
- 左侧竖线装饰正文区是核心版式特征

---

## Markdown → 日式杂志 映射规则

| Markdown | 组件 | 说明 |
|---|---|---|
| `# 标题` | 组件3 | 日文小字+大标题+副标题+导语 |
| `## 章节` | 组件7 | 暖棕编号标签+标题+正文 |
| 段落 | 组件4 | 左侧竖线装饰+正文 |
| `> 引用` | 组件9 | 暖棕左边框+斜体 |
| 核心金句 | 组件5 | 居中大字+译文注释 |
| 概念/关键词 | 组件8 | 汉字三列数据（間/侘/寂） |
| `![](图片)` | 组件10 | 无边框纯留白 |
| 文末 | 组件11 | 「— 終 —」居中 |
