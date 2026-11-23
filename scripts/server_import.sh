#!/bin/bash
# Run on your Hetzner server (ssh root@SERVER_IP) after copying the export there:
#   scp liquidity-export.tar.gz root@SERVER_IP:/root/
# Finds the Liquidity container (the one with a volume at /data) and hands it the export.
# The app notices it within 10 seconds and imports it (first time only).
set -euo pipefail
FILE=${1:-/root/liquidity-export.tar.gz}
[ -f "$FILE" ] || { echo "Not found: $FILE"; exit 1; }
C=""
for id in $(docker ps -q); do
  if docker inspect -f '{{range .Mounts}}{{.Destination}} {{end}}' "$id" | tr ' ' '\n' | grep -qx /data; then
    C=$id; break
  fi
done
[ -n "$C" ] || { echo "No running container with a /data volume. Check the app is deployed and its volume target is /data."; exit 1; }
echo "Copying into container $(docker inspect -f '{{.Name}}' "$C") ..."
docker cp "$FILE" "$C":/data/liquidity-export.tar.gz.part
docker exec "$C" mv /data/liquidity-export.tar.gz.part /data/liquidity-export.tar.gz
echo "Done. Watch it import with:  docker logs -f $C"
