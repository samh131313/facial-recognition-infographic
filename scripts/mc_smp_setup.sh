#!/bin/bash
# "Donut-style" survival PvP setup for Liquidity SMP.
#  - installs LuckPerms (+ EssentialsXSpawn if missing), fingerprint-checked
#  - EssentialsX: 5 s teleport delay, 45 s cooldown, 3 homes
#  - gives every player: chat, ignore, suicide, list, seen, tps, afk, skin,
#    homes, spawn, tpa/tpahere/tpaccept/tpdeny, random teleport
#  - keepInventory OFF, world border at the maximum
# Restarts the Minecraft server twice (~2 min). Run as root:  bash mc_smp_setup.sh
set -euo pipefail
SRV=/opt/minecraft/server
PL=$SRV/plugins
cd "$PL"

get() { # url file sha256
  if [ ! -f "$2" ]; then
    curl -fsSL -o "$2.tmp" "$1"
    echo "$3  $2.tmp" | sha256sum -c --quiet || { rm -f "$2.tmp"; echo "!! fingerprint mismatch for $2"; exit 1; }
    mv "$2.tmp" "$2"; echo "installed $2"
  else echo "already have $2"; fi
}
get https://download.luckperms.net/1679/bukkit/loader/LuckPerms-Bukkit-5.5.92.jar LuckPerms-Bukkit-5.5.92.jar \
    9a8dbe05ee18030a76c65900ab54c405e51c5b92373f6a4722db52ace9d7add0
get https://github.com/EssentialsX/Essentials/releases/download/2.20.1/EssentialsXSpawn-2.20.1.jar EssentialsXSpawn-2.20.1.jar \
    650d7c6a33865a02c5ffa4eb710def28e73d972c9aef85b2b1f4e71b9bd261a0

ESS=$PL/Essentials/config.yml
[ -f "$ESS" ] || { echo "!! $ESS missing (has EssentialsX started once?)"; exit 1; }
cp -n "$ESS" "$ESS.bak-smp" || true
sed -i 's/^teleport-cooldown: .*/teleport-cooldown: 45/; s/^teleport-delay: .*/teleport-delay: 5/' "$ESS"
python3 - "$ESS" <<'PY'
import re,sys
p=sys.argv[1]; s=open(p).read()
s=re.sub(r'(?m)^(sethome-multiple:\n  default:) \d+', r'\1 3', s)
open(p,'w').write(s)
PY
grep -nE '^teleport-(cooldown|delay):|^sethome-multiple:' -A1 "$ESS" | head -6

# temporary RCON (internal address only, random password) so this script can run commands
P=$SRV/server.properties
PASS=$(openssl rand -hex 24)
cp "$P" "$P.bak-smp"
setp() { if grep -q "^$1=" "$P"; then sed -i "s|^$1=.*|$1=$2|" "$P"; else echo "$1=$2" >> "$P"; fi; }
setp enable-rcon true; setp rcon.port 25575; setp rcon.password "$PASS"
chown -R minecraft:minecraft "$SRV"

waitup() { for i in $(seq 1 100); do journalctl -u minecraft --since "-4min" --no-pager | grep -q 'Done (' && return 0; sleep 3; done; echo "!! server did not start"; exit 1; }
echo "==> restarting (1/2)"; systemctl restart minecraft; sleep 5; waitup; sleep 5

HOST=$(grep '^server-ip=' "$P" | cut -d= -f2); HOST=${HOST:-127.0.0.1}
python3 - "$HOST" "$PASS" <<'PY'
import socket,struct,sys,time
host,pw=sys.argv[1],sys.argv[2]
s=socket.create_connection((host,25575),timeout=10)
def pkt(i,t,b):
    d=struct.pack('<ii',i,t)+b.encode()+b'\x00\x00'; s.sendall(struct.pack('<i',len(d))+d)
    n=struct.unpack('<i',s.recv(4))[0]; r=b''
    while len(r)<n: r+=s.recv(n-len(r))
    return r[8:-2].decode('utf-8','replace')
pkt(1,3,pw)
nodes=['essentials.msg','essentials.reply','essentials.me','essentials.ignore','essentials.suicide',
       'essentials.list','essentials.seen','essentials.afk','bukkit.command.tps',
       'skinsrestorer.command','skinsrestorer.command.set','skinsrestorer.command.clear',
       'essentials.sethome','essentials.home','essentials.delhome','essentials.sethome.multiple',
       'essentials.spawn','essentials.tpa','essentials.tpahere','essentials.tpaccept','essentials.tpdeny',
       'essentials.tpr']
cmds=['lp group default permission set %s true' % n for n in nodes]
cmds+=['gamerule keepInventory false','worldborder center 0 0','worldborder set 60000000']
for i,c in enumerate(cmds,2):
    out=pkt(i,2,c); print('>',c,'\n ',out.strip().replace('\n',' ')[:150]); time.sleep(0.3)
PY

echo "==> turning RCON back off, restarting (2/2)"
setp enable-rcon false; setp rcon.password ""
chown minecraft:minecraft "$P"
systemctl restart minecraft; sleep 5; waitup
echo "Done. In-game as op, set up random teleport:  /settpr center   /settpr minrange 500   /settpr maxrange 10000"
