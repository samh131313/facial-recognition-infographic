"""Only let the Liquidity website's own Minecraft pages use the shared-world relay (/eagler-relay).

Before: the relay also accepted the 'null' origin, i.e. Eaglercraft opened from a downloaded
.html file - so anyone with any client (including hacked ones) could use your relay.
After: only pages served by this site (same https origin) are accepted. Other websites were
already blocked.
Run inside the app container:  python /tmp/relay_lockdown.py   then: docker restart liquidity_web
Safe to re-run. Backup: flask_app.py.bak-relaylock
"""
import py_compile
import shutil
import sys

APP = (sys.argv[1] if len(sys.argv) > 1 else '/data/mysite') + '/flask_app.py'
OLD = ("    # Downloaded HTML and sandboxed game frames send the literal null origin.\n"
       "    if origins[0] == 'null':\n"
       "        return True\n")
NEW = ("    # Locked down (relay_lockdown.py): downloaded/offline clients send the null origin.\n"
       "    if origins[0] == 'null':\n"
       "        return False\n")

s = open(APP, encoding='utf-8').read()
if NEW in s:
    print('already locked down'); sys.exit(0)
if s.count(OLD) != 1:
    sys.exit('Relay origin check not found. Nothing changed.')
shutil.copy2(APP, APP + '.bak-relaylock')
open(APP + '.tmp', 'w', encoding='utf-8').write(s.replace(OLD, NEW))
py_compile.compile(APP + '.tmp', doraise=True)
shutil.move(APP + '.tmp', APP)
print('relay now only accepts the Liquidity website')
print('Done. Now run: docker restart liquidity_web')
