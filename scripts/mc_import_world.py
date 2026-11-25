#!/usr/bin/env python3
"""Import an Eaglercraft world (exported as a *vanilla* .zip) into the 24/7 server.

  python3 mc_import_world.py <world.zip> <HostUsername> [OtherUsername ...]

* Stops the server, backs up the current world folders to /opt/minecraft/world-backups/<time>.tar.gz
* Puts the imported world in place as "world" (Paper splits its Nether/End into world_nether /
  world_the_end on first start, so the old ones are moved into the backup)
* Moves the HOST's inventory/position from level.dat into playerdata/<uuid>.dat, because a
  dedicated server ignores the singleplayer player stored in level.dat
* Reports which guest usernames already have saved player data in the world
* Starts the server again

Undo: stop the server, delete world*, extract the backup tarball in /opt/minecraft/server, start it.
"""
import gzip
import hashlib
import io
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import time
import uuid
import zipfile

SRV = os.environ.get('MC_DIR', '/opt/minecraft/server')
BACKUPS = os.environ.get('MC_BACKUPS', '/opt/minecraft/world-backups')
DRY = os.environ.get('MC_DRYRUN') == '1'      # for testing: skip systemctl/chown


# ---------------- minimal NBT (Java edition, big-endian) ----------------
def _r_payload(t, f):
    rd = lambda n: f.read(n)
    if t == 1: return struct.unpack('>b', rd(1))[0]
    if t == 2: return struct.unpack('>h', rd(2))[0]
    if t == 3: return struct.unpack('>i', rd(4))[0]
    if t == 4: return struct.unpack('>q', rd(8))[0]
    if t == 5: return struct.unpack('>f', rd(4))[0]
    if t == 6: return struct.unpack('>d', rd(8))[0]
    if t == 7: n = struct.unpack('>i', rd(4))[0]; return rd(n)
    if t == 8: n = struct.unpack('>H', rd(2))[0]; return rd(n).decode('utf-8')
    if t == 9:
        et = rd(1)[0]; n = struct.unpack('>i', rd(4))[0]
        return (et, [_r_payload(et, f) for _ in range(n)])
    if t == 10:
        out = []
        while True:
            tt = rd(1)[0]
            if tt == 0: return out
            name = rd(struct.unpack('>H', rd(2))[0]).decode('utf-8')
            out.append((tt, name, _r_payload(tt, f)))
    if t == 11: n = struct.unpack('>i', rd(4))[0]; return list(struct.unpack('>%di' % n, rd(4 * n)))
    if t == 12: n = struct.unpack('>i', rd(4))[0]; return list(struct.unpack('>%dq' % n, rd(8 * n)))
    raise ValueError('bad NBT tag %d' % t)


def _w_payload(t, v, f):
    if t == 1: f.write(struct.pack('>b', v))
    elif t == 2: f.write(struct.pack('>h', v))
    elif t == 3: f.write(struct.pack('>i', v))
    elif t == 4: f.write(struct.pack('>q', v))
    elif t == 5: f.write(struct.pack('>f', v))
    elif t == 6: f.write(struct.pack('>d', v))
    elif t == 7: f.write(struct.pack('>i', len(v))); f.write(v)
    elif t == 8: b = v.encode('utf-8'); f.write(struct.pack('>H', len(b))); f.write(b)
    elif t == 9:
        et, items = v; f.write(bytes([et])); f.write(struct.pack('>i', len(items)))
        for it in items: _w_payload(et, it, f)
    elif t == 10:
        for tt, name, vv in v:
            b = name.encode('utf-8'); f.write(bytes([tt])); f.write(struct.pack('>H', len(b))); f.write(b)
            _w_payload(tt, vv, f)
        f.write(b'\x00')
    elif t == 11: f.write(struct.pack('>i', len(v))); f.write(struct.pack('>%di' % len(v), *v))
    elif t == 12: f.write(struct.pack('>i', len(v))); f.write(struct.pack('>%dq' % len(v), *v))
    else: raise ValueError('bad NBT tag %d' % t)


