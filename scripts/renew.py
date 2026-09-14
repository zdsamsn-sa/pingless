#!/usr/bin/env python3
"""
Pingless 自动续期 + AFK Credits 收集
增强：Cookie 有效性严格检查 + 全程截图 + 调试信息
"""

import os
import sys
import time
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ========== 配置 ==========
BASE_URL = "https://dash.pingless.org"
SERVER_ID = os.getenv("SERVER_ID", "b7887be7")
NUMERIC_ID = os.getenv("NUMERIC_ID", "4678")
MANAGE_URL = f"{BASE_URL}/server/manage?id={SERVER_ID}&numeric={NUMERIC_ID}&mode=server"
AFK_URL = f"{BASE_URL}/afk"

SESSION_COOKIE = os.getenv("SESSION_COOKIE")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
AFK_SECONDS = int(os.getenv("AFK_SECONDS", "1800"))  # 默认 30 分钟

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def notify(msg: str):
    print(msg)
    if TG_BOT_TOKEN and TG_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT_ID, "text": f"[Pingless] {msg}"},
                timeout=10,
            )
        except Exception as e:
            print(f"Telegram notify failed: {e}")


def save_screenshot(page, name: str):
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[截图] 已保存: {path}")
    return path


def dump_page_info(page, label: str):
    print(f"\n===== 页面调试 [{label}] =====")
    print(f"URL: {page.url}")
    print(f"Title: {page.title()}")

    try:
        buttons = page.locator("button, a[role='button'], [class*='btn'], [class*='button']").all()
        btn_texts = []
        for b in buttons[:40]:
            try:
                txt = b.inner_text(timeout=500).strip()
                if txt:
                    btn_texts.append(txt.replace("\n", " ")[:80])
            except:
                pass
        print(f"可见按钮/链接文字: {btn_texts}")
    except Exception as e:
        print(f"获取按钮失败: {e}")

    try:
        body_text = page.locator("body").inner_text(timeout=3000)
        keywords = ["Renew", "续期", "Extend", "Expire", "到期", "Credit", "AFK",
                    "Start", "Collect", "Claim", "Hours", "Remaining", "Discord", "Google"]
        found = [kw for kw in keywords if kw.lower() in body_text.lower()]
        print(f"页面包含关键词: {found}")
        print(f"页面文本摘要(前800字): {body_text[:800].replace(chr(10), ' ')}")
    except Exception as e:
        print(f"获取页面文本失败: {e}")
    print("===== 调试结束 =====\n")


