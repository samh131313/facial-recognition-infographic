#!/bin/bash
# Liquidity server tune-up (run as root on the Hetzner server). Safe to re-run.
#  1. 2 GB swap file (safety net so nothing crashes if RAM fills up), swappiness 10
#  2. Minecraft memory: -Xms512M -Xmx1536M  ->  -Xms1G -Xmx2G
#  3. view-distance 6 -> 8
#  4. Nightly world backup at 04:30 Indiana time (09:30 UTC), keeps the newest 7, in /root/world-backups
# Backups of every edited file: <file>.bak-<timestamp>. Restarts Minecraft at the end (~30s kick).
set -euo pipefail
TS=$(date +%s)
SRV=/opt/minecraft/server
UNIT=/etc/systemd/system/minecraft.service

echo "== 1. swap"
if swapon --show | grep -q '^/swapfile'; then
  echo "swap already on"
else
  [ -f /swapfile ] || fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  echo "swap on"
fi
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
echo 'vm.swappiness=10' > /etc/sysctl.d/99-liquidity-swap.conf
sysctl -q -p /etc/sysctl.d/99-liquidity-swap.conf
swapon --show

echo "== 2. Minecraft memory"
cp "$UNIT" "$UNIT.bak-$TS"
sed -i 's/-Xms512M/-Xms1G/; s/-Xmx1536M/-Xmx2G/' "$UNIT"
grep -o -E -- '-Xm[sx][0-9]+[MG]' "$UNIT" | tr '\n' ' '; echo

echo "== 3. view distance"
cp "$SRV/server.properties" "$SRV/server.properties.bak-$TS"
sed -i 's/^view-distance=.*/view-distance=8/' "$SRV/server.properties"
grep '^view-distance=' "$SRV/server.properties"

echo "== 4. nightly world backup"
cat > /usr/local/bin/liquidity-world-backup.sh <<'EOF'
#!/bin/bash
# World + player data + plugin data (no plugin jars). Keeps the newest 7 backups.
set -euo pipefail
OUT=/root/world-backups
mkdir -p "$OUT"
cd /opt/minecraft/server
ITEMS=()
for p in world world_nether world_the_end plugins usercache.json ops.json whitelist.json banned-players.json banned-ips.json; do
  [ -e "$p" ] && ITEMS+=("$p")
done
# The server keeps running, so tar may say "file changed as we read it" (exit 1): that is fine.
rc=0
tar czf "$OUT/world-$(date +%F-%H%M).tgz" --warning=no-file-changed --exclude='plugins/*.jar' --exclude='*/logs' "${ITEMS[@]}" || rc=$?
if [ "$rc" -gt 1 ]; then echo "backup failed (tar exit $rc)"; exit "$rc"; fi
ls -1t "$OUT"/world-*.tgz | tail -n +8 | while read -r old; do rm -f -- "$old"; done
ls -lh "$OUT"
EOF
chmod 755 /usr/local/bin/liquidity-world-backup.sh

cat > /etc/systemd/system/liquidity-world-backup.service <<'EOF'
[Unit]
Description=Liquidity nightly Minecraft world backup

[Service]
Type=oneshot
Nice=10
IOSchedulingClass=idle
ExecStart=/usr/local/bin/liquidity-world-backup.sh
EOF

cat > /etc/systemd/system/liquidity-world-backup.timer <<'EOF'
[Unit]
Description=Run the Liquidity world backup nightly

[Timer]
OnCalendar=*-*-* 09:30:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now liquidity-world-backup.timer
echo "first backup now (may take a minute)..."
/usr/local/bin/liquidity-world-backup.sh
systemctl list-timers liquidity-world-backup.timer --no-pager | head -3

echo "== restarting Minecraft to apply memory + view distance"
systemctl restart minecraft
sleep 45
systemctl is-active minecraft
ps -o rss=,args= -C java | cut -c1-120
free -m
echo "Done."