def nbt_load(path):
    f = io.BytesIO(gzip.decompress(open(path, 'rb').read()))
    t = f.read(1)[0]; name = f.read(struct.unpack('>H', f.read(2))[0]).decode('utf-8')
    return name, _r_payload(t, f)


def nbt_save(path, name, compound):
    f = io.BytesIO(); f.write(b'\x0a'); b = name.encode(); f.write(struct.pack('>H', len(b))); f.write(b)
    _w_payload(10, compound, f)
    open(path, 'wb').write(gzip.compress(f.getvalue()))


def get(compound, key):
    for t, n, v in compound:
        if n == key: return t, v
    return None, None


def offline_uuid(name):
    h = bytearray(hashlib.md5(('OfflinePlayer:' + name).encode()).digest())
    h[6] = h[6] & 0x0f | 0x30; h[8] = h[8] & 0x3f | 0x80
    return str(uuid.UUID(bytes=bytes(h)))


# ---------------- import ----------------
def sh(*cmd):
    if DRY: print('[dry-run]', ' '.join(cmd)); return
    subprocess.run(cmd, check=True)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    zpath, host, guests = sys.argv[1], sys.argv[2], sys.argv[3:]
    if not zipfile.is_zipfile(zpath):
        sys.exit('Not a zip file: %s (export the world as a VANILLA world .zip)' % zpath)

    stage = os.path.join(os.path.dirname(SRV), 'import-stage')
    shutil.rmtree(stage, ignore_errors=True); os.makedirs(stage)
    with zipfile.ZipFile(zpath) as z:
        for m in z.infolist():                      # safe extraction (no absolute/.. paths)
            p = os.path.normpath(m.filename)
            if p.startswith('..') or os.path.isabs(p): sys.exit('unsafe path in zip: ' + m.filename)
        z.extractall(stage)
    roots = [d for d, _, files in os.walk(stage) if 'level.dat' in files]
    if not roots:
        sys.exit('No level.dat found in the zip. Was it exported as a vanilla world?')
    root = min(roots, key=len)
    print('World found in zip at:', os.path.relpath(root, stage) or '.')

    name, level = nbt_load(os.path.join(root, 'level.dat'))
    _, data = get(level, 'Data')
    _, lname = get(data, 'LevelName')
    print('Level name:', lname)
    ptype, player = get(data, 'Player')

    os.makedirs(os.path.join(root, 'playerdata'), exist_ok=True)
    have = {f[:-4] for f in os.listdir(os.path.join(root, 'playerdata')) if f.endswith('.dat')}
    hu = offline_uuid(host)
    if player is not None:
        out = os.path.join(root, 'playerdata', hu + '.dat')
        if hu in have:
            shutil.copy2(out, out + '.before-host-import')
        nbt_save(out, '', player)
        print('Host %s: inventory/position moved from level.dat -> playerdata/%s.dat' % (host, hu))
    else:
        print('Host %s: no singleplayer player in level.dat (already a server-style world?)' % host)
    for g in guests:
        gu = offline_uuid(g)
        print('Guest %-16s %s' % (g, 'has saved data (items will be there)' if gu in have
                                     else 'NO saved data under this exact name (starts fresh)'))
    print('All player files in world:', len(have) + (0 if hu in have or player is None else 1))

    sh('systemctl', 'stop', 'minecraft')
    os.makedirs(BACKUPS, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    existing = [d for d in ('world', 'world_nether', 'world_the_end') if os.path.isdir(os.path.join(SRV, d))]
    if existing:
        bk = os.path.join(BACKUPS, 'before-import-%s.tar.gz' % stamp)
        with tarfile.open(bk, 'w:gz') as t:
            for d in existing: t.add(os.path.join(SRV, d), arcname=d)
        for d in existing: shutil.rmtree(os.path.join(SRV, d))
        print('Old world backed up to', bk)
    shutil.move(root, os.path.join(SRV, 'world'))
    shutil.rmtree(stage, ignore_errors=True)
    if not DRY:
        subprocess.run(['chown', '-R', 'minecraft:minecraft', SRV], check=True)
    sh('systemctl', 'start', 'minecraft')
    print('Imported. The first start converts the world (can take a minute or two):')
    print('  journalctl -u minecraft -f')


if __name__ == '__main__':
    main()
