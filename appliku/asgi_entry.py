"""Entry point: the original flask_app:multiplayer_asgi behind Appliku's HTTPS proxy.

The site is only reachable over HTTPS (Appliku's Let's Encrypt certificate), but the
proxy talks plain HTTP to this container. Liquidity's origin checks (site password form,
Eaglercraft relay, arena) compare the browser's https:// Origin against the request, so
present every request as https/wss and honour X-Forwarded-Host if the proxy rewrites Host.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.environ.get("LIQ_DATA", "/data"), "mysite"))
from flask_app import multiplayer_asgi  # noqa: E402

FORCE_HTTPS = os.environ.get("LIQ_FORCE_HTTPS", "1") != "0"


async def app(scope, receive, send):
    kind = scope.get("type")
    if kind in ("http", "websocket"):
        scope = dict(scope)
        if FORCE_HTTPS:
            scope["scheme"] = "wss" if kind == "websocket" else "https"
        headers = scope.get("headers") or []
        fwd = [v for k, v in headers if k == b"x-forwarded-host"]
        if fwd:
            host = fwd[0].split(b",")[0].strip()
            scope["headers"] = [(k, v) for k, v in headers if k != b"host"] + [(b"host", host)]
    await multiplayer_asgi(scope, receive, send)
