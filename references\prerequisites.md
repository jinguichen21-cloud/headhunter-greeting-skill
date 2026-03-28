# 环境依赖

## 通用要求

1. **微信客户端** — 已安装桌面版微信并处于已登录状态
2. **Python 环境** — Python 3.10+
3. **依赖库**：`pyautogui`、`pillow`、`pyperclip`
4. **网络连接** — 用于搜索节日信息

## macOS 额外要求

- `pyobjc` — macOS 原生 API（Quartz 窗口管理）
- 辅助功能权限：系统偏好设置 → 隐私与安全性 → 辅助功能
- 屏幕录制权限：系统偏好设置 → 隐私与安全性 → 屏幕录制
- 微信窗口必须在当前桌面空间（Space）内可见

## Windows 额外要求

- `pywin32` — Win32 API（窗口管理）
- `psutil` — 进程管理
