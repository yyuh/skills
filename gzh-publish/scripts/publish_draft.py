#!/usr/bin/env python3
"""公众号草稿存稿（UI 点击导航版）。

相比旧版「拼 token URL」，本版登录后通过点击菜单进入编辑器，
不依赖 token，更稳定。

流程：
  打开 mp.weixin.qq.com → 检测登录
    未登录 + 无头(自动化)：退出码 2（NEED-LOGIN），由调用方提示用户扫码
    未登录 + 有头(交互)  ：截图二维码 → 等扫码（最多 5 分钟）→ 登录后继续
    已登录              ：直接进入导航
  导航：内容管理 → 图文素材 → 新的创作 → 写新图文（每步 2s 等待 + 截图）
  --test 模式：到「写新图文」编辑器打开即停，报告 TEST_OK
  完整模式  ：注入正文 → 填标题 → 保存草稿

每步进度写入 outputs/publish_progress.log（实时 flush），并截图存 outputs/step_*.png。
依赖：playwright（pip install playwright && playwright install chromium）
"""
import argparse
import base64
import os
import sys
import time
from pathlib import Path

# skill 根目录（scripts/ 的上一级），所有运行时产物基于它解析，
# 确保无论从哪个 cwd 调用脚本，outputs / 登录态缓存都落在 skill 目录内。
SKILL_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_FILE = None


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if PROGRESS_FILE:
        try:
            with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
        except Exception:
            pass


def shot(page, name):
    path = str(SKILL_ROOT / "outputs" / f"step_{name}.png")
    try:
        page.screenshot(path=path, full_page=False)
        log(f"截图 → {path}")
    except Exception as e:
        log(f"截图 {name} 失败: {e}")
    return path


def is_logged_in(page):
    """DOM 文本判定：登录后有「草稿箱/图文素材/内容管理」，登录页有「扫码」。"""
    try:
        txt = page.inner_text("body", timeout=5000)
    except Exception:
        return False
    has_qr = ("扫码" in txt) or ("扫描二维码" in txt)
    has_console = ("草稿箱" in txt) or ("图文素材" in txt) or ("内容管理" in txt)
    return has_console and not has_qr


def click_text(page, text, step_name, timeout=10000):
    loc = page.locator(f"text={text}").first
    try:
        loc.wait_for(state="visible", timeout=timeout)
        loc.click(timeout=5000)
        log(f"{step_name}: 点击「{text}」成功")
        return True
    except Exception as e:
        log(f"{step_name}: 点击「{text}」失败: {e}")
        return False


def inject_html(page, html):
    """整段 base64 + 合成 paste 事件注入正文 ProseMirror。"""
    b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
    ok = page.evaluate("""(b64) => {
      const html = decodeURIComponent(escape(atob(b64)));
      const pms = document.querySelectorAll('.ProseMirror');
      let target = null;
      for (const pm of pms) {
        const ph = pm.getAttribute('data-placeholder') || '';
        if (ph.indexOf('标题') < 0) { target = pm; break; }
      }
      if (!target) return 'NO-PM';
      target.focus();
      const range = document.createRange();
      range.selectNodeContents(target);
      range.collapse(false);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      const dt = new DataTransfer();
      dt.setData('text/html', html);
      dt.setData('text/plain', '');
      const evt = document.createEvent('Event');
      evt.initEvent('paste', true, true);
      Object.defineProperty(evt, 'clipboardData', { get: () => dt });
      target.dispatchEvent(evt);
      return 'LEN:' + target.innerText.length;
    }""", b64)
    return ok


def fill_title(page, title):
    b64 = base64.b64encode(title.encode("utf-8")).decode("ascii")
    return page.evaluate("""(b64) => {
      const val = decodeURIComponent(escape(atob(b64)));
      const tas = document.querySelectorAll('textarea');
      let target = null;
      for (const ta of tas) {
        if ((ta.placeholder || '').indexOf('标题') >= 0) { target = ta; break; }
      }
      if (!target) return 'NO-TA';
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(target, val);
      target.dispatchEvent(new Event('input', {bubbles:true}));
      target.dispatchEvent(new Event('change', {bubbles:true}));
      return target.value;
    }""", b64)


