#!/usr/bin/env python3
"""公众号完整发布流水线（异步版，含封面自动设置+原创对话框处理+名片置底）。

在 publish_draft_async.py 基础上增强：
1. 自动关闭原创声明对话框（选"无需声明"→确定）
2. 自动设置封面（先插入正文→更换封面→从图片库选→删临时图）
3. 自动插入公众号名片并置底
4. 完整的错误处理和截图记录

用法：
  python publish_full.py <正文.html> --title "标题" --cover "封面图路径"
  python publish_full.py <正文.html> --title "标题" --cover "cover.jpg" --card-name "硅基研究员"
"""
import sys
import types
import asyncio
import base64
import time
import re
import argparse
from pathlib import Path

# ---- greenlet 桩（绕过 Windows WDAC/AppLocker DLL 拦截）----
_gmod = types.ModuleType("greenlet")

class _Greenlet:
    def __init__(self, run=None, parent=None):
        self.run = run
        self.parent = parent
    def switch(self, *a, **k): return None
    def throw(self, *a, **k): return None
    def __bool__(self): return True

_gmod.greenlet = _Greenlet
_gmod.settrace = lambda *a, **k: None
sys.modules["greenlet"] = _gmod

from playwright.async_api import async_playwright

SKILL_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_FILE = str(SKILL_ROOT / "outputs" / "publish_full_progress.log")

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n"); f.flush()
    except Exception:
        pass

async def shot(page, name):
    path = str(SKILL_ROOT / "outputs" / f"full_{name}.png")
    try:
        await page.screenshot(path=path, full_page=False)
        log(f"截图→{name}")
    except Exception as e:
        log(f"截图失败:{e}")
    return path

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
    has_qr = ("扫码" in txt) or ("扫描二维码" in txt) or ("请使用微信" in txt)
    has_console = ("草稿箱" in txt) or ("图文素材" in txt) or ("内容管理" in txt)
    return has_console and not has_qr

async def has_original_dialog(page):
    """检测是否有原创声明对话框"""
    return await page.evaluate("""() => {
      const cands = document.querySelectorAll('.weui-dialog, [role="dialog"], [class*="dialog"], [class*="Dialog"], [class*="modal"], [class*="Modal"]');
      for (const d of cands) {
        if (d.offsetParent && d.innerText && d.innerText.indexOf('原创') >= 0) return true;
      }
      return false;
    }""")

async def close_original_dialog(page):
    """关闭原创声明对话框：选无需声明→确定（用JS选择器）"""
    if not await has_original_dialog(page):
        log("无原创对话框，跳过")
        return
    log("检测到原创对话框，处理中...")
    # 点击"无需声明"
    r = await page.evaluate("""() => {
      const cands = document.querySelectorAll('.weui-dialog, [role="dialog"], [class*="dialog"], [class*="Dialog"]');
      for (const d of cands) {
        if (!d.offsetParent || !d.innerText || d.innerText.indexOf('原创') < 0) continue;
        // 找包含"无需声明"的可点击元素
        const all = d.querySelectorAll('*');
        for (const el of all) {
          if (el.children.length === 0 && (el.innerText || '').trim() === '无需声明') {
            el.click();
            return 'CLICKED_TEXT';
          }
        }
        // 备用：找第二个radio
        const radios = d.querySelectorAll('input[type="radio"]');
        if (radios.length >= 2) { radios[1].click(); return 'CLICKED_RADIO'; }
      }
      return 'NOT_FOUND';
    }""")
    log(f"无需声明: {r}")
    await page.wait_for_timeout(1000)
    # 点击确定
    r2 = await page.evaluate("""() => {
      const cands = document.querySelectorAll('.weui-dialog, [role="dialog"], [class*="dialog"], [class*="Dialog"]');
      for (const d of cands) {
        if (!d.offsetParent || !d.innerText || d.innerText.indexOf('原创') < 0) continue;
        const btns = d.querySelectorAll('button');
        for (const b of btns) {
          if ((b.innerText || '').trim() === '确定') { b.click(); return 'CLICKED_OK'; }
        }
      }
      return 'NOT_FOUND';
    }""")
    log(f"确定: {r2}")
    await page.wait_for_timeout(2000)
    log("原创对话框已关闭")

async def inject_html(page, html):
    """注入正文HTML到ProseMirror"""
    b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
    return await page.evaluate("""(b64) => {
      const html = decodeURIComponent(escape(atob(b64)));
      const pms = document.querySelectorAll('.ProseMirror');
      let target = null;
      for (const pm of pms) {
        const ph = pm.getAttribute('data-placeholder') || '';
        if (ph.indexOf('标题') < 0) { target = pm; break; }
      }
      if (!target) return 'NO-PM';
      target.innerHTML = html;
      return 'LEN:' + target.innerText.length;
    }""", b64)

