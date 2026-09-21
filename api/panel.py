"""Vercel Python function: the admin panel behind the session cookie set by api/auth.js.

Same HMAC scheme as auth.js (SESSION_SECRET over "session|email|exp", base64url payload "." signature). The DB is the
committed data/finclator.db bundled with the deployment (read-only filesystem → copied to /tmp for WAL/pragmas).
Local-only widgets (process probes, live log, vendor balance, rebuild links) are neutralised in-process.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import shutil
import sqlite3
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
SECRET = os.environ.get("SESSION_SECRET", "")
OWNER = os.environ.get("OWNER_EMAIL", "").lower()

# ── DB: the deployment filesystem is read-only; SQLite needs a writable dir for the WAL journal even for reads ──
_DB_SRC = ROOT / "data" / "finclator.db"
_DB_TMP = Path("/tmp") / "finclator.db"


def _db_path() -> Path:
    if not _DB_TMP.exists() or _DB_TMP.stat().st_size != _DB_SRC.stat().st_size:
        shutil.copyfile(_DB_SRC, _DB_TMP)
    return _DB_TMP


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


# ── session ──────────────────────────────────────────────────────────────────────────────────────────────────────
def _session_email(cookie_header: str) -> str | None:
    tok = None
    for part in (cookie_header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == "fc_session":
            tok = v
    if not tok or "." not in tok or not SECRET:
        return None
    p, _, sig = tok.partition(".")
    try:
        payload = base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)).decode()
    except Exception:  # noqa: BLE001
        return None
    want = base64.urlsafe_b64encode(hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    if not hmac.compare_digest(want, sig):
        return None
    purpose, email, exp = payload.split("|")
    if purpose != "session" or float(exp) < time.time() * 1000:
        return None
    return email


def _approved(email: str) -> bool:
    """Re-check approval on every request so a revoked user is out immediately (users.json in the private Blob)."""
    if email == OWNER:
        return True
    try:
        import urllib.request
        # private blobs are not fetchable by URL; ask our own auth function instead (same deployment, cookie forwarded)
        req = urllib.request.Request(f"{os.environ.get('SITE_URL', 'https://finclator.com')}/auth/me")
        req.add_header("Cookie", _current_cookie)
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200 and json.load(r).get("email") == email
    except Exception:  # noqa: BLE001
        return False


_current_cookie = ""


# ── panel rendering: reuse src.admin, with the local-only helpers patched out ────────────────────────────────────
def _render(path: str, qs: str, email: str) -> tuple[int, str, str]:
    os.environ.setdefault("FINCLATOR_ACTIVE_MODEL", os.environ.get("PANEL_MODEL", "qwen3:30b-a3b-instruct-2507-q4_K_M"))
    import sys
    sys.path.insert(0, str(ROOT))
    from src import admin, audit  # noqa: PLC0415

    admin._proc_running = lambda pattern: False
    admin._credits = lambda: None
    admin._log_tail = lambda n=200: "(live pipeline log is only available on the operator's machine)"
    admin.connect = _connect
    audit.connect = _connect
    audit.OUT = Path("/tmp/audit.html")
    who = f"<span style='margin-left:auto;color:#9aa'>{admin.html.escape(email)} · <a href='/auth/logout' style='color:#9ecbff'>sign out</a> · <a href='/' style='color:#9ecbff'>site</a></span>"
    orig_page = admin._page

    def page(title, body, active):
        html = orig_page(title, body, active)
        # rewrite tab links to live under /panel and drop the meta refresh + rebuild link (no writers in production)
        for old, new in (("href='/'", "href='/panel'"), ("href='/matrix'", "href='/panel/matrix'"), ("href='/accounts'", "href='/panel/accounts'"),
                         ("href='/audit'", "href='/panel/audit'"), ("href='/architecture'", "href='/panel/architecture'"),
                         ("href='/tables'", "href='/panel/tables'"), ("href='/api/status'", "href='/panel/api/status'"),
                         ("href='/tables?", "href='/panel/tables?"), ("href='/matrix?rebuild=1'", "href='/panel/matrix'"),
                         ("fetch('/api/log')", "fetch('/panel/api/log')")):
            html = html.replace(old, new)
        html = html.replace("<meta http-equiv=refresh content=60>", "").replace("<meta http-equiv=refresh content=30>", "")
        return html.replace("</nav>", who + "</nav>", 1)

    admin._page = page
    conn = _connect()
    try:
        if path in ("", "/", "progress"):
            return 200, "text/html; charset=utf-8", admin.page_progress(conn)
        if path == "matrix":
            return 200, "text/html; charset=utf-8", admin.page_matrix(conn)
        if path == "accounts":
            return 200, "text/html; charset=utf-8", admin.page_accounts(conn)
        if path == "audit":
            q = parse_qs(qs)
            acc = (q.get("account") or [None])[0]
            return 200, "text/html; charset=utf-8", page("audit", audit.body(conn, limit=600, account=acc), "/audit")
        if path == "architecture":
            return 200, "text/html; charset=utf-8", admin.page_architecture(conn)
        if path == "tables":
            return 200, "text/html; charset=utf-8", admin.page_tables(conn, qs)
        if path == "api/status":
            return 200, "application/json", json.dumps(admin.status(conn), indent=1)
        if path == "api/log":
            return 200, "text/plain; charset=utf-8", admin._log_tail()
        if path == "api/matrix":
            p = ROOT / "data" / "matrix.json"
            return 200, "application/json", p.read_text() if p.exists() else "{}"
        return 404, "text/plain; charset=utf-8", "not found"
    finally:
        conn.close()
        admin._page = orig_page


class handler(BaseHTTPRequestHandler):  # noqa: N801 — Vercel's Python runtime looks for `handler`
    def log_message(self, format, *args):  # noqa: A002
        pass

    def _send(self, code: int, ctype: str, body: str, extra: dict | None = None):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "private, no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        global _current_cookie
        u = urlparse(self.path)
        q = parse_qs(u.query)
        sub = (q.get("p") or [""])[0].strip("/")
        # pass the remaining query (minus p) to the page, e.g. tables?t=calls&o=200
        qs = "&".join(f"{k}={v}" for k, vs in q.items() if k != "p" for v in vs)
        _current_cookie = self.headers.get("Cookie", "")
        email = _session_email(_current_cookie)
        if not email:
            return self._send(302, "text/plain", "", {"Location": f"/login?next=/panel/{sub}"})
        if not _approved(email):
            return self._send(302, "text/plain", "", {"Location": "/login?e=denied"})
        try:
            code, ctype, body = _render(sub, qs, email)
        except Exception:  # noqa: BLE001
            import traceback
            code, ctype, body = 500, "text/plain; charset=utf-8", "panel error\n\n" + traceback.format_exc()
        self._send(code, ctype, body)
