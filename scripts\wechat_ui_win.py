"""
微信 GUI 自动化 — Windows 实现

通过 PyAutoGUI + pywin32 实现：
- win32gui 获取窗口信息
- PIL.ImageGrab 截图
- PyAutoGUI 模拟键鼠操作

截图后由 AI 通过环境内置的 view_image 工具识别内容。

依赖（Windows）：
  pip install pyautogui pillow pyperclip pywin32 psutil
"""

import subprocess
import time
import os
import sys
import tempfile

import pyautogui
import pyperclip
from PIL import Image, ImageGrab

from scripts.wechat_ui_base import WeChatUIBase, MODIFIER_KEY

# PyAutoGUI 安全设置
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

# Windows 微信常量（兼容 WeChat 和 Weixin 两个版本）
WECHAT_PROCESS_NAMES = ["WeChat.exe", "Weixin.exe"]
WECHAT_WINDOW_CLASSES = ["WeChatMainWndForPC", "WeixinMainWndForPC"]
WECHAT_WINDOW_TITLES = ["微信", "Weixin"]

# 常见安装路径（两个版本）
WECHAT_DEFAULT_PATHS = [
    os.path.expandvars(r"%ProgramFiles%\Tencent\WeChat\WeChat.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Tencent\WeChat\WeChat.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tencent\WeChat\WeChat.exe"),
    os.path.expandvars(r"%ProgramFiles%\Tencent\Weixin\Weixin.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Tencent\Weixin\Weixin.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tencent\Weixin\Weixin.exe"),
]


