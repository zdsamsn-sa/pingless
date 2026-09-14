#!/usr/bin/env python3
"""
Pingless 自动续期 + AFK
强化 Cookie 注入 + 详细调试 + TG 截图
"""

import os
import sys
import time
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright

BASE_URL = "https://dash.pingless.org"
SERVER_ID = os.getenv("SERVER_ID", "b7887be7")
NUMERIC_ID = os.getenv("NUMERIC_ID", "4678")
MANAGE_URL = f"{BASE_URL}/server/manage?id={SERVER_ID}&numeric={NUMERIC_ID}&mode=server"
AFK_URL = f"{BASE_URL}/afk"

SESSION_COOKIE = os.getenv("SESSION_COOKIE", "").strip()
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
AFK_SECONDS = int(os.getenv("AFK_SECONDS", "1800"))

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def tg_text(msg: str):
    print(msg)
    if TG_BOT_TOKEN and TG_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT_ID, "text": f"[Pingless] {msg}"},
                timeout=15,
            )
        except Exception as e:
            print(f"TG text error: {e}")


def tg_photo(path: Path, caption: str = ""):
    if not (TG_BOT_TOKEN and TG_CHAT_ID) or not path.exists():
        return
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto",
                data={"chat_id": TG_CHAT_ID, "caption": f"[Pingless] {caption}"[:900]},
                files={"photo": f},
                timeout=30,
            )
        print(f"[TG] 截图已发送: {path.name}")
    except Exception as e:
        print(f"TG photo error: {e}")


def save_shot(page, name: str, caption: str = ""):
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[截图] {path}")
    tg_photo(path, caption or name)
    return path


def parse_cookies(raw: str):
    """解析 Cookie 字符串，支持多种常见格式"""
    cookies = []
    if not raw:
        return cookies

    # 统一处理换行和分号
    raw = raw.replace("\n", ";").replace("\r", "")
    parts = [p.strip() for p in raw.split(";") if p.strip()]

    for part in parts:
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        # 过滤明显不是 cookie 的内容
        if name.lower() in ("path", "domain", "expires", "max-age", "secure", "httponly", "samesite"):
            continue
        cookies.append({"name": name, "value": value})
    return cookies


def inject_cookies(context, cookie_list):
    """把 cookie 注入到多个可能的 domain"""
    domains = [
        "dash.pingless.org",
        ".pingless.org",
        "pingless.org",
        ".dash.pingless.org",
    ]
    added = []
    for c in cookie_list:
        for domain in domains:
            try:
                context.add_cookies([{
                    "name": c["name"],
                    "value": c["value"],
                    "domain": domain,
                    "path": "/",
                    "secure": True,
                    "httpOnly": False,
                    "sameSite": "Lax",
                }])
                added.append(f"{c['name']}@{domain}")
            except Exception as e:
                print(f"  注入失败 {c['name']}@{domain}: {e}")
    return added


def is_auth_page(page) -> bool:
    url = page.url.lower()
    if "/auth" in url or "/login" in url:
        return True
    for text in ["Continue with Discord", "Continue with Google", "Sign in to Pingless"]:
        try:
            if page.locator(f'text="{text}"').count() > 0:
                return True
        except:
            pass
    return False