def is_logged_in(page) -> bool:
    """判断当前是否处于登录状态"""
    url = page.url.lower()
    if "/auth" in url or "login" in url:
        return False
    try:
        # 登录页特征
        if page.locator('text="Continue with Discord"').count() > 0:
            return False
        if page.locator('text="Continue with Google"').count() > 0:
            return False
        if page.locator('text="Sign in to Pingless"').count() > 0:
            return False
    except:
        pass
    return True


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900},
            locale="en-US",
        )
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            """
        )
        page = context.new_page()

        try:
            if not SESSION_COOKIE:
                notify("未提供 SESSION_COOKIE，无法继续")
                sys.exit(1)

            print("使用 Session Cookie 登录...")
            cookies = []
            for item in SESSION_COOKIE.split(";"):
                item = item.strip()
                if "=" in item:
                    name, value = item.split("=", 1)
                    cookies.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": ".pingless.org",
                        "path": "/",
                    })
            # 同时尝试不带点的 domain
            for item in SESSION_COOKIE.split(";"):
                item = item.strip()
                if "=" in item:
                    name, value = item.split("=", 1)
                    cookies.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": "dash.pingless.org",
                        "path": "/",
                    })
            context.add_cookies(cookies)

            # 先访问首页验证登录
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)
            save_screenshot(page, "01_home")
            dump_page_info(page, "首页")

            if not is_logged_in(page):
                notify("❌ Cookie 无效或已过期！请重新在浏览器登录后复制【完整】Cookie 更新到 SESSION_COOKIE")
                print("当前页面是登录页，Cookie 未生效。")
                sys.exit(1)

            print("✅ 登录状态有效")
            notify("登录成功，Cookie 有效")

            # ========== 续期 ==========
            print(f"访问管理页: {MANAGE_URL}")
            page.goto(MANAGE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_screenshot(page, "02_manage_page")
            dump_page_info(page, "管理页")

            if not is_logged_in(page):
                notify("❌ 访问管理页时掉登录了，Cookie 不完整或权限不足")
                sys.exit(1)

            renew_selectors = [
                'button:has-text("Renew")',
                'button:has-text("续期")',
                'button:has-text("Extend")',
                'button:has-text("Renew Server")',
                'button:has-text("Extend Server")',
                'a:has-text("Renew")',
                'a:has-text("续期")',
                '[data-action="renew"]',
                'button.renew',
                'button[class*="renew"]',
                'button:has-text("Claim")',
                'button:has-text("Free Renew")',
                'button:has-text("Renew Now")',
            ]

            renewed = False
            for sel in renew_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.count() > 0 and btn.is_visible(timeout=2000):
                        print(f"找到续期按钮: {sel}")
                        btn.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        btn.click(timeout=5000)
                        time.sleep(2)
                        for confirm_sel in [
                            'button:has-text("Confirm")',
                            'button:has-text("确认")',
                            'button:has-text("Yes")',
                            'button:has-text("OK")',
                            'button:has-text("确定")',
                        ]:
                            try:
                                cbtn = page.locator(confirm_sel).first
                                if cbtn.is_visible(timeout=1500):
                                    cbtn.click()
                                    print("已点击确认")
                                    break
                            except:
                                pass
                        time.sleep(2)
                        save_screenshot(page, "03_after_renew_click")
                        renewed = True
                        break
                except:
                    continue

            if renewed:
                notify(f"服务器 {SERVER_ID} 续期操作已执行")
            else:
                notify("未找到续期按钮，请查看 02_manage_page.png 截图确认按钮文字")

            # ========== AFK ==========
            print(f"访问 AFK 页面: {AFK_URL}")
            page.goto(AFK_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_screenshot(page, "04_afk_page")
            dump_page_info(page, "AFK页")

            if not is_logged_in(page):
                notify("❌ 访问 AFK 页时掉登录了")
                sys.exit(1)

            afk_selectors = [
                'button:has-text("Start")',
                'button:has-text("开始")',
                'button:has-text("AFK")',
                'button:has-text("Collect")',
                'button:has-text("Claim")',
                'button:has-text("Get Credits")',
                'button:has-text("Earn")',
                'button:has-text("开始挂机")',
                'button:has-text("开始收集")',
                '[data-action="afk"]',
                'button[class*="afk"]',
                'button[class*="start"]',
            ]

            for sel in afk_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.count() > 0 and btn.is_visible(timeout=2000):
                        print(f"找到 AFK 按钮: {sel}")
                        btn.scroll_into_view_if_needed()
                        btn.click(timeout=5000)
                        time.sleep(2)
                        save_screenshot(page, "05_afk_started")
                        break
                except:
                    continue

            # 挂机
            print(f"AFK 挂机中... 共 {AFK_SECONDS} 秒（约 {AFK_SECONDS//60} 分钟）")
            notify(f"开始 AFK 挂机 {AFK_SECONDS//60} 分钟")

            interval = 60  # 每分钟打印一次
            elapsed = 0
            while elapsed < AFK_SECONDS:
                sleep_time = min(interval, AFK_SECONDS - elapsed)
                time.sleep(sleep_time)
                elapsed += sleep_time
                print(f"  已挂机 {elapsed//60} 分 {elapsed%60} 秒 / 共 {AFK_SECONDS//60} 分钟")

                # 中途截图
                if elapsed == AFK_SECONDS // 2 or elapsed == AFK_SECONDS - interval:
                    save_screenshot(page, f"06_afk_{elapsed}s")

                # 检查是否还在登录状态
                if not is_logged_in(page):
                    notify("挂机过程中掉登录了")
                    break

            save_screenshot(page, "07_afk_final")
            dump_page_info(page, "AFK结束")
            notify("AFK 挂机结束，请查看截图确认 Credits 是否增加")

            # 输出当前 Cookie 方便更新
            cookies = context.cookies()
            cookie_str = "; ".join(
                f"{c['name']}={c['value']}"
                for c in cookies
                if "pingless" in c.get("domain", "")
            )
            print(f"\n当前有效 Cookie（可更新到 Secrets）:\n{cookie_str[:400]}...")

        except PlaywrightTimeout as e:
            notify(f"超时: {e}")
            try:
                save_screenshot(page, "error_timeout")
            except:
                pass
            sys.exit(1)
        except Exception as e:
            notify(f"异常: {e}")
            try:
                save_screenshot(page, "error_exception")
            except:
                pass
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