def save_draft(page):
    """点保存为草稿，并处理「无封面也要保存？」确认弹窗。"""
    page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) {
        if ((b.innerText || '').indexOf('保存为草稿') >= 0) { b.click(); return; }
      }
    }""")
    time.sleep(1.5)
    # 处理可能弹出的确认框（「确定」/「仍要保存」/「确认」等）
    handled = page.evaluate("""() => {
      // 找可见的弹窗/对话框
      const cands = document.querySelectorAll(
        '.weui-dialog, [role="dialog"], .dialog, [class*="dialog"], [class*="modal"], [class*="Dialog"], [class*="Modal"]'
      );
      for (const d of cands) {
        if (!d.offsetParent) continue;
        const btns = d.querySelectorAll('button, a');
        for (const b of btns) {
          const t = (b.innerText || '').trim();
          if (t === '确定' || t === '确认' || t === 'OK' || t.indexOf('仍要保存') >= 0) {
            b.click();
            return t;
          }
        }
      }
      return null;
    }""")
    log(f"保存确认: {handled}")
    time.sleep(3)
    return page.url


def main():
    global PROGRESS_FILE
    ap = argparse.ArgumentParser()
    ap.add_argument("html", help="已校验的正文 HTML 路径")
    ap.add_argument("--title", required=True)
    ap.add_argument("--account", default="硅基研究员")
    ap.add_argument("--headful", action="store_true", help="有头模式（交互扫码用）")
    ap.add_argument("--test", action="store_true", help="测试模式：跑到打开编辑器即停")
    ap.add_argument("--profile-dir", default=".gzh-profile-dir",
                    help="持久化浏览器 profile 目录（复用登录态，相对 skill 根）")
    ap.add_argument("--progress", default=None,
                    help="进度日志路径（默认写到 skill 根 outputs/publish_progress.log）")
    args = ap.parse_args()

    # 相对路径统一基于 skill 根解析，保证自包含
    profile_dir = Path(args.profile_dir)
    if not profile_dir.is_absolute():
        profile_dir = SKILL_ROOT / profile_dir
    if args.progress is None:
        PROGRESS_FILE = str(SKILL_ROOT / "outputs" / "publish_progress.log")
    else:
        PROGRESS_FILE = args.progress
    try:
        Path(PROGRESS_FILE).write_text("", encoding="utf-8")
        Path(PROGRESS_FILE).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    log("==== 启动存稿脚本（UI 点击导航版）====")
    if not Path(args.html).is_file():
        log(f"ERR: 找不到 HTML: {args.html}")
        sys.exit(1)
    html = Path(args.html).read_text(encoding="utf-8")
    log(f"正文已加载: {len(html)} 字符")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("ERR: 缺 playwright，请 pip install playwright && playwright install chromium")
        sys.exit(1)

    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        log("启动持久化浏览器上下文...")
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=not args.headful,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # 1. 打开后台
        log("打开 https://mp.weixin.qq.com")
        page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        time.sleep(2)
        shot(page, "01_home")

        # 2. 登录检测
        log("检测登录状态...")
        if is_logged_in(page):
            log("已登录，直接进入导航")
        else:
            if not args.headful:
                log("NEED-LOGIN: 未登录，自动化停止。"
                    "请人工用 --headful 扫码登录一次（cookie 会存进 profile 目录复用）。")
                ctx.close()
                sys.exit(2)
            log("未登录，截图二维码")
            qr_path = str(SKILL_ROOT / "outputs" / "login_qr.png")
            page.wait_for_timeout(2000)
            try:
                page.screenshot(path=qr_path, full_page=False)
                log(f"QR-READY: {qr_path}")
            except Exception as e:
                log(f"二维码截图失败: {e}")
            log("等待扫码登录（最多 5 分钟，扫到自动继续）...")
            ok = False
            for i in range(150):  # 每 2s 一次，共 300s
                time.sleep(2)
                if is_logged_in(page):
                    ok = True
                    break
                if i % 15 == 14:
                    log(f"仍在等待扫码... ({(i+1)*2}s)")
            if not ok:
                log("ERR: 5 分钟内未完成扫码，退出")
                ctx.close()
                sys.exit(1)
            log("扫码登录成功")
            time.sleep(2)
            shot(page, "02_after_login")

        # 3. 导航：登录后直接到主页「新的创作」→「文章」
        # 当前公众号后台 UI：主页有「新的创作」面板，第一项「文章」= 写新图文。
        log("---- 进入编辑器 ----")
        page.goto("https://mp.weixin.qq.com", wait_until="networkidle", timeout=60000)
        time.sleep(2)
        shot(page, "03_home_for_create")
        # 点「文章」：先点它的父级卡片（带点击处理的是容器，不是文字叶）；
        # 点不开就用页面里的 token 直跳编辑器 URL 兜底
        import re as _re
        clicked = page.evaluate("""() => {
          const blocks = document.querySelectorAll('div, section');
          for (const b of blocks) {
            const t = b.textContent || '';
            if (!t.includes('新的创作') || !t.includes('文章') || t.length > 300) continue;
            const all = b.querySelectorAll('div');
            for (const d of all) {
              const dt = (d.textContent || '').trim();
              if (dt === '文章' && d.children.length <= 1) {
                const item = d.parentElement || d;
                item.click();
                return 'CLICKED_ITEM';
              }
            }
            for (const d of all) {
              if ((d.textContent || '').trim() === '文章') { d.click(); return 'CLICKED_LEAF'; }
            }
          }
          return 'NO-ARTICLE';
        }""")
        log(f"点击文章: {clicked}")
        if clicked == "NO-ARTICLE":
            log("ERR: 主页「新的创作」里找不到「文章」入口")
            ctx.close()
            sys.exit(1)
        time.sleep(5)
        probe = page.evaluate("""() => ({
          pm: document.querySelectorAll('.ProseMirror').length,
          ta: document.querySelectorAll('textarea').length,
          url: location.href
        })""")
        log(f"点击后探测: {probe}")
        if probe.get("pm", 0) == 0 and probe.get("ta", 0) == 0:
            # 兜底：抓 token 直跳编辑器
            log("点击未触发编辑器，尝试用 token 直跳...")
            token = None
            m = _re.search(r"token=(\d+)", probe.get("url", ""))
            if m:
                token = m.group(1)
            if not token:
                for p in ctx.pages:
                    m = _re.search(r"token=(\d+)", p.url)
                    if m:
                        token = m.group(1)
                        break
            if token:
                editor_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg"
                              f"?t=media/appmsg_edit_v2&action=edit&isNew=1"
                              f"&type=10&lang=zh_CN&token={token}")
                log(f"直跳编辑器: {editor_url}")
                page.goto(editor_url, wait_until="networkidle", timeout=60000)
                time.sleep(5)
                if len(ctx.pages) > 1:
                    page = ctx.pages[-1]
                    log(f"切换到新标签页（共 {len(ctx.pages)} 个）")
                    try:
                        page.wait_for_load_state("networkidle", timeout=60000)
                    except Exception:
                        pass
                time.sleep(2)
                probe = page.evaluate("""() => ({
                  pm: document.querySelectorAll('.ProseMirror').length,
                  ta: document.querySelectorAll('textarea').length,
                  url: location.href
                })""")
                log(f"直跳后探测: {probe}")
            else:
                log("ERR: 找不到 token，无法兜底")
                ctx.close()
                sys.exit(1)
        shot(page, "04_editor")
        if probe.get("pm", 0) == 0 and probe.get("ta", 0) == 0:
            log("ERR: 编辑器确实没打开，请看 outputs/step_04_editor.png")
            ctx.close()
            sys.exit(1)
        log("TEST_OK: 编辑器已打开")

        if args.test:
            log("==== 测试模式结束，不注入不保存 ====")
            ctx.close()
            sys.exit(0)

        # 4. 注入正文
        log("注入正文...")
        try:
            inj = inject_html(page, html)
            log(f"INJECT: {inj}")
        except Exception as e:
            log(f"INJECT-ERR: {e}")
            inj = None
        time.sleep(2)
        # 5. 填标题
        log("填标题...")
        try:
            t = fill_title(page, args.title)
            log(f"TITLE: {t}")
        except Exception as e:
            log(f"TITLE-ERR: {e}")
        time.sleep(2)
        # 6. 保存草稿
        log("保存草稿...")
        try:
            url = save_draft(page)
            log(f"SAVED-URL: {url}")
        except Exception as e:
            log(f"SAVE-ERR: {e}")
            url = ""
        time.sleep(2)
        ctx.close()

    if url and "appmsgid=" in url:
        log("DONE: 已存入草稿箱")
        sys.exit(0)
    log("WARN: URL 未见 appmsgid，请人工检查草稿箱")
    sys.exit(0)


if __name__ == "__main__":
    main()
