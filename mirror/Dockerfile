# Backup address for Liquidity: a tiny nginx on Cloud Run (*.run.app) that forwards
# every request and WebSocket to the real server on Appliku. No data lives here.
FROM nginx:1.27-alpine
COPY default.conf.template /etc/nginx/templates/default.conf.template
# Cloud Run sends traffic to $PORT (8080).
ENV PORT=8080
