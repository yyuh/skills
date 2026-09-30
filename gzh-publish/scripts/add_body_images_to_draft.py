# -*- coding: utf-8 -*-
"""给已有草稿补正文插图（ProseMirror 安全方式：Selection 定位 + 剪贴板粘贴）
用法: python add_body_images_to_draft.py <appmsgid> 图1 图2 图3 [--anchors 锚点1 锚点2 ...]
锚点默认: 「01」「02」「03」大编号段落开头，图片插到各章节之前
自定义锚点示例（引流卡插到结尾引导前）:
  python add_body_images_to_draft.py <id> 图1 图2 图3 引流卡.png --anchors 01 02 03 点击下方卡片，关注硅基研究员
"""
import asyncio, sys, types, os, re

_gmod = types.ModuleType('greenlet')
class _Greenlet:
    def switch(self, *a, **k): return None
    def throw(self, *a, **k): return None
_gmod.greenlet = _Greenlet
sys.modules['greenlet'] = _gmod
from playwright.async_api import async_playwright

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL, 'scripts'))
from publish_full_v2 import copy_image_to_clipboard_retry  # 复用已验证的剪贴板函数

def log(msg):
    print(msg, flush=True)

async def paste_one(page, anchor, img_path):
    # 1) 光标 collapse 到锚点段落开头
    r = await page.evaluate(f"""() => {{
      const pms = document.querySelectorAll('.ProseMirror');
      let target = null;
      for (const pm of pms) {{
        if ((pm.getAttribute('data-placeholder')||'').indexOf('标题') >= 0) continue;
        target = pm; break;
      }}
      if (!target) return 'NO_PM';
      const ps = [...target.querySelectorAll('p')];
      const p = ps.find(el => (el.textContent||'').trim() === '{anchor}');
      if (!p) return 'NO_ANCHOR';
      const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      const first = walker.nextNode();
      if (!first) return 'NO_TEXTNODE';
      const range = document.createRange();
      range.setStart(first, 0);
      range.collapse(true);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      p.scrollIntoView({{block: 'center'}});
      return 'OK';
    }}""")
    if r != 'OK':
        return f'LOCATE_FAIL:{r}'
    await page.wait_for_timeout(600)
    # 2) 剪贴板
    ok = copy_image_to_clipboard_retry(str(img_path))
    if not ok:
        return 'CLIPBOARD_FAIL'
    # 3) Ctrl+V
    await page.keyboard.press('Control+V')
    # 4) 轮询等 mmbiz
    for i in range(30):
        await page.wait_for_timeout(1000)
        n = await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          for (const pm of pms) {
            if ((pm.getAttribute('data-placeholder')||'').indexOf('标题') >= 0) continue;
            let c = 0;
            for (const img of pm.querySelectorAll('img')) {
              const s = img.src || img.getAttribute('data-src') || '';
              if ((s.indexOf('mmbiz') >= 0 || s.indexOf('qpic') >= 0) && img.getBoundingClientRect().width > 50) c++;
            }
            return c;
          }
          return 0;
        }""")
        if n >= 1 and i >= 2:  # 至少出现1张mmbiz且已等2秒以上
            return f'OK:img{n}'
    return 'UPLOAD_TIMEOUT'

async def main():
    appmsgid = sys.argv[1]
    images = [a for a in sys.argv[2:] if a != '--anchors']
    # 可选自定义锚点: --anchors 锚点1 锚点2 ... （与图片一一对应，默认 01/02/03）
    if '--anchors' in sys.argv:
        ai = sys.argv.index('--anchors')
        imgs_part = sys.argv[2:ai]
        anchors = sys.argv[ai + 1:ai + 1 + len(imgs_part)]
        images = imgs_part
    else:
        anchors = ['01', '02', '03'][:len(images)]
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            os.path.join(SKILL, '.gzh-profile-dir'), headless=False,
            viewport={'width': 1440, 'height': 900},
            args=['--disable-blink-features=AutomationControlled'], channel='msedge')
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto('https://mp.weixin.qq.com', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(2000)
        m = re.search(r'token=(\d+)', page.url or '')
        token = m.group(1) if m else ''
        for pg in ctx.pages:
            if not token:
                mm = re.search(r'token=(\d+)', pg.url or '')
                if mm: token = mm.group(1)
        log(f'TOKEN: {token}')
        url = (f'https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit'
               f'&type=10&appmsgid={appmsgid}&token={token}&lang=zh_CN')
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(6000)
        # 关原创对话框（若有）
        try:
            el = page.locator('text=无需声明')
            if await el.count() > 0:
                await el.first.click()
                await page.wait_for_timeout(500)
                ok = page.locator('text=确定')
                if await ok.count() > 0:
                    await ok.first.click()
                    await page.wait_for_timeout(1000)
        except Exception:
            pass
        await page.wait_for_selector('.ProseMirror', timeout=15000)

        # 基线图片数
        base = await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          for (const pm of pms) {
            if ((pm.getAttribute('data-placeholder')||'').indexOf('标题') >= 0) continue;
            let c = 0;
            for (const img of pm.querySelectorAll('img')) {
              const s = img.src || img.getAttribute('data-src') || '';
              if ((s.indexOf('mmbiz') >= 0 || s.indexOf('qpic') >= 0) && img.getBoundingClientRect().width > 50) c++;
            }
            return c;
          }
          return 0;
        }""")
        log(f'基线mmbiz图片数: {base}')

        results = []
        for anchor, img in zip(anchors, images):
            img_path = img if os.path.isabs(img) else os.path.join(SKILL, img)
            log(f'粘贴插图 @锚点{anchor}: {os.path.basename(img_path)}')
            res = await paste_one(page, anchor, img_path)
            log(f'  -> {res}')
            results.append(res)
            await page.wait_for_timeout(1500)

        # 最终计数
        final = await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          for (const pm of pms) {
            if ((pm.getAttribute('data-placeholder')||'').indexOf('标题') >= 0) continue;
            let c = 0;
            for (const img of pm.querySelectorAll('img')) {
              const s = img.src || img.getAttribute('data-src') || '';
              if ((s.indexOf('mmbiz') >= 0 || s.indexOf('qpic') >= 0) && img.getBoundingClientRect().width > 50) c++;
            }
            return c;
          }
          return 0;
        }""")
        log(f'最终mmbiz图片数: {final} (基线 {base})')
        ok_count = sum(1 for r in results if r.startswith('OK'))
        if ok_count > 0:
            # 点保存为草稿
            await page.evaluate("""() => {
              const btns = [...document.querySelectorAll('button, .weui-desktop-btn, a')];
              const save = btns.find(b => (b.innerText||'').replace(/\\s/g,'') === '保存为草稿');
              if (save) { save.click(); return 'CLICKED'; }
              return 'NOT_FOUND';
            }""")
            await page.wait_for_timeout(8000)
            log('CUR_URL: ' + page.url[:130])
        log(f'SUMMARY: {results}')
        await page.screenshot(path=os.path.join(SKILL, 'outputs', '_add_imgs_final.png'))
        await ctx.close()

asyncio.run(main())
