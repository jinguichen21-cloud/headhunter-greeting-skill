"""
微信 GUI 自动化 — 平台路由层

根据当前操作系统自动加载对应的平台实现。
- macOS → wechat_ui_mac.WeChatUIMac
- Windows → wechat_ui_win.WeChatUIWin

对外暴露函数接口，保持 main.py 等调用方无需修改。
"""

import sys

# ── 根据平台加载实现 ──

if sys.platform == "darwin":
    from scripts.wechat_ui_mac import WeChatUIMac as _WeChatUIImpl
elif sys.platform == "win32":
    from scripts.wechat_ui_win import WeChatUIWin as _WeChatUIImpl
else:
    raise RuntimeError(f"不支持的操作系统: {sys.platform}（仅支持 macOS 和 Windows）")

# 全局单例
_instance = _WeChatUIImpl()


# ── 导出函数接口 ──


def check_wechat_status() -> dict:
    return _instance.check_wechat_status()


def take_screenshot_of_wechat() -> str:
    return _instance.take_screenshot_of_wechat()


def scan_contacts_screenshots(
    reset_to_top: bool = True, max_time: int = 240
) -> list[str]:
    return _instance.scan_contacts_screenshots(
        reset_to_top=reset_to_top, max_time=max_time
    )


def send_greeting_to_contact(
    contact_name: str, message: str, search_key: str = ""
) -> str:
    return _instance.send_greeting_to_contact(contact_name, message, search_key)


def random_delay():
    _instance.random_delay()


def activate_wechat():
    _instance.activate_wechat()


def hide_wechat():
    _instance.hide_wechat()


def close_chat():
    _instance.close_chat()


def screenshot_chat(contact_name: str, search_key: str = "") -> dict:
    return _instance.screenshot_chat(contact_name, search_key)
