# Pingless 自动续期 + AFK Credits

基于 GitHub Actions 的 Pingless 免费服务器自动续期与 AFK Credits 收集脚本。

## 功能

- 自动登录（推荐使用 Session Cookie）
- 自动点击服务器续期按钮（每 48 小时）
- 自动访问 `/afk` 页面收集 Credits
- 支持 Telegram 通知
- 支持手动触发

## 快速开始

1. 将本仓库内容上传到你的 **私有** GitHub 仓库。
2. 进入仓库 **Settings → Secrets and variables → Actions**，添加以下 Secrets：

| Secret 名称 | 必填 | 说明 |
|-------------|------|------|
| `SESSION_COOKIE` | **强烈推荐** | 手动登录后从浏览器复制的 Cookie |
| `SERVER_ID` | 是 | 服务器 id（示例：`b7887be7`） |
| `NUMERIC_ID` | 是 | numeric 参数（示例：`4678`） |
| `TG_BOT_TOKEN` | 否 | Telegram Bot Token |
| `TG_CHAT_ID` | 否 | Telegram Chat ID |
| `DISCORD_EMAIL` / `DISCORD_PASSWORD` | 否 | Discord 登录（不推荐，成功率低） |
| `GOOGLE_EMAIL` / `GOOGLE_PASSWORD` | 否 | Google 登录（不推荐） |

### 如何获取 SESSION_COOKIE（最稳方式）

1. 用浏览器登录 https://dash.pingless.org
2. 按 `F12` → **Application**（或 存储）→ **Cookies** → 选中 `dash.pingless.org`
3. 复制所有相关 Cookie，或使用浏览器扩展（如 Cookie-Editor）导出为 `name=value; name2=value2` 格式
4. 粘贴到 GitHub Secret `SESSION_COOKIE`

3. 启用 Actions 工作流后，会每 12 小时自动运行一次。也可在 Actions 页面手动触发。

## 文件说明

```
.
├── .github/workflows/pingless-renew.yml   # GitHub Actions 工作流
├── scripts/
│   ├── renew.py                           # 主脚本
│   └── requirements.txt                   # Python 依赖
├── README.md
└── .gitignore
```

## 注意事项

- Cloudflare 和页面结构可能会变化，若按钮点不到，请根据 Actions 日志中的截图更新 `scripts/renew.py` 里的选择器。
- 强烈建议把仓库设为 **Private**，避免泄露 Cookie。
- 首次运行后请查看 Actions 日志和生成的截图（`manage_page.png` 等），确认是否成功。
- AFK 收集时长可按实际效果调整脚本中的 `time.sleep()`。
- 续期频率默认每 12 小时，足以覆盖官方 48 小时续期窗口。

## 免责声明

本脚本仅供个人学习与自动化使用。请遵守 Pingless 服务条款，合理使用，避免滥用导致账号被封禁。使用风险自负。
