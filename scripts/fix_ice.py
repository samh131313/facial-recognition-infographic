# Makes flask_app.py tolerate Appliku escaping quotes (\") in LIQUIDITY_EAGLER_ICE_SERVERS.
# Run inside the container:  python /tmp/fix_ice.py   (then restart the container)
import py_compile, shutil, sys
p = sys.argv[1] if len(sys.argv) > 1 else '/data/mysite/flask_app.py'
s = open(p, encoding='utf-8').read()
old = """'[{"url":"stun:stun.l.google.com:19302"}]'))"""
new = """'[{"url":"stun:stun.l.google.com:19302"}]').replace('\\\\"', '"'))"""
if new in s:
    print('already patched'); sys.exit(0)
if s.count(old) != 1:
    print('pattern not found exactly once; nothing changed'); sys.exit(1)
shutil.copy2(p, p + '.bak-ice')
open(p, 'w', encoding='utf-8').write(s.replace(old, new))
py_compile.compile(p, doraise=True)
print('patched OK (backup: %s.bak-ice)' % p)
