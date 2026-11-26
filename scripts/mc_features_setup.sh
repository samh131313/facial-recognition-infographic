#!/bin/bash
# Liquidity SMP extras (run on the server as root):  bash mc_features_setup.sh
#  1. Voice chat: turns on EaglerXServer's built-in voice and points it at our TURN server
#  2. Stats: installs a 5-minute timer that copies a stats summary to the website
# Restarts the Minecraft server once (~1 min).
set -euo pipefail
BASE=https://raw.githubusercontent.com/samh131313/facial-recognition-infographic/${REV:-claude/pythonanywhwre-chromebook-migration-yo2dk7}
EX=/opt/minecraft/server/plugins/EaglercraftXServer
[ -f "$EX/settings.yml" ] || { echo "!! $EX/settings.yml not found"; exit 1; }

echo "==> Voice chat"
cp -n "$EX/settings.yml" "$EX/settings.yml.bak-voice" 2>/dev/null || true
cp -n "$EX/ice_servers.yml" "$EX/ice_servers.yml.bak-voice" 2>/dev/null || true
grep -n 'enable_voice_service' "$EX/settings.yml" || echo "(key not present yet)"
sed -i 's/^\(\s*enable_voice_service:\).*/\1 true/' "$EX/settings.yml"
grep -n 'enable_voice_service' "$EX/settings.yml"
PUB=$(ip -4 route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')
TPASS=$(cat /etc/liquidity-turn.pass 2>/dev/null || true)
python3 - "$EX/ice_servers.yml" "$PUB" "$TPASS" <<'PY'
import re,sys
p,pub,pw=sys.argv[1:4]
s=open(p).read() if __import__('os').path.exists(p) else ''
def setblock(s,key,body):
    pat=re.compile(r'(?ms)^%s:.*?(?=^[^\s-]|\Z)'%re.escape(key))  # lists may be unindented
    new=key+':\n'+body
    return pat.sub(lambda m:new,s,count=1) if pat.search(s) else s.rstrip('\n')+('\n' if s else '')+new
s=setblock(s,'ice_servers_no_passwd','  - stun:%s:3478\n  - stun:stun.l.google.com:19302\n'%pub)
if pw:
    s=setblock(s,'ice_servers_passwd',''.join('  - url: turn:%s:3478?transport=%s\n    username: liquidity\n    password: %s\n'%(pub,t,pw) for t in ('udp','tcp')))
open(p,'w').write(s)
print(open(p).read())
PY
chown -R minecraft:minecraft "$EX"

echo "==> Stats exporter (every 5 minutes)"
curl -fsSL "$BASE/scripts/smp_stats_export.py" -o /usr/local/bin/liquidity-smp-stats
chmod +x /usr/local/bin/liquidity-smp-stats
cat > /etc/systemd/system/liquidity-smp-stats.service <<UNIT
[Unit]
Description=Export Liquidity SMP stats to the website
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/bin/liquidity-smp-stats
UNIT
cat > /etc/systemd/system/liquidity-smp-stats.timer <<UNIT
[Unit]
Description=Export Liquidity SMP stats every 5 minutes
[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now liquidity-smp-stats.timer
/usr/bin/python3 /usr/local/bin/liquidity-smp-stats

echo "==> Restarting Minecraft for voice chat"
systemctl restart minecraft
echo "Done. Voice: join Liquidity SMP and look for the voice button in the pause/chat menu."
