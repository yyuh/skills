#!/usr/bin/env python3
"""给已有公众号草稿添加封面。

用法：
  python add_cover_to_draft.py --appmsgid 100000686 --cover "封面图路径"
"""
import sys
import types
import asyncio
import time
import re
import argparse
from pathlib import Path

# ---- greenlet 桩 ----
_gmod = types.ModuleType("greenlet")
class _Greenlet:
    def __init__(self, run=None, parent=None):
        self.run = run; self.parent = parent
    def switch(self, *a, **k): return None
    def throw(self, *a, **k): return None
    def __bool__(self): return True
_gmod.greenlet = _Greenlet
_gmod.settrace = lambda *a, **k: None
sys.modules["greenlet"] = _gmod

from playwright.async_api import async_playwright

SKILL_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_FILE = str(SKILL_ROOT / "outputs" / "add_cover_progress.log")

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n"); f.flush()
    except Exception:
        pass

async def shot(page, name):
    path = str(SKILL_ROOT / "outputs" / f"addcover_{name}.png")
    try:
        await page.screenshot(path=path, full_page=False)
        log(f"截图→{name}")
    except Exception as e:
        log(f"截图失败:{e}")

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
    # 已登录强标志：主页有「新的创作」面板，或左侧有「首页」+「内容管理」菜单
    has_console = ("新的创作" in txt) or (
        ("首页" in txt) and ("内容管理" in txt)
    )
    # 未登录强标志（登录页特有文案，已登录页的创作周报二维码不含这些词）
    has_login_page = ("微信扫一扫" in txt) or ("使用账号登录" in txt) or ("扫码登录" in txt)
    return has_console and not has_login_page

async def close_original_dialog(page):
    has = await page.evaluate("""() => {
      const cands = document.querySelectorAll('.weui-dialog, [role="dialog"], [class*="dialog"], [class*="Dialog"], [class*="modal"], [class*="Modal"]');
      for (const d of cands) {
        if (d.offsetParent && d.innerText && d.innerText.indexOf('原创') >= 0) return true;
      }
      return false;
    }""")
    if not has:
        log("无原创对话框，跳过")
        return
    log("处理原创对话框...")
    await page.evaluate("""() => {
      const cands = document.querySelectorAll('.weui-dialog, [role="dialog"], [class*="dialog"], [class*="Dialog"]');
      for (const d of cands) {
        if (!d.offsetParent || !d.innerText || d.innerText.indexOf('原创') < 0) continue;
        const all = d.querySelectorAll('*');
        for (const el of all) {
          if (el.children.length === 0 && (el.innerText || '').trim() === '无需声明') {
            el.click(); return;
          }
        }
        const radios = d.querySelectorAll('input[type="radio"]');
        if (radios.length >= 2) radios[1].click();
      }
    }""")
    await page.wait_for_timeout(1000)
    await page.evaluate("""() => {
      const cands = document.querySelectorAll('.weui-dialog, [role="dialog"], [class*="dialog"], [class*="Dialog"]');
      for (const d of cands) {
        if (!d.offsetParent || !d.innerText || d.innerText.indexOf('原创') < 0) continue;
        const btns = d.querySelectorAll('button');
        for (const b of btns) {
          if ((b.innerText || '').trim() === '确定') { b.click(); return; }
        }
      }
    }""")
    await page.wait_for_timeout(2000)
    log("原创对话框已关闭")