def _find_wechat_exe() -> str | None:
    """查找微信可执行文件路径（兼容 WeChat 和 Weixin）"""
    for p in WECHAT_DEFAULT_PATHS:
        if os.path.exists(p):
            return p
    # 注册表查找
    try:
        import winreg

        for reg_key in [r"Software\Tencent\WeChat", r"Software\Tencent\Weixin"]:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_key)
                install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                winreg.CloseKey(key)
                for exe_name in ["WeChat.exe", "Weixin.exe"]:
                    exe = os.path.join(install_path, exe_name)
                    if os.path.exists(exe):
                        return exe
            except Exception:
                continue
    except ImportError:
        pass
    # where 命令查找
    for exe_name in ["WeChat.exe", "Weixin.exe"]:
        result = subprocess.run(["where", exe_name], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")[0].strip()
    return None


class WeChatUIWin(WeChatUIBase):
    def __init__(self):
        self._wechat_exe = _find_wechat_exe()

    @staticmethod
    def _is_wechat_title(title: str) -> bool:
        """判断窗口标题是否属于微信"""
        return title in WECHAT_WINDOW_TITLES or any(
            t in title for t in WECHAT_WINDOW_TITLES
        )

    # ── 状态检查 ──

    def is_wechat_installed(self) -> bool:
        return self._wechat_exe is not None

    def is_wechat_running(self) -> bool:
        try:
            import psutil

            for proc in psutil.process_iter(["name"]):
                name = (proc.info["name"] or "").lower()
                if name in [p.lower() for p in WECHAT_PROCESS_NAMES]:
                    return True
            return False
        except ImportError:
            for proc_name in WECHAT_PROCESS_NAMES:
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {proc_name}"],
                    capture_output=True,
                    text=True,
                )
                if proc_name.lower() in result.stdout.lower():
                    return True
            return False

    def launch_wechat(self):
        if self._wechat_exe:
            os.startfile(self._wechat_exe)
        else:
            # 尝试两个可执行名
            for exe in ["Weixin.exe", "WeChat.exe"]:
                try:
                    subprocess.Popen([exe])
                    break
                except FileNotFoundError:
                    continue
        time.sleep(5)

    def activate_wechat(self):
        try:
            import win32gui
            import win32con

            hwnd = self._find_wechat_hwnd()
            if hwnd:
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.5)
        except ImportError:
            print("[警告] 未安装 pywin32，无法可靠激活窗口", file=sys.stderr)

    def hide_wechat(self):
        """将微信窗口最小化到任务栏。"""
        try:
            import win32gui
            import win32con

            hwnd = self._find_wechat_hwnd()
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                time.sleep(0.3)
        except ImportError:
            pass

    def _find_wechat_hwnd(self) -> int | None:
        """查找微信主窗口句柄（优先找最大的可见窗口）"""
        try:
            import win32gui

            candidates = []

            def enum_callback(hwnd, _):
                if not win32gui.IsWindowVisible(hwnd):
                    return
                title = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                if title in WECHAT_WINDOW_TITLES or class_name in WECHAT_WINDOW_CLASSES:
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if w > 50 and h > 50 and rect[0] > -10000:
                        candidates.append({"hwnd": hwnd, "width": w, "height": h})

            win32gui.EnumWindows(enum_callback, None)
            if not candidates:
                return None
            candidates.sort(key=lambda c: c["width"] * c["height"], reverse=True)
            return candidates[0]["hwnd"]
        except ImportError:
            return None

    def _check_logged_in(self, win: dict) -> bool:
        """
        覆写父类方法。
        Windows 微信（WeChat/Weixin）登录检测：
        - 登录窗口尺寸通常较小（约 280x400 或 350x500）
        - 已登录主界面通常 > 500x600
        - 新版 Weixin 使用 Web 技术，子控件数量可能为 0，不能依赖子控件判断
        - 因此主要靠尺寸判断，阈值设为 500x600
        """
        is_large = win["width"] > 500 and win["height"] > 600
        print(
            f"[检查] 微信窗口 {win['width']}x{win['height']}，"
            f"判定为{'已登录' if is_large else '未登录'}",
            file=sys.stderr,
        )
        return is_large

    def get_wechat_main_window(self) -> dict | None:
        try:
            import win32gui

            hwnd = self._find_wechat_hwnd()
            if not hwnd:
                return None
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            # 过滤异常尺寸（最小化窗口等）
            if w < 50 or h < 50:
                return None
            return {
                "id": hwnd,
                "x": rect[0],
                "y": rect[1],
                "width": w,
                "height": h,
                "on_screen": win32gui.IsWindowVisible(hwnd),
            }
        except ImportError:
            return None

    # ── 截图 ──

    def take_screenshot_of_wechat(self) -> str:
        self.activate_wechat()
        time.sleep(0.5)
        filepath = os.path.join(tempfile.gettempdir(), "wechat_screenshot.png")
        win = self.get_wechat_main_window()
        if win:
            bbox = (
                win["x"],
                win["y"],
                win["x"] + win["width"],
                win["y"] + win["height"],
            )
            img = ImageGrab.grab(bbox=bbox)
            img.save(filepath)
            return filepath
        img = ImageGrab.grab()
        img.save(filepath)
        return filepath

    def _screenshot_wechat_window(self, filename: str = "wechat_screenshot.png") -> str:
        """截图微信窗口（不 activate）。"""
        filepath = os.path.join(tempfile.gettempdir(), filename)
        win = self.get_wechat_main_window()
        if win:
            bbox = (
                win["x"],
                win["y"],
                win["x"] + win["width"],
                win["y"] + win["height"],
            )
            img = ImageGrab.grab(bbox=bbox)
            img.save(filepath)
            return filepath
        img = ImageGrab.grab()
        img.save(filepath)
        return filepath

    def take_screenshot_region(self, x: int, y: int, w: int, h: int) -> str:
        region_path = os.path.join(tempfile.gettempdir(), "region_crop.png")
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        img.save(region_path)
        return region_path

    # ── 通讯录扫描（截图模式） ──

    def scan_contacts_screenshots(
        self, reset_to_top: bool = True, max_time: int = 240
    ) -> list[str]:
        """滚动通讯录并逐屏截图，返回截图文件路径列表。"""
        import time as _time

        start = _time.time()

        self.activate_wechat()
        self._open_contacts_panel()
        time.sleep(0.5)
        win = self.get_wechat_main_window()
        if not win:
            raise RuntimeError("无法获取微信窗口信息")

        screenshots = []
        pyautogui.moveTo(win["x"] + 200, win["y"] + int(win["height"] * 0.7))

        if reset_to_top:
            for _ in range(30):
                pyautogui.scroll(10)
            time.sleep(0.5)

        # 截第一屏
        path = self._screenshot_wechat_window("wechat_contacts_0000.png")
        screenshots.append(path)

        same_count = 0
        last_size = None
        round_num = 0

        while True:
            round_num += 1

            elapsed = _time.time() - start
            if elapsed > max_time:
                print(f"[扫描] 达到时间上限 {max_time}s", file=sys.stderr)
                break

            pyautogui.scroll(-10)
            time.sleep(0.15)

            fname = f"wechat_contacts_{round_num:04d}.png"
            path = self._screenshot_wechat_window(fname)
            current_size = os.path.getsize(path)
            if last_size is not None and current_size == last_size:
                same_count += 1
                if same_count >= 3:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    break
            else:
                same_count = 0
            last_size = current_size
            screenshots.append(path)

        print(f"[扫描] 完成, 共 {len(screenshots)} 张截图", file=sys.stderr)
        return screenshots

    def _open_contacts_panel(self):
        self.activate_wechat()
        time.sleep(0.3)
        win = self.get_wechat_main_window()
        if not win:
            raise RuntimeError("无法获取微信窗口信息")
        pyautogui.click(win["x"] + 35, win["y"] + 120)
        time.sleep(0.5)

    def _get_wechat_window_ids(self) -> list[int]:
        """获取所有微信窗口句柄列表。"""
        try:
            import win32gui

            result = []

            def enum_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    class_name = win32gui.GetClassName(hwnd)
                    if (
                        title in WECHAT_WINDOW_TITLES
                        or class_name in WECHAT_WINDOW_CLASSES
                    ):
                        result.append(hwnd)

            win32gui.EnumWindows(enum_callback, None)
            return result
        except ImportError:
            return []

    def _get_foreground_window_info(self) -> dict | None:
        """获取当前最前端窗口的信息。"""
        try:
            import win32gui

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            return {
                "title": title,
                "hwnd": hwnd,
                "width": rect[2] - rect[0],
                "height": rect[3] - rect[1],
            }
        except ImportError:
            return None

    # ── 消息发送 ──

    def search_and_open_chat(self, contact_name: str) -> bool:
        """搜索联系人并打开聊天窗口，通过前端窗口检测候选人是否存在。"""
        self.activate_wechat()
        time.sleep(0.3)

        win = self.get_wechat_main_window()
        if not win:
            return False

        original_hwnd = win.get("id")
        original_width = win["width"]
        original_height = win["height"]

        pyautogui.hotkey(MODIFIER_KEY, "f")
        time.sleep(0.5)
        pyautogui.hotkey(MODIFIER_KEY, "a")
        time.sleep(0.1)
        pyperclip.copy(contact_name)
        pyautogui.hotkey(MODIFIER_KEY, "v")
        time.sleep(1.5)

        pyautogui.press("enter")
        time.sleep(0.8)

        # 检查最前端窗口
        front = self._get_foreground_window_info()
        if not front:
            pyautogui.press("escape")
            time.sleep(0.3)
            return False

        if not self._is_wechat_title(front["title"]):
            print(
                f"[发送] 搜索 '{contact_name}' 打开了非微信窗口（{front['title']}），关闭中",
                file=sys.stderr,
            )
            pyautogui.hotkey(MODIFIER_KEY, "w")
            time.sleep(0.5)
            self.activate_wechat()
            time.sleep(0.3)
            pyautogui.press("escape")
            time.sleep(0.3)
            return False

        if front["hwnd"] != original_hwnd:
            print(f"[发送] 搜索 '{contact_name}' 打开了新窗口，关闭中", file=sys.stderr)
            pyautogui.hotkey(MODIFIER_KEY, "w")
            time.sleep(0.5)
            pyautogui.press("escape")
            time.sleep(0.3)
            return False

        size_change = abs(front["width"] - original_width) + abs(
            front["height"] - original_height
        )
        if size_change > 100:
            print(
                f"[发送] 搜索 '{contact_name}' 窗口尺寸异常变化，关闭中",
                file=sys.stderr,
            )
            pyautogui.hotkey(MODIFIER_KEY, "w")
            time.sleep(0.5)
            pyautogui.press("escape")
            time.sleep(0.3)
            return False

        print(f"[发送] 搜索 '{contact_name}' 已进入聊天窗口", file=sys.stderr)
        return True

    def send_message(self, message: str) -> bool:
        """
        在当前聊天窗口发送消息。
        每个关键步骤前检查微信是否仍在前台，防止用户移动鼠标导致误操作。
        """
        win = self.get_wechat_main_window()
        if not win or not win.get("id"):
            return False
        original_hwnd = win["id"]

        # 步骤 1：点击输入框前，确认微信在前台
        if not self._ensure_wechat_focused(original_hwnd):
            return False
        input_x = win["x"] + win["width"] * 2 // 3
        input_y = win["y"] + win["height"] - 80
        pyautogui.click(input_x, input_y)
        time.sleep(0.3)

        # 步骤 2：粘贴前，确认微信仍在前台
        if not self._ensure_wechat_focused(original_hwnd):
            return False
        pyperclip.copy(message)
        pyautogui.hotkey(MODIFIER_KEY, "v")
        time.sleep(0.3)

        # 步骤 3：按 Enter 前，确认微信仍在前台
        if not self._ensure_wechat_focused(original_hwnd):
            return False
        pyautogui.press("enter")
        time.sleep(0.5)

        # 步骤 4：发送后确认
        front = self._get_foreground_window_info()
        if not front or not self._is_wechat_title(front["title"]):
            print("[发送] 发送后微信不在前台，消息可能未成功发送", file=sys.stderr)
            return False

        return True

    def _ensure_wechat_focused(self, expected_hwnd: int, max_retries: int = 2) -> bool:
        """确保微信在前台。如果不在则尝试激活，失败返回 False。"""
        for attempt in range(max_retries + 1):
            front = self._get_foreground_window_info()
            if front and front["hwnd"] == expected_hwnd:
                return True
            if attempt < max_retries:
                print(f"[发送] 微信不在前台，重新激活中", file=sys.stderr)
                self.activate_wechat()
                time.sleep(0.5)
        print("[发送] 无法将微信保持在前台，中止发送", file=sys.stderr)
        return False

    def close_chat(self):
        """关闭当前聊天/搜索面板。"""
        pyautogui.press("escape")
        time.sleep(0.5)
        pyautogui.press("escape")
        time.sleep(0.3)
