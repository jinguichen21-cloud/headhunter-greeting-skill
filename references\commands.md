# 脚本说明

## 脚本列表

| 脚本 | 用途 | 状态 |
|------|------|:----:|
| `scripts/main.py` | 主入口 | 可用 |
| `scripts/wechat_ui.py` | 平台路由层 | 可用 |
| `scripts/wechat_ui_base.py` | 平台抽象基类 | 可用 |
| `scripts/wechat_ui_mac.py` | macOS 实现 | 可用 |
| `scripts/wechat_ui_win.py` | Windows 实现 | 可用 |
| `scripts/candidates.py` | 候选人格式校验、称呼判断 | 可用 |
| `scripts/contacts_cache.py` | 候选人数据库管理 | [WIP] |

## 可用命令

| 命令 | 用途 | 返回 |
|------|------|------|
| `check` | 检查微信（安装+登录） | `{installed, running, logged_in, window_info}` |
| `send "名称" "内容" "主题"` | 发送单条微信消息 | `{candidate, message, status, timestamp}` |
| `hide` | 隐藏微信窗口到后台 | `{status: "hidden"}` |

send 内部每人完整循环：①检查安装+登录 → ②激活微信→搜索联系人 → ③发送（焦点验证）→ ④关闭聊天→隐藏微信。每人发完微信自动隐藏。

hide 可单独调用隐藏微信（通常不需要，send 内部已自动隐藏）。

## [WIP] 开发中命令（禁止调用）

| 命令 | 用途 |
|------|------|
| `scan_contacts` | 扫描通讯录 |
| `screenshot` / `screenshot_chat` | 截图 |
| `db_list` / `db_info` / `db_clear` | 候选人数据库操作 |

## 执行方式

所有命令必须在技能根目录下执行。使用以下固定写法定位技能目录：

```bash
SKILL_DIR=$(find ~/.real ~/.config -path "*/headhunter-greeting-skill/scripts/main.py" 2>/dev/null | head -1 | sed 's|/scripts/main.py||') && cd "$SKILL_DIR" && python3 scripts/main.py <命令>
```
