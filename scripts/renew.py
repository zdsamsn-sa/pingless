#!/usr/bin/env python3
"""
Pingless 自动续期 + AFK Credits 收集
支持：Session Cookie（推荐） / Discord / Google 登录
"""

import os
import sys
import time
import json
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ========== 配置 ==========
BASE_URL = "https://dash.pingless.org"
SERVER_ID = os.getenv("SERVER_ID", "b7887be7")
NUMERIC_ID = os.getenv("NUMERIC_ID", "4678")
MANAGE_URL = f"{BASE_URL}/server/manage?id={SERVER_ID}&numeric={NUMERIC_ID}&mode=server"
AFK_URL = f"{BASE_URL}/afk"

SESSION_COOKIE = os.getenv("SESSION_COOKIE")  # 推荐方式
DISCORD_EMAIL = os.getenv("DISCORD_EMAIL")
DISCORD_PASSWORD = os.getenv("DISCORD_PASSWORD")
GOOGLE_EMAIL = os.getenv("GOOGLE_EMAIL")
GOOGLE_PASSWORD = os.getenv("GOOGLE_PASSWORD")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def notify(msg: str):
    print(msg)
    if TG_BOT_TOKEN and TG_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT_ID, "text": f"[Pingless] {msg}"},
                timeout=10
            )
        except Exception as e:
            print(f"Telegram notify failed: {e}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        try:
            # ========== 登录处理 ==========
            if SESSION_COOKIE:
                print("使用 Session Cookie 登录...")
                # 解析 cookie 字符串（支持 "name=value; name2=value2" 格式）
                cookies = []
                for item in SESSION_COOKIE.split(";"):
                    item = item.strip()
                    if "=" in item:
                        name, value = item.split("=", 1)
                        cookies.append({
                            "name": name.strip(),
                            "value": value.strip(),
                            "domain": ".pingless.org",
                            "path": "/"
                        })
                context.add_cookies(cookies)
                page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            else:
                # OAuth 登录（成功率较低，推荐用 Cookie）
                page.goto(f"{BASE_URL}/auth", wait_until="networkidle", timeout=60000)
                if DISCORD_EMAIL and DISCORD_PASSWORD:
                    print("尝试 Discord 登录...")
                    page.click('a[href*="discord"]')
                    page.wait_for_load_state("networkidle")
                    # Discord 登录页面处理（可能需要手动调整选择器）
                    page.fill('input[name="email"]', DISCORD_EMAIL)
                    page.fill('input[name="password"]', DISCORD_PASSWORD)
                    page.click('button[type="submit"]')
                    page.wait_for_url("**/dash.pingless.org/**", timeout=60000)
                elif GOOGLE_EMAIL and GOOGLE_PASSWORD:
                    print("尝试 Google 登录...")
                    page.click('a[href*="google"]')
                    # Google 登录流程更复杂，建议优先使用 Cookie
                    notify("Google OAuth 自动化不稳定，请改用 SESSION_COOKIE")
                    sys.exit(1)
                else:
                    notify("未提供有效登录凭据（推荐 SESSION_COOKIE）")
                    sys.exit(1)

            # 检查是否登录成功
            if "auth" in page.url or "login" in page.url.lower():
                notify("登录失败，请检查 Cookie 或账号")
                page.screenshot(path="login_fail.png")
                sys.exit(1)

            print("登录成功")

            # ========== 续期服务器 ==========
            print(f"访问管理页: {MANAGE_URL}")
            page.goto(MANAGE_URL, wait_until="networkidle", timeout=60000)
            time.sleep(3)

            # 常见续期按钮选择器（根据实际页面调整）
            renew_selectors = [
                'button:has-text("Renew")',
                'button:has-text("续期")',
                'button:has-text("Extend")',
                '[data-action="renew"]',
                'button.renew',
                'a:has-text("Renew")',
                'button:has-text("Renew Server")',
            ]

            renewed = False
            for sel in renew_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        time.sleep(2)
                        # 可能有确认弹窗
                        try:
                            page.locator('button:has-text("Confirm"), button:has-text("确认"), button:has-text("Yes")').first.click(timeout=3000)
                        except:
                            pass
                        print("续期按钮已点击")
                        renewed = True
                        break
                except:
                    continue

            if renewed:
                notify(f"服务器 {SERVER_ID} 续期成功")
            else:
                # 可能已经续期过或按钮文字不同
                page.screenshot(path="manage_page.png")
                notify(f"未找到续期按钮，已截图。请检查管理页是否已续期或选择器需更新")

            # ========== AFK 收集 Credits ==========
            print(f"访问 AFK 页面: {AFK_URL}")
            page.goto(AFK_URL, wait_until="networkidle", timeout=60000)
            time.sleep(5)

            # AFK 页面通常只需要保持打开或点击开始按钮
            afk_selectors = [
                'button:has-text("Start")',
                'button:has-text("开始")',
                'button:has-text("AFK")',
                'button:has-text("Collect")',
                '[data-action="afk"]',
            ]
            for sel in afk_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        print("AFK 已启动")
                        break
                except:
                    continue

            # 保持页面一段时间收集 Credits（根据实际机制调整）
            print("AFK 挂机中...")
            time.sleep(30)  # 可按需延长
            notify("AFK Credits 收集完成")

            # 保存最新 Cookie（方便下次使用）
            cookies = context.cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies if "pingless" in c.get("domain", "")])
            print(f"当前 Cookie（可更新到 Secrets）:\n{cookie_str[:200]}...")

        except PlaywrightTimeout as e:
            notify(f"超时错误: {e}")
            page.screenshot(path="timeout.png")
            sys.exit(1)
        except Exception as e:
            notify(f"运行异常: {e}")
            page.screenshot(path="error.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    main()
