#!/usr/bin/env python3
"""
Pingless 自动续期 + AFK Credits
支持：
1. STORAGE_STATE_JSON（推荐，最稳，可含 localStorage）
2. SESSION_COOKIE（备用）
"""

import os
import sys
import json
import time
import base64
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright

BASE_URL = "https://dash.pingless.org"
SERVER_ID = os.getenv("SERVER_ID", "b7887be7")
NUMERIC_ID = os.getenv("NUMERIC_ID", "4678")
MANAGE_URL = f"{BASE_URL}/server/manage?id={SERVER_ID}&numeric={NUMERIC_ID}&mode=server"
AFK_URL = f"{BASE_URL}/afk"

STORAGE_STATE_JSON = os.getenv("STORAGE_STATE_JSON", "").strip()
SESSION_COOKIE = os.getenv("SESSION_COOKIE", "").strip()
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
AFK_SECONDS = int(os.getenv("AFK_SECONDS", "1800"))  # 默认 30 分钟

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
    try:
        page.screenshot(path=str(path), full_page=True)
        print(f"[截图] {path}")
        tg_photo(path, caption or name)
    except Exception as e:
        print(f"截图失败 {name}: {e}")
    return path


def dump_buttons(page, prefix: str = ""):
    """打印页面上所有可见按钮/链接文字，方便调试选择器"""
    try:
        texts = page.evaluate("""() => {
            const els = Array.from(document.querySelectorAll('button, a, [role="button"], input[type="submit"], .btn, [class*="button"]'));
            return els
                .filter(el => el.offsetParent !== null)
                .map(el => ({
                    tag: el.tagName,
                    text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 80),
                    class: (el.className || '').toString().slice(0, 60),
                    id: el.id || ''
                }))
                .filter(x => x.text.length > 0);
        }""")
        print(f"\n===== {prefix} 可见按钮/链接 =====")
        for i, t in enumerate(texts[:40]):
            print(f"  [{i}] <{t['tag']}> text='{t['text']}' class='{t['class']}' id='{t['id']}'")
        print("================================\n")
        return texts
    except Exception as e:
        print(f"dump_buttons 失败: {e}")
        return []


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
        if "free minecraft server hosting" in title:
            return True
        body = page.locator("body").inner_text(timeout=2000).lower()
        if "actually free" in body or ("get started free" in body and "logout" not in body):
            return True
    except:
        pass
    return False


def load_storage_state():
    if not STORAGE_STATE_JSON:
        return None
    raw = STORAGE_STATE_JSON
    try:
        if not raw.strip().startswith("{"):
            raw = base64.b64decode(raw).decode("utf-8")
        data = json.loads(raw)
        print(f"已加载 storage_state，cookies 数量: {len(data.get('cookies', []))}")
        if "origins" in data:
            for o in data["origins"]:
                ls = o.get("localStorage", [])
                print(f"  localStorage @ {o.get('origin')}: {len(ls)} 项")
        return data
    except Exception as e:
        print(f"解析 STORAGE_STATE_JSON 失败: {e}")
        return None


def try_click_renew(page) -> bool:
    """尝试多种方式点击续期按钮，并打印所有按钮方便调试"""
    dump_buttons(page, "管理页")

    # 精确选择器优先
    selectors = [
        'button:has-text("Renew")',
        'button:has-text("续期")',
        'button:has-text("Extend")',
        'button:has-text("Renew Server")',
        'button:has-text("Renew Now")',
        'button:has-text("Renew Free")',
        'a:has-text("Renew")',
        'button[class*="renew" i]',
        '[data-action="renew"]',
        'button:has-text("Extend Server")',
    ]

    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.count() and btn.is_visible(timeout=1500):
                print(f"找到续期按钮: {sel}")
                btn.scroll_into_view_if_needed()
                btn.click(timeout=5000)
                time.sleep(2)
                # 确认弹窗
                for csel in [
                    'button:has-text("Confirm")',
                    'button:has-text("确认")',
                    'button:has-text("Yes")',
                    'button:has-text("OK")',
                    'button:has-text("确定")',
                ]:
                    try:
                        cbtn = page.locator(csel).first
                        if cbtn.count() and cbtn.is_visible(timeout=1500):
                            cbtn.click()
                            print(f"点击确认: {csel}")
                            break
                    except:
                        pass
                time.sleep(2)
                return True
        except Exception as e:
            print(f"选择器 {sel} 失败: {e}")
            continue

    # 模糊匹配：找包含 renew / 续期 的按钮
    try:
        candidates = page.locator("button, a, [role='button']").all()
        for el in candidates:
            try:
                txt = (el.inner_text() or "").strip().lower()
                if any(k in txt for k in ["renew", "续期", "extend", "延长"]):
                    if el.is_visible():
                        print(f"模糊匹配到按钮: '{txt}'")
                        el.scroll_into_view_if_needed()
                        el.click(timeout=5000)
                        time.sleep(2)
                        return True
            except:
                continue
    except Exception as e:
        print(f"模糊匹配失败: {e}")

    return False


