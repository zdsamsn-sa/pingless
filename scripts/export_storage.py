#!/usr/bin/env python3
"""
在你自己的电脑上运行此脚本，生成 storage_state（最稳登录方式）
需要: pip install playwright && playwright install chromium
"""

from playwright.sync_api import sync_playwright
import json
import base64
import time

print("=" * 60)
print("Pingless storage_state 导出工具（推荐方式）")
print("=" * 60)
print("步骤：")
print("1. 即将打开浏览器窗口")
print("2. 请在浏览器中完成 Discord/Google 登录")
print("3. 登录成功后，确保能看到自己的服务器列表或 Dashboard")
print("4. 回到本终端按【回车】继续")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={"width": 1400, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    )
    page = context.new_page()
    page.goto("https://dash.pingless.org", wait_until="domcontentloaded")

    input("\n>>> 请在打开的浏览器中登录成功后，回到这里按回车继续...")

    for url in [
        "https://dash.pingless.org",
        "https://dash.pingless.org/afk",
    ]:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
        except:
            pass

    state = context.storage_state()
    browser.close()

    with open("storage_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print("\n✅ 已保存: storage_state.json")

    b64 = base64.b64encode(json.dumps(state, separators=(",", ":")).encode()).decode()
    with open("storage_state.b64.txt", "w", encoding="utf-8") as f:
        f.write(b64)
    print("✅ 已保存: storage_state.b64.txt")
    print("\n请把 storage_state.b64.txt 的【全部内容】复制到 GitHub Secret：")
    print("   Name : STORAGE_STATE_JSON")
    print("   Value: 粘贴 storage_state.b64.txt 的全部文字")
    print("\n完成后在 Actions 手动触发一次即可。")
