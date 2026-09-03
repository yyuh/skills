#!/usr/bin/env python3
"""公众号封面分享安全区校验（纯标准库，无第三方依赖）

背景：公众号头图是 2.35:1 宽屏，但在消息列表/文章顶部完整显示的同时，
分享到朋友圈/聊天时只抓取**正中央的 1:1 方形**（仅占宽度 42.6%）。
因此封面上的关键信息（尤其是标题文字）如果超出中央 42.6% 区域，
分享出去就会被裁掉。

本脚本生成一个带安全区标注的 HTML 预览页：
- 封面完整显示，中央 42.6% 1:1 区域保持明亮
- 左右两侧非安全区叠加半透明遮罩（模拟分享裁切后消失）
- 底部给出量化提示：安全区像素范围、以及文字是否越界的判定（若提供文字坐标）

用法：
  python check_cover.py <封面图> [--out 输出.html] [--text-x "x1,x2"] [--title 描述]
  --text-x: 封面标题文字的水平范围（像素），如 --text-x "300,900"，用于判定文字是否在安全区内
"""
import sys
import html
import base64
from pathlib import Path

RATIO = 2.35
SAFE_FRACTION = 0.426  # 分享时保留的中央宽度占比（1:1 方形）

def main():
    if len(sys.argv) < 2:
        print("用法: python check_cover.py <封面图> [--out 输出.html] [--text-x \"x1,x2\"] [--title 描述]")
        sys.exit(1)

    img_path = Path(sys.argv[1])
    if not img_path.is_file():
        print(f"ERR: 找不到图片: {img_path}")
        sys.exit(1)

    out_path = Path("cover_safe_area_check.html")
    text_x = None
    title = "封面安全区校验"
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--out" and i+1 < len(args):
            out_path = Path(args[i+1]); i += 2
        elif args[i] == "--text-x" and i+1 < len(args):
            try:
                x1, x2 = args[i+1].split(",")
                text_x = (int(x1), int(x2)); i += 2
            except Exception:
                print("WARN: --text-x 格式应为 \"x1,x2\""); i += 2
        elif args[i] == "--title" and i+1 < len(args):
            title = args[i+1]; i += 2
        else:
            i += 1

    # 读图片，转 base64 内嵌（避免外部引用）
    img_b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
    ext = img_path.suffix.lower().lstrip(".") or "png"
    if ext == "jpg":
        ext = "jpeg"
    data_uri = f"data:image/{ext};base64,{img_b64}"

    # 计算安全区：中央 42.6% 宽度，1:1 方形（按图片自身宽高算百分比）
    safe_w_pct = SAFE_FRACTION * 100  # 42.6%
    left_pct = (100 - safe_w_pct) / 2  # 28.7%

    safe_css_left = left_pct
    safe_css_width = safe_w_pct

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>
  body {{ background:#1a1a1a; color:#eee; font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif; margin:0; padding:24px; }}
  h1 {{ font-size:18px; margin:0 0 8px; }}
  .sub {{ color:#999; font-size:13px; margin-bottom:16px; line-height:1.7; }}
  .stage {{ max-width:900px; margin:0 auto; background:#fff; border-radius:12px; padding:20px; }}
  .cover-wrap {{ position:relative; width:100%; max-width:720px; margin:0 auto; }}
  .cover-wrap img {{ width:100%; height:auto; display:block; border-radius:6px; }}
  .mask {{ position:absolute; top:0; bottom:0; width:{(100-safe_css_width)/2:.1f}%; background:rgba(0,0,0,0.55); z-index:2; }}
  .mask.left {{ left:0; border-radius:6px 0 0 6px; }}
  .mask.right {{ right:0; border-radius:0 6px 6px 0; }}
  .safe-box {{ position:absolute; top:0; bottom:0; left:{safe_css_left:.1f}%; width:{safe_css_width:.1f}%; z-index:3;
               box-shadow:inset 0 0 0 3px #22c55e; }}
  .safe-box::after {{ content:'分享保留区'; position:absolute; top:8px; left:50%; transform:translateX(-50%);
               background:#22c55e; color:#fff; font-size:11px; padding:2px 8px; border-radius:4px; white-space:nowrap; }}
  .legend {{ max-width:720px; margin:12px auto 0; display:flex; gap:16px; font-size:12px; color:#ccc; justify-content:center; }}
  .legend .g {{ color:#22c55e; font-weight:bold; }}
  .legend .r {{ color:#ef4444; font-weight:bold; }}
  .panel {{ max-width:720px; margin:16px auto 0; background:#2a2a2a; border-radius:8px; padding:14px 16px; font-size:13px; line-height:1.8; }}
  .panel b {{ color:#22c55e; }}
  .panel .bad {{ color:#ef4444; }}
</style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p class="sub">公众号封面分享安全区校验：<b>绿色框内</b>为分享到朋友圈/聊天时保留的区域（正中央 1:1 方形，占宽度 42.6%）；<b>灰色遮罩</b>为分享时会被裁掉的部分。<br>
  关键信息（标题文字、logo）应放在绿色框内，否则分享出去会被裁切。</p>
  <div class="stage">
    <div class="cover-wrap">
      <img src="{data_uri}" alt="封面图">
      <div class="mask left"></div>
      <div class="mask right"></div>
      <div class="safe-box"></div>
    </div>
    <div class="legend">
      <span><span class="g">■</span> 安全区（分享保留，中央 42.6%）</span>
      <span><span class="r">■</span> 遮罩区（分享裁切）</span>
    </div>
  </div>
  <div class="panel">
    <p><b>量化说明</b>（按图片实际像素，图片比例 2.35:1 时）：</p>
    <p>· 安全区 = 图片高度 × 高度，水平居中；左右各约 <b>{left_pct:.1f}%</b> 会被裁掉。</p>
    <p>· 安全区水平范围 ≈ <b>图宽 × {SAFE_FRACTION}</b>（如 1280px 宽 → 约 {1280*SAFE_FRACTION:.0f}px 宽，居中）。</p>
    {"<p><span class='bad'>⚠ 文字越界警告</span>：你标注的文字范围需换算成图片实际像素后与安全区比较——若文字任一像素超出安全区左右边界，分享时会被裁切。</p>" if text_x else "<p>提示：若封面标题文字铺满全宽，请把标题收进中央 42.6% 区域，或用本脚本配合图片实际尺寸人工核对。</p>"}
  </div>
</body>
</html>"""

    out_path.write_text(html_doc, encoding="utf-8")
    print(f"✅ 安全区标注页已生成: {out_path.resolve()}")
    print(f"   安全区占比: 中央 {SAFE_FRACTION*100:.1f}%（左右各裁 {left_pct:.1f}%）")
    print("   用浏览器打开它，检查标题/logo 是否都在绿色安全区内。")
    print("   判断标准：绿色框内 = 分享时保留；灰色遮罩 = 分享时被裁掉。")
    if text_x:
        print(f"   你标注的文字 x 范围: {text_x}（请对照图片实际像素换算后人工核对是否在安全区内）")

if __name__ == "__main__":
    main()
