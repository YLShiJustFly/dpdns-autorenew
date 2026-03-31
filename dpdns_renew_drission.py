#!/usr/bin/env python3
"""
DPDNS Auto Renewal Script - Using DrissionPage
DrissionPage is a library specifically designed to bypass automation detection
"""

import requests
import json
import os
import sys
import time
from pathlib import Path

EMAIL = os.environ.get('EMAIL', '')
PASSWORD = os.environ.get('PASSWORD', '')
DOMAIN = os.environ.get('DOMAIN', '')
TOKEN_FILE = "/config/.dpdns_token.json"
COOKIES_FILE = "/config/.dpdns_cookies.json"


def save_cookies(session):
    """Save cookies to file"""
    try:
        cookies = {cookie.name: cookie.value for cookie in session.cookies}
        with open(COOKIES_FILE, 'w') as f:
            json.dump({'cookies': cookies, 'updated_at': time.time()}, f)
        print(f"Cookies saved to {COOKIES_FILE}")
    except Exception as e:
        print(f"Failed to save cookies: {e}")


def load_cookies():
    """Load cookies from file"""
    if os.path.exists(COOKIES_FILE):
        try:
            with open(COOKIES_FILE, 'r') as f:
                data = json.load(f)
                if time.time() - data.get('updated_at', 0) < 7 * 24 * 3600:
                    return data.get('cookies')
        except:
            pass
    return None


def try_login_with_cookies():
    """Attempt to login using saved cookies"""
    cookies = load_cookies()
    if not cookies:
        return None

    print("Attempting to login with saved cookies...")
    session = requests.Session()

    for name, value in cookies.items():
        session.cookies.set(name, value, domain='dash.domain.digitalplat.org')

    test_url = f"https://dash.domain.digitalplat.org/_panel_api/api/domains/{DOMAIN}"
    try:
        resp = session.get(test_url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('ok') and data.get('domain'):
                print("Login with cookies successful")
                return session
    except Exception as e:
        print(f"Cookie login failed: {e}")

    return None


def get_turnstile_token_with_drission():
    """Use DrissionPage to get turnstile token"""
    print("Starting DrissionPage...")

    try:
        from DrissionPage import ChromiumPage, ChromiumOptions
    except ImportError:
        print("DrissionPage not installed")
        return None

    co = ChromiumOptions()
    co.headless(False)  # Must use headed mode
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--window-size', '1920,1080')

    page = None
    try:
        page = ChromiumPage(co)
        print("Browser started successfully")

        # Visit login page
        print("Visiting login page...")
        page.get('https://dash.domain.digitalplat.org/auth/login')
        time.sleep(5)

        # Fill in credentials
        print("Filling in login credentials...")
        page.ele('css:input[type=email]').input(EMAIL)
        page.ele('css:input[type=password]').input(PASSWORD)

        # Take screenshot
        page.get_screenshot('/config/login_initial.png')
        print("Screenshot saved: /config/login_initial.png")

        # Wait for Turnstile to complete
        print("Waiting for Turnstile verification to complete...")
        max_wait = 120
        waited = 0
        token = None

        while waited < max_wait:
            try:
                turnstile_input = page.ele('css:input[name=cf-turnstile-response]')
                token = turnstile_input.attr('value')
                if token and len(token) > 100:
                    print(f"Detected Turnstile token (length: {len(token)})")
                    break
            except:
                pass

            # Check if login button is enabled
            try:
                login_btn = page.ele('css:button[type=submit]')
                if not login_btn.attr('disabled'):
                    print(f"Login button enabled (waited {waited} seconds)")
                    # Try to get token again
                    try:
                        turnstile_input = page.ele('css:input[name=cf-turnstile-response]')
                        token = turnstile_input.attr('value')
                        if token and len(token) > 100:
                            print(f"Detected Turnstile token (length: {len(token)})")
                    except:
                        pass
                    break
            except:
                pass

            time.sleep(2)
            waited += 2

        page.get_screenshot('/config/login_final.png')
        print(f"Final token length: {len(token) if token else 0}")

        return token

    except Exception as e:
        print(f"Browser startup failed: {e}")
        return None

    finally:
        if page:
            page.quit()


def login_with_token(turnstile_token):
    """Login using token"""
    url = "https://dash.domain.digitalplat.org/_panel_api/api/auth/login"

    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://dash.domain.digitalplat.org",
        "Referer": "https://dash.domain.digitalplat.org/auth/login",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    data = {
        "email": EMAIL,
        "password": PASSWORD,
        "turnstile_token": turnstile_token
    }

    session = requests.Session()
    resp = session.post(url, headers=headers, json=data)
    print(f"Login response: {resp.status_code}")

    if resp.status_code == 200:
        result = resp.json()
        if result.get('ok'):
            print("Login successful")
            save_cookies(session)
            return session
        else:
            print(f"Login failed: {result.get('error', 'Unknown error')}")
            return None
    else:
        print(f"Login failed: {resp.text}")
        return None


def renew_domain(session):
    """Renew domain"""
    url = f"https://dash.domain.digitalplat.org/_panel_api/api/domains/{DOMAIN}/renew"

    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Referer": f"https://dash.domain.digitalplat.org/domains/{DOMAIN}",
    }

    resp = session.post(url, headers=headers, json={})
    print(f"Renewal response: {resp.status_code}")

    try:
        data = resp.json()
    except:
        data = {"error": resp.text}

    if resp.status_code == 200 and data.get("ok"):
        print("Renewal successful!")
        return True
    elif "more than 180 days" in str(data):
        print("Not yet time for renewal (within 180 days)")
        return True
    else:
        print(f"Renewal failed: {data.get('error', resp.text)}")
        return False


def main():
    print("=" * 60)
    print("DPDNS Auto Renewal Tool (DrissionPage Edition)")
    print("=" * 60)

    if not EMAIL or not PASSWORD:
        print("Please set EMAIL and PASSWORD environment variables")
        return 1

    # First try to login with cookies
    session = try_login_with_cookies()

    if not session:
        # Use DrissionPage to get token
        print("\n[Start] Using DrissionPage to get Turnstile Token...")
        new_token = get_turnstile_token_with_drission()

        if not new_token:
            print("\nUnable to get turnstile_token")
            return 1

        print(f"\n[Login] Using Token to login and renew...")
        session = login_with_token(new_token)

    if not session:
        print("\nLogin failed")
        return 1

    success = renew_domain(session)

    if success:
        print("\nRenewal successful!")
        return 0
    else:
        print("\nRenewal failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
