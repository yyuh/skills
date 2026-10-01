# -*- coding: utf-8 -*-
"""Step B: 在【视频占位符1】位置插入素材库中的新视频，选封面，填作者，原创，保存，回读验证。
在 Step A 上传成功后运行。全程文本定位 + 截图，便于纠偏。"""
import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

SKILL = Path(r"C:\Users\18480\Desktop\项目\skill\gzh-publish-公众号推送")
PROFILE = SKILL / ".gzh-profile-dir"
APPMSGID = 100006196
TOKEN = "934230067"
EDIT_URL = ("https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit"
            "&action=edit&reprint_confirm=0&type=77&appmsgid={}"
            "&token={}&lang=zh_CN").format(APPMSGID, TOKEN)

def js_click_text(exact, contains=None, min_w=0):
    c = "exact:" + json.dumps(exact, ensure_ascii=False)
    return r"""
(param) => {
  const target = param.exact;
  let els = Array.from(document.querySelectorAll('a,button,span,div,label,li,p'));
  let hit = els.find(e => e.textContent.trim() === target && e.offsetParent !== null);
  if(!hit) return {ok:false, why:'no-exact'};
  const r = hit.getBoundingClientRect();
  if(r.width < 1) return {ok:false, why:'hidden'};
  return {ok:true, x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2), w:Math.round(r.width)};
}
""", {"exact": exact}

async def click_text(page, text, contains=False, wait=600, shot=None):
    if contains:
        js = r"""
(t) => {
  let els = Array.from(document.querySelectorAll('a,button,span,div,label,li,p'));
  let hit = els.find(e => (e.textContent||'').includes(t) && e.offsetParent!==null
            && e.textContent.trim().length < t.length+12);
  if(!hit) return {ok:false};
  const r=hit.getBoundingClientRect();
  return {ok:true,x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)};
}"""
    else:
        js = r"""
(t) => {
  let els = Array.from(document.querySelectorAll('a,button,span,div,label,li,p'));
  let hit = els.find(e => e.textContent.trim()===t && e.offsetParent!==null);
  if(!hit) return {ok:false};
  const r=hit.getBoundingClientRect();
  return {ok:true,x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)};
}"""
    loc = await page.evaluate(js, text)
    print("CLICK", json.dumps(text, ensure_ascii=False), json.dumps(loc, ensure_ascii=False), flush=True)
    if loc.get("ok"):
        await page.mouse.click(loc["x"], loc["y"])
        await page.wait_for_timeout(wait)
        if shot: await page.screenshot(path=str(SKILL/"outputs"/shot))
        return True
    return False

