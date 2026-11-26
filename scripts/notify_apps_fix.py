"""Notifications while an app (Minecraft, GPT, SMP stats...) is open inside the chat.

Before: with an app open, the chat still counted as 'being looked at', so
  * the in-site pop-up (toast) appeared BEHIND the app, invisible;
  * no sound for messages in the channel you were on;
  * no system notification (the browser thinks you're reading the chat, so push is skipped too).
After: an open app counts as 'away from the chat': the pop-up shows on top, the sound plays,
and a system notification appears (if notifications are allowed for the site).
Run inside the app container:  python /tmp/notify_apps_fix.py   then: docker restart liquidity_web
Safe to re-run. Backup: flask_app.py.bak-notifyapps
"""
import py_compile
import shutil
import sys

APP = (sys.argv[1] if len(sys.argv) > 1 else '/data/mysite') + '/flask_app.py'

# These match the page source as it appears inside flask_app.py (escaped quotes and \n).
FIXES = [
    (r"const active=n.channel===state.channel&&!document.hidden&&pin;",
     r"const liqApp=!!document.querySelector(\'#subapp.on\');const active=n.channel===state.channel&&!document.hidden&&!liqApp&&pin;"),
    (r"if(v5.notifyEnabled&&!v6.pushActive&&document.hidden&&\'Notification\' in window&&Notification.permission===\'granted\'){\n          const notification=new Notification(\'Liquidity\',{body:n.body,tag:\'liquidity-\'+n.id});notification.onclick=()=>{window.focus();openChannel(n.channel);notification.close();};\n        }",
     r"if(v5.notifyEnabled&&(liqApp||(!v6.pushActive&&document.hidden))&&\'Notification\' in window&&Notification.permission===\'granted\'){\n          const liqOpts={body:n.body,tag:\'liquidity-\'+n.id,icon:\'/liquidity-icon.svg\'};try{const notification=new Notification(\'Liquidity\',liqOpts);notification.onclick=()=>{window.focus();openChannel(n.channel);notification.close();};}catch(e){navigator.serviceWorker&&navigator.serviceWorker.getRegistration().then(r=>r&&r.showNotification(\'Liquidity\',{...liqOpts,data:{url:location.origin+\'/\'}})).catch(()=>{});}\n        }"),
    (r"transition: opacity .2s var(--ease), transform .2s var(--ease);\n  z-index: 60;",
     r"transition: opacity .2s var(--ease), transform .2s var(--ease);\n  z-index: 210;"),
]


def main():
    s = open(APP, encoding='utf-8').read()
    out, changed = s, 0
    for old, new in FIXES:
        if new in out:
            continue
        if out.count(old) != 1:
            sys.exit('Could not find the expected code (%r...). Nothing changed.' % old[:50])
        out = out.replace(old, new); changed += 1
    if not changed:
        print('already up to date'); return
    shutil.copy2(APP, APP + '.bak-notifyapps')
    open(APP + '.tmp', 'w', encoding='utf-8').write(out)
    py_compile.compile(APP + '.tmp', doraise=True)
    shutil.move(APP + '.tmp', APP)
    print('notifications now show while an app is open in the chat (%d changes)' % changed)


if __name__ == '__main__':
    main()
    print('Done. Now run: docker restart liquidity_web')
