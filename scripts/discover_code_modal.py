#!/usr/bin/env python3
"""点击微信编辑器「插入代码」按钮，捕获弹出的对话框 DOM 结构。"""
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
    try:
        url = page.url or ""
    except Exception:
        url = ""
    if "cgi-bin" in url and "connect" not in url and "qrconnect" not in url:
        return True
    try:
        txt = await page.inner_text("body", timeout=5000)
    except Exception:
        return False
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
    try:
        await np.click(".ProseMirror", timeout=8000)
    except Exception:
        pass
    await np.wait_for_timeout(1500)
    return np

async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(ROOT/".gzh-profile-dir"),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width":1440,"height":900},
        )
        np = await open_editor(ctx)
        if not np:
            await ctx.close(); return
        log("找到代码按钮，点击插入代码（force）...")
        # 工具栏上有 edui1_toolbar_mask 遮罩拦截指针事件，force 绕过拦截
        try:
            await np.click(".edui-for-insertcode", force=True, timeout=10000)
        except Exception as e:
            log(f"force click 失败: {e}; 改用 JS 派发事件")
            await np.evaluate("""() => {
              const el = document.querySelector('.edui-for-insertcode');
              ['mousedown','mouseup','click'].forEach(t=>el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})));
            }""")
        # 轮询等待 .edui-dialog 出现
        found = False
        for _ in range(20):
            await np.wait_for_timeout(500)
            cnt = await np.evaluate("document.querySelectorAll('.edui-dialog').length")
            if cnt:
                found = True; break
        log(f"dialog 出现: {found}")
        await np.wait_for_timeout(1500)
        info = await np.evaluate("""() => {
          const res = {};
          const iframes = Array.from(document.querySelectorAll('iframe')).map(f=> ({src:f.src||'', id:f.id||'', cls:String(f.className||'').slice(0,80)}));
          res.iframes = iframes;
          const dlg = document.querySelector('.edui-dialog');
          res.dlgHTML = (dlg||{}).outerHTML ? dlg.outerHTML.slice(0,10000) : 'NONE';
          // 主文档 + 所有 iframe 内查找代码输入框/语言选择
          const fields = [];
          const docs = [document];
          for (const f of document.querySelectorAll('iframe')) { try { if (f.contentDocument) docs.push(f.contentDocument); } catch(e){} }
          for (const doc of docs) {
            for (const el of doc.querySelectorAll('textarea, input, select')) {
              const t = el.tagName;
              const ph = el.getAttribute('placeholder')||'';
              const v = el.value!==undefined ? String(el.value).slice(0,80) : '';
              const cls = String(el.className||'').slice(0,120);
              const id = el.id||'';
              const name = el.name||'';
              const aria = el.getAttribute('aria-label')||'';
              const ti = el.getAttribute('title')||'';
              fields.push({tag:t, id:id, name:name, cls:cls, ph:ph, value:v, aria:aria, title:ti, loc: doc===document?'main':'iframe'});
            }
          }
          res.fields = fields;
          const btns = [];
          for (const doc of docs) {
            for (const el of doc.querySelectorAll('button, [role=button], a')) {
              const txt = (el.innerText||'').trim();
              const cls = String(el.className||'').slice(0,100);
              if (txt) btns.push({tag:el.tagName, text:txt, cls:cls, loc: doc===document?'main':'iframe'});
            }
          }
          res.btns = btns;
          return res;
        }""")
        (OUT/"code_modal_discovery.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"已保存对话框结构到 outputs/code_modal_discovery.json")
        log(f"iframe 数: {len(info['iframes'])}")
        log(f"dialog HTML(前400): {info['dlgHTML'][:400]}")
        log(f"字段数: {len(info['fields'])}")
        for f in info['fields']:
            log(f"FIELD [{f['loc']}] {f['tag']} id={f['id']} name={f['name']} cls={f['cls']} ph={f['ph']} aria={f['aria']} title={f['title']} value={f['value']}")
        log(f"按钮: {info['btns']}")
        await ctx.close()

asyncio.run(main())
