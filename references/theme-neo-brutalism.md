# 公众号排版组件库 —— 新丑撞色

> **使用说明**：本组件库为「新丑撞色」主题（Neo-Brutalism 高饱和硬派风），所有组件使用**内联样式**，可直接复制粘贴到微信公众号编辑器。
>
> **设计风格**：高饱和粉/蓝/黄三色 + 3px 粗黑边框 + 硬阴影（6px 偏移）+ 无圆角。粗、硬、直接，一拳打在脸上的冲击力。适合宣言、观点、潮流话题、反主流态度类文章。
>
> **公众号平台限制须知**：
> - ❌ 不支持 `<style>`/`<script>`、CSS class/id、`position:fixed/absolute`、`float`、`@media`/`@keyframes`、`display:grid`
> - ✅ 支持内联 `style`、`display:flex`（有限）、`linear-gradient`、`border-radius`、`box-shadow`、`<section>/<p>/<span>/<strong>/<img>` 等基础标签
>
> **WeChat 兼容铁律**：装饰性空元素内部放 `<span leaf=""><br></span>`；不要把 font-size 打在 strong 上；不用 position:absolute；无内容区域整块删掉。
>
> **新丑三原则**：① 边框必须粗（≥2px）② 阴影必须硬（不要模糊）③ 颜色必须饱和（不要灰调）。

---

## 设计变量速查表

```
背景色：       #FFF5E6（暖米白）
卡片背景：     #FFFFFF
新丑粉：       #FF6B9D（高饱和粉）
新丑蓝：       #3B82F6（高饱和蓝）
新丑黄：       #FFE500（高饱和黄）
边框色：       #000000（纯黑，3px）
硬阴影：       6px 6px 0 #000（无模糊）
硬阴影小：     4px 4px 0 #000
主文字色：     #000000
正文色：       #333333
次要文字：     #666666
正文字号：     13px
行高：         1.7
最大宽度：     677px
内容区边距：   0 20px
```

字体栈：`'Arial Black','Helvetica Neue',Arial,-apple-system,'PingFang SC',sans-serif`
正文字体：`Arial, Helvetica, sans-serif`

---

## 组件 1 全局容器

```html
<section style="max-width:677px;margin:0 auto;background:#FFF5E6;font-family:'Arial Black','Helvetica Neue',Arial,-apple-system,'PingFang SC',sans-serif;color:#000;line-height:1.5;overflow-x:hidden;">

  <!-- 所有组件放在这里 -->

</section>
```

---

## 组件 2 顶部色条 + 超大标题区

> 顶部蓝色色条，超大字号标题，关键词用色块高亮。

```html
<section style="background:#3B82F6;padding:10px 20px;border-bottom:3px solid #000;">
  <p style="font-size:10px;letter-spacing:2px;color:#fff;font-weight:900;margin:0;text-transform:uppercase;">
    <span leaf="">{{标签，如 ★ NEO-BRUTALISM · ISSUE 07 ★}}</span>
  </p>
</section>
<section style="padding:24px 20px 16px;">
  <p style="font-size:32px;font-weight:900;line-height:1.05;color:#000;margin:0 0 8px;letter-spacing:-1px;">
    <span style="background:#FF6B9D;padding:2px 6px;"><span leaf="">{{高亮词}}</span></span><span leaf="">{{标题中段}}</span>
  </p>
  <p style="font-size:32px;font-weight:900;line-height:1.05;color:#000;margin:0 0 12px;letter-spacing:-1px;">
    <span leaf="">{{标题前段}}</span><span style="color:#3B82F6;"><span leaf="">{{关键词}}</span></span><span leaf="">{{标题后段}}</span>
  </p>
  <p style="font-size:32px;font-weight:900;line-height:1.05;margin:0;letter-spacing:-1px;">
    <span style="background:#FFE500;border:2px solid #000;padding:2px 6px;display:inline-block;"><span leaf="">{{收尾关键词}}</span></span>
  </p>
</section>
```

---

## 组件 3 导语卡（白底粗框硬阴影）

```html
<section style="margin:0 20px 20px;padding:14px 16px;background:#fff;border:3px solid #000;box-shadow:6px 6px 0 #000;">
  <p style="font-size:13px;color:#333;line-height:1.7;margin:0;font-family:Arial,Helvetica,sans-serif;font-weight:400;">
    <span leaf="">{{导语内容}}</span>
  </p>
</section>
```

---

## 组件 4 三列色块卡（粉/蓝/黄）

