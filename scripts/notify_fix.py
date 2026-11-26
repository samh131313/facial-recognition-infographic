"""Website notification check + fix. Run inside the app container:
    python /tmp/notify_fix.py            then: docker restart liquidity_web
* Push notifications were still signed as the old PythonAnywhere site; now they use the
  current address (LIQUIDITY_PUBLIC_ORIGIN, else https://liquidity.applikuapp.com).
  Gives Apple/Google push servers 10s instead of 4s.
* Prints a health report: who has device notifications on, recent delivery results,
  errors, and whether the server can reach the Google/Apple/Mozilla push services.
Safe to re-run. Backup: flask_app.py.bak-notify
"""
import glob
import os
import py_compile
import shutil
import sqlite3
import sys
import time
from urllib.parse import urlparse

SITE = sys.argv[1] if len(sys.argv) > 1 else '/data/mysite'
APP = SITE + '/flask_app.py'

OLD = "vapid_claims={'sub':'https://gerbilzillo.pythonanywhere.com'},ttl=86400,timeout=4"
NEW = ("vapid_claims={'sub':os.environ.get('LIQUIDITY_PUBLIC_ORIGIN','').rstrip('/') "
       "or 'https://liquidity.applikuapp.com'},ttl=86400,timeout=10")


def patch():
    s = open(APP, encoding='utf-8').read()
    if NEW in s:
        print('push sender: already updated'); return
    if OLD not in s:
        print('push sender: pattern not found, left unchanged'); return
    shutil.copy2(APP, APP + '.bak-notify')
    open(APP + '.tmp', 'w', encoding='utf-8').write(s.replace(OLD, NEW))
    py_compile.compile(APP + '.tmp', doraise=True)
    shutil.move(APP + '.tmp', APP)
    print('push sender: now signed as the current site address')


def find_db():
    for p in [os.path.expanduser('~/chat.db'), '/data/chat.db', '/root/chat.db', SITE + '/chat.db'] + glob.glob('/data/**/chat.db', recursive=True):
        if os.path.exists(p):
            return p


def report():
    db = find_db()
    if not db:
        print('could not find chat.db'); return
    print('database:', db)
    c = sqlite3.connect(db)
    names = {r[0]: r[1] for r in c.execute('SELECT key, nickname FROM slate_users')} if c.execute(
        "SELECT 1 FROM sqlite_master WHERE name='slate_users'").fetchone() else {}
    now = time.time()
    print('\nDevices with notifications turned on:')
    rows = c.execute('SELECT s.user_key, s.subscription, s.last_error, s.created, '
                     '(SELECT MAX(a.expires) FROM account_sessions a WHERE a.hash=s.session_hash) FROM push_subscriptions s').fetchall()
    if not rows:
        print('  none - nobody has device notifications enabled on this site')
    for key, sub, err, created, exp in rows:
        try:
            import json
            host = urlparse(json.loads(sub).get('endpoint', '')).hostname
        except Exception:
            host = '?'
        state = 'login active' if exp and exp > now else 'LOGIN EXPIRED (gets nothing)'
        print('  %-18s %-34s %s%s' % (names.get(key, key[:8]), host, state, ('  error: ' + err) if err else ''))
    print('\nPush deliveries in the last 3 days:')
    for st, n in c.execute('SELECT o.status, COUNT(*) FROM push_outbox o JOIN notifications n ON n.id=o.notification_id '
                           'WHERE n.ts>? GROUP BY o.status', (now - 3 * 86400,)):
        print('  %-10s %d' % (st, n))
    stuck = c.execute("SELECT COUNT(*) FROM push_outbox o JOIN notifications n ON n.id=o.notification_id "
                      "WHERE o.status IN ('pending','sending') AND n.ts<?", (now - 600,)).fetchone()[0]
    print('  stuck for 10+ min:', stuck)
    print('\nIn-site notifications created in the last 3 days:',
          c.execute('SELECT COUNT(*) FROM notifications WHERE ts>?', (now - 3 * 86400,)).fetchone()[0])
    print('\nCan the server reach the push services?')
    try:
        import requests
        for h in ['fcm.googleapis.com', 'web.push.apple.com', 'updates.push.services.mozilla.com', 'wns2-by3p.notify.windows.com']:
            try:
                r = requests.post('https://' + h + '/', timeout=8)
                print('  %-36s yes (HTTP %d)' % (h, r.status_code))
            except Exception as e:
                print('  %-36s NO: %s' % (h, type(e).__name__))
    except ImportError:
        print('  requests not installed')
    try:
        import pywebpush  # noqa
        print('\npywebpush installed: yes')
    except ImportError:
        print('\npywebpush installed: NO - device notifications cannot be sent')


if __name__ == '__main__':
    patch()
    report()
    print('\nDone. Now run: docker restart liquidity_web')
