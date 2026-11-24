#!/bin/bash
# Run in Azure Cloud Shell (Bash):  bash deploy.sh liquidity.applikuapp.com [secret]
# Creates a free (F1) Linux Node web app that forwards to your Appliku site.
set -euo pipefail
TARGET=${1:?Usage: bash deploy.sh your-app.applikuapp.com [existing-secret]}
TARGET=${TARGET#https://}; TARGET=${TARGET%%/*}
SECRET=${2:-$(openssl rand -hex 32)}
RG=liquidity-rg
LOCATION=${LOCATION:-eastus2}
SKU=${SKU:-F1}
NAME_FILE=~/.liquidity-mirror-name
NAME=$(cat "$NAME_FILE" 2>/dev/null || echo "liquidity-$(openssl rand -hex 3)")
echo "$NAME" > "$NAME_FILE"
cd "$(dirname "$0")"

echo "==> Resource group $RG in $LOCATION"
az group create -n "$RG" -l "$LOCATION" -o none

echo "==> Deploying web app $NAME ($SKU plan, takes a few minutes)"
az webapp up -n "$NAME" -g "$RG" -l "$LOCATION" --runtime "NODE:22-lts" --sku "$SKU" --os-type Linux -o none

echo "==> Settings: WebSockets on, HTTPS only, target + secret"
az webapp config set -n "$NAME" -g "$RG" --web-sockets-enabled true --startup-file "node server.js" -o none
az webapp update -n "$NAME" -g "$RG" --https-only true -o none
az webapp config appsettings set -n "$NAME" -g "$RG" -o none --settings \
  TARGET="$TARGET" PROXY_SECRET="$SECRET" SCM_DO_BUILD_DURING_DEPLOYMENT=false
az webapp restart -n "$NAME" -g "$RG" -o none

HOST=$(az webapp show -n "$NAME" -g "$RG" --query defaultHostName -o tsv)
echo
echo "Backup address:  https://$HOST"
echo
echo "NOW in Appliku -> liquidity -> Environment Variables, set:"
echo "  LIQ_PROXY_SECRET = $SECRET"
echo "then click Deploy Now. Keep the secret private."
