# 公众号排版组件库 —— 红白色系

> **使用说明**：本组件库为「红白色系」主题（Red-White 力量感现代风），所有组件使用**内联样式**，可直接复制粘贴到微信公众号编辑器。
>
> **设计风格**：纯白底 + 正红 #DC2626 主色 + 深灰文字 + 圆角卡片 + 红色调柔和阴影 + 渐变分割线。干净、有力、现代，适合副业/赚钱/路径/方法论/实操指南类文章。
>
> **公众号平台限制须知**：
> - ❌ 不支持 `<style>`/`<script>`、CSS class/id、`position:fixed/absolute`、`float`、`@media`/`@keyframes`、`display:grid`
> - ✅ 支持内联 `style`、`display:flex`（有限）、`linear-gradient`、`border-radius`、`box-shadow`、`<section>/<p>/<span>/<strong>/<img>` 等基础标签
>
> **WeChat 兼容铁律**：装饰性空元素内部放 `<span leaf=""><br></span>`；不要把 font-size 打在 strong 上；不用 position:absolute；无内容区域整块删掉。
>
> **红白三原则**：① 红色只做强调（标签/编号/下划线/分割线），不整段铺红 ② 卡片用圆角+浅红底+红色调阴影，不用粗黑框 ③ 文字层级靠字号+颜色（深灰/中灰/浅灰），不靠加粗堆砌。

---

## 设计变量速查表

```
背景色：       #FFFFFF（纯白）
主色红：       #DC2626（正红，强调/标签/编号）
深红文字：     #1C1917（标题/重点）
正文色：       #374151（正文）
次要文字：     #6B7280（说明/注释）
浅灰文字：     #9CA3AF（标签/辅助）
浅红底：       #FEF2F2（卡片背景）
更浅红底：     #FEE2E2（高亮标签背景）
阴影：         0 4px 24px -4px rgba(220,38,38,0.15)
小圆角：       4px / 6px
中圆角：       10px
大圆角：       12px
分割线：       linear-gradient(to right,transparent,#FCA5A5,#DC2626,#FCA5A5,transparent)
下划线：       border-bottom:2px solid #FECACA
正文字号：     15px（红白色系正文比其他风格稍大，增强可读性）
行高：         1.8
最大宽度：     677px
内容区边距：   0 10px
```

字体栈：`-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif`

---

## 组件 1 全局容器

```html
<section style="max-width:677px;margin:0 auto;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;color:#374151;line-height:1.75;letter-spacing:0.5px;overflow-x:hidden;">

  <!-- 所有组件放在这里 -->

</section>
```

---

## 组件 2 开头引言卡片（大引号+红色高亮标签）

> 文章开头的核心观点卡，大引号装饰，关键词用红底白字标签高亮。

```html
<section style="margin:10px 10px 32px;background:#ffffff;border-radius:12px;box-shadow:0 4px 24px -4px rgba(220,38,38,0.15);padding:28px 24px 22px;overflow:hidden;">
  <p style="font-size:44px;color:#DC2626;font-weight:900;margin:0;line-height:0.6;">
    <span leaf="">"</span>
  </p>
  <p style="font-size:20px;font-weight:800;color:#1C1917;margin:12px 0 8px;line-height:1.75;padding-left:4px;">
    <span style="background:#DC2626;color:#FFFFFF;padding:2px 8px;border-radius:4px;"><span leaf="">{{高亮词1}}</span></span>
    <span leaf="">{{正文中段}}</span>
    <span style="background:#DC2626;color:#FFFFFF;padding:2px 8px;border-radius:4px;"><span leaf="">{{高亮词2}}</span></span>
    <span leaf="">{{收尾}}</span>
  </p>
  <p style="text-align:right;font-size:14px;color:#9CA3AF;margin:8px 0 0;letter-spacing:1px;">
    <span leaf="">—— 硅基研究员</span>
  </p>
</section>
```

---

## 组件 3 前言段落

