#!/usr/bin/env python3
"""
Pingless 自动续期 + AFK Credits
- 严格登录状态检测
- 关键图自动发送到 Telegram
"""

import os
import sys
import time
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BASE_URL = "https://dash.pingless.org"
SERVER_ID = os.getenv("SERVER_ID", "b7887be7")
NUMERIC_ID = os.getenv("NUMERIC_ID", "4678")
MANAGE_URL = f"{BASE_URL}/server/manage?id={SERVER_ID}&numeric={NUMERIC_ID}&mode=server"
AFK_URL = f"{BASE_URL}/afk"
DASHBOARD_CANDIDATES = [
    f"{BASE_URL}/",
    f"{BASE_URL}/dashboard",
    f"{BASE_URL}/servers",
    f"{BASE_URL}/panel",
    f"{BASE_URL}/home",
]

SESSION_COOKIE = os.getenv("SESSION_COOKIE")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
AFK_SECONDS = int(os.getenv("AFK_SECONDS", "1800"))

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def tg_text(msg: str):
    print(msg)
    if not (TG_BOT_TOKEN and TG_CHAT_ID):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": f"[Pingless] {msg}"},
            timeout=15,
        )
    except Exception as e:
        print(f"TG text failed: {e}")


def tg_photo(path: Path, caption: str = ""):
    """发送截图到 Telegram"""
    if not (TG_BOT_TOKEN and TG_CHAT_ID):
        return
    if not path.exists():
        return
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto",
                data={"chat_id": TG_CHAT_ID, "caption": f"[Pingless] {caption}"[:1000]},
                files={"photo": f},
                timeout=30,
            )
        print(f"[TG] 已发送截图: {path.name}")
    except Exception as e:
        print(f"TG photo failed: {e}")


def save_screenshot(page, name: str, send_tg: bool = True, caption: str = ""):
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[截图] {path}")
    if send_tg:
        tg_photo(path, caption or name)
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
                txt = b.inner_text(timeout=400).strip()
                if txt:
                    btn_texts.append(txt.replace("\n", " ")[:80])
            except:
                pass
        print(f"可见按钮: {btn_texts}")
    except Exception as e:
        print(f"按钮获取失败: {e}")
    try:
        body = page.locator("body").inner_text(timeout=3000)
        print(f"文本摘要: {body[:700].replace(chr(10), ' ')}")
    except:
        pass
    print("===== 结束 =====\n")


def is_auth_page(page) -> bool:
    """是否是登录页"""
    url = page.url.lower()
    if "/auth" in url or "/login" in url:
        return True
    try:
        if page.locator('text="Continue with Discord"').count() > 0:
            return True
        if page.locator('text="Continue with Google"').count() > 0:
            return True
        if page.locator('text="Sign in to Pingless"').count() > 0:
            return True
    except:
        pass
    return False