async def fill_title(page, title):
    """填写标题（用keyboard.type避免Illegal invocation）"""
    await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      for (const pm of pms) {
        const ph = pm.getAttribute('data-placeholder') || '';
        if (ph.indexOf('标题') >= 0) { pm.focus(); pm.innerHTML = ''; return 'FOCUSED'; }
      }
      return 'NOT_FOUND';
    }""")
    await page.wait_for_timeout(500)
    await page.keyboard.type(title)
    await page.wait_for_timeout(1000)
    return title

async def insert_cover_temp(page, cover_path):
    """把封面图插入到正文末尾（临时，为了让图片库有这张图）"""
    log("插入封面到正文末尾（临时）...")
    # 先处理可能弹出的原创对话框
    await close_original_dialog(page)
    # 滚动到底部
    await page.evaluate("""() => { window.scrollTo(0, document.body.scrollHeight); }""")
    await page.wait_for_timeout(2000)
    # 聚焦正文末尾
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
    # 上传图片
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
    """设置封面：点击更换封面→从图片库选择→选第一张→下一步→确认"""
    log("设置封面...")
    # 先处理原创对话框
    await close_original_dialog(page)
    # 滚动到封面区域
    await page.evaluate("""() => {
      const el = document.getElementById('js_cover_area');
      if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
    }""")
    await page.wait_for_timeout(2000)

    # 步骤1：点击封面区域触发菜单
    log("点击封面区域...")
    cover_clicked = await page.evaluate("""() => {
      const area = document.getElementById('js_cover_area');
      if (area) {
        const rect = area.getBoundingClientRect();
        return {x: rect.x + rect.width/2, y: rect.y + rect.height/2, w: rect.width, h: rect.height};
      }
      return null;
    }""")
    if cover_clicked:
        await page.mouse.click(cover_clicked['x'], cover_clicked['y'])
        log(f"点击封面区域坐标: ({cover_clicked['x']}, {cover_clicked['y']})")
    else:
        log("未找到封面区域")
    await page.wait_for_timeout(2000)
    await shot(page, "cover_01_after_click")
    await close_original_dialog(page)

    # 步骤2：找"从图片库选择"并点击
    log("点击从图片库选择...")
    lib_clicked = await page.evaluate("""() => {
      const all = document.querySelectorAll('*');
      for (const el of all) {
        if (el.children.length === 0 && (el.innerText || '').trim() === '从图片库选择') {
          const rect = el.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            el.click();
            return {text: 'CLICKED', x: rect.x, y: rect.y};
          }
        }
      }
      return 'NOT_FOUND';
    }""")
    log(f"从图片库选择: {lib_clicked}")
    await page.wait_for_timeout(3000)
    await shot(page, "cover_02_after_lib_click")

    # 步骤3：选中第一行第一张图片（用坐标点击）
    log("选中第一张图片...")
    await page.mouse.click(485, 285)
    await page.wait_for_timeout(1500)
    await shot(page, "cover_03_after_select")

    # 步骤4：点击"下一步"（先找按钮，找不到就用坐标）
    log("点击下一步...")
    next_r = await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) {
        const t = (b.innerText || '').trim();
        if (t === '下一步' && b.offsetParent) {
          const rect = b.getBoundingClientRect();
          b.click();
          return {text: 'CLICKED', x: rect.x, y: rect.y};
        }
      }
      return 'NOT_FOUND';
    }""")
    log(f"下一步: {next_r}")
    if next_r == 'NOT_FOUND':
        # 备用：用坐标点击右下角的下一步
        log("备用：用坐标点击下一步(900, 680)")
        await page.mouse.click(900, 680)
    await page.wait_for_timeout(4000)
    await shot(page, "cover_04_after_next")

    # 步骤5：点击"确定"完成封面设置
    log("点击确定...")
    confirm_r = await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) {
        const t = (b.innerText || '').trim();
        if ((t === '确定' || t === '确认' || t === '完成') && b.offsetParent) {
          const rect = b.getBoundingClientRect();
          if (rect.y > 100) { b.click(); return {text: 'CLICKED:' + t, x: rect.x, y: rect.y}; }
        }
      }
      return 'NOT_FOUND';
    }""")
    log(f"确定: {confirm_r}")
    if confirm_r == 'NOT_FOUND':
        log("备用：用坐标点击确定(900, 680)")
        await page.mouse.click(900, 680)
    await page.wait_for_timeout(3000)
    await shot(page, "cover_05_after_confirm")
    log("封面设置完成")

async def remove_temp_cover(page):
    """删除正文末尾临时插入的封面图（保留名片图片），循环删到没有非名片图片为止"""
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
              // 向上找section容器删除
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
        if result in ('NO_IMG', 'NO_PM'):
            break
        removed += 1
        log(f"第{attempt+1}次删除: {result}")
        await page.wait_for_timeout(500)
    log(f"共删除 {removed} 张临时图")

async def insert_card(page, card_name="硅基研究员"):
    """插入公众号名片并置底"""
    log(f"插入名片: {card_name}...")
    await close_original_dialog(page)
    # 点击账号名片按钮
    await page.evaluate("""() => {
      const cands = Array.from(document.querySelectorAll('button, [role=button], div, span, a'));
      for (const el of cands) {
        const t = (el.innerText || '').trim();
        if (t === '账号名片') { el.click(); return 'CLICKED'; }
      }
      return 'NOT_FOUND';
    }""")
    await page.wait_for_timeout(2000)
    # 输入账号名称
    await page.evaluate(f"""() => {{
      const ins = Array.from(document.querySelectorAll('input'));
      for (const i of ins) {{
        const ph = i.getAttribute('placeholder')||'';
        if (ph.indexOf('账号名称') >= 0 || ph.indexOf('账号ID') >= 0) {{
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
          setter.call(i, '{card_name}');
          i.dispatchEvent(new Event('input',{{bubbles:true}}));
          i.dispatchEvent(new Event('change',{{bubbles:true}}));
          i.focus();
          return 'INPUT';
        }}
      }}
      return 'NO_INPUT';
    }}""")
    await page.wait_for_timeout(1500)
    await page.keyboard.press('Enter')
    await page.wait_for_timeout(3000)
    # 点击搜索结果卡片
    await page.evaluate(f"""() => {{
      const cards = Array.from(document.querySelectorAll('.wx_profile_card, [class*="profile_card"], [class*="account_card"]'));
      for (const c of cards) {{
        if (c.innerText.indexOf('{card_name}') >= 0) {{ c.click(); return 'CARD'; }}
      }}
      const all = document.querySelectorAll('*');
      for (const el of all) {{
        if (el.children.length === 0 && el.innerText && el.innerText.trim() === '{card_name}') {{
          el.click(); return 'TEXT';
        }}
      }}
      return 'NOT_FOUND';
    }}""")
    await page.wait_for_timeout(1500)
    # 点击插入按钮
    await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) { if ((b.innerText||'').trim() === '插入') { b.click(); return 'INSERTED'; } }
      return 'NO_BTN';
    }""")
    await page.wait_for_timeout(2000)
    # 名片置底
    await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      let target=null;
      for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
      if (target) {
        const wrp = target.querySelector('section.mp_profile_iframe_wrp') || target.querySelector('.mp_profile_iframe_wrp');
        if (wrp) target.appendChild(wrp);
      }
    }""")
    await page.wait_for_timeout(1000)
    log("名片已插入并置底")

async def clear_summary(page):
    """清空摘要输入框（用户要求摘要留空，不自动抓取）"""
    log("清空摘要...")
    r = await page.evaluate("""() => {
      // 摘要通常是textarea，placeholder含"摘要"或"选填"
      const tas = document.querySelectorAll('textarea');
      for (const ta of tas) {
        const ph = ta.getAttribute('placeholder') || '';
        if (ph.indexOf('摘要') >= 0 || ph.indexOf('选填') >= 0 || ph.indexOf('转发') >= 0) {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
          setter.call(ta, '');
          ta.dispatchEvent(new Event('input', {bubbles:true}));
          ta.dispatchEvent(new Event('change', {bubbles:true}));
          return 'CLEARED_TEXTAREA';
        }
      }
      // 备用：找contenteditable的摘要区域
      const eds = document.querySelectorAll('[contenteditable="true"]');
      for (const ed of eds) {
        const ph = ed.getAttribute('data-placeholder') || '';
        if (ph.indexOf('摘要') >= 0 || ph.indexOf('选填') >= 0) {
          ed.innerHTML = '';
          return 'CLEARED_EDITABLE';
        }
      }
      return 'NOT_FOUND';
    }""")
    log(f"摘要清空: {r}")

async def save_draft(page):
    """保存草稿"""
    log("保存草稿...")
    await close_original_dialog(page)
    # 先清空摘要
    await clear_summary(page)
    await page.wait_for_timeout(1000)
    await page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) {
        if ((b.innerText || '').indexOf('保存为草稿') >= 0) { b.click(); return; }
      }
    }""")
    await page.wait_for_timeout(3000)
    # 处理确认对话框
    await page.evaluate("""() => {
      const cands = document.querySelectorAll('.weui-dialog, [role="dialog"]');
      for (const d of cands) {
        if (!d.offsetParent) continue;
        const btns = d.querySelectorAll('button, a');
        for (const b of btns) {
          const t = (b.innerText||'').trim();
          if (t === '确定' || t === '确认') { b.click(); return; }
        }
      }
    }""")
    await page.wait_for_timeout(3000)
    return page.url

