#!/usr/bin/env python3
"""通过 UEditor 实例 API 直接触发 insertcode 命令，捕获代码对话框结构。"""
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
    try: await np.click(".ProseMirror", timeout=8000)
    except Exception: pass
    await np.wait_for_timeout(1500)
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
        # 探查 UE 实例
        ueinfo = await np.evaluate("""() => {
          const out = {};
          out.hasUE = (typeof window.UE !== 'undefined');
          try { out.ueKeys = window.UE ? Object.keys(window.UE) : []; } catch(e){ out.ueKeys = 'ERR:'+e.message; }
          try { out.instants = window.UE && window.UE.instants ? Object.keys(window.UE.instants) : []; } catch(e){ out.instants = 'ERR:'+e.message; }
          // 常见的编辑器 id
          const ids = ['edui1','js_editor','editor','ueditor','js_editor1','edui'];
          out.foundEditors = {};
          for (const id of ids) {
            try {
              const ed = window.UE && window.UE.getEditor ? window.UE.getEditor(id) : null;
              if (ed) out.foundEditors[id] = {ready: ed.ready, isDestroyed: ed.isDestroyed, key: ed.key};
            } catch(e){}
          }
          return out;
        }""")
        log(f"UE 探查: {json.dumps(ueinfo, ensure_ascii=False)}")
        # 尝试通过 API 触发 insertcode
        trig = await np.evaluate("""() => {
          try {
            const ed = window.UE && (window.UE.getEditor('edui1') || (window.UE.instants && window.UE.instants.edui1));
            if (!ed) return 'NO_EDITOR';
            // 聚焦
            if (ed.focus) ed.focus();
            ed.execCommand('insertcode');
            return 'CALLED';
          } catch(e) { return 'ERR:'+e.message+' | '+e.stack; }
        }""")
        log(f"execCommand insertcode: {trig}")
        await np.wait_for_timeout(3000)
        info = await np.evaluate("""() => {
          const res = {};
          const iframes = Array.from(document.querySelectorAll('iframe')).map(f=> ({src:f.src||'', id:f.id||''}));
          res.iframes = iframes;
          const dlg = document.querySelector('.edui-dialog');
          res.dlgHTML = (dlg||{}).outerHTML ? dlg.outerHTML.slice(0,12000) : 'NONE';
          const docs = [document];
          for (const f of document.querySelectorAll('iframe')) { try { if (f.contentDocument) docs.push(f.contentDocument); } catch(e){} }
          const fields = [];
          for (const doc of docs) {
            for (const el of doc.querySelectorAll('textarea, input, select')) {
              fields.push({tag:el.tagName, id:el.id||'', name:el.name||'', cls:String(el.className||'').slice(0,120), ph:el.getAttribute('placeholder')||'', value:(el.value!==undefined?String(el.value).slice(0,80):''), loc: doc===document?'main':'iframe'});
            }
          }
          res.fields = fields;
          const btns = [];
          for (const doc of docs) {
            for (const el of doc.querySelectorAll('button, [role=button], a')) {
              const txt=(el.innerText||'').trim();
              if (txt) btns.push({text:txt, cls:String(el.className||'').slice(0,100), loc: doc===document?'main':'iframe'});
            }
          }
          res.btns = btns;
          return res;
        }""")
        (OUT/"code_modal_discovery.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"dialog 出现: {info['dlgHTML']!='NONE'}")
        log(f"dialog HTML(前600): {info['dlgHTML'][:600]}")
        log(f"字段: {json.dumps(info['fields'], ensure_ascii=False)}")
        log(f"按钮(含 iframe): {info['btns']}")
        await ctx.close()

asyncio.run(main())
