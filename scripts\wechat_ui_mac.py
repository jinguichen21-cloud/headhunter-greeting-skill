"""
微信 GUI 自动化 — macOS 实现

通过 PyAutoGUI + Quartz + AppleScript 实现微信 GUI 操控。
截图后由 AI 通过环境内置的 view_image 工具识别内容。

依赖：pyautogui, pillow, pyperclip, pyobjc (Quartz)
"""

import subprocess
import time
import os
import sys
import tempfile

import pyautogui
import pyperclip
import Quartz
from PIL import Image

from scripts.wechat_ui_base import WeChatUIBase, MODIFIER_KEY

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

WECHAT_OWNER_NAME = "微信"
WECHAT_PROCESS_NAME = "WeChat"
WECHAT_APP_PATH = "/Applications/WeChat.app"


def _run_applescript(script: str) -> tuple[str, str]:
    result = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, timeout=10
    )
    return result.stdout.strip(), result.stderr.strip()


def _get_retina_scale() -> int:
    try:
        d = Quartz.CGMainDisplayID()
        pw = Quartz.CGDisplayPixelsWide(d)
        lw = Quartz.CGDisplayBounds(d).size.width
        if pw > 0 and lw > 0:
            s = round(pw / lw)
            return s if s >= 2 else 2
    except Exception:
        pass
    return 2


def _to_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg
    return img.convert("RGB")


