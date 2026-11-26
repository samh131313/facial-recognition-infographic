"""Phone-only fixes for the chat page (screens 800px wide or less). Desktop/Chromebook layout unchanged.

* Tapping an app in the sidebar now closes the sidebar and shows the app full screen
  (before: the app opened behind the still-open sidebar, so nothing seemed to happen).
* Apps get a menu button to reopen the sidebar; tapping outside the sidebar closes it.
* No iOS auto-zoom when tapping text boxes (16px inputs), notch/home-bar safe areas,
  bigger tap targets, no rubber-band bounce.
Run inside the app container:  python /tmp/mobile_fix.py   then: docker restart liquidity_web
Safe to re-run (replaces its own block). Backup: flask_app.py.bak-mobile
"""
import py_compile
import re
import shutil
import sys

APP = (sys.argv[1] if len(sys.argv) > 1 else '/data/mysite') + '/flask_app.py'

# No single quotes, backslashes or newlines: inserted into a single-quoted Python literal.
BLOCK = (
    '<!--liq-mobile--><style id="liqMobile">'
    '#liqSubMenu{display:none}'
    '@media (max-width:800px){'
    'html,body{overscroll-behavior:none;-webkit-tap-highlight-color:transparent}'
    'html body input,html body textarea,html body select,html body #input,html body textarea#input{font-size:16px!important}'
    '#subapp{left:0!important}'
    '.scrim{z-index:150!important}'
    '#subapp .bar{padding-top:max(10px,env(safe-area-inset-top));padding-left:max(12px,env(safe-area-inset-left));padding-right:max(12px,env(safe-area-inset-right))}'
    '#subapp .bar #liqSubMenu{display:grid;place-items:center;margin-left:0!important;width:38px;height:38px;padding:0;font-size:18px}'
    '.topbar{padding-top:max(10px,env(safe-area-inset-top))}'
    '.composer{padding-bottom:max(12px,env(safe-area-inset-bottom))}'
    '.rail{padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}'
    'a.row{min-height:42px;align-items:center}'
    '}</style>'
    '<script>(function(){var mq=window.matchMedia("(max-width:800px)");var sub=document.getElementById("subapp");'
    'if(!sub)return;var app=document.querySelector(".app");'
    'function closeRailIfApp(){if(mq.matches&&sub.classList.contains("on")&&window.__liqCloseRail)window.__liqCloseRail()}'
    'document.addEventListener("click",function(e){var a=e.target&&e.target.closest?e.target.closest("a.row[href]"):null;'
    'if(a)setTimeout(closeRailIfApp,0)},true);'
    'new MutationObserver(closeRailIfApp).observe(sub,{attributes:true,attributeFilter:["class"]});'
    'var bar=sub.querySelector(".bar");if(bar&&!document.getElementById("liqSubMenu")){var b=document.createElement("button");'
    'b.id="liqSubMenu";b.type="button";b.setAttribute("aria-label","Open menu");b.textContent="☰";'
    'b.onclick=function(e){e.stopPropagation();if(app)app.dataset.rail="open"};bar.insertBefore(b,bar.firstChild)}'
    '})();</script><!--/liq-mobile-->'
)


def main():
    s = open(APP, encoding='utf-8').read()
    i = s.index('\nSLATE_PAGE = ') + 1
    j = s.index('\n', i)
    line = s[i:j]
    new = re.sub(r'<!--liq-mobile-->.*?<!--/liq-mobile-->', '', line)
    k = new.rindex('</body>')
    new = new[:k] + BLOCK + new[k:]
    if new == line:
        print('already up to date'); return
    shutil.copy2(APP, APP + '.bak-mobile')
    s = s[:i] + new + s[j:]
    open(APP + '.tmp', 'w', encoding='utf-8').write(s)
    py_compile.compile(APP + '.tmp', doraise=True)
    shutil.move(APP + '.tmp', APP)
    print('phone layout fixes added to the chat page')


if __name__ == '__main__':
    main()
    print('Done. Now run: docker restart liquidity_web')
