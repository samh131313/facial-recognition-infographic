# Liquidity on Google Cloud Run.
# Layout mirrors PythonAnywhere so flask_app.py runs unchanged:
#   HOME=/home/gerb          -> chat.db, gpt.db (local disk, backed up by Litestream)
#   /home/gerb/mysite        -> app code + games (baked into the image)
#   /home/gerb/mysite/media, pages, downloads -> Cloud Storage buckets (mounted)
FROM python:3.12-slim

ARG LITESTREAM_VERSION=0.3.13
ADD https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-v${LITESTREAM_VERSION}-linux-amd64.tar.gz /tmp/litestream.tgz
RUN tar -xzf /tmp/litestream.tgz -C /usr/local/bin litestream && rm /tmp/litestream.tgz

ENV HOME=/home/gerb \
    PYTHONPATH=/secrets \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /home/gerb/mysite
# app/ is filled by scripts/deploy.ps1 from your PythonAnywhere export (never committed).
COPY app/ /home/gerb/mysite/
COPY deploy/ /opt/liquidity/
RUN rm -f /home/gerb/mysite/secret.py \
 && mkdir -p media pages downloads \
 && chmod +x /opt/liquidity/start.sh

CMD ["/opt/liquidity/start.sh"]
