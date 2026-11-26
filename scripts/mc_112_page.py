"""Adds a full "Minecraft 1.12.2" page (/minecraft-1.12) next to the existing one, renamed "Minecraft 1.9.4".

* /minecraft-1.12 = the same page (launcher buttons, guides, Liquidity SMP dropdowns, Fullbright,
  resource packs) but it runs the 1.12 game (/minecraft/beta/) and offers the 1.12 x-ray packs.
* /minecraft keeps the 1.9.4 game and its working 1.9 packs; only its title changes.
* Fullbright is pinned per game (1.9: _eaglercraftX.g, 1.12: _eaglercraft112.g) so one page can
  never change the other game's brightness.
* Chat page "Your apps": "Minecraft 1.12.2" and "Minecraft 1.9.4".
Requires: mc_beta112_install.py, mc_packs_update.py already applied; 1.12 pack files in
minecraft_game/packs/.  Run inside the app container, then: docker restart liquidity_web
Safe to re-run. Backup: flask_app.py.bak-112page
"""
import ast
import py_compile
import re
import shutil
import sys

SITE = sys.argv[1] if len(sys.argv) > 1 else '/data/mysite'
APP = SITE + '/flask_app.py'
FILES = ('Liquidity-XRay-Outlines.zip', 'Liquidity-XRay-Outlines.png',
         'Liquidity-XRay-Classic.zip', 'Liquidity-XRay-Classic.png', 'fullbright.png',
         'Liquidity-XRay-Outlines-1.12.zip', 'Liquidity-XRay-Outlines-1.12.png',
         'Liquidity-XRay-Classic-1.12.zip', 'Liquidity-XRay-Classic-1.12.png')
FB_FIND = "const fbKey=(()=>{for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(/^_eaglercraft[^.]*[.]g$/.test(k))return k;}return '_eaglercraftX.g';})();"
START, END = '# --- minecraft 1.12 page (mc_112_page.py) ---', '# --- end minecraft 1.12 page ---'


def const(s, name):
    i = s.index('\n' + name + ' = ') + 1
    j = s.index('\n', i)
    return i, j, ast.literal_eval(s[i:j].split('=', 1)[1].strip())


def need(cond, msg):
    if not cond:
        sys.exit(msg + ' Nothing changed.')