```html
<section style="padding:0 10px 24px;">
  <p style="margin-bottom:16px;font-size:15px;line-height:1.8;text-align:justify;">
    <span leaf="">{{前言内容}}</span>
  </p>
  <p style="margin-bottom:0;font-size:15px;line-height:1.8;text-align:justify;">
    <span leaf="">{{先说结论：}}</span>
    <span style="background:#FEE2E2;color:#991B1B;padding:2px 6px;border-radius:3px;font-weight:700;"><span leaf="">{{核心结论}}</span></span>
    <span leaf="">{{收尾}}</span>
  </p>
</section>
```

---

## 组件 4 三列对比卡（编号+标题+说明+数据）

> 用于路径对比、选项对比、方法对比等。三列等宽，浅红底圆角卡。

```html
<section style="padding:0 10px 32px;">
  <p style="font-size:14px;color:#9CA3AF;margin:0 0 14px;letter-spacing:1px;">
    <span leaf="">{{小标题，如 📌 三条路径对比}}</span>
  </p>
  <section style="display:flex;justify-content:space-between;">
    <section style="flex:1;background:#FEF2F2;border-radius:10px;padding:16px 12px;margin-right:8px;text-align:center;border:1px solid #FEE2E2;">
      <p style="display:inline-block;background:#DC2626;color:#FFFFFF;font-size:16px;font-weight:800;padding:2px 10px;border-radius:4px;margin:0 0 8px;"><span leaf="">01</span></p>
      <p style="font-size:15px;font-weight:700;color:#1C1917;margin:0;"><span leaf="">{{标题1}}</span></p>
      <p style="font-size:12px;color:#991B1B;margin:6px 0 0;line-height:1.5;"><span leaf="">{{说明1}}</span></p>
      <p style="font-size:11px;color:#666;margin:4px 0 0;line-height:1.4;"><span leaf="">{{数据1}}</span></p>
    </section>
    <section style="flex:1;background:#FEF2F2;border-radius:10px;padding:16px 12px;margin-right:8px;text-align:center;border:1px solid #FEE2E2;">
      <p style="display:inline-block;background:#DC2626;color:#FFFFFF;font-size:16px;font-weight:800;padding:2px 10px;border-radius:4px;margin:0 0 8px;"><span leaf="">02</span></p>
      <p style="font-size:15px;font-weight:700;color:#1C1917;margin:0;"><span leaf="">{{标题2}}</span></p>
      <p style="font-size:12px;color:#991B1B;margin:6px 0 0;line-height:1.5;"><span leaf="">{{说明2}}</span></p>
      <p style="font-size:11px;color:#666;margin:4px 0 0;line-height:1.4;"><span leaf="">{{数据2}}</span></p>
    </section>
    <section style="flex:1;background:#FEF2F2;border-radius:10px;padding:16px 12px;text-align:center;border:1px solid #FEE2E2;">
      <p style="display:inline-block;background:#DC2626;color:#FFFFFF;font-size:16px;font-weight:800;padding:2px 10px;border-radius:4px;margin:0 0 8px;"><span leaf="">03</span></p>
      <p style="font-size:15px;font-weight:700;color:#1C1917;margin:0;"><span leaf="">{{标题3}}</span></p>
      <p style="font-size:12px;color:#991B1B;margin:6px 0 0;line-height:1.5;"><span leaf="">{{说明3}}</span></p>
      <p style="font-size:11px;color:#666;margin:4px 0 0;line-height:1.4;"><span leaf="">{{数据3}}</span></p>
    </section>
  </section>
</section>
```

---

## 组件 5 渐变分割线

```html
<section style="padding:0 10px;">
  <section style="height:1px;background:linear-gradient(to right,transparent,#FCA5A5,#DC2626,#FCA5A5,transparent);margin:0;">
    <span leaf=""><br></span>
  </section>
</section>
```

---

## 组件 6 章节标题区（编号方块+英文小字+大标题+底部红线）

