#!/usr/bin/env python3
"""
Pingless 自动续期 + AFK Credits 收集
支持：Session Cookie（推荐）
增强：全程截图 + 页面元素调试
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

# 截图输出目录
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
    """保存截图并打印路径"""
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[截图] 已保存: {path}")
    return path


def dump_page_info(page, label: str):
    """输出页面关键调试信息"""
    print(f"\n===== 页面调试 [{label}] =====")
    print(f"URL: {page.url}")
    print(f"Title: {page.title()}")

    # 所有可见按钮文字
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

    # 页面文本关键词
    try:
        body_text = page.locator("body").inner_text(timeout=3000)
        keywords = ["Renew", "续期", "Extend", "Expire", "到期", "Credit", "AFK", "Start", "Collect", "Claim", "Hours", "Remaining"]
        found = [kw for kw in keywords if kw.lower() in body_text.lower()]
        print(f"页面包含关键词: {found}")
        print(f"页面文本摘要(前800字): {body_text[:800].replace(chr(10), ' ')}")
    except Exception as e:
        print(f"获取页面文本失败: {e}")
    print("===== 调试结束 =====\n")


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
        # 隐藏 webdriver 特征
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            """
        )
        page = context.new_page()

        try:
            # ========== 1. 登录 ==========
            if not SESSION_COOKIE:
                notify("未提供 SESSION_COOKIE，无法继续")
                sys.exit(1)

            print("使用 Session Cookie 登录...")
            cookies = []
            for item in SESSION_COOKIE.split(";"):
                item = item.strip()
                if "=" in item:
                    name, value = item.split("=", 1)
                    cookies.append(
                        {
                            "name": name.strip(),
                            "value": value.strip(),
                            "domain": ".pingless.org",
                            "path": "/",
                        }
                    )
            context.add_cookies(cookies)

            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)
            save_screenshot(page, "01_home")

            if "auth" in page.url or "login" in page.url.lower():
                notify("登录失败，Cookie 可能已过期，请重新获取 SESSION_COOKIE")
                save_screenshot(page, "01_login_fail")
                sys.exit(1)

            print("登录成功")
            notify("登录成功")

            # ========== 2. 续期服务器 ==========
            print(f"访问管理页: {MANAGE_URL}")
            page.goto(MANAGE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)
            save_screenshot(page, "02_manage_page")
            dump_page_info(page, "管理页")

            # 更全面的续期按钮选择器
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
                'div[class*="renew"] button',
                'button:has-text("Claim")',
                'button:has-text("Free Renew")',
            ]

            renewed = False
            for sel in renew_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.count() > 0 and btn.is_visible(timeout=2000):
                        print(f"找到续期按钮，选择器: {sel}")
                        btn.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        btn.click(timeout=5000)
                        time.sleep(2)

                        # 尝试确认弹窗
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
                                    print("已点击确认按钮")
                                    break
                            except:
                                pass

                        time.sleep(2)
                        save_screenshot(page, "03_after_renew_click")
                        print("续期按钮已点击")
                        renewed = True
                        break
                except Exception:
                    continue

            if renewed:
                notify(f"服务器 {SERVER_ID} 续期操作已执行")
            else:
                notify(
                    "未找到续期按钮。请下载 screenshots/02_manage_page.png 查看实际页面，"
                    "并把按钮文字发给我更新选择器。"
                )
                # 额外尝试点击包含 renew 的任何元素
                try:
                    page.locator("text=/renew/i").first.click(timeout=2000)
                    print("尝试点击包含 renew 的文本元素")
                    save_screenshot(page, "03_text_renew_click")
                except:
                    pass

            # ========== 3. AFK 收集 Credits ==========
            print(f"访问 AFK 页面: {AFK_URL}")
            page.goto(AFK_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_screenshot(page, "04_afk_page")
            dump_page_info(page, "AFK页")

            # AFK 相关按钮
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

            afk_started = False
            for sel in afk_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.count() > 0 and btn.is_visible(timeout=2000):
                        print(f"找到 AFK 按钮，选择器: {sel}")
                        btn.scroll_into_view_if_needed()
                        btn.click(timeout=5000)
                        time.sleep(2)
                        save_screenshot(page, "05_afk_started")
                        print("AFK 已启动")
                        afk_started = True
                        break
                except:
                    continue

            if not afk_started:
                print("未找到明确的 Start/Collect 按钮，将保持页面打开尝试收集...")

            # 挂机一段时间
            hang_seconds = int(os.getenv("AFK_SECONDS", "60"))
            print(f"AFK 挂机中... 等待 {hang_seconds} 秒")
            for i in range(hang_seconds // 10):
                time.sleep(10)
                print(f"  已挂机 {(i+1)*10}/{hang_seconds} 秒")
                if i == (hang_seconds // 10) // 2:
                    save_screenshot(page, "06_afk_mid")

            save_screenshot(page, "07_afk_final")
            dump_page_info(page, "AFK结束")

            notify("AFK 流程执行完毕，请查看截图确认是否成功收集 Credits")

            # 输出最新 Cookie
            cookies = context.cookies()
            cookie_str = "; ".join(
                [
                    f"{c['name']}={c['value']}"
                    for c in cookies
                    if "pingless" in c.get("domain", "")
                ]
            )
            print(f"\n当前 Cookie（可更新到 Secrets）:\n{cookie_str[:300]}...")

        except PlaywrightTimeout as e:
            notify(f"超时错误: {e}")
            try:
                save_screenshot(page, "error_timeout")
            except:
                pass
            sys.exit(1)
        except Exception as e:
            notify(f"运行异常: {e}")
            try:
                save_screenshot(page, "error_exception")
            except:
                pass
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
