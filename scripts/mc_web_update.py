"""Adds the always-online server (Liquidity SMP, wss://<site>/mc) to the website's Minecraft:
1. minecraft_game/client.html.gz: a default "Liquidity SMP" entry in Multiplayer.
   The Liquidity relay stays the primary shared-world relay (unchanged).
2. flask_app.py: the new game-file size check, a cache-busting version, and an
   "Always-online server" help section with a copy-address button on /minecraft.

Run inside the app container:  python /tmp/mc_web_update.py   (then: docker restart liquidity_web)
Safe to re-run (skips parts already done). Backups: *.bak-mcweb
"""
import gzip
import py_compile
import re
import shutil
import sys

SITE = sys.argv[1] if len(sys.argv) > 1 else '/data/mysite'
GZ = SITE + '/minecraft_game/client.html.gz'
APP = SITE + '/flask_app.py'

SERVER_JS = ('servers: [{ addr: new URL("/mc", document.baseURI).href.replace(/^http/, "ws"), '
             'name: "Liquidity SMP", hideAddr: false }],\n\t')

HELP_HTML = (
    '<section class="card"><h2>Always-online server</h2>'
    '<p><strong>Liquidity SMP</strong> runs 24/7 on our server. Nobody needs to host, so you can play any time.</p>'
    '<ol><li>Launch the game and choose <strong>Multiplayer</strong>. <strong>Liquidity SMP</strong> is already in the list. '
    'If you don’t see it, choose <strong>Add Server</strong> and paste the address below.</li>'
    '<li>Join. The first time, open chat (<strong>T</strong>) right away and type '
    '<code>/register yourpassword yourpassword</code>. Pick a new password you don’t use anywhere else.</li>'
    '<li>Every time after that, type <code>/login yourpassword</code> when you join. To change it: '
    '<code>/changepassword old new</code>.</li>'
    '<li>Always use the <strong>same username</strong>. Your items, home and password belong to that name.</li></ol>'
    '<input id="serverValue" aria-label="Liquidity SMP server address" readonly>'
    '<button id="copyServer">Copy server address</button>'
    '<p class="muted">Shared worlds with join codes still work too. See <strong>Play with friends</strong>.</p></section>'
)

LAUNCHER_JS = ("const mcServer=new URL('/mc',location.href).href.replace(/^http/,'ws');"
               "$('serverValue').value=mcServer;"
               "$('copyServer').onclick=async()=>{try{await navigator.clipboard.writeText(mcServer);"
               "$('copyServer').textContent='Copied';}catch{$('serverValue').select();}};\\n")


def patch_game():
    raw = open(GZ, 'rb').read()
    html = gzip.decompress(raw).decode('utf-8')
    head = html[:60000]
    if 'name: "Liquidity SMP"' in head:
        print('game: default server already present')
        return len(raw)
    idx = head.find('relays:')
    if idx < 0 or head.count('relays:') != 1:
        sys.exit('game: could not find exactly one "relays:" in the launch options; nothing changed')
    if re.search(r'\bservers\s*:', head):
        sys.exit('game: launch options already define "servers:"; nothing changed (send this to Claude)')
    html = html[:idx] + SERVER_JS + html[idx:]
    data = gzip.compress(html.encode('utf-8'), compresslevel=9, mtime=0)
    shutil.copy2(GZ, GZ + '.bak-mcweb')
    with open(GZ + '.tmp', 'wb') as fh:
        fh.write(data)
    shutil.move(GZ + '.tmp', GZ)
    print('game: added default server "Liquidity SMP" (%d -> %d bytes)' % (len(raw), len(data)))
    return len(data)


def patch_app(size):
    s = open(APP, encoding='utf-8').read()
    orig = s
    s, n = re.subn(r'^MINECRAFT_ASSET_BYTES = \d+$', 'MINECRAFT_ASSET_BYTES = %d' % size, s, flags=re.M)
    if n != 1:
        sys.exit('app: MINECRAFT_ASSET_BYTES not found exactly once; nothing changed')
    if 'v=input-brand-2' in s:
        s = s.replace('v=input-brand-2', 'v=input-brand-3')
    if 'id="serverValue"' not in s:
        marker = '<section id="guideCard" class="card">'
        if s.count(marker) != 1:
            sys.exit('app: help-section marker not found; nothing changed')
        s = s.replace(marker, HELP_HTML + marker)
        lmark = "$('relayValue').value=relay;\\n"
        if s.count(lmark) != 1:
            sys.exit('app: launcher marker not found; nothing changed')
        s = s.replace(lmark, lmark + LAUNCHER_JS)
    if s == orig:
        print('app: already up to date')
        return
    shutil.copy2(APP, APP + '.bak-mcweb')
    with open(APP + '.tmp', 'w', encoding='utf-8') as fh:
        fh.write(s)
    py_compile.compile(APP + '.tmp', doraise=True)
    shutil.move(APP + '.tmp', APP)
    print('app: size check = %d, cache version bumped, help section added' % size)


if __name__ == '__main__':
    patch_app(patch_game())
    print('Done. Now run: docker restart liquidity_web')