async def insert_cover_temp(page, cover_path):
    log("插入封面到正文末尾（临时）...")
    await close_original_dialog(page)
    await page.evaluate("""() => { window.scrollTo(0, document.body.scrollHeight); }""")
    await page.wait_for_timeout(2000)
    await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      let target=null;
      for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
      if (target) {
        target.focus();
        const range = document.createRange();
        range.selectNodeContents(target);
        range.collapse(false);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
      }
    }""")
    await page.wait_for_timeout(1000)
    file_inputs = await page.query_selector_all('input[type="file"]')
    for i, inp in enumerate(file_inputs):
        try:
            await inp.set_input_files(cover_path)
            log(f"上传到输入框{i}成功")
            break
        except Exception as e:
            log(f"输入框{i}失败:{e}")
    await page.wait_for_timeout(10000)
    log("封面已插入正文末尾")

async def set_cover(page):
    log("设置封面...")
    await close_original_dialog(page)
    await page.evaluate("""() => {
      const el = document.getElementById('js_cover_area');
      if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
    }""")
    await page.wait_for_timeout(2000)
    log("悬停封面区域（触发弹窗）...")
    cover_pos = await page.evaluate("""() => {
      const area = document.getElementById('js_cover_area');
      if (area) {
        const rect = area.getBoundingClientRect();
        return {x: rect.x + rect.width/2, y: rect.y + rect.height/2};
      }
      return null;
    }""")
    if cover_pos:
        await page.mouse.move(cover_pos['x'], cover_pos['y'])
        await page.wait_for_timeout(1500)
        await page.mouse.move(cover_pos['x'] + 10, cover_pos['y'] + 5)
        await page.wait_for_timeout(2000)
    await shot(page, "01_after_hover")
    await close_original_dialog(page)
    log("点击从正文中选择（js_selectCoverFromContent）...")
    clicked = await page.evaluate("""() => {
      const btn = document.querySelector('.js_selectCoverFromContent');
      if (btn) {
        const rect = btn.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          btn.click();
          return true;
        }
      }
      return false;
    }""")
    if not clicked:
        log("js_selectCoverFromContent not visible, try clicking replace button...")
        await page.evaluate("""() => {
          const btn = document.querySelector('.js_chooseCover');
          if (btn) btn.click();
        }""")
        await page.wait_for_timeout(2000)
        clicked = await page.evaluate("""() => {
          const btn = document.querySelector('.js_selectCoverFromContent');
          if (btn) {
            const rect = btn.getBoundingClientRect();
            if (rect.width > 0) { btn.click(); return true; }
          }
          return false;
        }""")
    await page.wait_for_timeout(8000)
    await shot(page, "02_after_select")
    log("选中图片（新插入的封面）...")
    # Find image position in dialog and click with mouse
    img_pos = await page.evaluate("""() => {
      // Find all visible images in the dialog/popover
      const allImgs = document.querySelectorAll('img');
      for (let i = allImgs.length - 1; i >= 0; i--) {
        const img = allImgs[i];
        const rect = img.getBoundingClientRect();
        // Image should be visible, reasonable size, and in the dialog area (y > 300)
        if (rect.width > 50 && rect.width < 300 && rect.height > 50 && rect.height < 300 && rect.y > 300 && rect.y < 800) {
          return {x: rect.x + rect.width/2, y: rect.y + rect.height/2, w: rect.width, h: rect.height};
        }
      }
      return null;
    }""")
    if img_pos:
        log(f"  found image at ({img_pos['x']}, {img_pos['y']}), size {img_pos['w']}x{img_pos['h']}")
        await page.mouse.click(img_pos['x'], img_pos['y'])
        log("  double-clicked image")
    else:
        log("  no image found, trying default coordinate (330, 530)...")
        await page.mouse.click(340, 410)
    await page.wait_for_timeout(3000)
    await shot(page, "02b_after_img_select")
    log("点击下一步（坐标）...")
    # Find next button position and click
    next_pos = await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) {
        if ((b.innerText || '').trim() === '下一步' && b.offsetParent) {
          const rect = b.getBoundingClientRect();
          return {x: rect.x + rect.width/2, y: rect.y + rect.height/2};
        }
      }
      return null;
    }""")
    if next_pos:
        await page.mouse.click(next_pos['x'], next_pos['y'])
        log(f"  clicked next at ({next_pos['x']}, {next_pos['y']})")
    else:
        log("  next button not found, trying default coordinate...")
        await page.mouse.click(660, 850)
    await page.wait_for_timeout(4000)
    await shot(page, "03_after_next")
    log("点击确定（坐标）...")
    confirm_pos = await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) {
        const t = (b.innerText || '').trim();
        if ((t === '完成' || t === '确定' || t === '确认') && b.offsetParent) {
          const rect = b.getBoundingClientRect();
          if (rect.y > 100 && b.className.indexOf('disabled') < 0) {
            return {x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: t};
          }
        }
      }
      return null;
    }""")
    if confirm_pos:
        await page.mouse.click(confirm_pos['x'], confirm_pos['y'])
        log(f"  clicked confirm ({confirm_pos.get('text','?')}) at ({confirm_pos['x']}, {confirm_pos['y']})")
    else:
        log("  confirm button not found, trying default coordinate...")
        await page.mouse.click(720, 780)
    await page.wait_for_timeout(3000)
    await shot(page, "04_after_confirm")
    log("封面设置完成")

async def remove_temp_cover(page):
    log("删除临时封面图...")
    await page.evaluate("""() => { window.scrollTo(0, document.body.scrollHeight); }""")
    await page.wait_for_timeout(2000)
    removed = 0
    for attempt in range(5):
        result = await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          let target=null;
          for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
          if (!target) return 'NO_PM';
          const imgs = target.querySelectorAll('img');
          for (let i = imgs.length - 1; i >= 0; i--) {
            const img = imgs[i];
            const inCard = img.closest('.mp_profile_iframe_wrp') || img.closest('[class*="profile"]');
            if (!inCard) {
              let parent = img;
              for (let j = 0; j < 8; j++) {
                if (parent.parentElement && parent.parentElement.tagName === 'SECTION') {
                  parent.parentElement.remove();
                  return 'REMOVED_SECTION';
                }
                parent = parent.parentElement;
                if (!parent) break;
              }
              img.remove();
              return 'REMOVED_IMG';
            }
          }
          return 'NO_IMG';
        }""")
        if result in ('NO_IMG', 'NO_PM'): break
        removed += 1
        log(f"第{attempt+1}次删除: {result}")
        await page.wait_for_timeout(500)
    log(f"共删除 {removed} 张临时图")

