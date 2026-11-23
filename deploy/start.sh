#!/bin/sh
set -e
cd /home/gerb/mysite
python /opt/liquidity/bootstrap.py
# Litestream continuously copies chat.db / gpt.db to Cloud Storage and runs the app as a child.
exec litestream replicate -config /opt/liquidity/litestream.yml \
  -exec "uvicorn flask_app:multiplayer_asgi --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips=* --ws auto --timeout-graceful-shutdown 5"
