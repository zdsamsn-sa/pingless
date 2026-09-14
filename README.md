# Pingless 自动续期 + AFK Credits

基于 GitHub Actions 的 Pingless 免费服务器自动续期与 AFK Credits 收集脚本。

## 功能

- Session Cookie 登录（推荐）
- 自动尝试点击续期按钮
- 自动访问 `/afk` 并挂机收集 Credits
- **全程自动截图**，方便排查问题
- 页面元素调试信息输出（按钮文字 + 关键词）
- 截图自动上传为 Artifact
- 支持 Telegram 通知
- 支持手动触发

## 快速开始

1. 把本仓库内容放到你的 **私有** GitHub 仓库。
2. 进入 **Settings → Secrets and variables → Actions**，添加以下 Secrets：

| Secret 名称 | 必填 | 说明 |
|-------------|------|------|
| `SESSION_COOKIE` | **是** | 浏览器登录后复制的 Cookie |
| `SERVER_ID` | 是 | 服务器 id（示例 `b7887be7`） |
| `NUMERIC_ID` | 是 | numeric 参数（示例 `4678`） |
| `TG_BOT_TOKEN` | 否 | Telegram Bot Token |
| `TG_CHAT_ID` | 否 | Telegram Chat ID |

### 获取 SESSION_COOKIE

1. 浏览器登录 https://dash.pingless.org
2. 按 `F12` → Application → Cookies → 选中 `dash.pingless.org`
3. 复制所有 cookie（或用 Cookie-Editor 扩展导出为 `name=value; name2=value2`）
4. 粘贴到 Secret `SESSION_COOKIE`

3. 启用 Actions 后每 12 小时自动运行，也可手动触发。

## 截图说明

每次运行都会在 `screenshots/` 目录生成多张截图，并作为 Artifact 上传：

| 文件名 | 说明 |
|--------|------|
| `01_home.png` | 首页（登录后） |
| `02_manage_page.png` | 服务器管理页（续期前）**重点看这个** |
| `03_after_renew_click.png` | 点击续期后 |
| `04_afk_page.png` | AFK 页面初始 **重点看这个** |
| `05_afk_started.png` | 点击 AFK 按钮后 |
| `06_afk_mid.png` | 挂机中途 |
| `07_afk_final.png` | 挂机结束 |

**如何下载截图**：Actions 运行完成后 → 进入该次运行 → 底部 Artifacts → 下载 `screenshots-xxxxx`

## 调试建议

如果日志显示「未找到续期按钮」或 AFK 没有效果：

1. 下载最新截图，特别是 `02_manage_page.png` 和 `04_afk_page.png`
2. 把截图发给我，或告诉我页面上实际按钮的文字
3. 我会根据真实页面更新选择器

也可以在日志中查看「页面调试」输出的按钮文字和关键词。

## 调整 AFK 挂机时长

在工作流文件中修改环境变量：

```yaml
AFK_SECONDS: "120"   # 改为 120 秒等
```

## 免责声明

仅供个人学习使用。请遵守 Pingless 服务条款，合理使用，风险自负。
