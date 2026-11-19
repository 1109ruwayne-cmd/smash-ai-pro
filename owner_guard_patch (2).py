"""
owner_guard_patch.py — ASGI middleware that closes the open owner endpoints.

WHY MIDDLEWARE AND NOT A ROUTER
    You cannot find the file with the admin routes, and you cannot take the
    service down. Middleware does not need to know where the routes are. It sits
    in front of the whole app and refuses the request before any handler runs.
    That is the fastest real fix available without touching your route code.

THREE LINES TO INSTALL (near the bottom of main.py, after `app` exists):

    from owner_guard_patch import install_owner_guard
    install_owner_guard(app)          # reads the password from the environment
    # (leave your existing routes exactly as they are)

AND SET ONE ENVIRONMENT VARIABLE in Render → Environment:

    SMASH_OWNER_PASSWORD=<a new long password>

Until that variable is set, the guard refuses every owner request (fails closed),
so a forgotten env var can never mean "wide open".

WHAT IT PROTECTS
    /api/billing/admin*      dashboard, approve, reject, grant, coupon, security
    /api/selfheal*           internal repair history

WHAT IT DOES NOT TOUCH
    /api/usage, /api/status, /api/config, /api/chat, /api/files — your app keeps
    working for normal users. `/api/usage` already verifies the password itself.

SCOPE, STATED HONESTLY
    - One shared owner password, not per-person identities.
    - Lockout state is per-process (fine for one Render instance).
    - The password still travels in a header from the browser. The strong fix is
      a signed HttpOnly cookie; this closes the "no check at all" hole, which is
      the one being exploited today.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time

MAX_FAILURES = 3
BASE_LOCKOUT_S = 30
MAX_LOCKOUT_S = 900

PROTECTED_PREFIXES = ("/api/billing/admin", "/api/selfheal")

_SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
        return hmac.compare_digest(got, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


class _Lockout:
    def __init__(self) -> None:
        self._state: dict[str, list[float]] = {}   # key -> [failures, locked_until]
        self._lock = threading.Lock()

    def wait(self, key: str) -> float:
        with self._lock:
            f, until = self._state.get(key, [0, 0.0])
            return max(0.0, until - time.time())

    def fail(self, key: str) -> None:
        with self._lock:
            entry = self._state.setdefault(key, [0, 0.0])
            entry[0] += 1
            if entry[0] >= MAX_FAILURES:
                over = entry[0] - MAX_FAILURES
                entry[1] = time.time() + min(MAX_LOCKOUT_S, BASE_LOCKOUT_S * (2 ** over))

    def ok(self, key: str) -> None:
        with self._lock:
            self._state[key] = [0, 0.0]


def _is_protected(path: str) -> bool:
    return any(path.startswith(p) for p in PROTECTED_PREFIXES)


def _client(scope) -> str:
    if os.environ.get("SMASH_TRUSTED_PROXY") == "1":
        for name, value in scope.get("headers", []):
            if name == b"x-forwarded-for":
                return value.decode("latin-1").split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"


def _header(scope, target: bytes) -> str | None:
    for name, value in scope.get("headers", []):
        if name == target:
            return value.decode("latin-1")
    return None


async def _deny(send) -> None:
    body = b'{"detail":"Owner password required"}'
    await send({
        "type": "http.response.start",
        "status": 401,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"cache-control", b"no-store"),
        ],
    })
    await send({"type": "http.response.body", "body": body})


def install_owner_guard(app) -> None:
    """Wrap `app` so owner endpoints require the password. Call once.

    The lockout lives on the closure, not at module level. Module-level state
    would be shared by every app in the process — including test suites, where
    one test's failures would lock another test out. That is a real bug, not a
    theoretical one: it is exactly what broke on the first run.
    """
    lockout = _Lockout()

    @app.middleware("http")
    async def _owner_guard(request, call_next):
        if not _is_protected(request.url.path):
            return await call_next(request)

        stored = os.environ.get("SMASH_OWNER_PASSWORD_HASH", "").strip()
        plain = os.environ.get("SMASH_OWNER_PASSWORD", "").strip()
        if not stored and not plain:
            # Misconfigured: deny, and say why in the server log only.
            print("[owner-guard] REFUSING: set SMASH_OWNER_PASSWORD", flush=True)
            return _Response401()

        key = _client(request.scope)
        if lockout.wait(key) > 0:
            return _Response401()

        supplied = request.headers.get("x-admin-password") or ""
        if not supplied:
            lockout.fail(key)
            return _Response401()

        good = (verify_password(supplied, stored) if stored
                else hmac.compare_digest(supplied, plain))
        if not good:
            lockout.fail(key)
            return _Response401()

        lockout.ok(key)
        return await call_next(request)


class _Response401:
    """Minimal callable response, so this module needs no Starlette imports."""

    def __init__(self) -> None:
        self.status_code = 401
        self.media_type = "application/json"

    async def __call__(self, scope, receive, send):
        await _deny(send)


def _cli() -> None:
    import getpass
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "hash":
        pw = os.environ.get("PW") or getpass.getpass("New owner password: ")
        if len(pw) < 12:
            print("use at least 12 characters", file=sys.stderr)
            raise SystemExit(1)
        print(f"SMASH_OWNER_PASSWORD_HASH={hash_password(pw)}")
        return
    print(__doc__)


if __name__ == "__main__":
    _cli()