async def clear_summary(page):
    log("清空摘要...")
    await page.evaluate("""() => {
      const tas = document.querySelectorAll('textarea');
      for (const ta of tas) {
        const ph = ta.getAttribute('placeholder') || '';
        if (ph.indexOf('摘要') >= 0 || ph.indexOf('选填') >= 0 || ph.indexOf('转发') >= 0) {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
          setter.call(ta, '');
          ta.dispatchEvent(new Event('input', {bubbles:true}));
          ta.dispatchEvent(new Event('change', {bubbles:true}));
          return;
        }
      }
    }""")

async def save_draft(page):
    log("保存草稿...")
    await close_original_dialog(page)
    await clear_summary(page)
    await page.wait_for_timeout(1000)
    await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) {
        if ((b.innerText || '').indexOf('保存为草稿') >= 0) { b.click(); return; }
      }
    }""")
    await page.wait_for_timeout(3000)
    await page.evaluate("""() => {
      const cands = document.querySelectorAll('.weui-dialog, [role="dialog"]');
      for (const d of cands) {
        if (!d.offsetParent) continue;
        const btns = d.querySelectorAll('button, a');
        for (const b of btns) {
          if ((b.innerText||'').trim() === '确定') { b.click(); return; }
        }
      }
    }""")
    await page.wait_for_timeout(3000)
    return page.url

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--appmsgid", required=True, help="草稿的appmsgid")
    ap.add_argument("--cover", required=True, help="封面图路径")
    ap.add_argument("--profile-dir", default=".gzh-profile-dir")
    ap.add_argument("--wait-scan", type=int, default=600)
    args = ap.parse_args()

    profile_dir = Path(args.profile_dir)
    if not profile_dir.is_absolute():
        profile_dir = SKILL_ROOT / profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)

    try:
        Path(PROGRESS_FILE).write_text("", encoding="utf-8")
    except Exception:
        pass

    log("==== 启动补封面脚本 ====")
    if not Path(args.cover).is_file():
        log(f"ERR: 找不到封面图: {args.cover}")
        sys.exit(1)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)

        if await is_logged_in(page):
            log("已登录")
        else:
            log("未登录，等待扫码...")
            ok = False
            for i in range(args.wait_scan // 2):
                await page.wait_for_timeout(2000)
                for pg in ctx.pages:
                    if await is_logged_in(pg):
                        page = pg; ok = True; break
                if ok: break
            if not ok:
                log("ERR: 扫码超时")
                await ctx.close(); sys.exit(1)

        # 获取token
        token = None
        m = re.search(r"token=(\d+)", page.url or "")
        if m: token = m.group(1)
        if not token:
            for pg in ctx.pages:
                m = re.search(r"token=(\d+)", pg.url or "")
                if m: token = m.group(1); break

        if not token:
            log("ERR: 无法获取token")
            await ctx.close(); sys.exit(1)

        # 打开指定草稿
        edit_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg"
                    f"?t=media/appmsg_edit&action=edit&type=77"
                    f"&appmsgid={args.appmsgid}&token={token}&lang=zh_CN")
        log(f"打开草稿: {edit_url}")
        await page.goto(edit_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(8000)
        await shot(page, "00_draft_opened")

        await close_original_dialog(page)

        # 插入封面→设置封面→删临时图
        await insert_cover_temp(page, args.cover)
        await set_cover(page)
        await remove_temp_cover(page)

        await shot(page, "05_before_save")

        # 保存
        url = await save_draft(page)
        log(f"保存URL: {url}")
        await shot(page, "06_final")

        final = await page.evaluate("""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          let target=null;
          for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
          if (!target) return 'NO_PM';
          const imgs = target.querySelectorAll('img');
          let nonCardImgs = 0;
          imgs.forEach(img => {
            const inCard = img.closest('.mp_profile_iframe_wrp') || img.closest('[class*="profile"]');
            if (!inCard) nonCardImgs++;
          });
          return {textLength: target.innerText.length, totalImgs: imgs.length, nonCardImgs, card: target.querySelector('.mp_profile_iframe_wrp') ? 1 : 0};
        }""")
        log(f"最终检查: {final}")

        await page.wait_for_timeout(5000)
        await ctx.close()

    log("DONE: 封面已添加并保存")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
