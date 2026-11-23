# Liquidity on Appliku (Hetzner server).
# Everything that must survive deploys lives on ONE persistent volume mounted at /data,
# laid out exactly like your PythonAnywhere home folder:
#   /data/chat.db, /data/gpt.db, /data/.flask_session_key
#   /data/mysite/{flask_app.py, gpt_router.py, secret.py, media, pages, downloads, minecraft_game, fps_test}
FROM python:3.12-slim

ENV HOME=/data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# app/ may hold flask_app.py / gpt_router.py (once the repo is private). If it is empty,
# the copy imported from PythonAnywhere (on the volume) is used instead.
COPY app/ /opt/liquidity/app/
COPY appliku/ /opt/liquidity/
RUN chmod +x /opt/liquidity/start.sh

EXPOSE 8000
CMD ["/opt/liquidity/start.sh"]
