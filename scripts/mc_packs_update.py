"""Adds a "Resource packs" card to /minecraft with two entries styled like Minecraft resource packs:
  * Liquidity X-Ray: a real resource pack (download + import steps). Files served from
    minecraft_game/packs/ at /minecraft/packs/<file>.
  * Liquidity Fullbright: an opt-in toggle. It sets the game's saved brightness (gamma) to 10
    (no potion effect), and turning it off restores the player's previous brightness.

Run inside the app container, with the pack files already copied to /data/mysite/minecraft_game/packs:
    python /tmp/mc_packs_update.py      then: docker restart liquidity_web
Safe to re-run. Backup: flask_app.py.bak-packs
"""
import py_compile
import shutil
import sys

SITE = sys.argv[1] if len(sys.argv) > 1 else '/data/mysite'
APP = SITE + '/flask_app.py'

PACK_FILES = ('Liquidity-XRay-Outlines.zip', 'Liquidity-XRay-Outlines.png',
              'Liquidity-XRay-Classic.zip', 'Liquidity-XRay-Classic.png', 'fullbright.png')

ROUTE = ('''@app.get('/minecraft/packs/<path:name>')
def minecraft_pack_file(name):
    from pathlib import Path
    from flask import send_from_directory, abort
    if name not in __PACK_FILES__:
        abort(404)
    root = Path(__file__).resolve().parent / 'minecraft_game' / 'packs'
    return send_from_directory(root, name, as_attachment=name.endswith('.zip'), max_age=3600)


''').replace('__PACK_FILES__', repr(PACK_FILES))

# HTML for the page: no single quotes or backslashes (it is inserted into a single-quoted literal).
OLD_NOTE = ('Changes apply the next time the game starts. If the game is open, '
            'choose Save and Quit to Title, then launch it again. Turning it off restores your previous brightness.')
NEW_NOTE = ('Stays on: it is re-applied every time you open this page, even if the '
            'Brightness slider reset it. If the game is open, choose Save and Quit to Title and reload this page. '
            'Turning it off restores your previous brightness.')

CARD = (
    '<section class="card" id="packsCard"><h2>Resource packs</h2>'
    '<p class="muted" style="margin-top:0">Optional extras. Only players who turn them on get them. '
    'They work in singleplayer, shared worlds and Liquidity SMP.</p>'
    '<div style="display:flex;gap:12px;align-items:flex-start;padding:10px;margin:10px 0;'
    'background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.12);border-radius:8px">'
    '<img src="/minecraft/packs/fullbright.png" width="64" height="64" alt="" style="image-rendering:pixelated;flex:none">'
    '<div style="flex:1"><strong>Liquidity Fullbright</strong> <span id="fbStatus" class="muted"></span>'
    '<div class="muted">See in caves and at night without torches or potion effects.</div>'
    '<button id="fbToggle" style="margin-top:8px">Turn on</button>'
    '<div class="muted" style="margin-top:6px">Stays on: it is re-applied every time you open this page, even if the '
    'Brightness slider reset it. If the game is open, choose Save and Quit to Title and reload this page. '
    'Turning it off restores your previous brightness.</div></div></div>'
    '<div style="display:flex;gap:12px;align-items:flex-start;padding:10px;margin:10px 0;'
    'background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.12);border-radius:8px">'
    '<img src="/minecraft/packs/Liquidity-XRay-Outlines.png" width="64" height="64" alt="" style="image-rendering:pixelated;flex:none">'
    '<div style="flex:1"><strong>X-Ray Outlines</strong>'
    '<div class="muted">Stone, dirt, sand, gravel, cobblestone and netherrack become see-through with a thin outline on cave walls, so you can see cave shapes and ores. Mossy cobblestone stays visible (dungeons).</div>'
    '<a class="button" href="/minecraft/packs/Liquidity-XRay-Outlines.zip" download style="display:inline-block;margin-top:8px">Download Liquidity-XRay-Outlines.zip</a>'
    '</div></div>'
    '<div style="display:flex;gap:12px;align-items:flex-start;padding:10px;margin:10px 0;'
    'background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.12);border-radius:8px">'
    '<img src="/minecraft/packs/Liquidity-XRay-Classic.png" width="64" height="64" alt="" style="image-rendering:pixelated;flex:none">'
    '<div style="flex:1"><strong>X-Ray Classic</strong>'
    '<div class="muted">The original style: the same blocks are fully invisible, no outlines. Only ores, spawners, lava, water and mossy cobblestone show.</div>'
    '<a class="button" href="/minecraft/packs/Liquidity-XRay-Classic.zip" download style="display:inline-block;margin-top:8px">Download Liquidity-XRay-Classic.zip</a>'
    '</div></div>'
    '<p style="margin:8px 0 4px"><strong>Installing an x-ray pack</strong> (use one at a time):</p>'
    '<ol style="margin-top:0"><li>Download it above (keep the .zip, do not unzip it).</li>'
    '<li>In the game: <strong>Options… → Resource Packs… → Open resource pack</strong> and choose the .zip.</li>'
    '<li>Click it under <em>Available Resource Packs</em>, then <strong>Select this resource pack</strong>, then <strong>Done</strong>.</li>'
    '<li>To switch or turn off: click it under <em>Selected Resource Packs</em> to move it back. Old versions: click them and choose <strong>Delete this resource pack</strong>.</li></ol>'
    '<p class="muted">Works best with Fullbright on. Tip: in the Nether or dark areas also set <strong>Video Settings → Fog: OFF</strong>.</p>'
    '</section>'
)

