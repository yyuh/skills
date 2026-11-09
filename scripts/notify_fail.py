# -*- coding: utf-8 -*-
"""存稿失败告警：写标记文件 + 弹桌面通知（toast，失败回落 MessageBox）。

被 publish_full_v2.py 与各批量脚本调用。单文件、零依赖（只依赖系统 powershell）。
用法（独立测试）：
  python scripts/notify_fail.py "登录失效：扫码超时"
设置环境变量 NOTIFY_SKIP_POPUP=1 可只写标记文件、不弹窗（用于测试）。
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
FLAG = SKILL_ROOT / "outputs" / "LAST_PUBLISH_FAILED.json"


def notify_failure(reason, source="notify_fail.py"):
    """记录失败标记并弹桌面通知。本函数绝不抛异常（避免影响主流程退出码）。"""
    # 1) 写失败标记（供定时任务 / 其他 Agent 检测）
    try:
        rec = {}
        if FLAG.exists():
            try:
                rec = json.loads(FLAG.read_text(encoding="utf-8"))
            except Exception:
                rec = {}
        entry = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "reason": reason,
            "source": source,
        }
        rec["last_failure"] = entry
        rec.setdefault("history", []).append(entry)
        rec["history"] = rec["history"][-20:]
        FLAG.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[notify] 写标记失败: {e}", flush=True)

    # 2) 弹桌面通知（非阻塞；测试时可设 NOTIFY_SKIP_POPUP=1 跳过）
    if os.environ.get("NOTIFY_SKIP_POPUP") == "1":
        return
    try:
        ps = SCRIPT_DIR / "notify_toast.ps1"
        body = (reason or "")[:200]
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-File", str(ps),
             "-Title", "公众号存稿失败", "-Body", body],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            startupinfo=si, close_fds=True,
        )
    except Exception as e:
        print(f"[notify] 弹窗失败: {e}", flush=True)


if __name__ == "__main__":
    reason = sys.argv[1] if len(sys.argv) > 1 else "存稿失败，请检查。"
    notify_failure(reason)
