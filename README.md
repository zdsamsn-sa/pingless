# Pingless 自动续期 + AFK Credits

基于 GitHub Actions 的自动续期与 AFK 收集脚本。

## 功能

- 自动登录（推荐 `STORAGE_STATE_JSON`）
- 自动尝试点击续期按钮，并打印页面所有按钮文字方便调试
- 自动访问 `/afk` 并尝试启动收集，默认挂机 30 分钟
- **全程多处截图**，上传到 Actions Artifact，同时可发 Telegram
- 支持手动触发

## 推荐登录方式：STORAGE_STATE（最稳）

纯 Cookie 有时不够（可能依赖 localStorage）。请用 Playwright 的 storage_state。

### 在你自己电脑上导出

1. 安装依赖：
```bash
pip install playwright
playwright install chromium
```

2. 运行导出脚本（本仓库 `scripts/export_storage.py`）：
```bash
python scripts/export_storage.py
```

3. 脚本会打开浏览器 → **完成登录**（看到服务器列表）→ 回到终端按回车。

4. 生成两个文件：
   - `storage_state.json`
   - `storage_state.b64.txt`  ← 把**全部内容**复制到 GitHub Secret

5. 在仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret 名称 | 说明 |
|-------------|------|
| `STORAGE_STATE_JSON` | **推荐**，粘贴 `storage_state.b64.txt` 全部内容 |
| `SESSION_COOKIE` | 备用纯 Cookie |
| `SERVER_ID` | 服务器 id（如 `b7887be7`） |
| `NUMERIC_ID` | numeric 参数（如 `4678`） |
| `TG_BOT_TOKEN` / `TG_CHAT_ID` | 可选 Telegram 通知 |
| `AFK_SECONDS` | 可选，挂机秒数，默认 1800（30分钟） |

## 运行说明

- 默认每 2 小时自动跑一次（可改 cron）
- 也可在 Actions 页面手动 **Run workflow**
- 截图会：
  1. 上传为 Artifact（Actions 运行记录里下载）
  2. 如果配置了 Telegram，会直接发图

## 调试续期 / AFK 按钮

如果提示「未找到续期按钮」或 AFK 没真正收集：

1. 下载本次运行的 Artifact 截图（`02_manage_before.png`、`04_afk_before.png` 等）
2. 查看日志里打印的 **可见按钮列表**（脚本会 dump 所有 button/a 的文字）
3. 把截图 + 按钮列表发给我，我帮你精确改选择器

## 免责声明

仅供个人学习使用，请遵守 Pingless 服务条款，合理使用，风险自负。
