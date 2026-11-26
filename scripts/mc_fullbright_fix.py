"""Fix 'could not change it: TypeError: Failed to fetch' on the Fullbright button.

The button assumed the game's saved settings are always gzip+base64. Some saves have extra
bytes after the compressed data (or are stored uncompressed), and the browser's gzip reader
then fails with that confusing 'Failed to fetch'. Now it reads gzip tolerantly, also accepts
plain base64 or raw text settings, and writes back in the same format it found.
Applies to both the Minecraft 1.9.4 and 1.12 pages.
Run inside the app container:  python /tmp/mc_fullbright_fix.py   then: docker restart liquidity_web
Safe to re-run. Backup: flask_app.py.bak-fullbright
"""
import py_compile
import shutil
import sys

APP = (sys.argv[1] if len(sys.argv) > 1 else '/data/mysite') + '/flask_app.py'

OLD = (
    "async function fbRead(){const v=localStorage.getItem(fbKey);if(!v)return null;"
    "const bytes=Uint8Array.from(atob(v),c=>c.charCodeAt(0));"
    "return await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();}"
    "async function fbWrite(t){const gz=new Uint8Array(await new Response(new Blob([t]).stream()"
    ".pipeThrough(new CompressionStream('gzip'))).arrayBuffer());let s='';for(const c of gz)s+=String.fromCharCode(c);"
    "localStorage.setItem(fbKey,btoa(s));}"
)

# No backslashes (keeps it safe inside the page's Python string).
NEW = (
    "let fbFmt='gz';"
    "async function fbGunzip(b){const r=new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip')).getReader();"
    "const parts=[];try{for(;;){const x=await r.read();if(x.done)break;parts.push(x.value);}}catch(e){if(!parts.length)throw e;}"
    "return await new Blob(parts).text();}"
    "async function fbRead(){const v0=localStorage.getItem(fbKey);if(!v0)return null;const v=v0.trim();"
    "if(/^[A-Za-z0-9+/=]+$/.test(v)){let b=null;try{b=Uint8Array.from(atob(v),c=>c.charCodeAt(0));}catch(e){}"
    "if(b&&b[0]===31&&b[1]===139){fbFmt='gz';return await fbGunzip(b);}"
    "if(b){const t=new TextDecoder().decode(b);if(/^[A-Za-z_.]+:/m.test(t)){fbFmt='b64';return t;}}}"
    "if(/^[A-Za-z_.]+:/m.test(v0)){fbFmt='raw';return v0;}"
    "throw new Error('unrecognised settings format, starts with '+v0.slice(0,16));}"
    "async function fbWrite(t){if(fbFmt==='raw'){localStorage.setItem(fbKey,t);return;}let bytes;"
    "if(fbFmt==='b64')bytes=new TextEncoder().encode(t);"
    "else bytes=new Uint8Array(await new Response(new Blob([t]).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer());"
    "let s='';for(const c of bytes)s+=String.fromCharCode(c);localStorage.setItem(fbKey,btoa(s));}"
)


def main():
    s = open(APP, encoding='utf-8').read()
    n_old, n_new = s.count(OLD), s.count('async function fbGunzip(')
    if not n_old:
        print('already fixed' if n_new else 'Fullbright code not found - run mc_packs_update.py first'); return
    shutil.copy2(APP, APP + '.bak-fullbright')
    open(APP + '.tmp', 'w', encoding='utf-8').write(s.replace(OLD, NEW))
    py_compile.compile(APP + '.tmp', doraise=True)
    shutil.move(APP + '.tmp', APP)
    print('Fullbright button fixed on %d page(s)' % n_old)


if __name__ == '__main__':
    main()
    print('Done. Now run: docker restart liquidity_web')