def main():
    s = open(APP, encoding='utf-8').read()
    orig = s
    need('def minecraft_beta(' in s, 'Run mc_beta112_install.py first.')
    need('id="packsCard"' in s, 'Run mc_packs_update.py first.')

    # 1) 1.9.4 page: rename, and pin its Fullbright to the 1.9 game's settings
    s = s.replace('<title>Liquidity — Minecraft</title>', '<title>Liquidity — Minecraft 1.9.4</title>', 1)
    s = s.replace('<h1>Minecraft</h1>', '<h1>Minecraft 1.9.4</h1>', 1)
    i, j, L = const(s, 'MINECRAFT_LAUNCHER')
    if FB_FIND in L:
        L = L.replace(FB_FIND, "const fbKey='_eaglercraftX.g';")
        s = s[:i] + 'MINECRAFT_LAUNCHER = ' + repr(L) + s[j:]

    # 2) pack download whitelist: add the 1.12 packs
    import os as _os
    present = {f for f in _os.listdir(SITE + '/minecraft_game/packs') if f.endswith(('.zip', '.png'))} \
        if _os.path.isdir(SITE + '/minecraft_game/packs') else set()
    allowed = tuple(sorted(set(FILES) | present))
    s = re.sub(r"    if name not in \([^)]*\):\n        abort\(404\)",
               "    if name not in %r:\n        abort(404)" % (allowed,), s, count=1)

    # 3) build the 1.12 page + launcher from the (now renamed) 1.9.4 ones
    _, _, P = const(s, 'MINECRAFT_PAGE')
    _, _, L = const(s, 'MINECRAFT_LAUNCHER')
    reps = [('<title>Liquidity — Minecraft 1.9.4</title>', '<title>Liquidity — Minecraft 1.12.2</title>'),
            ('<h1>Minecraft 1.9.4</h1>', '<h1>Minecraft 1.12.2</h1>'),
            ('<small>EaglercraftL 1.9 · browser edition</small>', '<small>Eaglercraft 1.12.2 · browser edition (WASM)</small>'),
            ('<script src="/minecraft/launcher.js">', '<script src="/minecraft-1.12/launcher.js">'),
            ('/minecraft/packs/Liquidity-XRay-Outlines.', '/minecraft/packs/Liquidity-XRay-Outlines-1.12.'),
            ('/minecraft/packs/Liquidity-XRay-Classic.', '/minecraft/packs/Liquidity-XRay-Classic-1.12.'),
            ('Download Liquidity-XRay-Outlines.zip', 'Download Liquidity-XRay-Outlines-1.12.zip'),
            ('Download Liquidity-XRay-Classic.zip', 'Download Liquidity-XRay-Classic-1.12.zip'),
            ('<strong>Options… → Resource Packs… → Open resource pack</strong>',
             '<strong>Options… → Resource Packs… → Open Resource Pack Folder</strong>')]
    P2 = re.sub(r'<!--extra-packs-->.*?<!--/extra-packs-->', '', P, flags=re.S)  # re-added per version by mc_extra_packs.py
    for a, b in reps:
        need(a in P2, 'Expected text not found on the Minecraft page: %r.' % a[:60])
        P2 = P2.replace(a, b)
    note = ('<p class="muted" style="margin:10px 0 0">1.12.2 needs an up-to-date browser (Chrome/Edge 119+). '
            'If it will not load, use <a href="/minecraft">Minecraft 1.9.4</a>. Both play on Liquidity SMP. '
            'Singleplayer worlds, settings and packs are saved separately for each version.</p></section>')
    k = P2.index('</section>')            # end of the first card ("Ready to play")
    P2 = P2[:k] + note + P2[k + len('</section>'):]
    L2 = L
    for a, b in [("new URL('/minecraft/play/?v=input-brand-3',location.href)", "new URL('/minecraft/beta/',location.href)"),
                 ("const fbKey='_eaglercraftX.g';", "const fbKey='_eaglercraft112.g';"),
                 ('liquidity.fullbright.', 'liquidity.fullbright112.')]:
        need(a in L2, 'Expected text not found in the Minecraft launcher: %r.' % a[:60])
        L2 = L2.replace(a, b)

    block = (START + '\nMINECRAFT_112_PAGE = ' + repr(P2) + '\nMINECRAFT_112_LAUNCHER = ' + repr(L2) + '''

@app.get('/minecraft-1.12')
@app.get('/minecraft-1.12/')
def minecraft_112_home():
    response = app.response_class(MINECRAFT_112_PAGE, mimetype='text/html')
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/minecraft-1.12/launcher.js')
def minecraft_112_launcher():
    response = app.response_class(MINECRAFT_112_LAUNCHER, mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache'
    return response
''' + END + '\n\n')
    if START in s:
        a = s.index(START); b = s.index(END, a) + len(END) + 2
        s = s[:a] + block + s[b:]
    else:
        anchor = "@app.get('/minecraft/health')"
        need(s.count(anchor) == 1, 'Route anchor not found.')
        s = s.replace(anchor, block + anchor)

    # 4) chat page "Your apps"
    old = '<a class="row" href="/minecraft">Minecraft</a>'
    if old in s:
        s = s.replace(old, '<a class="row" href="/minecraft-1.12">Minecraft 1.12.2</a>'
                           '<a class="row" href="/minecraft">Minecraft 1.9.4</a>', 1)

    if s == orig:
        print('already up to date'); return
    shutil.copy2(APP, APP + '.bak-112page')
    open(APP + '.tmp', 'w', encoding='utf-8').write(s)
    py_compile.compile(APP + '.tmp', doraise=True)
    shutil.move(APP + '.tmp', APP)
    print('added /minecraft-1.12 page; renamed 1.9.4; Fullbright pinned per version; Your apps links updated')
    print('(if you use the extra packs, run mc_extra_packs.py again afterwards)')


if __name__ == '__main__':
    main()
    print('Done. Now run: docker restart liquidity_web')
