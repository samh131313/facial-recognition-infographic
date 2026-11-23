#!/bin/sh
set -e
python /opt/liquidity/prepare.py
cd /data/mysite
exec uvicorn asgi_entry:app --app-dir /opt/liquidity --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips='*' --ws auto --timeout-graceful-shutdown 5
