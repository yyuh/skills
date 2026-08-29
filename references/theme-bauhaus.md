# 公众号排版组件库 —— 包豪斯几何

> **使用说明**：本组件库为「包豪斯几何」主题（Bauhaus），所有组件使用**内联样式**，可直接复制粘贴到微信公众号编辑器。
>
> **设计风格**：包豪斯设计语言——红黄蓝三原色、圆形/方形/三角形几何元素、简洁排版。深色 Hero 区配几何装饰，每个章节配一个几何图形，三原色数据卡。适合设计评论、艺术、科技美学、观点类文章。
>
> **公众号平台限制须知**：
> - ❌ 不支持 `<style>`/`<script>`、CSS class/id、`position:fixed/absolute`、`float`、`@media`/`@keyframes`、`display:grid`
> - ✅ 支持内联 `style`、`display:flex`（有限）、`linear-gradient`、`border-radius`、`box-shadow`、`<section>/<p>/<span>/<strong>/<img>` 等基础标签
>
> **WeChat 兼容铁律**：装饰性空元素内部放 `<span leaf=""><br></span>`；不要把 font-size 打在 strong 上；不用 position:absolute；无内容区域整块删掉。
>
> **几何图形实现**：圆形用 `border-radius:50%`，方形用普通矩形，三角形用 border 技巧（`border-left/right: transparent; border-bottom: 颜色`），均不依赖 position:absolute。

---

## 设计变量速查表

```
背景色：       #F1EDE4（米灰）
Hero 背景：    #1A1A1A（近黑）
红色：         #E63946（包豪斯红）
黄色：         #F4D35E（包豪斯黄）
蓝色：         #2A9D8F（包豪斯蓝绿）
主文字色：     #1A1A1A
正文色：       #444444
辅助文字：     #999999
正文字号：     14px
行高：         1.75
最大宽度：     677px
内容区边距：   0 24px
```

字体栈：`'Helvetica Neue', Arial, -apple-system, 'PingFang SC', sans-serif`

---

## 组件 1 全局容器

```html
<section style="max-width:677px;margin:0 auto;background:#F1EDE4;font-family:'Helvetica Neue',Arial,-apple-system,'PingFang SC',sans-serif;color:#1A1A1A;line-height:1.75;letter-spacing:0.5px;overflow-x:hidden;">

  <!-- 所有组件放在这里 -->

</section>
```

---

## 组件 2 Hero 区（深色底 + 几何装饰 + 标题）

> 几何装饰用圆形、方形、三角形，放在 Hero 区内。注意三角形用 border 技巧实现。

```html
<section style="background:#1A1A1A;padding:36px 24px;overflow:hidden;">
  <!-- 圆形装饰（红） -->
  <section style="display:inline-block;width:80px;height:80px;background:#E63946;border-radius:50%;margin-bottom:16px;">
    <span leaf=""><br></span>
  </section>
  <p style="font-size:10px;letter-spacing:3px;color:#F4D35E;margin:0 0 14px;font-weight:700;">
    <span leaf="">{{标签，如 FORM FOLLOWS FUNCTION · N°07}}</span>
  </p>
  <p style="font-size:28px;font-weight:900;color:#fff;line-height:1.2;margin:0;letter-spacing:-0.5px;">
    <span style="color:#E63946;"><span leaf="">{{红色关键词}}</span></span>
    <span leaf="">{{标题中段}}</span>
    <span style="color:#F4D35E;"><span leaf="">{{黄色关键词}}</span></span>
  </p>
</section>
```

---

## 组件 3 正文区（padding 容器）

```html
<section style="padding:28px 24px;">
  <!-- 正文内容 -->
</section>
```

---

## 组件 4 章节（几何图形 + 标题 + 正文）

> 每个章节左侧一个几何图形（圆/方/三角轮换），右侧标题+正文。

### 4a. 圆形章节（红）

```html
<section style="display:flex;gap:16px;margin-bottom:24px;align-items:flex-start;">
  <section style="width:36px;height:36px;background:#E63946;border-radius:50%;flex-shrink:0;margin-top:2px;">
    <span leaf=""><br></span>
  </section>
  <section style="flex:1;">
    <p style="font-size:18px;font-weight:900;margin:0 0 8px;color:#1A1A1A;"><span leaf="">{{章节标题}}</span></p>
    <p style="font-size:13px;color:#444;line-height:1.75;margin:0;">
      <span leaf="">{{章节正文，关键词用 <strong style="color:#E63946;">红色加粗</strong>}}</span>
    </p>
  </section>
</section>
```

### 4b. 方形章节（蓝）

```html
<section style="display:flex;gap:16px;margin-bottom:24px;align-items:flex-start;">
  <section style="width:36px;height:36px;background:#2A9D8F;flex-shrink:0;margin-top:2px;">
    <span leaf=""><br></span>
  </section>
  <section style="flex:1;">
    <p style="font-size:18px;font-weight:900;margin:0 0 8px;color:#1A1A1A;"><span leaf="">{{章节标题}}</span></p>
    <p style="font-size:13px;color:#444;line-height:1.75;margin:0;">
      <span leaf="">{{章节正文}}</span>
    </p>
  </section>
</section>
```

### 4c. 三角形章节（黄）

