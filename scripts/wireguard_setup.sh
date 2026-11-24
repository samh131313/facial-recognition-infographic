#!/bin/bash
# Personal WireGuard VPN on your Hetzner server.
#   First run (sets up the server + first device):  bash wireguard_setup.sh iphone
#   Add another device later:                        bash wireguard_setup.sh laptop
# Prints a QR code: scan it in the WireGuard app (iPhone: "Add a tunnel" -> "Create from QR code").
# Also needs a Hetzner firewall rule: inbound UDP 51820 from Any IPv4.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Run as root."; exit 1; }
NAME=${1:-iphone}
case "$NAME" in *[!A-Za-z0-9_-]*|'') echo "Device name: letters, numbers, - or _ only."; exit 1;; esac
PORT=${PORT:-51820}
NET=10.8.0
DIR=/etc/wireguard
CONF=$DIR/wg0.conf

if ! command -v wg >/dev/null || ! command -v qrencode >/dev/null; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq wireguard qrencode iptables
fi

ROUTE=$(ip -4 route get 1.1.1.1)
IFACE=$(awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}' <<<"$ROUTE")
PUBIP=$(awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}' <<<"$ROUTE")
umask 077
mkdir -p "$DIR/clients"

if [ ! -f "$CONF" ]; then
  echo "==> Creating WireGuard server on $PUBIP:$PORT (interface $IFACE)"
  SK=$(wg genkey)
  wg pubkey <<<"$SK" > "$DIR/server.pub"
  cat > "$CONF" <<CFG
[Interface]
Address = $NET.1/24
ListenPort = $PORT
PrivateKey = $SK
# Docker (used by Appliku) blocks forwarding by default, so allow the VPN explicitly.
PostUp = iptables -I FORWARD 1 -i %i -j ACCEPT; iptables -I FORWARD 1 -o %i -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT; iptables -t nat -A POSTROUTING -s $NET.0/24 -o $IFACE -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT; iptables -t nat -D POSTROUTING -s $NET.0/24 -o $IFACE -j MASQUERADE
CFG
  echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-wireguard.conf
  sysctl -q -p /etc/sysctl.d/99-wireguard.conf
  if command -v ufw >/dev/null && ufw status | grep -q 'Status: active'; then
    ufw allow "$PORT"/udp >/dev/null
    ufw route allow in on wg0 out on "$IFACE" >/dev/null
  fi
  systemctl enable --now wg-quick@wg0
fi

CLIENT=$DIR/clients/$NAME.conf
if [ -f "$CLIENT" ]; then
  echo "==> Device '$NAME' already exists; showing its QR code again."
else
  USED=$(grep -oE "AllowedIPs = $NET\.[0-9]+" "$CONF" | awk -F. '{print $4}' | sort -n | tail -1 || true)
  HOSTNUM=$(( ${USED:-1} + 1 ))
  [ "$HOSTNUM" -lt 255 ] || { echo "No free addresses left."; exit 1; }
  IP=$NET.$HOSTNUM
  CSK=$(wg genkey); CPK=$(wg pubkey <<<"$CSK"); PSK=$(wg genpsk)
  printf '\n# %s\n[Peer]\nPublicKey = %s\nPresharedKey = %s\nAllowedIPs = %s/32\n' "$NAME" "$CPK" "$PSK" "$IP" >> "$CONF"
  cat > "$CLIENT" <<CFG
[Interface]
PrivateKey = $CSK
Address = $IP/32
DNS = 1.1.1.1, 9.9.9.9

[Peer]
PublicKey = $(cat "$DIR/server.pub")
PresharedKey = $PSK
Endpoint = $PUBIP:$PORT
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
CFG
  wg syncconf wg0 <(wg-quick strip wg0)
  echo "==> Added device '$NAME' ($IP)"
fi

echo
qrencode -t ansiutf8 < "$CLIENT"
echo
echo "Scan this in the WireGuard app. Config file: $CLIENT"
echo "Remember: Hetzner firewall needs inbound UDP $PORT allowed."
