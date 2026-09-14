#!/usr/bin/env python3
"""
在你自己的电脑上运行此脚本，生成 storage_state。
需要已安装: pip install playwright && playwright install chromium
"""

from playwright.sync_api import sync_playwright
import json
import base64
import time

print("=" * 50)
print("Pingless storage_state 导出工具")
print("=" * 50)
print("1. 即将打开浏览器")
print("2. 请在浏览器中完成登录（直到看到自己的服务器列表）")
print("3. 登录成功后回到这里按回车")
print("=" * 50)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://dash.pingless.org")

    input("\n>>> 请在打开的浏览器中登录成功后，回到这里按回车继续...")

    # 再访问一次管理页确保会话完整
    page.goto("https://dash.pingless.org")
    time.sleep(2)

    state = context.storage_state()
    browser.close()

    # 保存文件
    with open("storage_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print("\n已保存: storage_state.json")

    # 同时生成 base64，方便直接贴到 GitHub Secret
    b64 = base64.b64encode(json.dumps(state).encode()).decode()
    with open("storage_state.b64.txt", "w") as f:
        f.write(b64)
    print("已保存: storage_state.b64.txt （内容可直接粘贴到 GitHub Secret STORAGE_STATE_JSON）")
    print("\n请把 storage_state.b64.txt 的全部内容复制到 GitHub Secret: STORAGE_STATE_JSON")