```html
<section style="display:flex;gap:16px;margin-bottom:24px;align-items:flex-start;">
  <section style="width:0;height:0;border-left:18px solid transparent;border-right:18px solid transparent;border-bottom:31px solid #F4D35E;flex-shrink:0;margin-top:2px;">
    <span leaf=""><br></span>
  </section>
  <section style="flex:1;">
    <p style="font-size:18px;font-weight:900;margin:0 0 8px;color:#1A1A1A;"><span leaf="">{{章节标题}}</span></p>
    <p style="font-size:13px;color:#444;line-height:1.75;margin:0;">
      <span leaf="">{{章节正文}}</span>
    </p>
  </section>
</section>
```

---

## 组件 5 引用块（深色底 + 黄色左边框）

```html
<section style="margin:24px 0;padding:20px;background:#1A1A1A;color:#fff;border-left:6px solid #F4D35E;">
  <p style="font-size:17px;font-weight:700;line-height:1.6;margin:0;color:#fff;">
    <span leaf="">{{引用金句}}</span>
  </p>
  <p style="font-size:11px;color:#999;margin:10px 0 0;letter-spacing:1px;">
    <span leaf="">— {{出处}}</span>
  </p>
</section>
```

---

## 组件 6 数据块（三原色三列）

> 三列分别用红、黄、蓝背景。

```html
<section style="display:flex;gap:0;margin:24px 0;border:2px solid #1A1A1A;">
  <section style="flex:1;padding:14px 8px;text-align:center;background:#E63946;color:#fff;border-right:2px solid #1A1A1A;">
    <p style="font-size:24px;font-weight:900;margin:0;line-height:1;"><span leaf="">{{数字1}}</span></p>
    <p style="font-size:10px;margin:2px 0 0;opacity:0.85;letter-spacing:1px;"><span leaf="">{{说明1}}</span></p>
  </section>
  <section style="flex:1;padding:14px 8px;text-align:center;background:#F4D35E;color:#1A1A1A;border-right:2px solid #1A1A1A;">
    <p style="font-size:24px;font-weight:900;margin:0;line-height:1;"><span leaf="">{{数字2}}</span></p>
    <p style="font-size:10px;margin:2px 0 0;opacity:0.8;letter-spacing:1px;"><span leaf="">{{说明2}}</span></p>
  </section>
  <section style="flex:1;padding:14px 8px;text-align:center;background:#2A9D8F;color:#fff;">
    <p style="font-size:24px;font-weight:900;margin:0;line-height:1;"><span leaf="">{{数字3}}</span></p>
    <p style="font-size:10px;margin:2px 0 0;opacity:0.85;letter-spacing:1px;"><span leaf="">{{说明3}}</span></p>
  </section>
</section>
```

---

## 组件 7 正文段落

```html
<p style="margin-bottom:16px;font-size:14px;color:#444;line-height:1.8;">
  <span leaf="">{{前半句}}</span>
  <strong style="color:#E63946;"><span leaf="">{{关键词}}</span></strong>
  <span leaf="">{{后半句}}</span>
</p>
```

---

## 组件 8 图片（2px 黑框）

```html
<section style="margin:20px 0;border:2px solid #1A1A1A;">
  <span leaf=""><img src="{{图片URL}}" style="max-width:100%;height:auto;display:block;margin:0 auto;"></span>
</section>
```

---

## 组件 9 END 结尾（深色底 + 小字）

```html
<section style="padding:20px 24px;background:#1A1A1A;color:#999;font-size:11px;letter-spacing:2px;text-align:center;">
  <span leaf="">{{品牌名}} · BAUHAUS SERIES</span>
</section>
```

---

## 完整文章模板骨架

```html
<section style="max-width:677px;margin:0 auto;background:#F1EDE4;font-family:'Helvetica Neue',Arial,-apple-system,'PingFang SC',sans-serif;color:#1A1A1A;line-height:1.75;letter-spacing:0.5px;overflow-x:hidden;">
  <!-- 1. Hero区（组件2：深色底+几何装饰+标题） -->
  <!-- 2. 正文区（组件3） -->
  <!--    章节圆（组件4a）+ 章节方（组件4b）+ 章节三角（组件4c） -->
  <!--    引用块（组件5） -->
  <!--    数据块（组件6） -->
  <!--    正文段落（组件7） -->
  <!--    图片（组件8） -->
  <!-- 3. END结尾（组件9） -->
</section>
```

---

## 视觉层级与克制原则

- 只用红（#E63946）、黄（#F4D35E）、蓝（#2A9D8F）、黑、米白五色
- 几何图形（圆/方/三角）轮换使用，不重复
- 三原色数据块是标志性组件
- 深色 Hero 区 + 浅色正文区形成强对比
- 不用渐变、不用阴影、不用圆角（圆形除外）
- 字体粗细对比（900 vs 400）是主要视觉手段

---

## Markdown → 包豪斯几何 映射规则

| Markdown | 组件 | 说明 |
|---|---|---|
| `# 标题` | 组件2 | Hero区+几何装饰+渐变标题 |
| `## 章节` | 组件4a/4b/4c | 圆/方/三角轮换，左图右文 |
| 段落 | 组件7 | 关键词红色加粗 |
| `> 引用` | 组件5 | 深色底+黄色左边框 |
| 数据 | 组件6 | 三原色三列 |
| `![](图片)` | 组件8 | 2px黑框 |
| 文末 | 组件9 | 深色底+小字 |
