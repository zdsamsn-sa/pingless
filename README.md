# Pingless 自动续期 + AFK Credits

## 当前最稳登录方式（必做）

之前 `SESSION_COOKIE` 解析后经常是 **0 个有效 Cookie**，导致登录失败。  
请改用 **STORAGE_STATE_JSON**（包含 Cookie + localStorage），成功率最高。

### 一步步操作（约 3 分钟）

1. **在你自己的电脑**打开终端，安装依赖：
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. 下载本仓库的 `scripts/export_storage.py`，运行：
   ```bash
   python scripts/export_storage.py
   ```

3. 脚本会弹出浏览器 → **用 Discord 或 Google 登录 Pingless**  
   登录成功后，确保能看到服务器列表 / Dashboard。

4. 回到终端按 **回车**。

5. 会生成两个文件：
   - `storage_state.json`
   - `storage_state.b64.txt`  ← **用这个**

6. 打开 GitHub 仓库 → **Settings → Secrets and variables → Actions**  
   新建或更新 Secret：
   - **Name**：`STORAGE_STATE_JSON`
   - **Value**：把 `storage_state.b64.txt` 的**全部内容**粘贴进去（很长，正常）

7. 同时确认已有：
   - `SERVER_ID` = 你的服务器 id（如 `b7887be7`）
   - `NUMERIC_ID` = numeric 参数（如 `4678`）

8. 去 **Actions** 页面，手动 **Run workflow** 一次。

---

## 其他可选 Secrets

| Secret | 说明 |
|--------|------|
| `STORAGE_STATE_JSON` | **必须**，最稳登录方式 |
| `SESSION_COOKIE` | 备用（不推荐，容易解析失败） |
| `TG_BOT_TOKEN` / `TG_CHAT_ID` | Telegram 通知 + 截图 |
| `AFK_SECONDS` | 挂机秒数，默认 1800（30分钟） |

---

## 运行后如何确认成功

1. Actions 日志出现 `✅ 登录成功`
2. 下载 Artifact 里的截图：
   - `02_manage_before.png` 应是服务器管理页（不是首页）
   - `04_afk_before.png` 应是 AFK 页面
3. 如果续期按钮没点到，把日志里「可见按钮/链接」那段 + 截图发给我，我帮你改选择器

---

## 文件说明

```
scripts/
  export_storage.py   ← 在你电脑运行，导出登录状态
  renew.py            ← GitHub Actions 主脚本
  requirements.txt
.github/workflows/pingless-renew.yml
```

## 免责声明

仅供个人学习使用，请遵守服务条款，合理使用。