# Launcher JS: no double quotes or backslashes (it is inserted into a double-quoted literal).
FB_JS_V1 = (
    "const fbKey=(()=>{for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);"
    "if(/^_eaglercraft[^.]*[.]g$/.test(k))return k;}return '_eaglercraftX.g';})();"
    "const fbNL=String.fromCharCode(10);"
    "async function fbRead(){const v=localStorage.getItem(fbKey);if(!v)return null;"
    "const bytes=Uint8Array.from(atob(v),c=>c.charCodeAt(0));"
    "return await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();}"
    "async function fbWrite(t){const gz=new Uint8Array(await new Response(new Blob([t]).stream()"
    ".pipeThrough(new CompressionStream('gzip'))).arrayBuffer());let s='';for(const c of gz)s+=String.fromCharCode(c);"
    "localStorage.setItem(fbKey,btoa(s));}"
    "function fbGamma(t){const m=t.match(/^gamma:(.*)$/m);return m?parseFloat(m[1]):1;}"
    "function fbSet(t,v){return /^gamma:/m.test(t)?t.replace(/^gamma:.*$/m,'gamma:'+v):t+fbNL+'gamma:'+v;}"
    "async function fbShow(){try{const t=await fbRead();const on=!!t&&fbGamma(t)>1.5;"
    "$('fbToggle').textContent=on?'Turn off':'Turn on';$('fbStatus').textContent=on?'(on)':'(off)';}"
    "catch(e){$('fbStatus').textContent='(unavailable)';}}"
    "$('fbToggle').onclick=async()=>{try{const t=await fbRead();"
    "if(!t){$('fbStatus').textContent='(launch the game once, open Options and press Done, then try again)';return;}"
    "const g=fbGamma(t);if(g>1.5){await fbWrite(fbSet(t,localStorage.getItem('liquidity.fullbright.prev')||'1.0'));}"
    "else{localStorage.setItem('liquidity.fullbright.prev',String(g));await fbWrite(fbSet(t,'10.0'));}"
    "await fbShow();}catch(e){$('fbStatus').textContent='(could not change it: '+e+')';}};"
    "fbShow();"
)