```html
<section style="display:flex;gap:10px;margin:0 20px 20px;">
  <section style="flex:1;padding:14px 8px;text-align:center;background:#FF6B9D;border:3px solid #000;box-shadow:4px 4px 0 #000;">
    <p style="font-size:24px;font-weight:900;color:#000;margin:0;line-height:1;"><span leaf="">{{关键词1，如 RAW}}</span></p>
    <p style="font-size:9px;color:#000;margin:4px 0 0;letter-spacing:1px;font-family:Arial,sans-serif;font-weight:700;"><span leaf="">{{释义1}}</span></p>
  </section>
  <section style="flex:1;padding:14px 8px;text-align:center;background:#3B82F6;border:3px solid #000;box-shadow:4px 4px 0 #000;">
    <p style="font-size:24px;font-weight:900;color:#fff;margin:0;line-height:1;"><span leaf="">{{关键词2，如 BOLD}}</span></p>
    <p style="font-size:9px;color:#fff;margin:4px 0 0;letter-spacing:1px;font-family:Arial,sans-serif;font-weight:700;"><span leaf="">{{释义2}}</span></p>
  </section>
  <section style="flex:1;padding:14px 8px;text-align:center;background:#FFE500;border:3px solid #000;box-shadow:4px 4px 0 #000;">
    <p style="font-size:24px;font-weight:900;color:#000;margin:0;line-height:1;"><span leaf="">{{关键词3，如 HONEST}}</span></p>
    <p style="font-size:9px;color:#000;margin:4px 0 0;letter-spacing:1px;font-family:Arial,sans-serif;font-weight:700;"><span leaf="">{{释义3}}</span></p>
  </section>
</section>
```

---

## 组件 5 正文段落

```html
<section style="padding:0 20px 20px;">
  <p style="font-size:13px;color:#333;line-height:1.8;margin-bottom:12px;font-family:Arial,Helvetica,sans-serif;">
    <span leaf="">{{前半句}}</span>
    <span style="background:#FFE500;font-weight:700;padding:0 3px;"><span leaf="">{{关键词}}</span></span>
    <span leaf="">{{后半句}}</span>
  </p>
  <p style="font-size:13px;color:#333;line-height:1.8;margin:0;font-family:Arial,Helvetica,sans-serif;">
    <span leaf="">{{第二段，关键词用}}</span><span style="color:#FF6B9D;font-weight:900;"><span leaf="">{{彩色加粗}}</span></span><span leaf="">{{后半句}}</span>
  </p>
</section>
```

---

## 组件 6 引用块（蓝色底粗框硬阴影）

```html
<section style="margin:0 20px 20px;padding:16px;background:#3B82F6;border:3px solid #000;box-shadow:6px 6px 0 #000;">
  <p style="font-size:16px;font-weight:900;color:#fff;line-height:1.4;margin:0;font-style:italic;">
    <span leaf="">{{引用金句}}</span>
  </p>
</section>
```

---

## 组件 7 列表（粗框编号 + 底部分隔线）

```html
<section style="padding:0 20px 20px;">
  <p style="font-size:14px;font-weight:900;color:#000;margin:0 0 12px;"><span leaf="">{{列表标题}}</span></p>
  <section style="display:flex;gap:10px;align-items:center;padding:8px 0;border-bottom:2px solid #000;">
    <span style="width:24px;height:24px;background:#FF6B9D;border:2px solid #000;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;flex-shrink:0;"><span leaf="">1</span></span>
    <p style="font-size:12px;color:#333;margin:0;font-family:Arial,sans-serif;font-weight:700;"><span leaf="">{{列表项1}}</span></p>
  </section>
  <section style="display:flex;gap:10px;align-items:center;padding:8px 0;border-bottom:2px solid #000;">
    <span style="width:24px;height:24px;background:#3B82F6;border:2px solid #000;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;color:#fff;flex-shrink:0;"><span leaf="">2</span></span>
    <p style="font-size:12px;color:#333;margin:0;font-family:Arial,sans-serif;font-weight:700;"><span leaf="">{{列表项2}}</span></p>
  </section>
  <section style="display:flex;gap:10px;align-items:center;padding:8px 0;">
    <span style="width:24px;height:24px;background:#FFE500;border:2px solid #000;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;flex-shrink:0;"><span leaf="">3</span></span>
    <p style="font-size:12px;color:#333;margin:0;font-family:Arial,sans-serif;font-weight:700;"><span leaf="">{{列表项3}}</span></p>
  </section>
</section>
```

