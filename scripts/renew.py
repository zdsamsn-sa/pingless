#!/usr/bin/env python3
"""
Pingless 自动续期 + AFK Credits
优先使用 STORAGE_STATE_JSON（最稳）
截图/通知策略：仅在「续期成功」和「挂机完成」时发送
"""

import os
import sys
import json
import time
import base64
import re
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright

BASE_URL = "https://dash.pingless.org"
SERVER_ID = os.getenv("SERVER_ID", "b7887be7")
NUMERIC_ID = os.getenv("NUMERIC_ID", "4678")
MANAGE_URL = f"{BASE_URL}/server/manage?id={SERVER_ID}&numeric={NUMERIC_ID}&mode=server"
AFK_URL = f"{BASE_URL}/afk"

STORAGE_STATE_JSON = os.getenv("STORAGE_STATE_JSON", "").strip()
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


def save_shot(page, name: str, send_tg: bool = False, caption: str = ""):
    """默认只保存本地截图，不发 Telegram。需要通知时传 send_tg=True"""
    path = SCREENSHOT_DIR / f"{name}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
        print(f"[截图] {path}")
        if send_tg:
            tg_photo(path, caption or name)
    except Exception as e:
        print(f"截图失败 {name}: {e}")
    return path


def dump_buttons(page, prefix: str = ""):
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
        for i, t in enumerate(texts[:50]):
            print(f"  [{i}] <{t['tag']}> text='{t['text']}' class='{t['class']}' id='{t['id']}'")
        print("================================\n")
        return texts
    except Exception as e:
        print(f"dump_buttons 失败: {e}")
        return []


def has_session_cookie(context) -> bool:
    for c in context.cookies():
        name = c.get("name", "").lower()
        if name in ("pingless.sid", "sid", "userid", "user_id", "session", "token"):
            print(f"检测到会话 Cookie: {c['name']}")
            return True
    return False


def is_logged_in(page, context=None) -> bool:
    url = page.url.lower()
    if "/auth" in url or "/login" in url:
        return False
    if context and has_session_cookie(context):
        try:
            body = page.locator("body").inner_text(timeout=3000).lower()
            public_signals = ["actually free", "get started free", "spin up a minecraft server"]
            private_signals = ["logout", "sign out", "dashboard", "my servers", "create server",
                               "server list", "console", "file manager", "renew", "afk", "credits"]
            has_public = any(s in body for s in public_signals)
            has_private = any(s in body for s in private_signals)
            if has_private:
                return True
            if has_public and not has_private:
                return False
            return True
        except:
            return True
    return False


def load_storage_state():
    if not STORAGE_STATE_JSON:
        return None
    raw = STORAGE_STATE_JSON.strip()
    try:
        if not raw.startswith("{"):
            try:
                raw = base64.b64decode(raw).decode("utf-8")
            except Exception:
                raw = base64.b64decode(re.sub(r"\s+", "", raw)).decode("utf-8")
        data = json.loads(raw)
        print(f"[storage_state] cookies: {len(data.get('cookies', []))}")
        if "origins" in data:
            for o in data["origins"]:
                print(f"  localStorage @ {o.get('origin')}: {len(o.get('localStorage', []))} 项")
        return data
    except Exception as e:
        print(f"解析 STORAGE_STATE_JSON 失败: {e}")
        return None


