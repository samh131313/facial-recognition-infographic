"""Build extra resource packs for BOTH games from the game files on this server, and list them on
the Minecraft pages.  Run inside the app container:
    python /tmp/mc_extra_packs.py          then: docker restart liquidity_web

Packs (each built twice: 1.9.4 = pack_format 1, 1.12.2 = pack_format 3):
  Liquidity-OreHighlight  bright colored outlines on ores, only on faces touching air (no x-ray)
  Liquidity-FPS-Lite      half-resolution block textures, animations frozen (weak Chromebooks)
  Liquidity-FPS-UltraLite quarter-resolution block textures, animations frozen (very weak ones)
  Liquidity-PvP-QoL       low fire, clearer water, no pumpkin blur

The texture-based packs are derived from the game's own textures, so they are generated here from
minecraft_game/client.html.gz (1.9.4) and client112.html.gz (1.12.2) instead of being stored in git.
Safe to re-run. Backup: flask_app.py.bak-extrapacks
"""
import base64
import gzip
import io
import json
import lzma
import os
import py_compile
import re
import shutil
import struct
import sys
import zipfile
import zlib

from PIL import Image, ImageDraw

SITE = sys.argv[1] if len(sys.argv) > 1 else '/data/mysite'
GAME = SITE + '/minecraft_game'
PACKS = GAME + '/packs'
APP = SITE + '/flask_app.py'

# ----------------------------------------------------------------- reading game assets
def read_epk(raw):
    if raw[:8] != b'EAGPKG$$':
        raise ValueError('not an EPK')
    p = 8
    p += 1 + raw[p]; p += 1 + raw[p]
    p += 2 + struct.unpack('>H', raw[p:p + 2])[0]
    p += 8 + 4
    comp = chr(raw[p]); p += 1
    body = raw[p:]
    if comp == 'G': body = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(body)
    elif comp == 'Z': body = zlib.decompressobj().decompress(body)
    files, q = {}, 0
    while q < len(body):
        tag = body[q:q + 4]; q += 4
        if tag == b'END$': break
        n = body[q]; q += 1; name = body[q:q + n].decode('utf-8'); q += n
        ln = struct.unpack('>i', body[q:q + 4])[0]; q += 4
        if tag == b'FILE':
            files[name] = body[q + 4:q + ln - 1]
        q += ln + 1
    return files


def assets_19(html):
    """1.9.4 client: gzip'd JS bundle in a <style> tag, which contains base64 EPKs."""
    m = re.search(r'id="eaglercraftXClientBundle">data:application/octet-stream;base64,([A-Za-z0-9+/=]+)<', html)
    bundle = gzip.decompress(base64.b64decode(m.group(1)))
    files = {}
    for mm in re.finditer(rb'RUFHUEtH[A-Za-z0-9+/=]+', bundle):
        try: files.update(read_epk(base64.b64decode(mm.group(0))))
        except Exception: pass
    return files


def assets_112(html):
    """1.12.2 client: base64 EPW whose xz sections contain EPKs."""
    m = re.search(r'assetsURI = "data:application/octet-stream;base64,([A-Za-z0-9+/=]+)"', html)
    epw = base64.b64decode(m.group(1))
    files = {}
    for mm in re.finditer(rb'\xfd7zXZ', epw):
        try: sec = lzma.LZMADecompressor().decompress(epw[mm.start():])
        except Exception: continue
        if sec[:8] == b'EAGPKG$$':
            try: files.update(read_epk(sec))
            except Exception: pass
    return files


def load(version):
    path = GAME + ('/client.html.gz' if version == '1.9' else '/client112.html.gz')
    html = gzip.decompress(open(path, 'rb').read()).decode('utf-8')
    a = assets_19(html) if version == '1.9' else assets_112(html)
    return {k[len('assets/minecraft/'):]: v for k, v in a.items() if k.startswith('assets/minecraft/')}


# ----------------------------------------------------------------- helpers
def png(im):
    b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()


def icon(label, color, badge):
    im = Image.new('RGBA', (64, 64), color + (255,)); d = ImageDraw.Draw(im)
    for i, (x, y) in enumerate([(8, 8), (36, 8), (8, 30), (36, 30)]):
        d.rectangle([x, y, x + 19, y + 17], outline=(255, 255, 255, 180))
    if badge: d.rectangle([38, 0, 63, 11], fill=(30, 120, 220, 255)); d.text((40, 0), '1.12', fill=(255, 255, 255, 255))
    d.rectangle([0, 50, 63, 63], fill=(0, 0, 0, 200)); d.text((3, 51), label, fill=(255, 255, 255, 255))
    return png(im)


