# -*- coding: utf-8 -*-
"""Step A: 把 H264 视频上传到公众号素材库（只上传，不定位插入）。
限流已冷却后只跑一次。成功标志：素材库出现新视频且无 上传中/处理中。"""
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

SKILL = Path(r"C:\Users\18480\Desktop\项目\skill\gzh-publish-公众号推送")
PROFILE = SKILL / ".gzh-profile-dir"
VIDEO = r"E:\gzh-videos\howtolivebetter_intro_h264.mp4"
EDIT_URL = ("https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit"
            "&action=edit&reprint_confirm=0&type=77&appmsgid=100006196"
            "&token=934230067&lang=zh_CN")

CLICK_UPLOAD_JS = r"""
() => {
  const els = Array.from(document.querySelectorAll('a,button,span,div'));
  const hit = els.find(e => e.textContent.trim() === '本地上传' && e.offsetParent !== null);
  if(!hit) return {ok:false};
  const r = hit.getBoundingClientRect();
  return {ok:true, x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)};
}
"""

DIALOG_STATE_JS = r"""
() => {
  const dlg = Array.from(document.querySelectorAll('[role="dialog"],.weui-desktop-dialog,.weui-desktop-mask~*'))
    .find(d => { const r=d.getBoundingClientRect(); return r.width>500 && r.height>300; });
  if(!dlg) return {dlg:false};
  const txt = dlg.innerText || '';
  const m = txt.match(/[0-9]{1,3}\s*%|上传中|处理中|转码中|上传失败|过于频繁|稍后再试/);
  // 视频条目（素材库卡片）
  const items = dlg.querySelectorAll('li,[class*="item"],[class*="card"],[class*="video"]');
  return {dlg:true, state: m?m[0]:'', itemCount:items.length,
          head: txt.replace(/\s+/g,' ').slice(0,200)};
}
"""

async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE), headless=False, channel="msedge",
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width":1440,"height":900})
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        signals = {"fc":0, "freq":False}
        async def on_fc(fc):
            signals["fc"] += 1
            print("FILECHOOSER_FIRED", signals["fc"], "multiple=", fc.is_multiple, flush=True)
            await fc.set_files(VIDEO)
            print("SET_FILES_DONE", flush=True)
        page.on("filechooser", lambda fc: asyncio.create_task(on_fc(fc)))

        def on_resp(r):
            u = r.url.lower()
            if "filetransfer" in u or "upload" in u or "asynctransfer" in u:
                print("RESP", r.status, r.url[:130], flush=True)
        page.on("response", on_resp)

        await page.goto(EDIT_URL, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(6000)
        # 关可能的原创声明弹窗
        await page.evaluate(r"""() => {
          const b = Array.from(document.querySelectorAll('label,span,div')).find(e=>e.textContent.trim().startsWith('无需声明'));
          if(b){ b.click(); const ok=Array.from(document.querySelectorAll('button,div,span')).find(e=>e.textContent.trim()==='确定'); if(ok) ok.click(); }
        }""")
        await page.wait_for_timeout(1000)

        # 打开 视频 弹窗
        await page.mouse.click(550, 27)
        await page.wait_for_timeout(1800)
        await page.screenshot(path=str(SKILL/"outputs"/"va_dialog_open.png"))

        # 点 本地上传（先取坐标）
        loc = await page.evaluate(CLICK_UPLOAD_JS)
        print("UPLOAD_BTN", json.dumps(loc, ensure_ascii=False), flush=True)
        if loc.get("ok"):
            await page.mouse.click(loc["x"], loc["y"])
        await page.wait_for_timeout(2500)
        await page.screenshot(path=str(SKILL/"outputs"/"va_after_upload_click.png"))

        # 轮询上传/转码
        appeared = False
        for i in range(60):
            await page.wait_for_timeout(2000)
            st = await page.evaluate(DIALOG_STATE_JS)
            if i % 3 == 0:
                print(f"poll{i}", json.dumps(st, ensure_ascii=False)[:300], flush=True)
            head = st.get("head","")
            if "过于频繁" in head or "稍后再试" in head:
                signals["freq"] = True
                print("STILL_RATE_LIMITED", flush=True)
                break
            if signals["fc"] > 0 and st.get("state","") == "" and i > 5:
                # 文件选过、且无进度/报错，稳定几帧后认为入库
                print("UPLOAD_SETTLED", json.dumps(st, ensure_ascii=False)[:300], flush=True)
                appeared = True
                await page.screenshot(path=str(SKILL/"outputs"/"va_upload_settled.png"))
                break
        await page.screenshot(path=str(SKILL/"outputs"/"va_end.png"))
        print("RESULT", json.dumps({"filechooser":signals["fc"], "freq":signals["freq"], "settled":appeared}, ensure_ascii=False), flush=True)
        await ctx.close()

asyncio.run(main())
