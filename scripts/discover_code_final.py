#!/usr/bin/env python3
"""诊断：聚焦后工具栏遮罩是否消失；点击插入代码后是否出现任何 dialog/textarea/select。"""
import sys, types, asyncio, time, json
from pathlib import Path

_gmod = types.ModuleType("greenlet")
class _G:
    def switch(self,*a,**k): return None
    def throw(self,*a,**k): return None
_gmod.greenlet = _G
sys.modules["greenlet"] = _gmod
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

async def is_logged_in(page):
    try: url = page.url or ""
    except Exception: url = ""
    if "cgi-bin" in url and "connect" not in url and "qrconnect" not in url:
        return True
    try: txt = await page.inner_text("body", timeout=5000)
    except Exception: return False
    return ("草稿箱" in txt or "图文素材" in txt or "内容管理" in txt) and \
           not ("扫码" in txt or "请使用微信" in txt)

async def open_editor(ctx):
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(2000)
    if not await is_logged_in(page):
        log("NOT-LOGGED-IN"); return None
    async with ctx.expect_page(timeout=15000) as np_info:
        await page.evaluate("""() => {
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
          let node; while (node = walker.nextNode()) {
            if (node.textContent.trim() !== '文章') continue;
            let p = node.parentElement; let inNew=false;
            while (p){ if ((p.textContent||'').includes('新的创作')){inNew=true;break;} p=p.parentElement; }
            if (inNew) { let el=node.parentElement; while(el&&el!==document.body){ if (el.onclick||el.tagName==='A'||el.tagName==='BUTTON'||window.getComputedStyle(el).cursor==='pointer'||el.getAttribute('role')==='button'){el.click();return;} el=el.parentElement; } node.parentElement.click(); return; }
          }
        }""")
    np = await np_info.value
    await np.wait_for_load_state("domcontentloaded", timeout=60000)
    await np.wait_for_selector(".ProseMirror", timeout=25000)
    return np

async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(ROOT/".gzh-profile-dir"), headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width":1440,"height":900},
        )
        np = await open_editor(ctx)
        if not np:
            await ctx.close(); return
        # 聚焦编辑器正文
        await np.click(".ProseMirror", timeout=8000)
        await np.wait_for_timeout(3000)
        # 遮罩状态
        mask = await np.evaluate("""() => {
          const m = document.querySelector('#edui1_toolbar_mask, [class*="edui_toolbar_mask"]');
          if (!m) return 'NO_MASK';
          const r = m.getBoundingClientRect();
          const cs = getComputedStyle(m);
          return {display:cs.display, visibility:cs.visibility, pe:cs.pointerEvents, w:Math.round(r.width), h:Math.round(r.height), top:Math.round(r.top)};
        }""")
        log(f"聚焦后遮罩状态: {mask}")
        # 不隐藏遮罩，直接真实点击代码按钮
        try:
            await np.click(".edui-for-insertcode", timeout=8000)
            log("点击成功")
        except Exception as e:
            log(f"点击失败: {e}")
        await np.wait_for_timeout(2500)
        info = await np.evaluate("""() => {
          const res = {};
          res.eduiDialog = document.querySelectorAll('.edui-dialog').length;
          // 可见的 weui dialog
          const wd = Array.from(document.querySelectorAll('.weui-desktop-dialog__wrp, .weui-desktop-dialog'));
          res.weuiVisible = wd.filter(d=>{const s=d.style; return s.display!=='none' && getComputedStyle(d).visibility!=='hidden';}).length;
          // 所有 textarea（排除已知 title/digest）
          const tas = Array.from(document.querySelectorAll('textarea')).map(t=>({id:t.id||'', cls:String(t.className||'').slice(0,60), ph:t.getAttribute('placeholder')||'', len:(t.value||'').length}));
          res.textareas = tas;
          // 所有 select
          const sels = Array.from(document.querySelectorAll('select')).map(s=>({id:s.id||'', cls:String(s.className||'').slice(0,60), opts:Array.from(s.options).map(o=>o.text).slice(0,30)}));
          res.selects = sels;
          // 任何含 '语言' 文本的元素
          const langEls = [];
          const all = document.querySelectorAll('*');
          for (const el of all) {
            const t = (el.textContent||'').trim();
            if (t==='语言' || t.indexOf('代码语言')>=0 || t==='插入代码') langEls.push({tag:el.tagName, cls:String(el.className||'').slice(0,60), text:t.slice(0,30)});
          }
          res.langEls = langEls.slice(0,20);
          // body 尾部 3k
          res.bodyTail = document.body.innerHTML.slice(-3000);
          return res;
        }""")
        (OUT/"code_modal_discovery.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"eduiDialog={info['eduiDialog']} weuiVisible={info['weuiVisible']}")
        log(f"textareas={info['textareas']}")
        log(f"selects={info['selects']}")
        log(f"langEls={info['langEls']}")
        log(f"bodyTail(前500)={info['bodyTail'][:500]}")
        await ctx.close()

asyncio.run(main())
