#!/bin/bash
# Always-online Eaglercraft server for Liquidity (runs next to the website and the relay).
# Uses the official template: Paper 1.12.2 + EaglerXServer + ViaVersion/ViaBackwards/ViaRewind
# (EaglercraftX 1.8-based clients, like the site's "1.9.4 u35" build, can join) + AuthMe + SkinsRestorer.
#
# Run on the Hetzner server as root:  bash mc_server_setup.sh
# Safe to re-run: keeps the existing world, players and configs.
#
# This step does NOT touch the website, nginx, Docker, the relay or coturn.
# The server listens only on 127.0.0.1:25565 (not reachable from the internet).
# Browsers reach it later through the website at wss://<your-site>/mc (separate step).
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Run as root."; exit 1; }

DIR=/opt/minecraft
SRV=$DIR/server
TEMPLATE=https://github.com/Eaglercraft-Templates/Eaglercraft-Server-Paper
HEAP_MAX=${HEAP_MAX:-1536M}   # CX23 has 4 GB; the website + coturn need the rest
HEAP_MIN=${HEAP_MIN:-512M}

echo "==> Installing Java"
apt-get update -qq
if apt-cache show openjdk-17-jre-headless >/dev/null 2>&1; then JAVA_PKG=openjdk-17-jre-headless
else JAVA_PKG=openjdk-21-jre-headless; fi
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$JAVA_PKG" git >/dev/null
JAVA_BIN=$(ls -d /usr/lib/jvm/java-17-openjdk-*/bin/java /usr/lib/jvm/java-21-openjdk-*/bin/java 2>/dev/null | head -1 || true)
[ -x "$JAVA_BIN" ] || JAVA_BIN=$(command -v java)
"$JAVA_BIN" -version 2>&1 | head -1

id minecraft >/dev/null 2>&1 || useradd --system --home-dir "$DIR" --shell /usr/sbin/nologin minecraft
mkdir -p "$DIR"

if [ ! -f "$SRV/paper-1.12.2.jar" ]; then
  echo "==> Downloading the Eaglercraft Paper server template"
  rm -rf "$DIR/template-tmp"
  git clone -q --depth 1 "$TEMPLATE" "$DIR/template-tmp"
  rm -rf "$DIR/template-tmp/.git"
  mkdir -p "$SRV"
  cp -rn "$DIR/template-tmp/." "$SRV/"
  rm -rf "$DIR/template-tmp"
fi

echo "==> Server settings"
P=$SRV/server.properties
setprop() { if grep -q "^$1=" "$P"; then sed -i "s|^$1=.*|$1=$2|" "$P"; else echo "$1=$2" >> "$P"; fi; }
# Listen address: 127.0.0.1 by default. If the server already uses another private address
# (e.g. the Docker "applications" gateway 10.99.1.1 so Appliku's nginx container can reach it), keep it.
CUR_IP=$(grep -E '^server-ip=' "$P" | cut -d= -f2 || true)
setprop server-ip "${MC_BIND:-${CUR_IP:-127.0.0.1}}"
setprop server-port 25565
setprop online-mode false
setprop motd 'Liquidity SMP'
setprop max-players 20
setprop view-distance 6
setprop enable-rcon false
echo "eula=true" > "$SRV/eula.txt"
chown -R minecraft:minecraft "$DIR"

echo "==> Background service (starts on boot, restarts if it crashes)"
cat > /etc/systemd/system/minecraft.service <<UNIT
[Unit]
Description=Liquidity Eaglercraft server (Paper 1.12.2 + EaglerXServer)
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=minecraft
WorkingDirectory=$SRV
ExecStart=$JAVA_BIN -Xms$HEAP_MIN -Xmx$HEAP_MAX -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+DisableExplicitGC -Dcom.mojang.eula.agree=true -jar paper-1.12.2.jar nogui
Restart=always
RestartSec=10
# Paper saves the world when it receives SIGTERM
KillSignal=SIGTERM
TimeoutStopSec=90
SuccessExitStatus=0 1 143
MemoryMax=2200M
Nice=5

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable minecraft >/dev/null 2>&1
systemctl restart minecraft

echo "==> Waiting for the server to finish starting (first start generates the world, ~1-3 min)"
for i in $(seq 1 90); do
  if journalctl -u minecraft --since "-5min" --no-pager 2>/dev/null | grep -q 'Done ('; then
    echo "==> Minecraft server is up."
    break
  fi
  if ! systemctl is-active --quiet minecraft; then
    echo "!! The server stopped. Last log lines:"; journalctl -u minecraft -n 40 --no-pager; exit 1
  fi
  sleep 3
done
journalctl -u minecraft -n 15 --no-pager | grep -E 'Done \(|EaglerX|Listening|ERROR|WARN' || true
echo
ss -tlnp | grep ':25565' || echo "!! Nothing listening on 25565 yet - check: journalctl -u minecraft -n 80"
echo
echo "Useful commands:"
echo "  status:   systemctl status minecraft"
echo "  logs:     journalctl -u minecraft -f"
echo "  restart:  systemctl restart minecraft"
echo "  files:    $SRV"
echo
echo "NEXT (separate step, touches the website): route wss://<your-site>/mc to this server."