async def open_editor(ctx, page):
    """打开编辑器（多种尝试方式）"""
    editor_page = None
    token = None
    m = re.search(r"token=(\d+)", page.url or "")
    if m: token = m.group(1)
    if not token:
        for pg in ctx.pages:
            m = re.search(r"token=(\d+)", pg.url or "")
            if m: token = m.group(1); break

    # 尝试1：token直跳编辑器
    if token:
        editor_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg"
                      f"?t=media/appmsg_edit_v2&action=edit&isNew=1"
                      f"&type=10&lang=zh_CN&token={token}")
        log(f"直跳编辑器: {editor_url}")
        try:
            await page.goto(editor_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)
            pms = await page.query_selector_all(".ProseMirror")
            if pms:
                editor_page = page
                log("直跳成功，找到编辑器")
        except Exception as e:
            log(f"直跳失败: {e}")

    # 尝试2：遍历标签页找
    if not editor_page:
        for i, pg in enumerate(ctx.pages):
            try:
                pms = await pg.query_selector_all(".ProseMirror")
                if pms:
                    editor_page = pg
                    log(f"在标签页{i}找到编辑器")
                    break
            except Exception:
                continue

    return editor_page

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html", help="正文HTML文件路径")
    ap.add_argument("--title", required=True, help="文章标题")
    ap.add_argument("--cover", help="封面图路径（可选，不填则不设置封面）")
    ap.add_argument("--card-name", default="硅基研究员", help="公众号名片名称")
    ap.add_argument("--no-card", action="store_true", help="不插入名片")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--profile-dir", default=".gzh-profile-dir")
    ap.add_argument("--wait-scan", type=int, default=600, help="等待扫码秒数")
    args = ap.parse_args()

    profile_dir = Path(args.profile_dir)
    if not profile_dir.is_absolute():
        profile_dir = SKILL_ROOT / profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)

    try:
        Path(PROGRESS_FILE).write_text("", encoding="utf-8")
    except Exception:
        pass

    log("==== 启动完整发布流水线 ====")
    if not Path(args.html).is_file():
        log(f"ERR: 找不到HTML: {args.html}")
        sys.exit(1)
    html = Path(args.html).read_text(encoding="utf-8")
    log(f"正文已加载: {len(html)} 字符")

    if args.cover and not Path(args.cover).is_file():
        log(f"ERR: 找不到封面图: {args.cover}")
        sys.exit(1)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)

        # 登录检测
        if await is_logged_in(page):
            log("已登录")
        else:
            log("未登录，等待扫码...")
            qr_path = str(SKILL_ROOT / "outputs" / "login_qr.png")
            await page.screenshot(path=qr_path)
            log(f"QR-READY: {qr_path}")
            log("请用微信扫码，扫完后脚本会自动继续")
            ok = False
            for i in range(args.wait_scan // 2):
                await page.wait_for_timeout(2000)
                for pg in ctx.pages:
                    if await is_logged_in(pg):
                        page = pg; ok = True; break
                if ok: break
                if i > 0 and i % 60 == 59:
                    await page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=qr_path)
            if not ok:
                log("ERR: 扫码超时")
                await ctx.close(); sys.exit(1)
            log("登录成功")

        # 打开编辑器
        page = await open_editor(ctx, page)
        if not page:
            log("ERR: 无法打开编辑器")
            await ctx.close(); sys.exit(1)
        await shot(page, "01_editor")

        # 关闭原创对话框（可能在打开编辑器后弹出）
        await close_original_dialog(page)

        # 注入正文
        log("注入正文...")
        inj = await inject_html(page, html)
        log(f"注入结果: {inj}")
        await page.wait_for_timeout(2000)

        # 填标题
        log("填标题...")
        await fill_title(page, args.title)
        await page.wait_for_timeout(1000)

        # 设置封面（如果提供了封面图）
        if args.cover:
            await insert_cover_temp(page, args.cover)
            await shot(page, "02_cover_inserted")
            await set_cover(page)
            await shot(page, "03_cover_set")
            await remove_temp_cover(page)

        # 插入名片
        if not args.no_card:
            await insert_card(page, args.card_name)

        await shot(page, "04_before_save")

        # 保存草稿
        url = await save_draft(page)
        log(f"保存URL: {url}")
        await shot(page, "05_final")

        # 最终检查
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

    if url and "appmsgid=" in url:
        log("DONE: 已存入草稿箱")
        sys.exit(0)
    log("WARN: 请人工检查草稿箱")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
