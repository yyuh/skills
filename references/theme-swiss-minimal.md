# 公众号排版组件库 —— 瑞士极简

> **使用说明**：本组件库为「瑞士极简」主题（瑞士国际主义风格），所有组件使用**内联样式**，可直接复制粘贴到微信公众号编辑器。
>
> **设计风格**：瑞士国际主义排版——网格感、无衬线粗体、左对齐、大量留白、黑白灰+一点红。顶部信息栏、超粗大标题、三列网格 meta、编号列表。适合深度短文、观点、设计评论、科技观察类文章。
>
> **公众号平台限制须知**：
> - ❌ 不支持 `<style>`/`<script>`、CSS class/id、`position:fixed/absolute`、`float`、`@media`/`@keyframes`、`display:grid`
> - ✅ 支持内联 `style`、`display:flex`（有限）、`linear-gradient`、`border-radius`、`box-shadow`、`<section>/<p>/<span>/<strong>/<img>` 等基础标签
>
> **WeChat 兼容铁律**：装饰性空元素内部放 `<span leaf=""><br></span>`；不要把 font-size 打在 strong 上；不用 position:absolute；无内容区域整块删掉。

---

## 设计变量速查表

```
背景色：       #FFFFFF
主文字色：     #000000
正文色：       #1A1A1A
次要文字：     #666666
辅助文字：     #999999
分隔线：       #000000（实线）/ #EEEEEE（细线）
强调色：       #E63946（瑞士红，仅用于编号和少量强调）
正文字号：     14px
行高：         1.8
字间距：       0.5px
最大宽度：     677px
内容区边距：   0 28px
上下留白：     40px
```

字体栈：`'Helvetica Neue', Helvetica, Arial, -apple-system, 'PingFang SC', sans-serif`

---

## 组件 1 全局容器

```html
<section style="max-width:677px;margin:0 auto;background:#FFFFFF;font-family:'Helvetica Neue',Helvetica,Arial,-apple-system,'PingFang SC',sans-serif;color:#1A1A1A;line-height:1.8;letter-spacing:0.5px;overflow-x:hidden;padding:40px 28px;">

  <!-- 所有组件放在这里 -->

</section>
```

---

## 组件 2 顶部信息栏 + 超粗大标题

> 顶部左右分栏信息（品牌/期号），底部黑线分隔。标题用超粗无衬线体，字间距收紧。

```html
<section style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:40px;padding-bottom:16px;border-bottom:1px solid #000;">
  <section>
    <p style="font-size:10px;letter-spacing:2px;color:#000;font-weight:700;text-transform:uppercase;margin:0;line-height:1.4;">
      <span leaf="">{{品牌名，如 SILICON RESEARCH}}</span>
    </p>
  </section>
  <section style="text-align:right;">
    <p style="font-size:10px;letter-spacing:1px;color:#666;margin:0;line-height:1.4;">
      <span leaf="">{{期号}}</span>
    </p>
    <p style="font-size:10px;letter-spacing:1px;color:#999;margin:4px 0 0;line-height:1.4;">
      <span leaf="">{{日期}}</span>
    </p>
  </section>
</section>
<section style="margin-bottom:8px;">
  <p style="font-size:42px;font-weight:900;line-height:1.05;letter-spacing:-1px;color:#000;margin:0;">
    <span leaf="">{{标题第一行}}</span>
  </p>
  <p style="font-size:42px;font-weight:900;line-height:1.05;letter-spacing:-1px;color:#000;margin:0;">
    <span leaf="">{{标题第二行}}</span>
  </p>
</section>
<p style="font-size:13px;color:#666;line-height:1.6;margin:0 0 40px;max-width:280px;">
  <span leaf="">{{副标题/导语}}</span>
</p>
```

---

## 组件 3 三列网格 meta

```html
<section style="display:flex;gap:20px;margin-bottom:36px;">
  <section style="flex:1;">
    <p style="font-size:9px;letter-spacing:2px;color:#999;text-transform:uppercase;margin:0 0 8px;font-weight:700;"><span leaf="">{{标签1}}</span></p>
    <p style="font-size:12px;color:#333;line-height:1.7;margin:0;"><span leaf="">{{内容1}}</span></p>
  </section>
  <section style="flex:1;">
    <p style="font-size:9px;letter-spacing:2px;color:#999;text-transform:uppercase;margin:0 0 8px;font-weight:700;"><span leaf="">{{标签2}}</span></p>
    <p style="font-size:12px;color:#333;line-height:1.7;margin:0;"><span leaf="">{{内容2}}</span></p>
  </section>
  <section style="flex:1;">
    <p style="font-size:9px;letter-spacing:2px;color:#999;text-transform:uppercase;margin:0 0 8px;font-weight:700;"><span leaf="">{{标签3}}</span></p>
    <p style="font-size:12px;color:#333;line-height:1.7;margin:0;"><span leaf="">{{内容3}}</span></p>
  </section>
</section>
```

