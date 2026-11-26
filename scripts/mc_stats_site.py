"""Website: Liquidity SMP status widget (chat sidebar) + per-player stats page (/smp-stats).

* /smp-stats/status.json : asks the Minecraft server directly (server-list ping) who is online. Cached 20 s.
* /smp-stats/data.json  : the summary written every 5 min by smp_stats_export.py on the host.
* /smp-stats      : leaderboards + a card per player (playtime, kills, deaths, mobs, ores, ...).
* Chat "Your apps": a live "Liquidity SMP: N online" line and an "SMP stats" app.
Run inside the app container:  python /tmp/mc_stats_site.py   then: docker restart liquidity_web
Safe to re-run. Backup: flask_app.py.bak-stats
"""
import py_compile
import shutil
import sys

SITE = sys.argv[1] if len(sys.argv) > 1 else '/data/mysite'
APP = SITE + '/flask_app.py'
START, END = '# --- smp stats (mc_stats_site.py) ---', '# --- end smp stats ---'

STATS_PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Liquidity SMP stats</title><style>
:root{color-scheme:dark;--bg:#111318;--card:#1b1e25;--line:#2b2f38;--ink:#e7e9ee;--mut:#9aa1ad;--acc:#7aa2ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif;padding:16px;max-width:1100px;margin:auto}
h1{font-size:22px;margin:0}h2{font-size:16px;margin:0 0 8px}.mut{color:var(--mut)}
header{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:12px 0}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}.tabs button{background:#262a33;color:var(--ink);border:1px solid var(--line);border-radius:999px;padding:5px 12px;cursor:pointer}
.tabs button.on{background:var(--acc);color:#0b0d12;border-color:var(--acc)}
table{width:100%;border-collapse:collapse}td{padding:6px 4px;border-bottom:1px solid var(--line)}td.n{text-align:right;font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.kv{display:grid;grid-template-columns:1fr auto;gap:2px 10px}.kv span:nth-child(even){text-align:right;font-variant-numeric:tabular-nums}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}.chip{background:#262a33;border-radius:6px;padding:2px 7px;font-size:12px}
.on-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#3ecf8e;margin-right:6px}
</style></head><body>
<header><h1>Liquidity SMP stats</h1><span id="status" class="mut">loading…</span></header>
<section class="card"><h2>Leaderboards</h2><div class="tabs" id="tabs"></div><table id="board"></table></section>
<div class="grid" id="players"></div>
<p class="mut">Stats update every few minutes while the server runs. Players are listed by their Minecraft username.</p>
<script>
const $=id=>document.getElementById(id);
const fmt=n=>Number(n||0).toLocaleString();
const hm=m=>{m=m||0;const h=Math.floor(m/60);return h?h+'h '+(m%60)+'m':m+'m'};
const km=m=>m>=1000?(m/1000).toFixed(1)+' km':fmt(m)+' m';
const nice=s=>String(s).replace(/_ore$/,'').replace(/_/g,' ').replace(/^./,c=>c.toUpperCase());
const BOARDS=[['Playtime','playtime_min',hm],['Player kills','player_kills',fmt],['Mob kills','mob_kills',fmt],
 ['Deaths','deaths',fmt],['K/D','kd',v=>v.toFixed(2)],['Blocks mined','blocks_mined',fmt],['Diamonds','diamonds',fmt],
 ['Distance','distance_m',km],['Damage dealt','damage_dealt_hearts',v=>fmt(v)+' ♥'],['Advancements','advancements',fmt]];
let data=null,cur=0,online=new Set();
function board(){const [label,key,f]=BOARDS[cur];
 const rows=[...data.players].sort((a,b)=>(b[key]||0)-(a[key]||0));
 $('board').innerHTML='';rows.forEach((p,i)=>{const tr=document.createElement('tr');
  tr.innerHTML='<td class="mut">'+(i+1)+'</td><td></td><td class="n"></td>';
  tr.children[1].textContent=p.name;if(online.has(p.name)){const d=document.createElement('span');d.className='on-dot';tr.children[1].prepend(d)}
  tr.children[2].textContent=f(p[key]||0);$('board').appendChild(tr)});
 [...$('tabs').children].forEach((b,i)=>b.classList.toggle('on',i===cur));}
function chips(list,f){const d=document.createElement('div');d.className='chips';
 (list||[]).forEach(([k,v])=>{const c=document.createElement('span');c.className='chip';c.textContent=nice(k)+' '+(f?f(v):fmt(v));d.appendChild(c)});
 if(!(list||[]).length){const c=document.createElement('span');c.className='mut';c.textContent='none yet';d.appendChild(c)}return d}
function cards(){const g=$('players');g.innerHTML='';
 data.players.forEach(p=>{const c=document.createElement('section');c.className='card';
  const h=document.createElement('h2');h.textContent=p.name;if(online.has(p.name)){const d=document.createElement('span');d.className='on-dot';h.prepend(d)}c.appendChild(h);
  const kv=document.createElement('div');kv.className='kv';
  [['Playtime',hm(p.playtime_min)],['Player kills',fmt(p.player_kills)],['Deaths',fmt(p.deaths)],['K/D',p.kd.toFixed(2)],
   ['Mob kills',fmt(p.mob_kills)],['Blocks mined',fmt(p.blocks_mined)],['Items crafted',fmt(p.items_crafted)],
   ['Distance travelled',km(p.distance_m)],['Jumps',fmt(p.jumps)],['Damage dealt',fmt(p.damage_dealt_hearts)+' ♥'],
   ['Damage taken',fmt(p.damage_taken_hearts)+' ♥'],['Fish caught',fmt(p.fish_caught)],['Animals bred',fmt(p.animals_bred)],
   ['Villager trades',fmt(p.trades)],['Items enchanted',fmt(p.enchants)],['Tools broken',fmt(p.tools_broken)],
   ['Advancements',fmt(p.advancements)],['Alive for',hm(p.since_death_min)]].forEach(([k,v])=>{
    const a=document.createElement('span');a.textContent=k;const b=document.createElement('span');b.textContent=v;kv.append(a,b)});
  c.appendChild(kv);
  for(const [t,l] of [['Ores mined',Object.entries(p.ores||{}).sort((a,b)=>b[1]-a[1])],['Mobs killed',p.top_mobs_killed],
                      ['Killed most by',p.top_killed_by],['Most mined',p.top_blocks_mined]]){
   const s=document.createElement('div');s.className='mut';s.style.marginTop='8px';s.textContent=t;c.append(s,chips(l))}
  g.appendChild(c)})}
async function load(){
 try{const s=await (await fetch('/smp-stats/status.json',{cache:'no-store'})).json();
  online=new Set(s.players||[]);$('status').textContent=s.ok?('Liquidity SMP: '+s.online+' online'+(s.players&&s.players.length?' ('+s.players.join(', ')+')':'')):'Liquidity SMP: offline';}catch(e){}
 try{data=await (await fetch('/smp-stats/data.json',{cache:'no-store'})).json();
  data.players.forEach(p=>{p.kd=p.player_kills/Math.max(1,p.deaths);p.diamonds=(p.ores||{}).diamond_ore||0});
  if(!$('tabs').children.length)BOARDS.forEach(([l],i)=>{const b=document.createElement('button');b.textContent=l;b.onclick=()=>{cur=i;board()};$('tabs').appendChild(b)});
  board();cards();
  if(data.updated)$('status').textContent+=' · stats updated '+new Date(data.updated*1000).toLocaleTimeString();
 }catch(e){$('players').innerHTML='<p class="mut">No stats yet. They appear a few minutes after the stats job first runs.</p>'}}
load();setInterval(load,60000);
</script></body></html>'''

CODE = START + '''
SMP_STATS_PAGE = ''' + repr(STATS_PAGE) + '''
_smp_status_cache = {'t': 0, 'v': None}


def _smp_ping(host, port, timeout=3):
    import socket, struct, json as _j
    def varint(n):
        out = b''
        while True:
            b = n & 0x7f; n >>= 7
            out += bytes([b | (0x80 if n else 0)])
            if not n: return out
    def read_varint(sock):
        n = shift = 0
        while True:
            c = sock.recv(1)
            if not c: raise IOError('closed')
            n |= (c[0] & 0x7f) << shift; shift += 7
            if not c[0] & 0x80: return n
    with socket.create_connection((host, port), timeout=timeout) as s:
        hb = host.encode()
        hs = varint(0) + varint(340) + varint(len(hb)) + hb + struct.pack('>H', port) + varint(1)
        s.sendall(varint(len(hs)) + hs + varint(1) + varint(0))
        read_varint(s); read_varint(s); ln = read_varint(s); buf = b''
        while len(buf) < ln:
            chunk = s.recv(ln - len(buf))
            if not chunk: break
            buf += chunk
    return _j.loads(buf.decode('utf-8'))


@app.get('/smp-stats/status.json')
def smp_status_api():
    import time as _t
    now = _t.time()
    if now - _smp_status_cache['t'] > 20:
        host = os.environ.get('LIQ_MC_HOST', '10.99.1.1')
        try:
            d = _smp_ping(host, int(os.environ.get('LIQ_MC_PORT', '25565')))
            pl = d.get('players', {}) or {}
            v = dict(ok=True, online=int(pl.get('online', 0)), max=int(pl.get('max', 0)),
                     players=sorted(str(p.get('name', ''))[:16] for p in (pl.get('sample') or []) if p.get('name')))
        except Exception:
            v = dict(ok=False, online=0, max=0, players=[])
        _smp_status_cache.update(t=now, v=v)
    r = jsonify(_smp_status_cache['v']); r.headers['Cache-Control'] = 'no-store'; return r


@app.get('/smp-stats/data.json')
def smp_stats_api():
    import json as _j
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smp_stats.json')
    try:
        d = _j.load(open(p))
    except Exception:
        d = {'updated': 0, 'players': []}
    r = jsonify(d); r.headers['Cache-Control'] = 'no-store'; return r


@app.get('/smp-stats')
@app.get('/smp-stats/')
def smp_stats_page():
    r = app.response_class(SMP_STATS_PAGE, mimetype='text/html'); r.headers['Cache-Control'] = 'no-store'; return r
''' + END + '\n\n'

# Chat sidebar: no single quotes / backslashes / newlines (inserted into a single-quoted literal).
WIDGET = ('<div class="row" id="smpStatus" title="Liquidity SMP (24/7 Minecraft server)">'
          '<span id="smpDot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#777;margin-right:8px"></span>'
          '<span id="smpText">Liquidity SMP: checking…</span></div>')
WIDGET_JS = ('<script>(function(){var t=document.getElementById("smpText"),d=document.getElementById("smpDot");'
             'if(!t)return;function up(){fetch("/smp-stats/status.json",{cache:"no-store"}).then(function(r){return r.json()})'
             '.then(function(s){if(!s.ok){t.textContent="Liquidity SMP: offline";d.style.background="#c55";return}'
             't.textContent="Liquidity SMP: "+s.online+" online"+(s.players&&s.players.length?" ("+s.players.join(", ")+")":"");'
             'd.style.background=s.online?"#3ecf8e":"#888"}).catch(function(){})}up();setInterval(up,30000)})();</script>')
APPS_ANCHOR = '<h2 class="group__label">Your apps</h2>'
STATS_ROW = '<a class="row" href="/smp-stats">SMP stats</a>'


def main():
    s = open(APP, encoding='utf-8').read()
    orig = s
    if START in s:
        a = s.index(START); b = s.index(END, a) + len(END) + 2
        s = s[:a] + CODE + s[b:]
    else:
        anchor = "@app.get('/minecraft/health')"
        if s.count(anchor) != 1: sys.exit('route anchor not found. Nothing changed.')
        s = s.replace(anchor, CODE + anchor)
    if 'id="smpStatus"' not in s:
        if s.count(APPS_ANCHOR) != 1: sys.exit('"Your apps" not found. Nothing changed.')
        s = s.replace(APPS_ANCHOR, APPS_ANCHOR + WIDGET + STATS_ROW, 1)
        i = s.index('\nSLATE_PAGE = '); j = s.index('\n', i + 1)
        line = s[i:j]
        k = line.rindex('</body>')
        s = s[:i] + line[:k] + WIDGET_JS + line[k:] + s[j:]
    for old, new in ((",'/multiplayer-test','/shooter-test/']", ",'/multiplayer-test','/smp-stats','/shooter-test/']"),
                     (",\\'/multiplayer-test\\',\\'/shooter-test/\\']", ",\\'/multiplayer-test\\',\\'/smp-stats\\',\\'/shooter-test/\\']")):
        if old in s and new not in s: s = s.replace(old, new, 1)
    if s == orig:
        print('already up to date'); return
    shutil.copy2(APP, APP + '.bak-stats')
    open(APP + '.tmp', 'w', encoding='utf-8').write(s)
    py_compile.compile(APP + '.tmp', doraise=True)
    shutil.move(APP + '.tmp', APP)
    print('added: SMP status widget, SMP stats app (/smp-stats)')


if __name__ == '__main__':
    main()
    print('Done. Now run: docker restart liquidity_web')