def is_public_landing(page) -> bool:
    """是否是公开宣传首页（未登录）"""
    try:
        title = page.title().lower()
        if "free minecraft server hosting" in title:
            return True
        body = page.locator("body").inner_text(timeout=2000).lower()
        if "get started free" in body and "continue with discord" not in body:
            # 进一步判断有没有用户相关元素
            if page.locator('text=/my server|dashboard|logout|sign out|account/i').count() == 0:
                return True
    except:
        pass
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900},
            locale="en-US",
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            "window.chrome = { runtime: {} };"
        )
        page = context.new_page()

        try:
            if not SESSION_COOKIE:
                tg_text("未配置 SESSION_COOKIE")
                sys.exit(1)

            print("注入 Cookie...")
            cookies = []
            for item in SESSION_COOKIE.split(";"):
                item = item.strip()
                if "=" not in item:
                    continue
                name, value = item.split("=", 1)
                name, value = name.strip(), value.strip()
                # 同时写入两个 domain，提高兼容性
                for domain in [".pingless.org", "dash.pingless.org", "pingless.org"]:
                    cookies.append({"name": name, "value": value, "domain": domain, "path": "/"})
            context.add_cookies(cookies)

            # 1. 先访问首页
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)
            save_screenshot(page, "01_home", caption="首页")
            dump_page_info(page, "首页")

            if is_auth_page(page):
                tg_text("❌ 首页直接进入登录页，Cookie 完全无效，请重新获取完整 Cookie")
                sys.exit(1)

            if is_public_landing(page):
                tg_text("❌ 当前停留在公开宣传页，未进入登录后控制台。Cookie 无效或不完整，请重新用 Cookie-Editor 导出全部 Cookie")
                sys.exit(1)

            # 2. 强制访问管理页验证真实登录状态
            print(f"验证管理页: {MANAGE_URL}")
            page.goto(MANAGE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_screenshot(page, "02_manage_page", caption="管理页")
            dump_page_info(page, "管理页")

            if is_auth_page(page):
                tg_text("❌ 访问管理页被重定向到登录页。Cookie 无效/过期/不完整。\n请重新登录浏览器后，用 Cookie-Editor 导出【全部】Cookie 更新 Secret")
                sys.exit(1)

            tg_text("✅ 真实登录成功，已进入管理页")

            # ========== 续期 ==========
            renew_selectors = [
                'button:has-text("Renew")',
                'button:has-text("续期")',
                'button:has-text("Extend")',
                'button:has-text("Renew Server")',
                'button:has-text("Extend Server")',
                'button:has-text("Renew Now")',
                'a:has-text("Renew")',
                'a:has-text("续期")',
                '[data-action="renew"]',
                'button[class*="renew"]',
                'button:has-text("Claim")',
            ]
            renewed = False
            for sel in renew_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.count() and btn.is_visible(timeout=2000):
                        print(f"点击续期: {sel}")
                        btn.scroll_into_view_if_needed()
                        btn.click(timeout=5000)
                        time.sleep(2)
                        for csel in ['button:has-text("Confirm")', 'button:has-text("确认")',
                                     'button:has-text("Yes")', 'button:has-text("OK")', 'button:has-text("确定")']:
                            try:
                                if page.locator(csel).first.is_visible(timeout=1500):
                                    page.locator(csel).first.click()
                                    break
                            except:
                                pass
                        time.sleep(2)
                        save_screenshot(page, "03_after_renew", caption="点击续期后")
                        renewed = True
                        break
                except:
                    continue

            if renewed:
                tg_text(f"服务器 {SERVER_ID} 续期已执行")
            else:
                tg_text("未找到续期按钮，请查看管理页截图确认按钮文字")

            # ========== AFK ==========
            print(f"进入 AFK: {AFK_URL}")
            page.goto(AFK_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_screenshot(page, "04_afk_page", caption="AFK 页面")
            dump_page_info(page, "AFK页")

            if is_auth_page(page):
                tg_text("❌ AFK 页掉登录")
                sys.exit(1)

            for sel in [
                'button:has-text("Start")', 'button:has-text("开始")', 'button:has-text("AFK")',
                'button:has-text("Collect")', 'button:has-text("Claim")', 'button:has-text("Get Credits")',
                'button:has-text("Earn")', 'button[class*="afk"]', 'button[class*="start"]',
            ]:
                try:
                    btn = page.locator(sel).first
                    if btn.count() and btn.is_visible(timeout=2000):
                        print(f"点击 AFK 按钮: {sel}")
                        btn.click(timeout=5000)
                        time.sleep(2)
                        save_screenshot(page, "05_afk_started", caption="AFK 已启动")
                        break
                except:
                    continue

            tg_text(f"开始 AFK 挂机 {AFK_SECONDS // 60} 分钟")
            elapsed = 0
            while elapsed < AFK_SECONDS:
                time.sleep(min(60, AFK_SECONDS - elapsed))
                elapsed += 60
                print(f"  已挂机 {min(elapsed, AFK_SECONDS) // 60} 分钟")
                if elapsed == 60 or elapsed == AFK_SECONDS // 2:
                    save_screenshot(page, f"06_afk_{elapsed}s", caption=f"挂机中 {elapsed//60}min")
                if is_auth_page(page):
                    tg_text("挂机过程中掉登录")
                    break

            save_screenshot(page, "07_afk_final", caption="AFK 结束")
            dump_page_info(page, "AFK结束")
            tg_text("AFK 流程结束，请查看截图")

        except Exception as e:
            tg_text(f"异常: {e}")
            try:
                save_screenshot(page, "error", caption=f"异常 {e}")
            except:
                pass
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