---

## 组件 4 正文段落

```html
<p style="margin-bottom:20px;font-size:14px;color:#1A1A1A;line-height:1.8;text-align:left;">
  <span leaf="">{{前半句}}</span>
  <strong style="font-weight:900;"><span leaf="">{{关键词}}</span></strong>
  <span leaf="">{{后半句}}</span>
</p>
```

---

## 组件 5 引用块（上下粗线）

```html
<section style="margin:36px 0;padding:20px 0;border-top:2px solid #000;border-bottom:1px solid #000;">
  <p style="font-size:20px;font-weight:900;line-height:1.4;letter-spacing:-0.5px;color:#000;margin:0;">
    <span leaf="">{{引用金句}}</span>
  </p>
  <p style="font-size:10px;color:#999;margin:10px 0 0;letter-spacing:1px;">
    <span leaf="">— {{出处}}</span>
  </p>
</section>
```

---

## 组件 6 章节标题（红色编号 + 粗体标题）

```html
<section style="margin-top:40px;margin-bottom:16px;">
  <p style="font-size:11px;font-weight:900;color:#E63946;letter-spacing:2px;margin:0 0 8px;">
    <span leaf="">{{编号，如 01 / METHOD}}</span>
  </p>
  <p style="font-size:22px;font-weight:900;color:#000;margin:0;line-height:1.3;">
    <span leaf="">{{章节标题}}</span>
  </p>
</section>
```

---

## 组件 7 列表（红色编号 + 底部分隔线）

```html
<section style="margin:20px 0;">
  <section style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #EEE;font-size:13px;color:#333;">
    <span style="font-weight:900;color:#E63946;min-width:20px;"><span leaf="">01</span></span>
    <span leaf="">{{列表项}}</span>
  </section>
  <section style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #EEE;font-size:13px;color:#333;">
    <span style="font-weight:900;color:#E63946;min-width:20px;"><span leaf="">02</span></span>
    <span leaf="">{{列表项}}</span>
  </section>
  <section style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #EEE;font-size:13px;color:#333;">
    <span style="font-weight:900;color:#E63946;min-width:20px;"><span leaf="">03</span></span>
    <span leaf="">{{列表项}}</span>
  </section>
</section>
```

---

## 组件 8 图片（无边框纯留白）

```html
<section style="margin:32px 0;">
  <span leaf=""><img src="{{图片URL}}" style="max-width:100%;height:auto;display:block;margin:0 auto;"></span>
</section>
```

---

## 组件 9 END 结尾（顶部黑线 + 左右分栏）

```html
<section style="margin-top:48px;padding-top:16px;border-top:1px solid #000;display:flex;justify-content:space-between;">
  <p style="font-size:9px;color:#999;letter-spacing:1px;margin:0;"><span leaf="">{{品牌名}}</span></p>
  <p style="font-size:9px;color:#999;letter-spacing:1px;margin:0;"><span leaf="">— END —</span></p>
</section>
```

---

## 完整文章模板骨架

```html
<section style="max-width:677px;margin:0 auto;background:#FFFFFF;font-family:'Helvetica Neue',Helvetica,Arial,-apple-system,'PingFang SC',sans-serif;color:#1A1A1A;line-height:1.8;letter-spacing:0.5px;overflow-x:hidden;padding:40px 28px;">
  <!-- 1. 顶部信息栏+大标题（组件2） -->
  <!-- 2. 三列meta（组件3） -->
  <!-- 3. 正文段落（组件4 × N） -->
  <!-- 4. 引用块（组件5） -->
  <!-- 5. 章节标题（组件6）+ 正文 -->
  <!-- 6. 列表（组件7） -->
  <!-- 7. 图片（组件8） -->
  <!-- 8. END结尾（组件9） -->
</section>
```

---

## 视觉层级与克制原则

- 全篇只用黑、白、灰 + 一点红（#E63946）
- 红色仅用于编号和章节标签，不用于正文
- 字体粗细对比是主要视觉手段（900粗体 vs 400常规）
- 左对齐，不居中（除特殊设计）
- 分隔线用实线，不用虚线
- 不用圆角、不用阴影、不用渐变

---

## Markdown → 瑞士极简 映射规则

| Markdown | 组件 | 说明 |
|---|---|---|
| `# 标题` | 组件2 | 顶部信息栏+超粗大标题 |
| `## 章节` | 组件6 | 红色编号+粗体标题 |
| 段落 | 组件4 | 左对齐，关键词900粗体 |
| `> 引用` | 组件5 | 上下黑线+粗体金句 |
| `1. 2. 3.` | 组件7 | 红色编号+底部分隔线 |
| `![](图片)` | 组件8 | 无边框纯留白 |
| 文末 | 组件9 | 顶部黑线+左右分栏 |