def write_pack(name, version, desc, files, ico):
    fmt = 3 if version == '1.12' else 1
    suffix = '-1.12' if version == '1.12' else ''
    out = '%s/%s%s.zip' % (PACKS, name, suffix)
    with zipfile.ZipFile(out + '.tmp', 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('pack.mcmeta', json.dumps({'pack': {'pack_format': fmt, 'description': desc + (' (1.12)' if version == '1.12' else '')}}, indent=1))
        z.writestr('pack.png', ico)
        for k, v in sorted(files.items()):
            z.writestr('assets/minecraft/' + k, v)
    os.replace(out + '.tmp', out)
    open('%s/%s%s.png' % (PACKS, name, suffix), 'wb').write(ico)
    print('built %-40s %4d files' % (os.path.basename(out), len(files)))


def frames(im):
    w, h = im.size
    return (h // w) if (h > w and h % w == 0) else 1


# ----------------------------------------------------------------- packs
ORES = {'coal_ore': (40, 40, 40), 'iron_ore': (226, 192, 170), 'gold_ore': (255, 215, 0),
        'diamond_ore': (80, 240, 255), 'emerald_ore': (40, 230, 90), 'lapis_ore': (40, 90, 255),
        'redstone_ore': (255, 40, 40), 'lit_redstone_ore': (255, 80, 80), 'quartz_ore': (245, 245, 245)}
ORE_ITEMS = ('coal_ore', 'iron_ore', 'gold_ore', 'diamond_ore', 'emerald_ore', 'lapis_ore', 'redstone_ore', 'quartz_ore')


def ore_highlight(a):
    files = {}
    W, E = 0.6, 0.02          # line width (1/16 block units) and how far it sits outside the block
    for ore, col in ORES.items():
        if 'models/block/%s.json' % ore not in a: continue
        tex = 'blocks/liquidity_hl_' + ore
        files['textures/' + tex + '.png'] = png(Image.new('RGBA', (16, 16), col + (255,)))
        els = [{'from': [0, 0, 0], 'to': [16, 16, 16], 'faces': {
            f: {'uv': [0, 0, 16, 16], 'texture': '#ore', 'cullface': f} for f in ('down', 'up', 'north', 'south', 'west', 'east')}}]
        for face, axis, val in (('north', 2, -E), ('south', 2, 16 + E), ('west', 0, -E), ('east', 0, 16 + E), ('down', 1, -E), ('up', 1, 16 + E)):
            o = [x for x in (0, 1, 2) if x != axis]
            for a0, a1, b0, b1 in ((0, 16, 0, W), (0, 16, 16 - W, 16), (0, W, W, 16 - W), (16 - W, 16, W, 16 - W)):
                frm, to = [0, 0, 0], [0, 0, 0]
                frm[axis] = to[axis] = val
                frm[o[0]], to[o[0]], frm[o[1]], to[o[1]] = a0, a1, b0, b1
                els.append({'from': frm, 'to': to, 'faces': {face: {'uv': [0, 0, 16, 16], 'texture': '#line', 'cullface': face}}})
        src = 'redstone_ore' if ore == 'lit_redstone_ore' else ore
        files['models/block/%s.json' % ore] = json.dumps({'textures': {'ore': 'blocks/' + src, 'line': tex, 'particle': 'blocks/' + src}, 'elements': els}).encode()
    for it in ORE_ITEMS:
        if 'models/item/%s.json' % it in a:
            files['models/item/%s.json' % it] = json.dumps({'parent': 'block/cube_all', 'textures': {'all': 'blocks/' + it}}).encode()
    return files


def fps(a, factor):
    files = {}
    for k, v in a.items():
        if not (k.startswith('textures/blocks/') and k.endswith('.png')): continue
        try: im = Image.open(io.BytesIO(v)).convert('RGBA')
        except Exception: continue
        w, h = im.size
        if w < 4: continue
        if frames(im) > 1: im = im.crop((0, 0, w, w)); h = w      # freeze animation: first frame only
        nw = max(1, w // factor)
        small = im.resize((nw, max(1, h * nw // w)), Image.NEAREST)
        files[k] = png(small)        # no .mcmeta in this pack -> the frozen frame is used as-is
    return files


def qol(a):
    files = {}
    for layer in ('textures/blocks/fire_layer_0.png', 'textures/blocks/fire_layer_1.png'):
        if layer not in a: continue
        im = Image.open(io.BytesIO(a[layer])).convert('RGBA'); w, h = im.size
        n = frames(im); px = im.load()
        for f in range(n):
            for y in range(int(w * 0.55)):                      # clear the top 55% of each frame
                for x in range(w): px[x, f * w + y] = (0, 0, 0, 0)
        files[layer[len(''):]] = png(im)
        if layer + '.mcmeta' in a: files[layer + '.mcmeta'] = a[layer + '.mcmeta']
    for water in ('textures/blocks/water_still.png', 'textures/blocks/water_flow.png'):
        if water not in a: continue
        im = Image.open(io.BytesIO(a[water])).convert('RGBA')
        r, g, b, al = im.split(); im = Image.merge('RGBA', (r, g, b, al.point(lambda v: v * 45 // 100)))
        files[water] = png(im)
        if water + '.mcmeta' in a: files[water + '.mcmeta'] = a[water + '.mcmeta']
    if 'textures/misc/pumpkinblur.png' in a:
        w, h = Image.open(io.BytesIO(a['textures/misc/pumpkinblur.png'])).size
        files['textures/misc/pumpkinblur.png'] = png(Image.new('RGBA', (w, h), (0, 0, 0, 0)))
    return files


PACKLIST = [  # name, title, description, builder, icon label, icon color
    ('Liquidity-OreHighlight', 'Ore Highlight', 'Bright colored outlines on ores you can actually see. No x-ray, fair for PvP.',
     ore_highlight, 'ORES', (40, 34, 60)),
    ('Liquidity-FPS-Lite', 'FPS Lite', 'Half-resolution block textures and frozen animations. For weak Chromebooks.',
     lambda a: fps(a, 2), 'FPS', (20, 60, 40)),
    ('Liquidity-FPS-UltraLite', 'FPS Ultra Lite', 'Quarter-resolution block textures and frozen animations. For very weak Chromebooks.',
     lambda a: fps(a, 4), 'FPS++', (10, 80, 30)),
    ('Liquidity-PvP-QoL', 'PvP Quality of Life', 'Low fire, clearer water and no pumpkin blur.',
     qol, 'PVP QOL', (90, 30, 30)),
]


# ----------------------------------------------------------------- website
def row(href_base, title, desc):
    return ('<div style="display:flex;gap:12px;align-items:flex-start;padding:10px;margin:10px 0;'
            'background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.12);border-radius:8px">'
            '<img src="/minecraft/packs/' + href_base + '.png" width="64" height="64" alt="" style="image-rendering:pixelated;flex:none">'
            '<div style="flex:1"><strong>' + title + '</strong><div class="muted">' + desc + '</div>'
            '<a class="button" href="/minecraft/packs/' + href_base + '.zip" download style="display:inline-block;margin-top:8px">'
            'Download ' + href_base + '.zip</a></div></div>')


def block(version):
    sfx = '-1.12' if version == '1.12' else ''
    return ('<!--extra-packs--><h3 style="margin:16px 0 4px">More packs</h3>'
            '<p class="muted" style="margin-top:0">Install them the same way as the x-ray packs. Several can be on at once '
            '(for example FPS Lite + PvP Quality of Life); packs higher in the Selected list win. '
            'Ore Highlight shows ores on cave walls, not through stone.</p>'
            + ''.join(row(n + sfx, t, d) for n, t, d, *_ in PACKLIST) + '<!--/extra-packs-->')


def const(s, name):
    i = s.index('\n' + name + ' = ') + 1; j = s.index('\n', i)
    import ast
    return i, j, ast.literal_eval(s[i:j].split('=', 1)[1].strip())


def update_site():
    s = open(APP, encoding='utf-8').read(); orig = s
    allowed = set()
    for f in os.listdir(PACKS):
        if f.endswith(('.zip', '.png')): allowed.add(f)
    s = re.sub(r"    if name not in \([^)]*\):\n        abort\(404\)",
               "    if name not in %r:\n        abort(404)" % (tuple(sorted(allowed)),), s, count=1)
    for name, version in (('MINECRAFT_PAGE', '1.9'), ('MINECRAFT_112_PAGE', '1.12')):
        if ('\n' + name + ' = ') not in s:
            print('note: %s not found (skipped)' % name); continue
        i, j, P = const(s, name)
        P = re.sub(r'<!--extra-packs-->.*?<!--/extra-packs-->', '', P, flags=re.S)
        anchor = '<p class="muted">Works best with Fullbright on.'
        if anchor not in P:
            sys.exit('Resource packs card not found on %s. Nothing changed.' % name)
        P = P.replace(anchor, block(version) + anchor, 1)
        s = s[:i] + name + ' = ' + repr(P) + s[j:]
    if s == orig:
        print('website: already up to date'); return
    shutil.copy2(APP, APP + '.bak-extrapacks')
    open(APP + '.tmp', 'w', encoding='utf-8').write(s)
    py_compile.compile(APP + '.tmp', doraise=True)
    shutil.move(APP + '.tmp', APP)
    print('website: packs listed on both Minecraft pages')


def main():
    os.makedirs(PACKS, exist_ok=True)
    for version in ('1.9', '1.12'):
        try:
            a = load(version)
        except FileNotFoundError:
            print('skip %s: game file not installed' % version); continue
        print('%s: %d game assets read' % (version, len(a)))
        for name, title, desc, fn, lab, col in PACKLIST:
            write_pack(name, version, desc, fn(a), icon(lab, col, version == '1.12'))
    if '--no-site' not in sys.argv:
        update_site()


if __name__ == '__main__':
    main()
    print('Done. Now run: docker restart liquidity_web')
