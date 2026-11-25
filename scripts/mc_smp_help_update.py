"""Adds a "Liquidity SMP commands" section to the "Always-online server" card on /minecraft:
one dropdown per command group, plus rules and "Shared worlds vs Liquidity SMP".

Run inside the app container:  python /tmp/mc_smp_help_update.py   then: docker restart liquidity_web
Safe to re-run (replaces its own block). Backup: flask_app.py.bak-smphelp
"""
import py_compile
import shutil
import sys

SITE = sys.argv[1] if len(sys.argv) > 1 else '/data/mysite'
APP = SITE + '/flask_app.py'
START, END = '<!--smp-help-->', '<!--/smp-help-->'

# No single quotes or backslashes: this is inserted into a single-quoted Python literal.
c = lambda t: '<code>' + t + '</code>'
def dd(title, *rows):
    """One dropdown; rows are (command, what it does)."""
    items = ''.join('<li>' + c(cmd) + ': ' + what + '</li>' for cmd, what in rows)
    return '<details style="margin-top:8px"><summary>' + title + '</summary><ul>' + items + '</ul></details>'


BLOCK = (
    START + '<h3 style="margin:14px 0 4px">Liquidity SMP commands</h3>' +
    dd('Logging in',
       ('/register pass pass', 'first time only, pick a new password'),
       ('/login pass', 'every time you join (within 30 seconds)'),
       ('/changepassword old new', 'change your password')) +
    dd('Homes (up to 3)',
       ('/sethome name', 'save a home where you stand'),
       ('/home name', 'go to a home'),
       ('/delhome name', 'delete a home')) +
    dd('Teleporting (5 s countdown, 45 s cooldown)',
       ('/spawn', 'go to spawn'),
       ('/tpr', 'random spot 500 to 10,000 blocks away'),
       ('/tpa player', 'ask to teleport to someone'),
       ('/tpahere player', 'ask someone to teleport to you'),
       ('/tpaccept', 'accept a request'),
       ('/tpdeny', 'deny a request')) +
    dd('Chat',
       ('/msg player text', 'private message'),
       ('/r text', 'reply to your last message'),
       ('/me action', 'action message'),
       ('/ignore player', 'hide someone’s messages'),
       ('/afk', 'mark yourself away')) +
    dd('Info and other',
       ('/help', 'list the commands you can use'),
       ('/list', 'who is online'),
       ('/seen player', 'when someone was last online'),
       ('/tps', 'server speed (20 is perfect)'),
       ('/suicide', 'respawn (you drop your items)'),
       ('/skin set name', 'use another player’s skin'),
       ('/skin clear', 'reset your skin')) +
    '<details style="margin-top:8px"><summary>Rules and how it works</summary><ul>'
    '<li>PvP is on.</li><li><strong>You drop everything when you die</strong> (keepInventory is off).</li>'
    '<li>Teleports need you to stand still 5 seconds, so you cannot escape a fight instantly.</li>'
    '<li>The world is effectively unlimited.</li>'
    '<li>Always join with the <strong>same username</strong>, capitals included. Items, homes and password belong to that exact name.</li>'
    '</ul></details>'
    '<details style="margin-top:8px"><summary>Shared worlds vs Liquidity SMP</summary>'
    '<p><strong>Shared world</strong> (join code): runs inside the host’s browser. It only exists while the host plays, '
    'everyone is kicked when they leave, and lag depends on the host’s computer.</p>'
    '<p><strong>Liquidity SMP</strong> (Multiplayer list): runs on our server 24/7. Nobody hosts, join or leave any time, '
    'full speed. Use it for the main survival world.</p>'
    '<p>Shared and singleplayer worlds are saved in your browser (export to back up). Liquidity SMP is saved on the server.</p>'
    '</details>' + END
)

ANCHOR = '<p class="muted">Shared worlds with join codes still work too.'


def main():
    s = open(APP, encoding='utf-8').read()
    if START in s:
        a = s.index(START); b = s.index(END, a) + len(END)
        new = s[:a] + BLOCK + s[b:]
    else:
        if s.count(ANCHOR) != 1:
            sys.exit('Always-online card not found; run mc_web_update.py first. Nothing changed.')
        new = s.replace(ANCHOR, BLOCK + ANCHOR)
    if new == s:
        print('already up to date'); return
    shutil.copy2(APP, APP + '.bak-smphelp')
    open(APP + '.tmp', 'w', encoding='utf-8').write(new)
    py_compile.compile(APP + '.tmp', doraise=True)
    shutil.move(APP + '.tmp', APP)
    print('added: SMP command dropdowns, rules, shared-vs-SMP')


if __name__ == '__main__':
    main()
    print('Done. Now run: docker restart liquidity_web')
