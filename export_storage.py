#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import json
import base64
import time

print("=" * 60)
print("Pingless storage_state 导出工具")
print("=" * 60)
print("1. 即将打开浏览器")
print("2. 请完成 Discord/Google 登录")
print("3. 登录成功后回到这里按回车")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={"width": 1400, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    )
    page = context.new_page()
    page.goto("https://dash.pingless.org", wait_until="domcontentloaded")

    input("\n>>> 请在浏览器中登录成功后，回到这里按回车继续...")

    for url in ["https://dash.pingless.org", "https://dash.pingless.org/afk"]:
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
    print("\n请把 storage_state.b64.txt 的全部内容复制到 GitHub Secret: STORAGE_STATE_JSON")