# Pingless 自动续期 + AFK Credits

## 重要：Cookie 必须完整有效

当前最常见失败原因是 **SESSION_COOKIE 不完整或已过期**。

### 正确获取 Cookie 步骤

1. 浏览器打开 https://dash.pingless.org 并**成功登录**（能看到服务器列表）
2. 按 F12 → Application → Cookies → 选择 `https://dash.pingless.org`
3. 使用扩展 **Cookie-Editor** 导出全部 Cookie（格式：`name=value; name2=value2`）
4. 完整粘贴到 GitHub Secret `SESSION_COOKIE`

只复制 `cf_clearance` 是不够的，必须包含真正的会话 Cookie。

## 运行频率与 AFK 时长说明

GitHub Actions 单次任务最长约 6 小时，**无法一次挂满 24 小时**。

当前默认策略：
- 每 **2 小时** 自动运行一次
- 每次 AFK 挂机 **30 分钟**
- 全天大约累计 6 小时在线时间

如需调整，修改工作流里的：
```yaml
AFK_SECONDS: "1800"   # 秒，1800=30分钟，3600=1小时
```
以及 cron 表达式。

## Secrets 配置

| Secret | 必填 | 说明 |
|--------|------|------|
| SESSION_COOKIE | 是 | 完整 Cookie |
| SERVER_ID | 是 | 服务器 id |
| NUMERIC_ID | 是 | numeric 参数 |
| TG_BOT_TOKEN / TG_CHAT_ID | 否 | Telegram 通知 |

## 截图与调试

每次运行都会上传截图到 Artifact，重点查看：
- `01_home.png` / `02_manage_page.png` / `04_afk_page.png`

如果这些截图还是登录页，说明 Cookie 仍无效。