def try_click_renew(page) -> bool:
    dump_buttons(page, "管理页")
    selectors = [
        'button:has-text("Renew")', 'button:has-text("续期")', 'button:has-text("Extend")',
        'button:has-text("Renew Server")', 'button:has-text("Renew Now")', 'button:has-text("Renew Free")',
        'a:has-text("Renew")', 'button[class*="renew" i]', '[data-action="renew"]',
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.count() and btn.is_visible(timeout=1500):
                print(f"找到续期按钮: {sel}")
                btn.scroll_into_view_if_needed()
                btn.click(timeout=5000)
                time.sleep(2)
                for csel in ['button:has-text("Confirm")', 'button:has-text("确认")',
                             'button:has-text("Yes")', 'button:has-text("OK")', 'button:has-text("确定")']:
                    try:
                        cbtn = page.locator(csel).first
                        if cbtn.count() and cbtn.is_visible(timeout=1500):
                            cbtn.click()
                            print(f"点击确认: {csel}")
                            break
                    except:
                        pass
                return True
        except Exception as e:
            print(f"选择器 {sel} 失败: {e}")
    try:
        for el in page.locator("button, a, [role='button']").all():
            try:
                txt = (el.inner_text() or "").strip().lower()
                if any(k in txt for k in ["renew", "续期", "extend", "延长"]):
                    if el.is_visible():
                        print(f"模糊匹配到: '{txt}'")
                        el.scroll_into_view_if_needed()
                        el.click(timeout=5000)
                        time.sleep(2)
                        return True
            except:
                continue
    except:
        pass
    return False


def try_start_afk(page) -> bool:
    dump_buttons(page, "AFK 页")
    selectors = [
        'button:has-text("Start")', 'button:has-text("开始")', 'button:has-text("AFK")',
        'button:has-text("Collect")', 'button:has-text("Claim")',
        'button:has-text("Collect Credits")', 'button:has-text("Start AFK")',
        'button:has-text("Go AFK")', 'button:has-text("开始挂机")',
        '[data-action="afk"]', 'button[class*="afk" i]',
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
    try:
        for el in page.locator("button, a, [role='button']").all():
            try:
                txt = (el.inner_text() or "").strip().lower()
                if any(k in txt for k in ["afk", "collect", "claim", "start", "开始", "挂机"]):
                    if el.is_visible():
                        print(f"模糊匹配 AFK: '{txt}'")
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
            print("已使用 STORAGE_STATE_JSON 创建上下文")

        context = browser.new_context(**context_kwargs)
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = context.new_page()

        try:
            if not storage:
                tg_text("❌ 请配置 STORAGE_STATE_JSON")
                sys.exit(1)

            print(f"直接访问管理页: {MANAGE_URL}")
            page.goto(MANAGE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(6)
            save_shot(page, "01_manage_first")  # 仅本地，不发 TG
            print(f"URL: {page.url} | Title: {page.title()}")

            real_cookies = context.cookies()
            print(f"浏览器当前 Cookie 数: {len(real_cookies)}")
            for c in real_cookies:
                if "pingless" in c.get("domain", ""):
                    print(f"  {c['name']}={str(c['value'])[:40]}... @ {c['domain']}")

            if "/auth" in page.url.lower() or "free minecraft server hosting" in page.title().lower():
                print("管理页被重定向，尝试首页后再进管理页...")
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
                time.sleep(4)
                page.goto(MANAGE_URL, wait_until="domcontentloaded", timeout=60000)
                time.sleep(5)
                save_shot(page, "01c_manage_retry")

            if not is_logged_in(page, context):
                if has_session_cookie(context):
                    print("有会话 Cookie，强制继续执行...")
                else:
                    tg_text("❌ 登录失败，请重新导出 storage_state")
                    sys.exit(1)
            else:
                print("✅ 登录成功")

            # ========== 续期 ==========
            page.goto(MANAGE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_shot(page, "02_manage_before")  # 仅本地

            renewed = try_click_renew(page)
            time.sleep(2)
            # 只有续期成功才发通知 + 截图
            if renewed:
                save_shot(page, "03_renew_success", send_tg=True, caption="✅ 续期成功")
                tg_text("✅ 续期成功")
            else:
                save_shot(page, "03_renew_fail", send_tg=True, caption="⚠️ 未找到续期按钮")
                tg_text("⚠️ 未找到续期按钮（请看截图）")

            # ========== AFK ==========
            page.goto(AFK_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            save_shot(page, "04_afk_before")  # 仅本地

            started = try_start_afk(page)
            time.sleep(2)
            save_shot(page, "05_afk_started")  # 仅本地
            print(f"AFK {'已启动' if started else '未找到按钮，仍保持页面打开'}，开始挂机 {AFK_SECONDS//60} 分钟")

            elapsed = 0
            while elapsed < AFK_SECONDS:
                sleep_sec = min(60, AFK_SECONDS - elapsed)
                time.sleep(sleep_sec)
                elapsed += sleep_sec
                print(f"  已挂机 {elapsed//60} / {AFK_SECONDS//60} 分钟")
                try:
                    page.mouse.move(100 + (elapsed % 50), 200 + (elapsed % 30))
                    page.evaluate("window.scrollBy(0, 5)")
                except:
                    pass
                # 中途截图只存本地，不发 TG
                if elapsed in (60, AFK_SECONDS // 2) or elapsed % 300 == 0:
                    save_shot(page, f"06_afk_{elapsed}s")

            # 挂机完成：发送通知 + 截图
            save_shot(page, "07_afk_done", send_tg=True, caption=f"✅ AFK 挂机完成（{AFK_SECONDS//60}分钟）")
            tg_text(f"✅ AFK 挂机完成（{AFK_SECONDS//60}分钟）")

        except Exception as e:
            tg_text(f"❌ 异常: {e}")
            try:
                save_shot(page, "error", send_tg=True, caption=f"异常: {str(e)[:80]}")
            except:
                pass
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
