# 已知问题与经验

## 搜索候选人验证

微信搜索优先级：微信号 > 姓名 > 手机号。

**问题**：候选人不存在时按 Enter 可能打开错误窗口。
**解决**：按 Enter 前记录微信主窗口 ID 和尺寸，按 Enter 后检查最前端窗口：
- 最前端不是微信 → Cmd+W 关闭 → not_found
- 窗口 ID 变了 → Cmd+W 关闭 → not_found
- 窗口尺寸剧变(>100px) → Cmd+W 关闭 → not_found
- 前端仍是原窗口且尺寸正常 → 继续发送

## 微信登录状态判断

**macOS**：通过窗口尺寸启发式判断。登录界面约 280x400，主界面 >700x500。

**Windows**：多重验证（更可靠）：
1. 检查是否有 `WeChatMainWndForPC`/`WeixinMainWndForPC` 类名的可见窗口
2. 窗口尺寸 > 700x500
3. **子控件数量检测**：已登录的微信主界面有大量子控件（>10），登录窗口很少（<5）
4. 新版 Weixin 登录窗口可能很大，单靠尺寸无法区分，子控件数量是关键判据

`check` 返回 `logged_in: true/false`。send 命令内部也会自动 check。

## 微信状态检查不激活窗口

`check_wechat_status` 使用 Quartz API 后台查询，不会将微信弹到前台。

## 发送后操作

- 每条发送后自动 `close_chat()` 回到主界面
- **每人发完后** `hide_wechat()` 隐藏到后台（不是全部发完才隐藏）

## screencapture RGBA 问题

`screencapture -l` 输出 RGBA，截图保存前自动转 RGB（透明区域填白）。

## 微信窗口在其他 Space

微信在另一个 macOS Space 时截图可能空白。`activate_wechat()` 同时调用 `activate` 和 `reopen`。

---

## [WIP] 扫描通讯录相关（开发中）

- 通讯录入口坐标 `(x+30, y+165)`
- 联系人列表滚动区域 `(x+200, y+height*0.5)`
- 每次滚动距离 = (窗口高度 - 100) / 10，超时 240s
- 回到顶部：`scroll(32767)` x 10 次
