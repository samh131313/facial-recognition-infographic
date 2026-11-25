#!/usr/bin/env python3
"""Recover player data (inventories) from an Eaglercraft world .epk into the 24/7 server.

A *vanilla* export of an Eaglercraft world leaves out the guests' player files, but the .epk
keeps them. This reads the .epk directly (EPK v2 format), lists every player file in it, and
copies those that belong to the given usernames into /opt/minecraft/server/world/playerdata.

  python3 mc_epk_players.py "<world.epk>" --list
  python3 mc_epk_players.py "<world.epk>" Ayanokoji indefinableblob

Existing files for those players are kept as *.before-epk. Stops/starts the server around the copy.
The named players must NOT be online while this runs.
"""
import gzip
import hashlib
import io
import os
import shutil
import struct
import subprocess
import sys
import uuid
import zlib

SRV = os.environ.get('MC_DIR', '/opt/minecraft/server')
DRY = os.environ.get('MC_DRYRUN') == '1'


def read_epk(path):
    raw = open(path, 'rb').read()
    if raw[:8] != b'EAGPKG$$':
        sys.exit('Not an EPK file')
    p = 8
    n = raw[p]; p += 1 + n                      # version string
    n = raw[p]; p += 1 + n                      # package file name
    n = struct.unpack('>H', raw[p:p + 2])[0]; p += 2 + n   # comment
    p += 8                                      # timestamp
    count = struct.unpack('>i', raw[p:p + 4])[0]; p += 4
    comp = chr(raw[p]); p += 1
    body = raw[p:]
    if comp == 'G': body = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(body)   # ignores trailing bytes
    elif comp == 'Z': body = zlib.decompressobj().decompress(body)
    elif comp != '0': sys.exit('Unknown EPK compression: %r' % comp)
    files, q = {}, 0
    while q < len(body):
        tag = body[q:q + 4]; q += 4
        if tag == b'END$': break
        n = body[q]; q += 1; name = body[q:q + n].decode('utf-8'); q += n
        ln = struct.unpack('>i', body[q:q + 4])[0]; q += 4
        if tag == b'FILE':
            crc = struct.unpack('>I', body[q:q + 4])[0]; q += 4
            data = body[q:q + ln]; q += ln
            if zlib.crc32(data) & 0xffffffff != crc: sys.exit('CRC mismatch in ' + name)
            if body[q:q + 1] != b':': sys.exit('Bad EPK record after ' + name)
            q += 1
            files[name] = data
        else:
            q += ln                              # HEAD records: metadata
        if body[q:q + 1] != b'>': sys.exit('Bad EPK record separator after ' + name)
        q += 1
    print('EPK: %d files (header says %d)' % (len(files), count))
    return files


def offline_uuid(name):
    h = bytearray(hashlib.md5(('OfflinePlayer:' + name).encode()).digest())
    h[6] = h[6] & 0x0f | 0x30; h[8] = h[8] & 0x3f | 0x80
    return str(uuid.UUID(bytes=bytes(h)))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    files = read_epk(sys.argv[1])
    players = {k: v for k, v in files.items()
               if k.endswith('.dat') and ('playerdata/' in k or 'players/' in k)}
    print('Player files in the EPK:')
    for k, v in sorted(players.items()):
        print('  %-70s %d bytes' % (k, len(v)))
    if not players:
        print('  (none) - .dat files present:', sorted(k for k in files if k.endswith('.dat'))[:30])
    if sys.argv[2] == '--list':
        return

    wanted = {}
    for name in sys.argv[2:]:
        u = offline_uuid(name)
        hit = [k for k in players if os.path.basename(k)[:-4].lower() in (u, name.lower())]
        if hit:
            wanted[name] = (u, players[hit[0]], hit[0])
            print('%-16s -> found %s' % (name, hit[0]))
        else:
            print('%-16s -> NOT found (expected %s.dat or %s.dat)' % (name, u, name))
    if not wanted:
        sys.exit('Nothing to copy. Send this output to Claude.')

    if not DRY: subprocess.run(['systemctl', 'stop', 'minecraft'], check=True)
    dst = os.path.join(SRV, 'world', 'playerdata'); os.makedirs(dst, exist_ok=True)
    for name, (u, data, src) in wanted.items():
        out = os.path.join(dst, u + '.dat')
        if os.path.exists(out): shutil.copy2(out, out + '.before-epk')
        open(out, 'wb').write(data)
        print('copied %s -> playerdata/%s.dat' % (name, u))
    if not DRY:
        subprocess.run(['chown', '-R', 'minecraft:minecraft', dst], check=True)
        subprocess.run(['systemctl', 'start', 'minecraft'], check=True)
    print('Done. They can join now with those exact usernames.')


if __name__ == '__main__':
    main()
