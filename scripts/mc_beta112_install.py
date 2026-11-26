"""Install Eaglercraft 1.12.2 (WASM) side by side at /minecraft/beta/  (current game untouched).

  python /tmp/mc_beta112_install.py /tmp/1.12_WASM.html      then: docker restart liquidity_web

* Checks the file's fingerprint (the copy inspected from the Offline-HTML-Games-Pack repo).
* Launch options: Liquidity SMP pre-added, Liquidity relay as the only/primary relay, and
  SEPARATE browser storage (worlds, settings, resource packs) so 1.12 can never touch the
  1.9 client's saves on the same site.
* Saves the patched game as minecraft_game/client112.html.gz and adds the /minecraft/beta/ route.
Safe to re-run. Backup: flask_app.py.bak-beta112
"""
import gzip
import hashlib
import py_compile
import re
import shutil
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '/tmp/1.12_WASM.html'
SITE = sys.argv[2] if len(sys.argv) > 2 else '/data/mysite'
SHA = '3f41bd86fbf72476cf8253940aa248d56105186ce64b6c3236df9e9102c92081'

OPTS = '''window.eaglercraftXOpts = {
	container: "game_frame",
	worldsDB: "worlds_112",
	resourcePacksDB: "resourcePacks_112",
	localStorageNamespace: "_eaglercraft112",
	servers: [{ addr: new URL("/mc", document.baseURI).href.replace(/^http/, "ws"), name: "Liquidity SMP", hideAddr: false }],
	relays: [{ addr: new URL("/eagler-relay", document.baseURI).href.replace(/^http/, "ws"), comment: "Liquidity", primary: true }],
	checkRelaysForUpdates: false
};'''

ROUTE = '''@app.get('/minecraft/beta')
def minecraft_beta_redirect():
    from flask import redirect
    return redirect('/minecraft/beta/', code=301)


@app.get('/minecraft/beta/')
def minecraft_beta():
    from pathlib import Path
    from flask import send_file, abort
    asset = Path(__file__).resolve().parent / 'minecraft_game' / 'client112.html.gz'
    if not asset.is_file():
        abort(503, description='Minecraft 1.12 beta is not installed.')
    r = send_file(asset, mimetype='text/html', conditional=True, max_age=3600)
    r.headers['Content-Encoding'] = 'gzip'
    r.headers['X-Content-Type-Options'] = 'nosniff'
    return r


'''


def main():
    raw = open(SRC, 'rb').read()
    if hashlib.sha256(raw).hexdigest() != SHA:
        sys.exit('Fingerprint mismatch: this is not the inspected 1.12_WASM.html. Nothing changed.')
    html = raw.decode('utf-8')
    head = html[:5000]
    m = re.search(r'window\.eaglercraftXOpts = \{.*?\n\};', head, re.S)
    if not m:
        sys.exit('Launch options not found. Nothing changed.')
    html = html[:m.start()] + OPTS + html[m.end():]
    html = html.replace('School will launch in', 'Game will launch in', 1)
    out = SITE + '/minecraft_game/client112.html.gz'
    with open(out + '.tmp', 'wb') as fh:
        fh.write(gzip.compress(html.encode('utf-8'), compresslevel=6, mtime=0))
    shutil.move(out + '.tmp', out)
    print('game: patched and saved', out)

    app = SITE + '/flask_app.py'
    s = open(app, encoding='utf-8').read()
    if 'def minecraft_beta(' in s:
        print('app: /minecraft/beta/ route already present'); return
    anchor = "@app.get('/minecraft/health')"
    if s.count(anchor) != 1:
        sys.exit('route anchor not found; game file saved but route not added')
    shutil.copy2(app, app + '.bak-beta112')
    s = s.replace(anchor, ROUTE + anchor)
    open(app + '.tmp', 'w', encoding='utf-8').write(s)
    py_compile.compile(app + '.tmp', doraise=True)
    shutil.move(app + '.tmp', app)
    print('app: added /minecraft/beta/ route')


if __name__ == '__main__':
    main()
    print('Done. Now run: docker restart liquidity_web')