def is_public_landing(page) -> bool:
    try:
        title = page.title().lower()
        if "free minecraft server hosting" in title and "dashboard" not in title:
            return True
        body = page.locator("body").inner_text(timeout=2000).lower()
        # 宣传页特征
        if "actually free" in body or "get started free" in body:
            if page.locator('text=/logout|sign out|my servers|dashboard|account/i').count() == 0:
                return True
    except:
        pass
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900},
            locale="en-US",
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = context.new_page()

        try:
            if not SESSION_COOKIE:
                tg_text("❌ 未配置 SESSION_COOKIE")
                sys.exit(1)

            print(f"原始 Cookie 长度: {len(SESSION_COOKIE)} 字符")
            cookie_list = parse_cookies(SESSION_COOKIE)
            print(f"解析到 {len(cookie_list)} 个 Cookie:")
            for c in cookie_list:
                print(f"  - {c['name']} = {c['value'][:40]}{'...' if len(c['value'])>40 else ''}")

            if len(cookie_list) == 0:
                tg_text("❌ Cookie 解析结果为空，格式可能不对。请用 Cookie-Editor 导出 Header String 格式")
                sys.exit(1)

            added = inject_cookies(context, cookie_list)
            print(f"成功注入记录数: {len(added)}")

            # 访问首页
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_shot(page, "01_home", "首页")

            print(f"当前 URL: {page.url}")
            print(f"当前 Title: {page.title()}")

            # 打印浏览器实际持有的 cookie
            real_cookies = context.cookies()
            print(f"浏览器当前 Cookie 数量: {len(real_cookies)}")
            for c in real_cookies:
                if "pingless" in c.get("domain", ""):
                    print(f"  [实际] {c['name']} @ {c['domain']}")

            if is_auth_page(page):
                tg_text("❌ 进入了登录页，Cookie 完全无效")
                sys.exit(1)

            if is_public_landing(page):
                tg_text(
                    "❌ 仍停留在公开宣传页，Cookie 没有建立登录会话。\n"
                    "请按以下步骤重新获取：\n"
                    "1. 无痕窗口打开 dash.pingless.org 并登录成功\n"
                    "2. 用 Cookie-Editor 扩展 → Export → Header String\n"
                    "3. 完整粘贴到 GitHub Secret SESSION_COOKIE（覆盖旧值）"
                )
                sys.exit(1)

            # 验证管理页
            print(f"访问管理页: {MANAGE_URL}")
            page.goto(MANAGE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_shot(page, "02_manage", "管理页")

            if is_auth_page(page) or is_public_landing(page):
                tg_text("❌ 管理页跳转失败，Cookie 仍无效")
                sys.exit(1)

            tg_text("✅ 登录成功，已进入管理页")

            # 续期
            renewed = False
            for sel in [
                'button:has-text("Renew")', 'button:has-text("续期")', 'button:has-text("Extend")',
                'button:has-text("Renew Server")', 'button:has-text("Renew Now")',
                'a:has-text("Renew")', '[data-action="renew"]', 'button[class*="renew"]',
            ]:
                try:
                    btn = page.locator(sel).first
                    if btn.count() and btn.is_visible(timeout=2000):
                        btn.click(timeout=5000)
                        time.sleep(2)
                        for csel in ['button:has-text("Confirm")', 'button:has-text("确认")', 'button:has-text("Yes")', 'button:has-text("OK")']:
                            try:
                                if page.locator(csel).first.is_visible(timeout=1500):
                                    page.locator(csel).first.click()
                                    break
                            except:
                                pass
                        save_shot(page, "03_renewed", "续期后")
                        renewed = True
                        break
                except:
                    continue
            tg_text("续期已执行" if renewed else "未找到续期按钮，请看管理页截图")

            # AFK
            page.goto(AFK_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_shot(page, "04_afk", "AFK页")

            if is_auth_page(page):
                tg_text("❌ AFK 页掉登录")
                sys.exit(1)

            for sel in [
                'button:has-text("Start")', 'button:has-text("开始")', 'button:has-text("AFK")',
                'button:has-text("Collect")', 'button:has-text("Claim")', 'button[class*="start"]',
            ]:
                try:
                    btn = page.locator(sel).first
                    if btn.count() and btn.is_visible(timeout=2000):
                        btn.click()
                        time.sleep(2)
                        save_shot(page, "05_afk_start", "AFK启动")
                        break
                except:
                    continue

            tg_text(f"开始挂机 {AFK_SECONDS//60} 分钟")
            elapsed = 0
            while elapsed < AFK_SECONDS:
                time.sleep(min(60, AFK_SECONDS - elapsed))
                elapsed += 60
                print(f"  已挂机 {min(elapsed, AFK_SECONDS)//60} 分钟")
                if elapsed in (60, AFK_SECONDS // 2):
                    save_shot(page, f"06_afk_{elapsed}s", f"挂机中{elapsed//60}min")
                if is_auth_page(page):
                    tg_text("挂机中掉登录")
                    break

            save_shot(page, "07_done", "AFK结束")
            tg_text("全部流程结束")

        except Exception as e:
            tg_text(f"异常: {e}")
            try:
                save_shot(page, "error", str(e)[:80])
            except:
                pass
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
