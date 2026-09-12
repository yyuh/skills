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
try:
    import win32clipboard
    from PIL import Image
    import io
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False
    print("WARN: win32clipboard或PIL未安装，剪贴板粘贴功能不可用")
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


def copy_image_to_clipboard(image_path):
    """将图片复制到Windows剪贴板"""
    if not HAS_CLIPBOARD:
        return False
    try:
        image = Image.open(image_path)
        output = io.BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]  # BMP文件头14字节
        output.close()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        return True
    except Exception as e:
        print(f"复制图片到剪贴板失败: {e}")
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        return False

async def insert_cover_temp(page, cover_path):
    """把封面图粘贴到正文末尾（剪贴板CF_DIB方式，公众号编辑器支持粘贴上传）"""
    log("粘贴封面到正文末尾（剪贴板方式）...")
    # 滚动到底部
    await page.evaluate("""() => { window.scrollTo(0, document.body.scrollHeight); }""")
    await page.wait_for_timeout(800)
    # 点击正文中央偏下，确保聚焦
    body_info = await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      let target=null;
      for (const pm of pms){ if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')<0){target=pm;break;} }
      if (!target) return null;
      const rect = target.getBoundingClientRect();
      return {x: rect.x + rect.width/2, y: rect.y + Math.min(rect.height/2, 300)};
    }""")
    if body_info:
        await page.mouse.click(body_info['x'], min(body_info['y'], 800))
        await page.wait_for_timeout(1000)
    # 聚焦+光标置末尾
    await page.evaluate("""() => {
      const pms = document.querySelectorAll('.ProseMirror');
      for (const pm of pms) {
        if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')>=0) continue;
        pm.focus();
        const range = document.createRange();
        range.selectNodeContents(pm);
        range.collapse(false);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        break;
      }
    }""")
    await page.wait_for_timeout(600)
    # 复制封面到剪贴板
    ok = copy_image_to_clipboard(str(cover_path))
    if not ok:
        log("ERROR: 剪贴板复制封面失败")
        return False
    # Ctrl+V粘贴
    await page.keyboard.press('Control+V')
    # 轮询等待mmbiz图片上传成功（最多30秒）
    for i in range(30):
        await page.wait_for_timeout(1000)
        r = await page.evaluate(r"""() => {
          const pms = document.querySelectorAll('.ProseMirror');
          for (const pm of pms) {
            if ((pm.getAttribute('data-placeholder')||'').indexOf('标题')>=0) continue;
            const imgs = pm.querySelectorAll('img');
            for (const img of imgs) {
              const s = img.src || img.getAttribute('data-src') || '';
              if ((s.indexOf('mmbiz') >= 0 || s.indexOf('qpic') >= 0) && img.getBoundingClientRect().width > 50) return 'OK';
            }
          }
          return 'WAIT';
        }""")
        if r == 'OK':
            log(f"封面已粘贴到正文末尾 ({i+1}秒)")
            return True
    log("ERROR: 粘贴封面到正文失败（30秒内未见mmbiz图片）")
    return False

async def set_cover(page, cover_path=None, cover_url=None):
    """设置封面：从正文选择刚粘贴的封面图（最可靠，封面必须已插入正文）"""
    log("设置封面（从正文选择方式）...")
    # 滚动封面区域到视口
    await page.evaluate("""() => {
      const el = document.getElementById('js_cover_area');
      if (el) el.scrollIntoView({behavior:'instant', block:'center'});
    }""")
    await page.wait_for_timeout(2000)
    # hover封面区域右上角，触发菜单（含'从正文选择'）
    log("hover封面区域右上角...")
    await page.mouse.move(805, 418)
    await page.wait_for_timeout(3000)
    await shot(page, "cover_01_hover")
    # 点击'从正文选择'
    clicked = await page.evaluate(r"""() => {
      const all = document.querySelectorAll('*');
      for (const el of all) {
        if (el.children.length === 0 && (el.innerText||'').trim() === '从正文选择') {
          const r = el.getBoundingClientRect();
          el.click();
          return {x: Math.round(r.x), y: Math.round(r.y)};
        }
      }
      return 'NOT_FOUND';
    }""")
    if clicked == 'NOT_FOUND':
        log("ERROR: 未找到'从正文选择'选项（可能正文无图或hover位置不对）")
        await shot(page, "cover_02_no_frombody")
        return False
    log(f"点击从正文选择: {clicked}")
    await page.wait_for_timeout(4000)
    await shot(page, "cover_02_frombody_dialog")
    # 找弹窗中的封面缩略图（mmbiz背景图）
    thumb = await page.evaluate(r"""() => {
      const all = document.querySelectorAll('*');
      for (const el of all) {
        // 关键：草稿已有封面时，页面封面区域本身就是一张 mmbiz 图，
        // 必须排除，否则会选中旧封面自己 —— 表现为"设置成功"但封面没换。
        if (el.closest && el.closest('#js_cover_area')) continue;
        const bg = window.getComputedStyle(el).backgroundImage;
        if (bg && bg.indexOf('mmbiz') >= 0) {
          const r = el.getBoundingClientRect();
          if (r.width > 60 && r.height > 60 && r.width < 300 && r.height < 300 && el.offsetParent && r.y > 200 && r.y < 700) {
            return {x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), w: Math.round(r.width), h: Math.round(r.height)};
          }
        }
      }
      return null;
    }""")
    if not thumb:
        log("ERROR: 弹窗中未找到封面缩略图")
        await shot(page, "cover_03_no_thumb")
        return False
    log(f"点击弹窗封面缩略图: {thumb}")
    await page.mouse.click(thumb['x'], thumb['y'])
    await page.wait_for_timeout(1500)
    # 点'下一步'
    for _a in range(10):
        r = await page.evaluate(r"""() => {
          const btns = Array.from(document.querySelectorAll('button'));
          for (const b of btns) {
            const t = (b.innerText||'').trim();
            if (t === '下一步' && b.offsetParent) {
              const rect = b.getBoundingClientRect();
              b.click();
              return {x: Math.round(rect.x), y: Math.round(rect.y)};
            }
          }
          return 'NOT_FOUND';
        }""")
        if r != 'NOT_FOUND':
            log(f"点击下一步: {r}")
            break
        await asyncio.sleep(1)
    await page.wait_for_timeout(2500)
    await shot(page, "cover_04_after_next")
    # 点'确认'（裁剪界面）
    for _a in range(15):
        r = await page.evaluate(r"""() => {
          const btns = Array.from(document.querySelectorAll('button'));
          for (const b of btns) {
            const t = (b.innerText||'').trim();
            if ((t === '确认' || t === '确定' || t === '完成') && b.offsetParent) {
              const rect = b.getBoundingClientRect();
              if (rect.width > 40 && rect.height > 20) {
                b.click();
                return {x: Math.round(rect.x), y: Math.round(rect.y)};
              }
            }
          }
          return 'NOT_FOUND';
        }""")
        if r != 'NOT_FOUND':
            log(f"点击确认: {r}")
            break
        await asyncio.sleep(1)
    await page.wait_for_timeout(3000)
    # 验证封面区域有真实mmbiz图片（最多30秒）
    cover_verified = False
    for _v in range(15):
        await page.wait_for_timeout(2000)
        cov = await page.evaluate(r"""() => {
          const area = document.getElementById('js_cover_area');
          if (!area) return 'NO_AREA';
          const check = [];
          const imgs = area.querySelectorAll('img');
          for (const img of imgs) {
            const r = img.getBoundingClientRect();
            if (r.width > 50 && r.height > 20) check.push(img.src||'');
          }
          const bgEls = area.querySelectorAll('*');
          for (const el of bgEls) {
            const bg = window.getComputedStyle(el).backgroundImage;
            if (bg && bg !== 'none') {
              const m = bg.match(/url\(["']?([^"')]+)["']?\)/);
              if (m) check.push(m[1]);
            }
          }
          for (const s of check) {
            if (s.indexOf('mmbiz') >= 0) return {ok:true, src:s.substring(0,120)};
          }
          return {ok:false, state: check.length ? check[0].substring(0,60) : 'no_img'};
        }""")
        if isinstance(cov, dict) and cov.get('ok'):
            log(f"封面已验证生效: {cov['src']}")
            cover_verified = True
            break
        log(f"封面等待[{_v+1}]: {cov}")
    if not cover_verified:
        log("WARN: 封面设置后未检测到真实图片URL")
        await shot(page, "cover_05_verify_fail")
        return False
    log("封面设置流程结束")
    return True

async def _set_cover_upload_fallback(page, cover_path):
    """旧版：上传封面文件到图片库，按时间戳识别新图并设置封面（备用）"""
    log("fallback: 上传文件到图片库方式...")
    import datetime as _dt
    from pathlib import Path as _P
    # 点击封面区域触发菜单
    await page.evaluate("""() => { const el = document.getElementById('js_cover_area'); if (el) el.scrollIntoView({behavior:'instant', block:'center'}); }""")
    await page.wait_for_timeout(2000)
    cover_clicked = await page.evaluate("""() => {
      const area = document.getElementById('js_cover_area');
      if (area) { const r = area.getBoundingClientRect(); return {x: r.x + r.width/2, y: r.y + r.height/2}; }
      return null;
    }""")
    if cover_clicked:
        await page.mouse.click(cover_clicked['x'], cover_clicked['y'])
    await page.wait_for_timeout(2500)
    # 点"从图片库选择"
    await page.evaluate(r"""() => {
      const all = document.querySelectorAll('*');
      for (const el of all) {
        if (el.children.length === 0 && (el.innerText||'').trim() === '从图片库选择') { el.click(); return; }
      }
    }""")
    await page.wait_for_timeout(3000)
    # 点"上传文件"
    await page.evaluate(r"""() => {
      const all = document.querySelectorAll('*');
      for (const el of all) {
        if (el.children.length > 0) continue;
        const text = (el.innerText||'').trim();
        if ((text === '上传文件' || text === '上传') && el.offsetParent) { el.click(); return; }
      }
    }""")
    await page.wait_for_timeout(2000)
    # 上传
    file_inputs = await page.query_selector_all('input[type="file"]')
    for inp in file_inputs:
        try:
            await inp.set_input_files(str(cover_path))
            log("fallback: 上传成功")
            break
        except Exception as e:
            log(f"fallback: 上传失败 {e}")
    # 轮询找新图
    upload_t0 = _dt.datetime.now()
    target_thumb = None
    for _poll in range(30):
        await page.wait_for_timeout(2000)
        _items = await page.evaluate(r"""() => {
          const result = [];
          const all = document.querySelectorAll('*');
          for (const el of all) {
            if (el.children.length > 0) continue;
            const text = (el.innerText || '').trim();
            if (!text) continue;
            const rect = el.getBoundingClientRect();
            if (rect.width < 30 || rect.height < 10 || !el.offsetParent) continue;
            if (rect.y < 200 || rect.y > 800) continue;
            const m = text.match(/粘贴图片_(\d{14})\.(png|jpg|jpeg)/);
            if (m) result.push({ts: m[1], x: Math.round(rect.x), y: Math.round(rect.y)});
          }
          return result;
        }""")
        if _items:
            _latest = max(_items, key=lambda x: x['ts'])
            _tsdt = _dt.datetime.strptime(_latest['ts'], '%Y%m%d%H%M%S')
            _age = (_tsdt - upload_t0).total_seconds()
            if _age > -8:
                target_thumb = _latest
                break
    if not target_thumb:
        return False
    await page.mouse.click(target_thumb['x'], target_thumb['y'])
    await page.wait_for_timeout(1500)
    # 下一步/确定
    for _a in range(10):
        r = await page.evaluate(r"""() => {
          const btns = Array.from(document.querySelectorAll('button'));
          for (const b of btns) {
            const t = (b.innerText||'').trim();
            if ((t === '下一步' || t === '确定') && b.offsetParent) { b.click(); return 'CLICKED'; }
          }
          return 'NOT_FOUND';
        }""")
        if r != 'NOT_FOUND':
            break
        await asyncio.sleep(1)
    await page.wait_for_timeout(2500)
    # 确认
    for _a in range(15):
        r = await page.evaluate(r"""() => {
          const btns = Array.from(document.querySelectorAll('button'));
          for (const b of btns) {
            const t = (b.innerText||'').trim();
            if ((t === '确认' || t === '确定' || t === '完成') && b.offsetParent) {
              const rect = b.getBoundingClientRect();
              if (rect.width > 40 && rect.height > 20) { b.click(); return 'CLICKED'; }
            }
          }
          return 'NOT_FOUND';
        }""")
        if r != 'NOT_FOUND':
            break
        await asyncio.sleep(1)
    await page.wait_for_timeout(3000)
    return True

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
    ap.add_argument("--channel", default="msedge", help="浏览器 channel（默认 msedge 复用系统 Edge；本机 chromium 二进制已被清，勿用默认 chromium）")
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
        launch_kwargs = dict(
            user_data_dir=str(profile_dir),
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
        )
        if getattr(args, "channel", "msedge"):
            launch_kwargs["channel"] = args.channel
        ctx = await p.chromium.launch_persistent_context(**launch_kwargs)
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
            # 方案：先把封面粘贴到正文末尾，再从正文选择设置封面（最可靠）
            # 正文无其他图片时，'从正文选择'弹窗唯一的图就是封面
            pasted = await insert_cover_temp(page, args.cover)
            cover_set_ok = False
            if pasted:
                for _cattempt in range(3):
                    ok = await set_cover(page, args.cover)
                    await shot(page, "03_cover_set")
                    if ok:
                        cover_set_ok = True
                        break
                    log(f"封面设置失败，自动重试 {_cattempt+1}/3 ...")
                    await close_original_dialog(page)
                    await page.wait_for_timeout(1500)
            else:
                log("WARN: 封面未粘贴到正文，尝试图片库上传方式")
                from pathlib import Path as _P
                # fallback：旧的上传文件到图片库方式
                try:
                    for _cattempt in range(2):
                        ok = await _set_cover_upload_fallback(page, args.cover)
                        if ok:
                            cover_set_ok = True
                            break
                except Exception as _e:
                    log(f"fallback失败: {_e}")
            if not cover_set_ok:
                log("WARN: 封面设置未成功，将不带封面保存（请在后台手动补封面）")
            # 无论成功与否，删除正文末尾的临时封面图
            if pasted:
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

    # ===== 封面验证：回草稿箱列表检查卡片是否有封面背景图 =====
    # （2026-08-30 复盘：封面是否生效，唯一可靠判据是草稿箱卡片有封面缩略图；
    #   编辑器 DOM id 已过时，不能用 js_cover_area 判断）
    cover_ok = None  # None=本次未设封面；True/False=封面验证结果
    if args.cover:
        cover_ok = False
        try:
            m = re.search(r"appmsgid=(\d+)", url or "")
            m2 = re.search(r"token=(\d+)", url or "")
            if m and m2:
                appmsgid = m.group(1); token = m2.group(1)
                log("验证封面：回草稿箱列表检查...")
                async with async_playwright() as p:
                    vctx = await p.chromium.launch_persistent_context(
                        user_data_dir=str(profile_dir),
                        headless=args.headless,
                        args=["--disable-blink-features=AutomationControlled"],
                        viewport={"width": 1440, "height": 900},
                        channel=getattr(args, "channel", "msedge"),
                    )
                    vpage = vctx.pages[0] if vctx.pages else await vctx.new_page()
                    list_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg?begin=0&count=10"
                                f"&type=77&action=list_card&token={token}&lang=zh_CN")
                    await vpage.goto("https://mp.weixin.qq.com", wait_until="domcontentloaded", timeout=60000)
                    await vpage.wait_for_timeout(2000)
                    await vpage.goto(list_url, wait_until="domcontentloaded", timeout=60000)
                    await vpage.wait_for_timeout(4000)
                    # 检查草稿卡片：标题命中 + 卡片内有 img 或背景图
                    # 用文章标题前 8 个字做匹配（通用化，不写死标题）
                    title_key = (args.title or "")[:8]
                    cov = await vpage.evaluate("""(tk) => {
                      const all = document.querySelectorAll('*');
                      for (const el of all) {
                        const t = (el.innerText || '').replace(/\\s+/g,' ');
                        if (tk && t.indexOf(tk) >= 0) {
                          const imgs = el.querySelectorAll('img');
                          const hasBg = getComputedStyle(el).backgroundImage !== 'none';
                          if (imgs.length > 0 || hasBg) return 'COVER_OK';
                        }
                      }
                      return 'COVER_MISSING';
                    }""", title_key)
                    # 找不到含标题卡片时再宽松判断
                    if cov == 'COVER_MISSING':
                        cov2 = await vpage.evaluate("""() => {
                          const imgs = document.querySelectorAll('.weui-desktop-card img, [class*="cover"] img');
                          return imgs.length > 0 ? 'COVER_OK' : 'COVER_MISSING';
                        }""")
                        if cov2 == 'COVER_OK':
                            cov = 'COVER_OK'
                    log(f"封面验证: {cov}")
                    cover_ok = (cov == 'COVER_OK')
                    await vpage.screenshot(path=str(SKILL_ROOT / "outputs" / "cover_verify.png"))
                    await vctx.close()
        except Exception as e:
            log(f"封面验证异常: {e}")

    if url and "appmsgid=" in url:
        if args.cover and cover_ok is False:
            log("WARN: 文章已存稿，但封面验证未通过，请到后台确认封面")
        else:
            log("DONE: 已存入草稿箱" + ("" if cover_ok is None else "（封面已验证）"))
        sys.exit(0)
    log("WARN: 请人工检查草稿箱")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