async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE), headless=False, channel="msedge",
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width":1440,"height":900})
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(EDIT_URL, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(6000)
        # 关原创声明弹窗（无需声明→确定）
        await page.evaluate(r"""() => {
          const b=Array.from(document.querySelectorAll('label,span,div')).find(e=>e.textContent.trim().startsWith('无需声明'));
          if(b){b.click();const ok=Array.from(document.querySelectorAll('button,div,span')).find(e=>e.textContent.trim()==='确定');if(ok)ok.click();}
        }""")
        await page.wait_for_timeout(1200)

        # 1) 定位视频占位符并删除，光标留该处
        found = await page.evaluate(r"""
() => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n, hits=[];
  while(n=walker.nextNode()){ if(n.textContent.includes('视频占位符')) hits.push(n); }
  if(!hits.length) return {ok:false};
  const t=hits[0];
  // 找所在块级 p
  let el=t.parentElement; while(el && el.tagName!=='P' && el.getAttribute && el.getAttribute('data-role')!=='body') el=el.parentElement;
  el.scrollIntoView({block:'center'});
  const r=el.getBoundingClientRect();
  return {ok:true,x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)};
}""")
        print("PLACEHOLDER", json.dumps(found, ensure_ascii=False), flush=True)
        await page.screenshot(path=str(SKILL/"outputs"/"vb_placeholder.png"))
        await page.mouse.click(found["x"], found["y"])
        await page.wait_for_timeout(400)
        await page.keyboard.press("Home")
        await page.keyboard.press("Shift+End")
        await page.keyboard.press("Delete")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(SKILL/"outputs"/"vb_after_delete.png"))

        # 2) 打开视频弹窗
        await page.mouse.click(550, 27)
        await page.wait_for_timeout(1800)
        await page.screenshot(path=str(SKILL/"outputs"/"vb_video_dialog.png"))

        # 3) 选素材库第一个（最新上传）视频卡片：直接点弹窗内最上方视频缩略
        pick = await page.evaluate(r"""
() => {
  const dlg = Array.from(document.querySelectorAll('[role="dialog"],.weui-desktop-dialog'))
    .find(d=>{const r=d.getBoundingClientRect();return r.width>500;});
  if(!dlg) return {ok:false};
  // 视频卡片通常是 li / 带封面图的块；取第一个含 img 或 video 的可点卡片
  const cards = Array.from(dlg.querySelectorAll('li,[class*="item"],[class*="card"],[class*="video"]'))
    .filter(e=>{const r=e.getBoundingClientRect();return r.width>120 && r.height>80 && (e.querySelector('img,video')||/视频|蒙太奇|生活/.test(e.textContent));});
  if(!cards.length) return {ok:false, n:0};
  const c=cards[0]; const r=c.getBoundingClientRect();
  return {ok:true,x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2),n:cards.length,
          txt:c.textContent.replace(/\s+/g,' ').slice(0,60)};
}""")
        print("PICK_CARD", json.dumps(pick, ensure_ascii=False), flush=True)
        await page.mouse.click(pick["x"], pick["y"])
        await page.wait_for_timeout(900)
        await page.screenshot(path=str(SKILL/"outputs"/"vb_card_selected.png"))

        # 4) 确定
        await click_text(page, "确定", wait=1500, shot="vb_after_confirm.png")

        # 5) 若弹出 选封面/视频信息 框：选第一张有色封面
        for k in range(3):
            cov = await page.evaluate(r"""
() => {
  const dlg = Array.from(document.querySelectorAll('[role="dialog"],.weui-desktop-dialog'))
    .find(d=>{const r=d.getBoundingClientRect();return r.width>500 && /封面|封面选择|视频信息|选择封面/.test(d.innerText);});
  if(!dlg) return {ok:false};
  const opts = Array.from(dlg.querySelectorAll('li,[class*="item"],[class*="frame"],img'))
    .filter(e=>{const r=e.getBoundingClientRect();return r.width>80&&r.height>50;});
  if(!opts.length) return {ok:true, dlgOnly:true};
  const o=opts[0]; const r=o.getBoundingClientRect();
  return {ok:true,x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)};
}""")
            print("COVER_DIALOG", json.dumps(cov, ensure_ascii=False), flush=True)
            if not cov.get("ok"): break
            if "x" in cov:
                await page.mouse.click(cov["x"], cov["y"])
                await page.wait_for_timeout(700)
                await page.screenshot(path=str(SKILL/"outputs"/"vb_cover_picked.png"))
            await click_text(page, "确定", wait=1400, shot=f"vb_cover_confirm_{k}.png")

        await page.screenshot(path=str(SKILL/"outputs"/"vb_inserted.png"))

        # 6) 作者 + 原创
        await page.evaluate(r"""
() => {
  const inp = document.querySelector('#author,input[placeholder*="作者"],input[placeholder*="请输入作者"]');
  if(inp){ const set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
    set.call(inp,'硅基研究员'); inp.dispatchEvent(new Event('input',{bubbles:true})); }
}""")
        await page.wait_for_timeout(500)
        await click_text(page, "原创", contains=True, wait=800, shot="vb_original.png")

        # 7) 保存为草稿
        await click_text(page, "保存为草稿", wait=2500, shot="vb_saved.png")
        if not await click_text(page, "保存", wait=2500, shot="vb_saved2.png"):
            await page.keyboard.press("Control+s")
            await page.wait_for_timeout(2500)
        await page.screenshot(path=str(SKILL/"outputs"/"vb_save_end.png"))

        # 8) 回读验证
        await page.goto(EDIT_URL, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(6000)
        verify = await page.evaluate(r"""
() => {
  const body = document.querySelector('#js_editor_content, .ProseMirror, #edui1_contentholder') || document.body;
  const txt = body.innerText || '';
  const imgs = Array.from(body.querySelectorAll('img'));
  const real = imgs.filter(i => (i.naturalWidth||i.width) > 60);
  const cards = Array.from(document.querySelectorAll('[class*="card"],mp-common-profile,mpcps')).length;
  const videoEl = body.querySelectorAll('iframe,video,[class*="video"],mp-common-videosnap,mpvideosnap').length;
  return {placeholderLeft: (txt.match(/占位符/g)||[]).length,
          imgCount: real.length, videoEl,
          hasVideoText: /视频/.test(txt),
          head: txt.replace(/\s+/g,' ').slice(0,120)};
}""")
        print("VERIFY", json.dumps(verify, ensure_ascii=False), flush=True)
        await page.screenshot(path=str(SKILL/"outputs"/"vb_verify.png"))
        await ctx.close()

asyncio.run(main())