class WeChatUIMac(WeChatUIBase):
    # ── 状态检查 ──

    def is_wechat_installed(self) -> bool:
        return os.path.exists(WECHAT_APP_PATH)

    def is_wechat_running(self) -> bool:
        r = subprocess.run(["pgrep", "-x", WECHAT_PROCESS_NAME], capture_output=True)
        return r.returncode == 0

    def launch_wechat(self):
        subprocess.run(["open", WECHAT_APP_PATH], check=True)
        time.sleep(3)

    def activate_wechat(self):
        _run_applescript(
            'tell application "WeChat" to activate\ntell application "WeChat" to reopen'
        )
        time.sleep(0.8)

    def hide_wechat(self):
        """将微信窗口隐藏到后台，不遮挡其他窗口。"""
        _run_applescript(
            'tell application "System Events" to set visible of process "WeChat" to false'
        )
        time.sleep(0.3)

    def _get_wechat_window_ids(self) -> list[int]:
        """获取所有微信窗口的 ID 列表。"""
        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID
        )
        ids = []
        for w in windows:
            if str(w.get("kCGWindowOwnerName", "")) != WECHAT_OWNER_NAME:
                continue
            b = w.get("kCGWindowBounds", {})
            ww, hh = int(b.get("Width", 0)), int(b.get("Height", 0))
            if ww > 100 and hh > 100 and int(w.get("kCGWindowLayer", -1)) == 0:
                ids.append(int(w.get("kCGWindowNumber", 0)))
        return ids

    def get_wechat_main_window(self) -> dict | None:
        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID
        )
        candidates = []
        for w in windows:
            if str(w.get("kCGWindowOwnerName", "")) != WECHAT_OWNER_NAME:
                continue
            b = w.get("kCGWindowBounds", {})
            ww, hh = int(b.get("Width", 0)), int(b.get("Height", 0))
            if ww > 100 and hh > 100 and int(w.get("kCGWindowLayer", -1)) == 0:
                candidates.append(
                    {
                        "id": int(w.get("kCGWindowNumber", 0)),
                        "name": str(w.get("kCGWindowName", "")),
                        "x": int(b.get("X", 0)),
                        "y": int(b.get("Y", 0)),
                        "width": ww,
                        "height": hh,
                        "on_screen": bool(w.get("kCGWindowIsOnscreen", False)),
                    }
                )
        if not candidates:
            return None
        pool = [c for c in candidates if c["on_screen"]] or candidates
        return max(pool, key=lambda c: c["width"] * c["height"])

    # ── 截图（自动 RGBA→RGB） ──

    def _screenshot_wechat_window(self, filename: str = "wechat_screenshot.png") -> str:
        """截图微信窗口（不 activate），自动转 RGB。"""
        fp = os.path.join(tempfile.gettempdir(), filename)
        win = self.get_wechat_main_window()
        if win and win.get("id"):
            r = subprocess.run(
                ["screencapture", "-x", "-o", "-l", str(win["id"]), fp],
                capture_output=True,
            )
            if r.returncode == 0 and os.path.exists(fp):
                _to_rgb(Image.open(fp)).save(fp)
                return fp
        subprocess.run(["screencapture", "-x", fp], check=True)
        _to_rgb(Image.open(fp)).save(fp)
        return fp

    def take_screenshot_of_wechat(self) -> str:
        """截图微信窗口（不激活到前台），返回文件路径。"""
        return self._screenshot_wechat_window()

    def take_screenshot_region(self, x: int, y: int, w: int, h: int) -> str:
        full = os.path.join(tempfile.gettempdir(), "region_full.png")
        out = os.path.join(tempfile.gettempdir(), "region_crop.png")
        subprocess.run(["screencapture", "-x", full], check=True)
        s = _get_retina_scale()
        img = Image.open(full)
        _to_rgb(img.crop((x * s, y * s, (x + w) * s, (y + h) * s))).save(out)
        os.remove(full)
        return out

    # ── 通讯录扫描（截图模式，AI 通过 view_image 识别） ──

    def scan_contacts_screenshots(
        self, reset_to_top: bool = True, max_time: int = 240
    ) -> list[str]:
        """
        滚动通讯录并逐屏截图，返回截图文件路径列表。

        Args:
            reset_to_top: 是否先回到列表顶部（首次扫描 True，继续扫描 False）
            max_time: 最大扫描时间（秒），默认 240s，留 60s 余量给 300s 超时
        """
        import time as _time

        start = _time.time()

        self.activate_wechat()
        self._open_contacts_panel()
        time.sleep(0.5)

        win = self.get_wechat_main_window()
        if not win:
            raise RuntimeError("无法获取微信窗口信息")

        screenshots = []

        if reset_to_top:
            self._scroll_to_top(win)

        # 将鼠标移到联系人列表可滚动区域
        scroll_x = win["x"] + 200
        scroll_y = win["y"] + int(win["height"] * 0.7)
        pyautogui.moveTo(scroll_x, scroll_y)
        time.sleep(0.2)

        # 先截当前屏
        path = self._screenshot_wechat_window("wechat_contacts_0000.png")
        screenshots.append(path)

        # 计算每次滚动量：窗口高度 - 100px 的重叠区域，避免漏人
        # macOS 上 pyautogui.scroll 1 单位 ≈ 10px
        page_scroll = -max(10, (win["height"] - 100) // 10)

        same_count = 0
        last_size = None
        round_num = 0
        timed_out = False

        while True:
            round_num += 1

            # 超时保护
            elapsed = _time.time() - start
            if elapsed > max_time:
                print(
                    f"[扫描] 达到时间上限 {max_time}s，已扫描 {round_num - 1} 轮",
                    file=sys.stderr,
                )
                timed_out = True
                break

            # 滚动一页（窗口高度 - 100px）
            pyautogui.scroll(page_scroll)
            time.sleep(0.2)

            # 截图
            fname = f"wechat_contacts_{round_num:04d}.png"
            path = self._screenshot_wechat_window(fname)

            # 判断到底：文件大小连续相同
            current_size = os.path.getsize(path)
            if last_size is not None and current_size == last_size:
                same_count += 1
                if same_count >= 3:
                    print(
                        f"[扫描] 列表已到底，共扫描 {round_num} 轮",
                        file=sys.stderr,
                    )
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    break
            else:
                same_count = 0
            last_size = current_size

            screenshots.append(path)

        elapsed = _time.time() - start
        print(
            f"[扫描] 完成, 共 {len(screenshots)} 张截图, 耗时 {elapsed:.0f}s"
            + (", 未扫完(超时)" if timed_out else ""),
            file=sys.stderr,
        )
        return screenshots

    def _scroll_to_top(self, win: dict):
        """通过大幅度向上滚动回到联系人列表顶部（兼容 5000+ 联系人）。"""
        scroll_x = win["x"] + 200
        scroll_y = win["y"] + int(win["height"] * 0.5)
        pyautogui.moveTo(scroll_x, scroll_y)
        time.sleep(0.2)

        # 临时关闭 PAUSE，用最大滚动值快速到顶
        # macOS scroll 单次最大有效值约 32767
        # 5000 联系人约需滚动 150000+ 单位，用 32767 x 10 次覆盖
        old_pause = pyautogui.PAUSE
        pyautogui.PAUSE = 0
        for _ in range(10):
            pyautogui.scroll(32767)
        pyautogui.PAUSE = old_pause
        time.sleep(0.5)

        print("[扫描] 已滚动到列表顶部", file=sys.stderr)

    def _open_contacts_panel(self):
        """点击通讯录图标（左侧边栏第 2 个，y_offset≈165）。"""
        self.activate_wechat()
        time.sleep(0.5)
        win = self.get_wechat_main_window()
        if not win:
            raise RuntimeError("无法获取微信窗口信息")
        pyautogui.click(win["x"] + 30, win["y"] + 165)
        time.sleep(1)

    def _get_frontmost_window(self) -> dict | None:
        """获取当前最前端（最顶部）窗口的信息，不限于微信。"""
        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly
            | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID,
        )
        for w in windows:
            layer = int(w.get("kCGWindowLayer", -1))
            b = w.get("kCGWindowBounds", {})
            ww, hh = int(b.get("Width", 0)), int(b.get("Height", 0))
            if layer == 0 and ww > 50 and hh > 50:
                return {
                    "owner": str(w.get("kCGWindowOwnerName", "")),
                    "id": int(w.get("kCGWindowNumber", 0)),
                    "width": ww,
                    "height": hh,
                }
        return None

    # ── 消息发送 ──

    def search_and_open_chat(self, contact_name: str) -> bool:
        """
        搜索联系人并打开聊天窗口。

        验证逻辑：
        1. 记录按 Enter 前微信主窗口的 ID 和尺寸
        2. 按 Enter 后检查系统最前端窗口：
           - 最前端不是微信 → 被其他窗口覆盖（搜索打开了外部页面）→ Cmd+W 关闭 → False
           - 最前端是微信但窗口 ID 变了或尺寸剧烈变化 → 打开了微信内的新窗口 → Cmd+W 关闭 → False
           - 最前端仍是原来的微信主窗口 → 正常进入聊天 → True
        """
        self.activate_wechat()
        time.sleep(0.5)
        win = self.get_wechat_main_window()
        if not win:
            return False

        # 记录微信主窗口的 ID 和尺寸
        original_id = win.get("id")
        original_width = win["width"]
        original_height = win["height"]

        # 点击搜索框
        pyautogui.click(win["x"] + 190, win["y"] + 33)
        time.sleep(0.5)
        pyautogui.hotkey(MODIFIER_KEY, "a")
        time.sleep(0.1)

        # 输入搜索关键词
        pyperclip.copy(contact_name)
        pyautogui.hotkey(MODIFIER_KEY, "v")
        time.sleep(1.5)

        # 按 Enter 选中第一个搜索结果
        pyautogui.press("enter")
        time.sleep(1.0)

        # 检查最前端窗口是否仍然是微信主窗口
        front = self._get_frontmost_window()
        if not front:
            print(f"[发送] 搜索 '{contact_name}' 无法获取前端窗口信息", file=sys.stderr)
            pyautogui.press("escape")
            time.sleep(0.3)
            return False

        if front["owner"] != WECHAT_OWNER_NAME:
            # 最前端不是微信 → 被外部窗口覆盖（如浏览器搜索页面）
            print(
                f"[发送] 搜索 '{contact_name}' 打开了非微信窗口（{front['owner']}），关闭中",
                file=sys.stderr,
            )
            pyautogui.hotkey(MODIFIER_KEY, "w")
            time.sleep(0.5)
            # 回到微信并关闭搜索
            self.activate_wechat()
            time.sleep(0.3)
            pyautogui.press("escape")
            time.sleep(0.3)
            return False

        if front["id"] != original_id:
            # 最前端是微信但窗口 ID 变了 → 打开了微信内的新窗口（如联系人详情）
            print(
                f"[发送] 搜索 '{contact_name}' 打开了微信新窗口（ID {front['id']} != {original_id}），关闭中",
                file=sys.stderr,
            )
            pyautogui.hotkey(MODIFIER_KEY, "w")
            time.sleep(0.5)
            pyautogui.press("escape")
            time.sleep(0.3)
            return False

        # 检查窗口尺寸是否剧烈变化（可能是弹出了不同大小的窗口替换了主窗口）
        size_change = abs(front["width"] - original_width) + abs(
            front["height"] - original_height
        )
        if size_change > 100:
            print(
                f"[发送] 搜索 '{contact_name}' 窗口尺寸异常变化（差异 {size_change}px），关闭中",
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
        if not win:
            return False
        original_id = win.get("id")

        # 步骤 1：点击输入框前，确认微信在前台
        if not self._ensure_wechat_focused(original_id):
            return False
        pyautogui.click(win["x"] + win["width"] * 2 // 3, win["y"] + win["height"] - 80)
        time.sleep(0.3)

        # 步骤 2：粘贴前，确认微信仍在前台
        if not self._ensure_wechat_focused(original_id):
            return False
        pyperclip.copy(message)
        pyautogui.hotkey(MODIFIER_KEY, "v")
        time.sleep(0.3)

        # 步骤 3：按 Enter 前，确认微信仍在前台
        if not self._ensure_wechat_focused(original_id):
            return False
        pyautogui.press("enter")
        time.sleep(1.0)

        # 步骤 4：发送后，确认微信仍在前台（如果不在说明发送可能失败）
        front = self._get_frontmost_window()
        if not front or front["owner"] != WECHAT_OWNER_NAME:
            print("[发送] 发送后微信不在前台，消息可能未成功发送", file=sys.stderr)
            return False

        return True

    def _ensure_wechat_focused(self, expected_id: int, max_retries: int = 2) -> bool:
        """确保微信在前台且是预期的窗口。如果不在前台则尝试激活，失败则返回 False。"""
        for attempt in range(max_retries + 1):
            front = self._get_frontmost_window()
            if (
                front
                and front["owner"] == WECHAT_OWNER_NAME
                and front["id"] == expected_id
            ):
                return True
            if attempt < max_retries:
                print(
                    f"[发送] 微信不在前台（当前: {front['owner'] if front else '未知'}），重新激活中",
                    file=sys.stderr,
                )
                self.activate_wechat()
                time.sleep(0.5)
        print("[发送] 无法将微信保持在前台，中止发送", file=sys.stderr)
        return False

    def close_chat(self):
        win = self.get_wechat_main_window()
        if win:
            pyautogui.click(win["x"] + 190, win["y"] + 90)
            time.sleep(0.5)
