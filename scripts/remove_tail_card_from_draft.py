# -*- coding: utf-8 -*-
"""从已有草稿中删除引流卡图（2026-09-27 引流卡取消）
定位逻辑：在正文 ProseMirror 里按文档顺序收集所有 <p>，找到含「点击下方卡片」引导语的段落，
向前回溯最近一个含 mmbiz 图片（宽>50）的段落（即引流卡），用 Range 选中该 img + Backspace 删除，
最后保存草稿。
用法: python remove_tail_card_from_draft.py <appmsgid>
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

def log(msg):
    print(msg, flush=True)

JS_FIND = """() => {
  const pms = document.querySelectorAll('.ProseMirror');
  let target = null;
  for (const pm of pms) {
    if ((pm.getAttribute('data-placeholder')||'').indexOf('标题') >= 0) continue;
    target = pm; break;
  }
  if (!target) return JSON.stringify({r:'NO_PM'});
  // 收集所有 mmbiz 真图，找最后一张宽高比>1.7（2:1 卡片）的图 = 引流卡
  const all = [...target.querySelectorAll('img')].filter(img => {
    const s = img.getAttribute('src') || img.getAttribute('data-src') || '';
    return (s.indexOf('mmbiz') >= 0 || s.indexOf('qpic') >= 0) && img.getBoundingClientRect().width > 50;
  });
  const cards = all.filter(img => {
    const r = img.getBoundingClientRect();
    return r.height > 0 && r.width / r.height > 1.7;
  });
  if (cards.length === 0) return JSON.stringify({r:'NO_CARD', real: all.length});
  const img = cards[cards.length - 1];
  const r = img.getBoundingClientRect();
  return JSON.stringify({r:'FOUND', w: Math.round(r.width), h: Math.round(r.height),
    real: all.length, cards: cards.length});
}"""

JS_SELECT = """() => {
  const pms = document.querySelectorAll('.ProseMirror');
  let target = null;
  for (const pm of pms) {
    if ((pm.getAttribute('data-placeholder')||'').indexOf('标题') >= 0) continue;
    target = pm; break;
  }
  if (!target) return 'NO_PM';
  const all = [...target.querySelectorAll('img')].filter(img => {
    const s = img.getAttribute('src') || img.getAttribute('data-src') || '';
    return (s.indexOf('mmbiz') >= 0 || s.indexOf('qpic') >= 0) && img.getBoundingClientRect().width > 50;
  });
  const cards = all.filter(img => {
    const r = img.getBoundingClientRect();
    return r.height > 0 && r.width / r.height > 1.7;
  });
  if (cards.length === 0) return 'NO_CARD';
  const img = cards[cards.length - 1];
  img.scrollIntoView({block: 'center'});
  const range = document.createRange();
  range.selectNode(img);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
  return 'SELECTED:' + Math.round(img.getBoundingClientRect().width) + 'x' + Math.round(img.getBoundingClientRect().height);
}"""

JS_COUNT = """() => {
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
}"""

async def main():
    appmsgid = sys.argv[1]
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

        base = await page.evaluate(JS_COUNT)
        log(f'基线mmbiz图片数: {base}')

        found = await page.evaluate(JS_FIND)
        log(f'定位引流卡: {found}')
        if '"FOUND"' not in found:
            log('SUMMARY: NO_CARD_FOUND, 不做任何修改')
            await page.screenshot(path=os.path.join(SKILL, 'outputs', f'_rm_card_nofind_{appmsgid}.png'))
            await ctx.close()
            return

        sel = await page.evaluate(JS_SELECT)
        log(f'选中: {sel}')
        if not sel.startswith('SELECTED'):
            log('SUMMARY: SELECT_FAIL')
            await ctx.close()
            return
        await page.wait_for_timeout(600)

        sel2 = await page.evaluate(JS_SELECT)
        log(f'重选中: {sel2}')
        await page.wait_for_timeout(400)
        await page.keyboard.press('Backspace')
        await page.wait_for_timeout(2500)

        final = await page.evaluate(JS_COUNT)
        log(f'删除后mmbiz图片数: {final} (基线 {base})')
        if final >= base:
            log('SUMMARY: DELETE_FAIL 图片数未减少，不保存')
            await page.screenshot(path=os.path.join(SKILL, 'outputs', f'_rm_card_fail_{appmsgid}.png'))
            await ctx.close()
            return

        await page.evaluate("""() => {
          const btns = [...document.querySelectorAll('button, .weui-desktop-btn, a')];
          const save = btns.find(b => (b.innerText||'').replace(/\\s/g,'') === '保存为草稿');
          if (save) { save.click(); return 'CLICKED'; }
          return 'NOT_FOUND';
        }""")
        await page.wait_for_timeout(8000)
        log('CUR_URL: ' + page.url[:130])
        await page.screenshot(path=os.path.join(SKILL, 'outputs', f'_rm_card_{appmsgid}.png'))
        log(f'SUMMARY: OK base={base} final={final}')
        await ctx.close()

asyncio.run(main())
