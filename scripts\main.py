#!/usr/bin/env python3
"""
猎头节日问候 - 微信自动化主控脚本（跨平台：macOS / Windows）

使用方式（由 AI 通过 Bash 工具调用）：

  python scripts/main.py check                     # 检查微信状态
  python scripts/main.py send "名称" "内容" "节日"   # 发送单条消息
  python scripts/main.py screenshot                 # [WIP] 截图微信窗口
  python scripts/main.py screenshot_chat "关键词"   # [WIP] 搜索联系人并截图
  python scripts/main.py scan_contacts              # [WIP] 扫描通讯录
  python scripts/main.py db_info                    # [WIP] 查看候选人数据库状态
  python scripts/main.py db_list                    # [WIP] 列出候选人
  python scripts/main.py db_clear                   # [WIP] 清除候选人数据库
"""

import sys
import os
import json
import time
import random

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SKILL_DIR)

from scripts.wechat_ui import (
    check_wechat_status,
    take_screenshot_of_wechat,
    scan_contacts_screenshots,
    send_greeting_to_contact,
    hide_wechat,
    screenshot_chat,
)
from scripts.candidates import (
    parse_candidate,
    determine_appellation,
    process_manual_candidates,
)
from scripts.contacts_cache import (
    load_cache,
    has_cache,
    get_cache_summary,
    get_cached_candidates,
    clear_cache,
)


def cmd_check():
    status = check_wechat_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


def cmd_screenshot():
    path = take_screenshot_of_wechat()
    print(json.dumps({"screenshot_path": path}, ensure_ascii=False))


def cmd_screenshot_chat(search_key: str):
    """搜索联系人，打开聊天窗口并截图。"""
    result = screenshot_chat(search_key, search_key)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_scan_contacts(continue_scan: bool = False):
    """扫描通讯录，返回截图文件路径列表。"""
    screenshots = scan_contacts_screenshots(
        reset_to_top=not continue_scan,
        max_time=240,
    )
    result = {
        "total_screenshots": len(screenshots),
        "screenshots": screenshots,
        "continued": continue_scan,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_db_info():
    """查看候选人数据库状态。"""
    if not has_cache():
        print(json.dumps({"has_cache": False, "summary": "无缓存"}, ensure_ascii=False))
    else:
        cache = load_cache()
        print(
            json.dumps(
                {
                    "has_cache": True,
                    "scan_time": cache.get("scan_time", ""),
                    "candidates_count": len(cache.get("candidates", [])),
                    "summary": get_cache_summary(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )


def cmd_db_list():
    """列出候选人数据库中的候选人。"""
    candidates = get_cached_candidates()
    print(
        json.dumps(
            {"count": len(candidates), "candidates": candidates},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_db_clear():
    """清除候选人数据库。"""
    clear_cache()
    print(json.dumps({"cleared": True}, ensure_ascii=False))


def cmd_send(contact_name: str, message: str, festival: str = ""):
    # 发送前强制检查微信状态（代码层面保障，即使 AI 跳过 check 也能拦截）
    status_check = check_wechat_status()
    if not status_check.get("installed"):
        print(
            json.dumps(
                {
                    "error": "wechat_not_installed",
                    "message": "微信未安装，请先前往 https://weixin.qq.com/ 下载并安装",
                    "status": "blocked",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if not status_check.get("logged_in"):
        print(
            json.dumps(
                {
                    "error": "wechat_not_logged_in",
                    "message": "微信未登录，请先登录微信后再发送",
                    "status": "blocked",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    status = send_greeting_to_contact(contact_name, message)
    result = {
        "candidate": contact_name,
        "message": message,
        "festival": festival,
        "status": status,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    # 不在这里 hide_wechat()，由 AI 在所有候选人发完后调用 hide 命令
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_hide():
    """隐藏微信窗口到后台。"""
    hide_wechat()
    print(json.dumps({"status": "hidden"}, ensure_ascii=False))


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/main.py <command> [args...]")
        print("命令: check | send | hide")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "check":
        cmd_check()
    elif cmd == "screenshot":
        cmd_screenshot()
    elif cmd == "screenshot_chat":
        if len(sys.argv) < 3:
            print('用法: python scripts/main.py screenshot_chat "联系人搜索关键词"')
            sys.exit(1)
        cmd_screenshot_chat(sys.argv[2])
    elif cmd == "scan_contacts":
        continue_flag = "--continue" in sys.argv
        cmd_scan_contacts(continue_scan=continue_flag)
    elif cmd == "db_info":
        cmd_db_info()
    elif cmd == "db_list":
        cmd_db_list()
    elif cmd == "db_clear":
        cmd_db_clear()
    elif cmd == "send":
        if len(sys.argv) < 4:
            print('用法: python scripts/main.py send "名称" "内容" ["节日"]')
            sys.exit(1)
        cmd_send(
            sys.argv[2],
            sys.argv[3],
            sys.argv[4] if len(sys.argv) > 4 else "",
        )
    elif cmd == "hide":
        cmd_hide()
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