def try_start_afk(page) -> bool:
    """尝试启动 AFK / 收集 Credits"""
    dump_buttons(page, "AFK 页")

    selectors = [
        'button:has-text("Start")',
        'button:has-text("开始")',
        'button:has-text("AFK")',
        'button:has-text("Collect")',
        'button:has-text("Claim")',
        'button:has-text("Collect Credits")',
        'button:has-text("Start AFK")',
        'button:has-text("Go AFK")',
        'button:has-text("开始挂机")',
        '[data-action="afk"]',
        'button[class*="afk" i]',
    ]

    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.count() and btn.is_visible(timeout=1500):
                print(f"找到 AFK 按钮: {sel}")
                btn.scroll_into_view_if_needed()
                btn.click(timeout=5000)
                time.sleep(2)
                return True
        except:
            continue

    # 模糊
    try:
        candidates = page.locator("button, a, [role='button']").all()
        for el in candidates:
            try:
                txt = (el.inner_text() or "").strip().lower()
                if any(k in txt for k in ["afk", "collect", "claim", "start", "开始", "挂机"]):
                    if el.is_visible():
                        print(f"模糊匹配 AFK 按钮: '{txt}'")
                        el.scroll_into_view_if_needed()
                        el.click(timeout=5000)
                        time.sleep(2)
                        return True
            except:
                continue
    except:
        pass

    return False


def main():
    storage = load_storage_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )

        context_kwargs = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "viewport": {"width": 1400, "height": 900},
            "locale": "en-US",
        }
        if storage:
            context_kwargs["storage_state"] = storage

        context = browser.new_context(**context_kwargs)
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = context.new_page()

        try:
            if not storage and SESSION_COOKIE:
                print("使用 SESSION_COOKIE 方式...")
                cookies = []
                for part in SESSION_COOKIE.replace("\n", ";").split(";"):
                    part = part.strip()
                    if "=" in part:
                        n, v = part.split("=", 1)
                        n, v = n.strip(), v.strip()
                        if n and n.lower() not in ("path", "domain", "expires", "secure", "httponly", "samesite"):
                            for domain in ["dash.pingless.org", ".pingless.org"]:
                                cookies.append({
                                    "name": n, "value": v,
                                    "domain": domain, "path": "/",
                                    "secure": True, "sameSite": "Lax",
                                })
                context.add_cookies(cookies)
                print(f"注入 Cookie 数: {len(cookies)}")

            if not storage and not SESSION_COOKIE:
                tg_text("❌ 请配置 STORAGE_STATE_JSON（推荐）或 SESSION_COOKIE")
                sys.exit(1)

            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)
            save_shot(page, "01_home", "首页")
            print(f"URL: {page.url} | Title: {page.title()}")

            real_cookies = context.cookies()
            print(f"浏览器 Cookie 数: {len(real_cookies)}")
            for c in real_cookies:
                if "pingless" in c.get("domain", ""):
                    print(f"  {c['name']} @ {c['domain']}")

            if is_auth_page(page) or is_public_landing(page):
                tg_text("❌ 仍未登录成功，请检查 Cookie / STORAGE_STATE_JSON")
                sys.exit(1)

            # ========== 管理页续期 ==========
            page.goto(MANAGE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_shot(page, "02_manage_before", "管理页-续期前")

            if is_auth_page(page) or is_public_landing(page):
                tg_text("❌ 管理页跳转失败 / 掉登录")
                sys.exit(1)

            tg_text("✅ 登录成功，进入管理页")

            renewed = try_click_renew(page)
            time.sleep(2)
            save_shot(page, "03_manage_after", "管理页-续期后")
            tg_text("续期已点击" if renewed else "未找到续期按钮（已截图+打印按钮列表，请把截图和日志发我）")

            # ========== AFK ==========
            page.goto(AFK_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_shot(page, "04_afk_before", "AFK页-开始前")

            if is_auth_page(page):
                tg_text("❌ AFK 页掉登录")
                sys.exit(1)

            started = try_start_afk(page)
            time.sleep(2)
            save_shot(page, "05_afk_started", "AFK页-点击后")

            if started:
                tg_text(f"AFK 已启动，开始挂机 {AFK_SECONDS // 60} 分钟")
            else:
                tg_text("未找到明确的 Start/Collect 按钮，仍会保持页面打开挂机（请看截图确认是否需要手动操作）")

            # 挂机循环（保持页面活跃）
            elapsed = 0
            while elapsed < AFK_SECONDS:
                sleep_sec = min(60, AFK_SECONDS - elapsed)
                time.sleep(sleep_sec)
                elapsed += sleep_sec
                mins = elapsed // 60
                print(f"  已挂机 {mins} 分钟 / {AFK_SECONDS // 60} 分钟")

                # 偶尔动一下鼠标/滚动，防止被判定为完全空闲
                try:
                    page.mouse.move(100 + (elapsed % 50), 200 + (elapsed % 30))
                    page.evaluate("window.scrollBy(0, 10)")
                except:
                    pass

                if elapsed in (60, AFK_SECONDS // 2, AFK_SECONDS - 60) or elapsed % 300 == 0:
                    save_shot(page, f"06_afk_{elapsed}s", f"挂机中 {mins}min")

                if is_auth_page(page):
                    tg_text("挂机过程中掉登录了")
                    break

            save_shot(page, "07_done", "全部结束")
            tg_text("✅ 续期 + AFK 流程完成")

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