FB_JS = (
    "const fbKey=(()=>{for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);"
    "if(/^_eaglercraft[^.]*[.]g$/.test(k))return k;}return '_eaglercraftX.g';})();"
    "const fbNL=String.fromCharCode(10);"
    "async function fbRead(){const v=localStorage.getItem(fbKey);if(!v)return null;"
    "const bytes=Uint8Array.from(atob(v),c=>c.charCodeAt(0));"
    "return await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();}"
    "async function fbWrite(t){const gz=new Uint8Array(await new Response(new Blob([t]).stream()"
    ".pipeThrough(new CompressionStream('gzip'))).arrayBuffer());let s='';for(const c of gz)s+=String.fromCharCode(c);"
    "localStorage.setItem(fbKey,btoa(s));}"
    "function fbGamma(t){const m=t.match(/^gamma:(.*)$/m);return m?parseFloat(m[1]):1;}"
    "function fbSet(t,v){return /^gamma:/m.test(t)?t.replace(/^gamma:.*$/m,'gamma:'+v):t+fbNL+'gamma:'+v;}"
    "const fbWant=()=>localStorage.getItem('liquidity.fullbright.want')==='1';"
    "async function fbApply(){const t=await fbRead();if(!t)return;const g=fbGamma(t);"
    "if(localStorage.getItem('liquidity.fullbright.want')===null&&g>1.5)localStorage.setItem('liquidity.fullbright.want','1');"
    "if(fbWant()&&g<=1.5){localStorage.setItem('liquidity.fullbright.prev',String(g));await fbWrite(fbSet(t,'10.0'));}}"
    "function fbShow(){const on=fbWant();$('fbToggle').textContent=on?'Turn off':'Turn on';"
    "$('fbStatus').textContent=on?'(on)':'(off)';}"
    "$('fbToggle').onclick=async()=>{try{const t=await fbRead();"
    "if(!t){$('fbStatus').textContent='(launch the game once, open Options and press Done, then try again)';return;}"
    "if(fbWant()){localStorage.setItem('liquidity.fullbright.want','0');"
    "await fbWrite(fbSet(t,localStorage.getItem('liquidity.fullbright.prev')||'1.0'));}"
    "else{localStorage.setItem('liquidity.fullbright.want','1');const g=fbGamma(t);"
    "if(g<=1.5)localStorage.setItem('liquidity.fullbright.prev',String(g));await fbWrite(fbSet(t,'10.0'));}"
    "fbShow();}catch(e){$('fbStatus').textContent='(could not change it: '+e+')';}};"
    "fbApply().catch(()=>{}).finally(fbShow);"
)


def main():
    s = open(APP, encoding='utf-8').read()
    orig = s
    if "def minecraft_pack_file(" not in s:
        anchor = "@app.get('/minecraft/health')"
        if s.count(anchor) != 1:
            sys.exit('route anchor not found; nothing changed')
        s = s.replace(anchor, ROUTE + anchor)
    if 'id="packsCard"' in s:                       # replace an older card with the current one
        a = s.index('<section class="card" id="packsCard">')
        b = s.index('</section>', a) + len('</section>')
        s = s[:a] + CARD + s[b:]
    import re as _re
    s = _re.sub(r"    if name not in \([^)]*\):\n        abort\(404\)", "    if name not in %r:\n        abort(404)" % (PACK_FILES,), s)
    if 'id="packsCard"' not in s:
        marker = '<section id="guideCard" class="card">'
        if s.count(marker) != 1:
            sys.exit('page marker not found; nothing changed')
        s = s.replace(marker, CARD + marker)
    launcher_line = s.split('MINECRAFT_LAUNCHER = ', 1)[1].split('\n', 1)[0]
    if FB_JS_V1 in launcher_line:                      # upgrade the first version in place
        s = s.replace(FB_JS_V1, FB_JS)
    if OLD_NOTE in s:
        s = s.replace(OLD_NOTE, NEW_NOTE)
    if 'fbToggle' not in s.split('MINECRAFT_LAUNCHER = ', 1)[1].split('\n', 1)[0]:
        lmark = "$('relayValue').value=relay;\\n"
        if s.count(lmark) != 1:
            sys.exit('launcher marker not found; nothing changed')
        s = s.replace(lmark, lmark + FB_JS + "\\n")
    if s == orig:
        print('already up to date'); return
    shutil.copy2(APP, APP + '.bak-packs')
    open(APP + '.tmp', 'w', encoding='utf-8').write(s)
    py_compile.compile(APP + '.tmp', doraise=True)
    shutil.move(APP + '.tmp', APP)
    print('updated: /minecraft/packs route, Resource packs card, Fullbright (remembers your choice)')


if __name__ == '__main__':
    main()
    print('Done. Now run: docker restart liquidity_web')