```html
<section style="margin-top:16px;margin-bottom:24px;padding:0 10px;">
  <section style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;padding-bottom:14px;border-bottom:3px solid #DC2626;">
    <section style="display:flex;align-items:center;">
      <span style="display:inline-block;background:#DC2626;color:#FFFFFF;font-size:22px;font-weight:900;padding:4px 14px;border-radius:6px;margin-right:14px;line-height:1.3;"><span leaf="">{{编号，如 01}}</span></span>
      <section>
        <p style="font-size:11px;color:#DC2626;font-weight:700;letter-spacing:3px;margin:0 0 2px;text-transform:uppercase;">
          <span leaf="">{{英文小字，如 SELL SKILLS}}</span>
        </p>
        <h3 style="font-size:20px;font-weight:800;color:#1C1917;margin:0;letter-spacing:0.5px;">
          <span leaf="">{{章节标题}}</span>
        </h3>
      </section>
    </section>
  </section>
</section>
```

---

## 组件 7 正文段落（关键词下划线/高亮）

```html
<section style="padding:0 10px 20px;">
  <p style="margin-bottom:16px;font-size:15px;line-height:1.8;text-align:justify;">
    <span leaf="">{{前半句}}</span>
    <span style="border-bottom:2px solid #FECACA;font-weight:600;"><span leaf="">{{关键词（下划线）}}</span></span>
    <span leaf="">{{中段}}</span>
    <span style="background:#FEE2E2;color:#991B1B;padding:1px 4px;border-radius:3px;font-weight:700;"><span leaf="">{{关键词（高亮）}}</span></span>
    <span leaf="">{{后半句}}</span>
  </p>
</section>
```

---

## 组件 8 案例卡（浅红底+圆角+左侧红条）

> 用于真实案例、数据支撑、反例等。

```html
<section style="margin:0 10px 24px;padding:16px 18px;background:#FEF2F2;border-radius:10px;border-left:4px solid #DC2626;">
  <p style="font-size:12px;font-weight:700;color:#DC2626;margin:0 0 8px;letter-spacing:1px;">
    <span leaf="">{{标签，如 📌 真实案例}}</span>
  </p>
  <p style="font-size:14px;color:#374151;line-height:1.8;margin:0;">
    <span leaf="">{{案例内容}}</span>
  </p>
</section>
```

---

## 组件 9 数据高亮卡（白底+红色调阴影+大数字）

> 用于关键数据、核心指标、对比数字等。

```html
<section style="margin:0 10px 24px;padding:20px;background:#FFFFFF;border-radius:12px;box-shadow:0 4px 24px -4px rgba(220,38,38,0.15);text-align:center;">
  <p style="font-size:36px;font-weight:900;color:#DC2626;margin:0;line-height:1.2;">
    <span leaf="">{{大数字}}</span>
  </p>
  <p style="font-size:13px;color:#6B7280;margin:8px 0 0;line-height:1.6;">
    <span leaf="">{{数字说明}}</span>
  </p>
</section>
```

---

## 组件 10 引用块（大引号+深红文字）

```html
<section style="margin:0 10px 24px;padding:20px 24px;background:#FFFFFF;border-left:4px solid #DC2626;border-radius:0 8px 8px 0;">
  <p style="font-size:16px;font-weight:700;color:#1C1917;line-height:1.7;margin:0;font-style:italic;">
    <span leaf="">{{引用内容}}</span>
  </p>
</section>
```

---

## 组件 11 步骤卡（编号+标题+说明，纵向排列）

> 用于操作步骤、方法论、起步指南等。

