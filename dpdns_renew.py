#!/usr/bin/env python3
"""
DigitalPlat (dpdns.org) 域名免费续期

站点已迁移：
  旧: https://dash.domain.digitalplat.org/_panel_api/...   (308 -> 新站)
  新: https://dashboard.digitalplat.org/_panel_api/...

新站要求 CSRF 双提交：
  - cookie: panel_csrf_token
  - header: X-CSRF-Token
  缺失时接口返回 400 {"code":"csrf_failed","error":"Invalid CSRF token"}

登录仍然需要 Cloudflare Turnstile token，因此保留浏览器（DrissionPage）取值。
拿到 turnstile_token + 浏览器 cookie 后，所有 API 调用都用 requests 完成。

续期接口：
  POST /_panel_api/api/domains/{domain}/renew
  headers: Idempotency-Key: <uuid4>
  body:    {"renewal_type": "free", "years": 1}
  免费续期需满足 free_renewal.available（到期前 120 天内）。
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests

BASE = "https://dashboard.digitalplat.org"
API = BASE + "/_panel_api"

EMAIL = os.environ.get("EMAIL", "").strip()
PASSWORD = os.environ.get("PASSWORD", "").strip()
DOMAIN = os.environ.get("DOMAIN", "").strip()
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "/config"))
COOKIES_FILE = CONFIG_DIR / ".dpdns_cookies.json"
STATE_FILE = CONFIG_DIR / ".dpdns_state.json"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# cookie 持久化
# --------------------------------------------------------------------------- #
def save_cookies(session):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "cookies": [
            {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
            for c in session.cookies
        ],
        "updated_at": time.time(),
    }
    COOKIES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    try:
        COOKIES_FILE.chmod(0o600)
    except OSError:
        pass
    log(f"cookies 已保存: {COOKIES_FILE}")


def load_cookies(session):
    if not COOKIES_FILE.exists():
        return False
    try:
        data = json.loads(COOKIES_FILE.read_text())
    except Exception as exc:
        log(f"读取 cookies 失败: {exc}")
        return False
    for item in data.get("cookies", []):
        try:
            session.cookies.set(
                item["name"],
                item["value"],
                domain=item.get("domain") or ".digitalplat.org",
                path=item.get("path") or "/",
            )
        except Exception:
            pass
    return bool(session.cookies)


# --------------------------------------------------------------------------- #
# API 封装
# --------------------------------------------------------------------------- #
class Api:
    def __init__(self, session=None):
        self.s = session or requests.Session()
        self.s.headers.update(
            {
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Origin": BASE,
                "Referer": BASE + "/auth/login",
                "User-Agent": UA,
            }
        )

    def csrf_token(self):
        """GET /api/security/csrf -> {csrf_token}"""
        try:
            r = self.s.get(f"{API}/api/security/csrf", timeout=30)
            tok = (r.json() or {}).get("csrf_token")
            if tok:
                return tok
        except Exception as exc:
            log(f"获取 csrf token 失败: {exc}")
        # 退化为直接从 cookie 读取（双提交，cookie 和 header 值相同）
        return self.s.cookies.get("panel_csrf_token")

    def request(self, method, path, *, json_body=None, extra_headers=None, retry_csrf=True):
        url = API + path
        headers = {}
        if extra_headers:
            headers.update(extra_headers)
        if method.upper() not in ("GET", "HEAD", "OPTIONS"):
            headers["X-CSRF-Token"] = self.csrf_token()
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        r = self.s.request(
            method, url, json=json_body, headers=headers, timeout=60, allow_redirects=False
        )
        if method.upper() not in ("GET", "HEAD", "OPTIONS") and retry_csrf:
            try:
                payload = r.json()
            except Exception:
                payload = {}
            if r.status_code == 400 and payload.get("code") == "csrf_failed":
                log("csrf 失效，重新获取后重试一次")
                headers["X-CSRF-Token"] = self.csrf_token()
                r = self.s.request(
                    method, url, json=json_body, headers=headers, timeout=60, allow_redirects=False
                )
        return r

    def me(self):
        return self.request("GET", "/api/auth/me")

    def domain(self, name):
        return self.request("GET", f"/api/domains/{requests.utils.quote(name, safe='')}")

    def renew(self, name, renewal_type="free", years=1):
        return self.request(
            "POST",
            f"/api/domains/{requests.utils.quote(name, safe='')}/renew",
            json_body={"renewal_type": renewal_type, "years": years},
            extra_headers={"Idempotency-Key": str(uuid.uuid4())},
        )

    def login(self, email, password, turnstile_token):
        return self.request(
            "POST",
            "/api/auth/login",
            json_body={
                "email": email,
                "password": password,
                "turnstile_token": turnstile_token,
            },
            retry_csrf=False,
        )


# --------------------------------------------------------------------------- #
# 浏览器取 turnstile token + cookie
# --------------------------------------------------------------------------- #
def cf_host_rules():
    """把 Cloudflare 挑战域名钉到 IPv4。

    有些容器只有 IPv4 出口，Chrome 会优先用 AAAA 记录，导致 Turnstile 的
    iframe 一直加载不出来，表现为『永远等不到 token』。
    """
    import socket

    rules = []
    for host in (
        "challenges.cloudflare.com",
        "hagen.challenges.cloudflare.com",
        "brunhild.challenges.cloudflare.com",
    ):
        try:
            infos = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)
            ip = infos[0][4][0]
            rules.append(f"MAP {host} {ip}")
        except Exception:
            continue
    return ",".join(rules)


def click_turnstile_checkbox(page):
    """Turnstile managed 模式下偶尔要手动点复选框，跨域 iframe 用 CDP 坐标点击。"""
    try:
        rect = page.run_js(
            """return (() => {
                const f = document.querySelector('iframe[src*="challenges.cloudflare.com"]');
                if (!f) return null;
                const r = f.getBoundingClientRect();
                return {x: r.x, y: r.y, w: r.width, h: r.height};
            })()"""
        )
        if not rect:
            return
        x = rect["x"] + 30
        y = rect["y"] + rect["h"] / 2
        page.run_cdp("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button="left", clickCount=1)
        page.run_cdp("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button="left", clickCount=1)
        log("已点击 Turnstile 复选框")
    except Exception as exc:
        log(f"点击 Turnstile 复选框失败: {exc}")


def browser_login_cookies(email, password, timeout_sec=180):
    """打开登录页，等 Turnstile token，返回 (cookies list, turnstile_token).

    注意：不要在浏览器里填表单。新版页面是 React 受控组件，输入会触发重渲染，
    把 Turnstile 的 iframe 弄没，token 就永远不出来。登录由 requests 完成，
    这里只需要 token + 页面 cookie。
    """
    from DrissionPage import ChromiumOptions, ChromiumPage

    co = ChromiumOptions()
    co.headless(bool(os.environ.get("HEADLESS", "").lower() in ("1", "true")))
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-dev-shm-usage")
    co.set_argument("--disable-gpu")
    co.set_argument("--window-size=1920,1080")
    # 不要伪造 UA：UA 和真实内核版本不一致更容易被 Turnstile 判定为自动化
    rules = cf_host_rules()
    if rules:
        co.set_argument(f"--host-resolver-rules={rules}")

    page = None
    try:
        page = ChromiumPage(co)
        log("浏览器已启动")

        page.get(BASE + "/auth/login")
        time.sleep(5)
        log("已打开登录页，等待 Turnstile")

        token = None
        deadline = time.time() + timeout_sec
        last_click = time.time()
        while time.time() < deadline:
            try:
                el = page.ele("css:input[name=cf-turnstile-response]", timeout=1)
                value = el.attr("value") if el else None
                if value and len(value) > 100:
                    token = value
                    break
            except Exception:
                pass
            try:
                # 注意：DrissionPage 的 run_js 按函数体执行，必须显式 return
                value = page.run_js(
                    "return window.turnstile ? window.turnstile.getResponse() : null"
                )
                if value and len(value) > 100:
                    token = value
                    break
            except Exception:
                pass

            # 每 20 秒尝试点一次 Turnstile 复选框（managed 模式偶发需要交互）
            if time.time() - last_click > 20:
                last_click = time.time()
                click_turnstile_checkbox(page)

            time.sleep(2)

        if not token:
            log("未取到 Turnstile token（可能需要人工过验证码）")
            return None, None

        cookies = []
        try:
            raw = page.cookies(all_domains=True)
        except Exception:
            raw = page.cookies()

        for c in raw:
            if isinstance(c, dict):
                cookies.append(
                    {
                        "name": c.get("name"),
                        "value": c.get("value"),
                        "domain": c.get("domain") or ".digitalplat.org",
                        "path": c.get("path") or "/",
                    }
                )
            else:  # 老版本返回 Cookie 对象
                cookies.append(
                    {
                        "name": c.name,
                        "value": c.value,
                        "domain": getattr(c, "domain", None) or ".digitalplat.org",
                        "path": getattr(c, "path", None) or "/",
                    }
                )
        cookies = [c for c in cookies if c["name"] and c["value"]]

        log(f"Turnstile token 长度={len(token)}, 浏览器 cookie 数={len(cookies)}")
        return cookies, token
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass


def install_browser_cookies(api, cookies):
    for item in cookies:
        api.s.cookies.set(
            item["name"],
            item["value"],
            domain=item.get("domain") or ".digitalplat.org",
            path=item.get("path") or "/",
        )


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def ensure_login(api):
    r = api.me()
    if r.status_code == 200:
        log("复用已有会话成功")
        return True

    log(f"会话不可用（HTTP {r.status_code}），走浏览器登录")
    log(f"使用账号: {EMAIL}（密码长度 {len(PASSWORD)}）")
    if not EMAIL or not PASSWORD:
        log("缺少 EMAIL / PASSWORD 环境变量")
        return False

    cookies, token = browser_login_cookies(EMAIL, PASSWORD)
    if not token:
        return False

    install_browser_cookies(api, cookies)
    api.s.headers["Referer"] = BASE + "/auth/login"
    r = api.login(EMAIL, PASSWORD, token)
    log(f"登录响应: HTTP {r.status_code}")

    try:
        payload = r.json()
    except Exception:
        payload = {}

    if r.status_code == 200 and payload.get("ok"):
        log("登录成功")
        save_cookies(api.s)
        return True

    if payload.get("two_factor_required"):
        log("账号开启了两步验证，无法无人值守登录；需先关闭 2FA 或加白本设备")
        return False

    log(f"登录失败: {payload or r.text[:300]}")
    return False


def main():
    log("=" * 56)
    log("DigitalPlat 域名免费续期")
    log("=" * 56)

    if not DOMAIN:
        log("缺少 DOMAIN 环境变量")
        return 1

    api = Api()
    load_cookies(api.s)

    if not ensure_login(api):
        return 1

    r = api.domain(DOMAIN)
    if r.status_code != 200:
        log(f"查询域名失败: HTTP {r.status_code} {r.text[:300]}")
        return 1

    domain = (r.json() or {}).get("domain") or {}
    expiry = domain.get("expiry_date")
    lifecycle = domain.get("lifecycle_type")
    free = domain.get("free_renewal") or {}
    log(f"域名={DOMAIN} 到期={expiry} 类型={lifecycle}")
    log(f"免费续期可用={free.get('available')} 开放时间={free.get('opens_at')}")

    if lifecycle and lifecycle != "permanent":
        pass  # 订阅型域名的免费续期同样看 free_renewal

    if not free.get("available"):
        if free.get("opens_at"):
            log("还没到免费续期窗口，跳过")
        else:
            log("该域名当前不支持免费续期，跳过")
        return 0

    if DRY_RUN:
        log("DRY_RUN=true，仅检查不续期")
        return 0

    r = api.renew(DOMAIN, renewal_type="free", years=1)
    log(f"续期响应: HTTP {r.status_code}")
    try:
        payload = r.json()
    except Exception:
        payload = {}

    if r.status_code == 200 and payload.get("ok"):
        new_domain = payload.get("domain") or {}
        log(f"续期成功，新到期时间: {new_domain.get('expiry_date')}")
        return 0

    log(f"续期失败: {payload or r.text[:500]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
