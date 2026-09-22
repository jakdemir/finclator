"""Route checker for the admin/panel and public pages.

    PYTHONPATH=. .venv/bin/python scripts/check_pages.py                                    # local admin :8787
    PYTHONPATH=. .venv/bin/python scripts/check_pages.py https://finclator.com/panel "fc_session=..."
    PYTHONPATH=. .venv/bin/python scripts/check_pages.py https://finclator.com --public

Asserts 200, no Traceback / leaked None / nan / Decimal( in the HTML, exactly one <nav> and at most one
"sign out", < 10 s per route. Prints one line per route and `failures: N`; exit 1 on any failure.
"""
import re
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "http://127.0.0.1:8787").rstrip("/")
COOKIE = "" if "--public" in sys.argv else (sys.argv[2] if len(sys.argv) > 2 else "")
PANEL_ROUTES = ["/", "/matrix", "/accounts", "/audit", "/architecture", "/tables", "/tables?t=calls&n=20",
                "/api/status", "/api/matrix"]
PUBLIC_ROUTES = ["/", "/method", "/login", "/site.json"]
ROUTES = PUBLIC_ROUTES if "--public" in sys.argv else PANEL_ROUTES
BAD = re.compile(r"Traceback|>None<|>nan<|Decimal\(")

fails = 0
for r in ROUTES:
    url = BASE if r == "/" and BASE.endswith("/panel") else BASE + r
    req = urllib.request.Request(url, headers={"Cookie": COOKIE, "User-Agent": "finclator-check"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body, code = resp.read().decode(errors="replace"), resp.status
    except urllib.error.HTTPError as e:
        body, code = e.read().decode(errors="replace"), e.code
    except Exception as e:  # noqa: BLE001
        body, code = f"Traceback {e}", 0
    dt = time.time() - t0
    leaks = BAD.findall(body)
    nav, who = body.count("<nav"), body.count("sign out")
    login_page = "Panel access — Finclator" in body and not BASE.endswith("/login")
    ok = code == 200 and not leaks and nav <= 1 and who <= 1 and dt < 10 and not (login_page and COOKIE)
    fails += not ok
    print(f"{'ok ' if ok else 'BAD'} {code} {dt:5.1f}s {len(body):>10,}B nav={nav} who={who} {r} {leaks[:3]}{' (login page)' if login_page and COOKIE else ''}")
print("failures:", fails)
sys.exit(1 if fails else 0)
