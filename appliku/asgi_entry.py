"""Entry point: the original flask_app:multiplayer_asgi behind Appliku's HTTPS proxy.

The site is only reachable over HTTPS (Appliku's Let's Encrypt certificate), but the
proxy talks plain HTTP to this container. Liquidity's origin checks (site password form,
Eaglercraft relay, arena) compare the browser's https:// Origin against the request, so
present every request as https/wss.

Backup address (mirror/ on Cloud Run): the mirror must send Host = the applikuapp.com
name so Appliku can route it, and reports the address the visitor actually used in
X-Liquidity-Host. That is trusted only when X-Liquidity-Proxy matches LIQ_PROXY_SECRET.
"""
import hmac
import os
import sys

sys.path.insert(0, os.path.join(os.environ.get("LIQ_DATA", "/data"), "mysite"))
from flask_app import multiplayer_asgi  # noqa: E402

FORCE_HTTPS = os.environ.get("LIQ_FORCE_HTTPS", "1") != "0"
PROXY_SECRET = os.environ.get("LIQ_PROXY_SECRET", "").encode()
PRIVATE = (b"x-liquidity-host", b"x-liquidity-proxy")


def _first(headers, name):
    for k, v in headers:
        if k == name:
            return v
    return None


async def app(scope, receive, send):
    kind = scope.get("type")
    if kind in ("http", "websocket"):
        scope = dict(scope)
        if FORCE_HTTPS:
            scope["scheme"] = "wss" if kind == "websocket" else "https"
        headers = list(scope.get("headers") or [])
        host = None
        secret = _first(headers, b"x-liquidity-proxy")
        mirror_host = _first(headers, b"x-liquidity-host")
        if PROXY_SECRET and secret and mirror_host and hmac.compare_digest(secret, PROXY_SECRET):
            host = mirror_host.strip()
        elif _first(headers, b"x-forwarded-host"):
            host = _first(headers, b"x-forwarded-host").split(b",")[0].strip()
        headers = [(k, v) for k, v in headers if k not in PRIVATE]
        if host and all(32 < c < 127 for c in host) and len(host) < 256:
            headers = [(k, v) for k, v in headers if k != b"host"] + [(b"host", host)]
        scope["headers"] = headers
    await multiplayer_asgi(scope, receive, send)
