"""Open "Minecraft 1.12.2" and "Multiplayer test" inside the chat (keeping the sidebar), like the other apps.

Run inside the app container:  python /tmp/mc_embed_apps.py   then: docker restart liquidity_web
Safe to re-run. Backup: flask_app.py.bak-embed
"""
import py_compile
import shutil
import sys

APP = (sys.argv[1] if len(sys.argv) > 1 else '/data/mysite') + '/flask_app.py'
OLD = "['/gpt','/pages','/minecraft','/shooter-test/']"
NEW = "['/gpt','/pages','/minecraft','/minecraft-1.12','/multiplayer-test','/shooter-test/']"

s = open(APP, encoding='utf-8').read()
done = False
for old, new in ((OLD, NEW), (OLD.replace("'", "\\'"), NEW.replace("'", "\\'"))):
    if new in s:
        print('already up to date'); sys.exit(0)
    if s.count(old) == 1:
        shutil.copy2(APP, APP + '.bak-embed')
        s = s.replace(old, new)
        open(APP + '.tmp', 'w', encoding='utf-8').write(s)
        py_compile.compile(APP + '.tmp', doraise=True)
        shutil.move(APP + '.tmp', APP)
        print('Minecraft 1.12.2 and Multiplayer test now open inside the chat'); done = True
        break
if not done:
    sys.exit('App list not found. Nothing changed.')
print('Done. Now run: docker restart liquidity_web')