```html
<section style="margin:0 10px 24px;padding:18px 20px;background:#FEF2F2;border-radius:10px;">
  <p style="font-size:13px;font-weight:700;color:#DC2626;margin:0 0 12px;letter-spacing:1px;">
    <span leaf="">{{标题，如 ✅ 怎么开始}}</span>
  </p>
  <p style="font-size:14px;color:#374151;line-height:2;margin:0;">
    <span style="color:#DC2626;font-weight:800;"><span leaf="">1. </span></span><span leaf="">{{步骤1}}</span><br>
    <span style="color:#DC2626;font-weight:800;"><span leaf="">2. </span></span><span leaf="">{{步骤2}}</span><br>
    <span style="color:#DC2626;font-weight:800;"><span leaf="">3. </span></span><span leaf="">{{步骤3}}</span>
  </p>
</section>
```

---

## 组件 12 结语

```html
<section style="padding:24px 10px 32px;">
  <p style="margin-bottom:16px;font-size:15px;color:#374151;line-height:1.8;text-align:justify;">
    <span leaf="">{{结语第一段}}</span>
  </p>
  <p style="margin-bottom:0;font-size:15px;color:#374151;line-height:1.8;text-align:justify;">
    <span leaf="">{{结语第二段}}</span>
    <span style="background:#FEE2E2;color:#991B1B;padding:1px 4px;border-radius:3px;font-weight:700;"><span leaf="">{{核心金句}}</span></span>
    <span leaf="">{{收尾}}</span>
  </p>
</section>
```

---

## 组件 13 签名区

```html
<section style="padding:0 10px 20px;text-align:center;">
  <p style="font-size:13px;color:#9CA3AF;margin:0;line-height:1.8;">
    <span leaf="">—— 硅基研究员 · 一个AI研究员的日常记录</span>
  </p>
</section>
```

---

## 组件 14 footer-cta 三连卡（点赞/推荐/转发）

> 图标上文字下，SVG 图标，flex 居中 gap 24-28px，每项 40px 圆形浅底容器。红白色系主题色。

```html
<section style="padding:24px 10px 20px;display:flex;justify-content:center;gap:28px;border-top:1px solid #FEE2E2;margin-top:8px;">
  <section style="text-align:center;">
    <section style="width:40px;height:40px;background:#FEF2F2;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 6px;">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>
    </section>
    <p style="font-size:11px;color:#DC2626;font-weight:700;margin:0;letter-spacing:1px;"><span leaf="">点赞</span></p>
  </section>
  <section style="text-align:center;">
    <section style="width:40px;height:40px;background:#FEF2F2;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 6px;">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
    </section>
    <p style="font-size:11px;color:#DC2626;font-weight:700;margin:0;letter-spacing:1px;"><span leaf="">推荐</span></p>
  </section>
  <section style="text-align:center;">
    <section style="width:40px;height:40px;background:#FEF2F2;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 6px;">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 18v-4a8 8 0 0 1 8-8h8"></path><polyline points="16 2 20 6 16 10"></polyline></svg>
    </section>
    <p style="font-size:11px;color:#DC2626;font-weight:700;margin:0;letter-spacing:1px;"><span leaf="">转发</span></p>
  </section>
</section>
```

---

## 文章类型 → 组件组合配方表

| 文章类型 | 推荐组件组合 |
|---------|------------|
| 副业/赚钱/路径 | 1→2→3→4→5→6→7→8→11→12→13→14 |
| 实操指南/教程 | 1→2→3→5→6→7→8→11→12→13→14 |
| 观点/方法论 | 1→2→3→5→6→7→9→10→12→13→14 |
| 案例分析 | 1→2→3→4→5→6→7→8→9→12→13→14 |

---

## 红白色系使用纪律

1. **红色只做强调**：标签、编号、下划线、分割线、图标，不整段铺红底
2. **正文用深灰**：#374151，不用纯黑，降低视觉疲劳
3. **卡片用浅红底**：#FEF2F2，不用纯白（和全局白底混在一起没层次）
4. **阴影用红色调**：rgba(220,38,38,0.15)，不用灰色阴影
5. **正文字号 15px**：比其他风格稍大，红白色系主打可读性
6. **编号用红底白字圆角方块**：不用圆形，不用粗黑框
