#!/usr/bin/env python3
"""发现微信编辑器「代码」按钮的真实选择器。"""
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

async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(ROOT/".gzh-profile-dir"),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width":1440,"height":900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        if not await is_logged_in(page):
            log("NOT-LOGGED-IN")
            await ctx.close(); return
        log("已登录，打开编辑器...")
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
        # 点击进入编辑器正文，触发工具栏渲染
        try:
            await np.click(".ProseMirror", timeout=8000)
        except Exception:
            pass
        await np.wait_for_timeout(1500)
        # 等待 UEditor 工具栏渲染
        try:
            await np.wait_for_selector('[class*="edui-"]', timeout=10000)
        except Exception:
            pass
        await np.wait_for_timeout(2500)
        info = await np.evaluate("""() => {
          const out = [];
          const all = Array.from(document.querySelectorAll('button, [role=button], div, span, a, i, svg, [class*="edui-"], [class*="toolbar"] *'));
          for (const el of all) {
            const t = (el.innerText||'').trim();
            const al = el.getAttribute('aria-label')||'';
            const ti = el.getAttribute('title')||'';
            const cls = String(el.className||'').slice(0,120);
            const html = String(el.innerHTML||'').slice(0,200);
            const data = {};
            for (const a of el.attributes) { if (a.name.startsWith('data-')) data[a.name]=a.value.slice(0,60); }
            const isCode = cls.toLowerCase().indexOf('code')>=0 || cls.indexOf('代码')>=0 ||
                           (t.indexOf('<')>=0 && t.indexOf('>')>=0) || t.indexOf('</')>=0 ||
                           al.indexOf('代码')>=0 || ti.indexOf('代码')>=0 || al.toLowerCase().indexOf('code')>=0 || ti.toLowerCase().indexOf('code')>=0;
            if (isCode || (el.tagName==='BUTTON' && (al||ti||data['data-type']))) {
              out.push({tag:el.tagName, text:t, aria:al, title:ti, cls:cls, html:html, data:data});
            }
          }
          // 顶部菜单栏
          const menu = [];
          for (const el of document.querySelectorAll('button, [role=button], div, span, a')) {
            const t = (el.innerText||'').trim();
            if (t==='账号名片' || t==='代码' || t.indexOf('代码')>=0) {
              menu.push({tag:el.tagName, text:t, cls:String(el.className||'').slice(0,80), html:String(el.innerHTML||'').slice(0,200)});
            }
          }
          // iframe 信息
          const iframes = Array.from(document.querySelectorAll('iframe')).map(f=> ({src:f.src||'', name:f.name||'', id:f.id||''}));
          const toolbar = document.querySelector('.edui-editor-toolbarboxinner, .edui-editor-toolbarbox, #js_editor_toolbarbox, .editor_toolbar, [class*="toolbar"]');
          const html = document.documentElement.outerHTML;
          return {count:out.length, btns:out.slice(0,40), menu:menu.slice(0,20), iframes:iframes, toolbarHTML: (toolbar||{}).outerHTML?.slice(0,5000)||'', htmlLen: html.length, html: html.slice(0,200000)};
        }""")
        (OUT/"toolbar_discovery.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"已保存 toolbar 结构到 outputs/toolbar_discovery.json; 候选按钮 {info['count']} 个")
        for b in info['btns']:
            log(f"BTN {b['tag']} text={b['text']} aria={b['aria']} title={b['title']} cls={b['cls']} data={b['data']} html={b['html']}")
        log("--- top menu 账号名片/代码 ---")
        for m in info['menu']:
            log(f"MENU {m['tag']} text={m['text']} cls={m['cls']} html={m['html']}")
        await ctx.close()

asyncio.run(main())
