"""
微信 GUI 自动化 — 平台抽象基类

定义所有平台实现必须提供的接口。
macOS 实现见 wechat_ui_mac.py，Windows 实现见 wechat_ui_win.py。

图像理解由 AI 通过环境内置的 view_image 工具完成，脚本只负责截图。
"""

import sys
import time
import random
from abc import ABC, abstractmethod


# 跨平台的修饰键名称
MODIFIER_KEY = "command" if sys.platform == "darwin" else "ctrl"


class WeChatUIBase(ABC):
    """微信 GUI 操控抽象基类"""

    # ── 微信状态检查 ──

    @abstractmethod
    def is_wechat_installed(self) -> bool:
        """检查微信是否已安装"""
        ...

    @abstractmethod
    def is_wechat_running(self) -> bool:
        """检查微信进程是否在运行"""
        ...

    @abstractmethod
    def launch_wechat(self):
        """启动微信"""
        ...

    @abstractmethod
    def activate_wechat(self):
        """将微信窗口激活到前台"""
        ...

    @abstractmethod
    def hide_wechat(self):
        """将微信窗口隐藏到后台"""
        ...

    @abstractmethod
    def get_wechat_main_window(self) -> dict | None:
        """
        获取微信主窗口信息。
        返回 dict: {"id": .., "x": .., "y": .., "width": .., "height": .., "on_screen": bool}
        或 None（未找到窗口）。
        """
        ...

    # ── 截图 ──

    @abstractmethod
    def take_screenshot_of_wechat(self) -> str:
        """截取微信窗口，返回截图文件路径"""
        ...

    @abstractmethod
    def take_screenshot_region(self, x: int, y: int, w: int, h: int) -> str:
        """截取屏幕指定区域（逻辑坐标），返回截图文件路径"""
        ...

    # ── 通讯录扫描 ──

    @abstractmethod
    def scan_contacts_screenshots(
        self, reset_to_top: bool = True, max_time: int = 240
    ) -> list[str]:
        """滚动通讯录并逐屏截图，返回截图文件路径列表。AI 通过 view_image 识别。"""
        ...

    # ── 消息发送 ──

    @abstractmethod
    def search_and_open_chat(self, contact_name: str) -> bool:
        """搜索联系人并打开聊天窗口"""
        ...

    @abstractmethod
    def send_message(self, message: str) -> bool:
        """在当前聊天窗口发送消息"""
        ...

    @abstractmethod
    def close_chat(self):
        """关闭当前聊天窗口 / 搜索面板，回到列表干净状态"""
        ...

    def screenshot_chat(self, contact_name: str, search_key: str = "") -> dict:
        """
        搜索联系人，打开聊天窗口，截图返回。

        Returns:
            {"found": True, "screenshot_path": "..."} 或
            {"found": False, "screenshot_path": ""}
        """
        actual_search = search_key.strip() if search_key else contact_name
        try:
            found = self.search_and_open_chat(actual_search)
            if not found:
                self.close_chat()
                return {"found": False, "screenshot_path": ""}
            time.sleep(0.5)
            path = self.take_screenshot_of_wechat()
            return {"found": True, "screenshot_path": path}
        except Exception as e:
            print(f"[错误] screenshot_chat {contact_name}: {e}")
            try:
                self.close_chat()
            except Exception:
                pass
            return {"found": False, "screenshot_path": ""}

    # ── 通用方法（跨平台） ──

    def send_greeting_to_contact(
        self, contact_name: str, message: str, search_key: str = ""
    ) -> str:
        """
        完整流程（每人一个完整循环）：
        激活微信 → 搜索联系人 → 发送消息 → 验证 → 关闭聊天 → 隐藏微信
        返回状态: "sent" / "not_found" / "failed"
        """
        actual_search = search_key.strip() if search_key else contact_name
        try:
            # search_and_open_chat 内部会 activate_wechat
            found = self.search_and_open_chat(actual_search)
            if not found:
                self.close_chat()
                self.hide_wechat()
                return "not_found"

            success = self.send_message(message)
            self.close_chat()
            self.hide_wechat()
            return "sent" if success else "failed"

        except Exception as e:
            print(f"[错误] 发送给 {contact_name} 时出错: {e}")
            try:
                self.close_chat()
                self.hide_wechat()
            except Exception:
                pass
            return "failed"

    def check_wechat_status(self) -> dict:
        """检查微信状态，返回结果字典（含登录状态判断）"""
        result = {
            "installed": self.is_wechat_installed(),
            "running": False,
            "logged_in": False,
            "window_info": None,
        }

        if result["installed"]:
            result["running"] = self.is_wechat_running()

            if not result["running"]:
                try:
                    self.launch_wechat()
                    result["running"] = self.is_wechat_running()
                except Exception:
                    pass

            if result["running"]:
                try:
                    win = self.get_wechat_main_window()
                    if win:
                        result["window_info"] = {
                            "id": win.get("id"),
                            "x": win["x"],
                            "y": win["y"],
                            "width": win["width"],
                            "height": win["height"],
                            "on_screen": win.get("on_screen", True),
                        }
                        # 通过窗口尺寸判断登录状态（基础方案，子类可覆写）
                        result["logged_in"] = self._check_logged_in(win)
                        if not result["logged_in"]:
                            print(
                                f"[检查] 微信窗口({win['width']}x{win['height']})，"
                                "判定为未登录",
                                file=sys.stderr,
                            )
                except Exception:
                    pass

        return result

    def _check_logged_in(self, win: dict) -> bool:
        """
        判断微信是否已登录。默认用窗口尺寸判断，子类可覆写。
        登录界面（二维码）窗口较小（约 280x400），主界面通常更大。
        阈值设为 400x450，兼容用户缩小过的主窗口。
        """
        return win["width"] > 400 and win["height"] > 450

    @staticmethod
    def random_delay():
        """随机延迟 1-10 秒"""
        delay = random.randint(1, 10)
        print(f"  等待 {delay} 秒...")
        time.sleep(delay)