---

## 组件 8 大数字展示（粗边框）

```html
<section style="display:flex;gap:0;margin:0 20px 20px;border-top:3px solid #000;border-bottom:3px solid #000;">
  <section style="flex:1;text-align:center;padding:12px 8px;border-right:2px solid #000;">
    <p style="font-size:36px;font-weight:900;color:#FF6B9D;margin:0;line-height:1;letter-spacing:-2px;"><span leaf="">{{数字1}}</span></p>
    <p style="font-size:9px;color:#666;margin:4px 0 0;letter-spacing:1px;font-family:Arial,sans-serif;"><span leaf="">{{说明1}}</span></p>
  </section>
  <section style="flex:1;text-align:center;padding:12px 8px;border-right:2px solid #000;">
    <p style="font-size:36px;font-weight:900;color:#000;margin:0;line-height:1;letter-spacing:-2px;"><span leaf="">{{数字2}}</span></p>
    <p style="font-size:9px;color:#666;margin:4px 0 0;letter-spacing:1px;font-family:Arial,sans-serif;"><span leaf="">{{说明2}}</span></p>
  </section>
  <section style="flex:1;text-align:center;padding:12px 8px;">
    <p style="font-size:36px;font-weight:900;color:#3B82F6;margin:0;line-height:1;letter-spacing:-2px;"><span leaf="">{{数字3}}</span></p>
    <p style="font-size:9px;color:#666;margin:4px 0 0;letter-spacing:1px;font-family:Arial,sans-serif;"><span leaf="">{{说明3}}</span></p>
  </section>
</section>
```

---

## 组件 9 图片（粗边框）

```html
<section style="margin:0 20px 20px;border:3px solid #000;box-shadow:6px 6px 0 #000;">
  <span leaf=""><img src="{{图片URL}}" style="max-width:100%;height:auto;display:block;margin:0 auto;"></span>
</section>
```

---

## 组件 10 END 结尾（黑底黄字）

```html
<section style="background:#000;padding:14px 20px;text-align:center;border-top:3px solid #000;">
  <p style="font-size:10px;color:#FFE500;letter-spacing:2px;margin:0;font-weight:900;">
    <span leaf="">★ {{品牌名}} · NEO-BRUTALISM ★</span>
  </p>
</section>
```

---

## 完整文章模板骨架

```html
<section style="max-width:677px;margin:0 auto;background:#FFF5E6;font-family:'Arial Black','Helvetica Neue',Arial,-apple-system,'PingFang SC',sans-serif;color:#000;line-height:1.5;overflow-x:hidden;">
  <!-- 1. 顶部色条+超大标题（组件2） -->
  <!-- 2. 导语卡（组件3） -->
  <!-- 3. 三列色块卡（组件4，核心卖点） -->
  <!-- 4. 正文段落（组件5 × N） -->
  <!-- 5. 引用块（组件6，核心金句） -->
  <!-- 6. 列表（组件7） -->
  <!-- 7. 大数字展示（组件8） -->
  <!-- 8. 图片（组件9） -->
  <!-- 9. END结尾（组件10） -->
</section>
```

---

## 视觉层级与克制原则

- 三色轮换：粉（#FF6B9D）、蓝（#3B82F6）、黄（#FFE500），不要用第四种颜色
- 所有卡片必须有 3px 黑色粗边框 + 硬阴影（6px 6px 0 #000）
- 不用圆角、不用渐变、不用模糊阴影、不用灰调
- 大标题用 Arial Black 900 粗体，正文用 Arial 常规体
- 关键词高亮用黄底黑字（#FFE500）或彩色加粗
- 硬阴影偏移方向统一（右下），不要混用

---

## Markdown → 新丑撞色 映射规则

| Markdown | 组件 | 说明 |
|---|---|---|
| `# 标题` | 组件2 | 顶部色条+超大字号+色块高亮 |
| `## 章节` | 组件5（章节标题） | 粗体黑字+黄底高亮 |
| 段落 | 组件5 | 正文，关键词黄底或彩色加粗 |
| `> 引用` | 组件6 | 蓝色底粗框硬阴影 |
| 核心卖点 | 组件4 | 粉蓝黄三列色块卡 |
| `1. 2. 3.` | 组件7 | 粗框编号+底部分隔线 |
| 数据展示 | 组件8 | 粗边框大数字三列 |
| `![](图片)` | 组件9 | 3px粗框+硬阴影 |
| 文末 | 组件10 | 黑底黄字 |
