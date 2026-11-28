# 公開版（GitHub Pages）を書き出す：元のサイトと同じページ（index.html）をそのまま使い、
# 保存先（db）の代わりに、書き出した data.json を読む「閲覧専用」にする。全体公開と合言葉つきの記事を入れる。
# 合言葉つきは暗号化されたまま入れる（合言葉そのもの＝passkeys は絶対に入れない）。非公開（priv）は入れない。
# 使い方: python3 -I gen2.py <db_dir> <site_html> <out_dir> <base_url>
import json, glob, os, sys, re, base64, html, shutil
from datetime import datetime, timezone, timedelta

DB, SRC, OUT, BASE = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].rstrip('/') + '/'
JST = timezone(timedelta(hours=9))
CAT = {'settei': 'うちの子設定', 'kouryu': '交流記録', 'koneta': '小ネタ', 'shindan': '診断'}
esc = lambda s: html.escape(str(s or ''), quote=True)

def load(col):
    out = {}
    for f in glob.glob(os.path.join(DB, col, '*.json')):
        d = json.load(open(f, encoding='utf8'))
        out[os.path.basename(f)[:-5].replace('@', '~')] = d
    return out

shutil.rmtree(OUT, ignore_errors=True)
for d in ('p', 'img', 'og'): os.makedirs(os.path.join(OUT, d), exist_ok=True)

# 公開版のパスワード：covers の site~gate があれば、中身（data.json と画像）を鍵で暗号化して出す。
# 鍵は管理人だけが読める sitekey にある。パスワード自体はどこにも無い。鍵が無ければ、中身を出さずに止める（暗号化しないまま公開しない）
GATE = None; KEY = None
_gc = {}
for f in glob.glob(os.path.join(DB, 'covers', '*.json')):
    if os.path.basename(f) == 'site@gate.json': _gc = json.load(open(f, encoding='utf8'))
if _gc.get('wk'):
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception:
        print('エラー: 暗号化の部品（cryptography）がありません。公開版を書き出さずに止めます'); sys.exit(2)
    kf = os.path.join(DB, 'sitekey', 'k.json')
    if not os.path.exists(kf):
        print('エラー: 公開版のパスワードが設定されていますが、鍵（sitekey）が書き出されていません。公開版を書き出さずに止めます'); sys.exit(2)
    KEY = base64.b64decode(json.load(open(kf, encoding='utf8'))['k'])
    GATE = {k: _gc[k] for k in ('salt', 'iv', 'wk', 'iter')}
def seal(b):
    iv = os.urandom(12)
    return iv + AESGCM(KEY).encrypt(iv, b, None)

def save_data_url(u, name):
    head, b64 = u.split(',', 1)
    ext = 'png' if 'png' in head else 'webp' if 'webp' in head else 'jpg'
    raw = base64.b64decode(b64)
    if KEY:   # 暗号化して .bin に。見る人のページで、パスワードを入れた後にもとに戻す
        rel = f'img/{name}.bin'
        open(os.path.join(OUT, rel), 'wb').write(seal(raw))
        open(os.path.join(OUT, '..', f'plain_{name}.{ext}'), 'wb').write(raw)   # カード画像づくり用（公開しない作業場所）
        return rel
    rel = f'img/{name}.{ext}'
    open(os.path.join(OUT, rel), 'wb').write(raw)
    return rel

SHOW = ('public', 'pass')
raw_covers = load('covers')
# 夢創作（フォルダのジャンルが yume）は公開版に出さない：その記事・フォルダ・表紙・タブ・タグを外す
genres = ((raw_covers.get('site~fgenre') or {}).get('genres') or {})
HIDE_FOLDERS = {f for f, g in genres.items() if g == 'yume'}
posts = {k: v for k, v in load('posts').items() if v.get('vis') in SHOW and (v.get('album') or '') not in HIDE_FOLDERS}
for v in posts.values():
    if v.get('vis') == 'public': v.pop('enc', None)
    else: v.pop('body', None); v.pop('original', None)   # 合言葉つきは暗号文（enc）だけ

images = []
for k, v in sorted(load('images').items()):
    if v.get('post') not in posts: continue
    if v.get('enc') and posts[v['post']].get('vis') == 'pass':   # 合言葉つきの画像は暗号文のまま
        images.append({'id': k, 'post': v['post'], 'i': v.get('i'), 'enc': v['enc']}); continue
    u = v.get('data') or ''
    if not u.startswith('data:'): continue
    cont = u.endswith('#c'); u = u[:-2] if cont else u
    rel = save_data_url(u, re.sub(r'[^A-Za-z0-9_-]', '_', k))
    images.append({'id': k, 'post': v['post'], 'i': v.get('i'), 'data': rel + ('#c' if cont else '')})

covers = {}
used_tags = {t for v in posts.values() for t in (v.get('tags') or [])}
for n, (k, v) in enumerate(raw_covers.items()):
    v = dict(v)
    if k == 'site~gate': continue   # 錠は data.json の外側に置く
    if k != 'site~fgenre' and v.get('tag') in HIDE_FOLDERS: continue   # 夢創作のフォルダ・表紙
    if k == 'site~fgenre': v['genres'] = {f: g for f, g in genres.items() if f not in HIDE_FOLDERS}
    if k == 'site~forder' and isinstance(v.get('order'), list): v['order'] = [f for f in v['order'] if f not in HIDE_FOLDERS]   # 並び順からも夢創作のフォルダ名を外す
    if k == 'site~tagkind' and isinstance(v.get('kinds'), dict): v['kinds'] = {t: x for t, x in v['kinds'].items() if t in used_tags}
    for f in ('data', 'avatar'):
        if isinstance(v.get(f), str) and v[f].startswith('data:'):
            v[f] = save_data_url(v[f], f'cover{n}')
    covers[k] = v

data = {'posts': posts, 'covers': covers, 'images': images}
if KEY:
    # 確認用の中身は公開しない作業場所に置き、公開する data.json は暗号文だけにする
    json.dump(data, open(os.path.join(OUT, '..', 'data_plain.json'), 'w', encoding='utf8'), ensure_ascii=False)
    sealed = seal(json.dumps(data, ensure_ascii=False).encode('utf8'))
    json.dump({'gate': GATE, 'enc': base64.b64encode(sealed).decode()}, open(os.path.join(OUT, 'data.json'), 'w', encoding='utf8'))
else:
    json.dump(data, open(os.path.join(OUT, 'data.json'), 'w', encoding='utf8'), ensure_ascii=False)

ui = (covers.get('site~ui') or {}).get('ui') or {}
SITE = ui.get('name') or '花菱のうちの子帳'
SUB = ui.get('sub') or ''

# 保存先の代わり：data.json を読み、元のページが使う呼び出し（読むだけ）に答える
SHIM = r'''<script>
(()=>{
 // パスワードつきの公開版：data.json が暗号文なら、パスワード画面を出して、正しければ中身と画像をもとに戻す
 const b64d=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
 const open1=async(K,u8)=>new Uint8Array(await crypto.subtle.decrypt({name:'AES-GCM',iv:u8.slice(0,12)},K,u8.slice(12)));
 const ask=()=>new Promise(res=>{
   const go=()=>{ let w=document.getElementById('gate'); if(w){ const f=w.querySelector('form'), i=w.querySelector('input'), e=w.querySelector('.e'), bt=w.querySelector('button'); f.onsubmit=ev=>{ev.preventDefault(); if(!i.value)return; bt.disabled=true; e.textContent='確かめています…'; res({pw:i.value,fail:m=>{bt.disabled=false;e.textContent=m;i.select()},done:()=>w.remove()})}; return }
     w=document.createElement('div'); w.id='gate';
     w.innerHTML=`<style>#gate{position:fixed;inset:0;z-index:99999;display:grid;place-items:center;padding:24px;background:#0f0a1a;color:#f5f2ff;font-family:"Noto Sans JP","Hiragino Sans",sans-serif}
#gate form{width:min(340px,100%);display:grid;gap:12px;text-align:center}#gate h1{margin:0 0 4px;font-size:22px;font-weight:700}#gate p{margin:0;font-size:13px;color:#cdc4ea}
#gate input{height:50px;border-radius:14px;border:1px solid rgba(185,139,255,.45);background:rgba(255,255,255,.06);color:#fff;font-size:16px;padding:0 14px;outline:none}#gate input:focus{border-color:#b98bff}
#gate button{height:50px;border:0;border-radius:14px;background:linear-gradient(120deg,#6d28d9,#c026d3);color:#fff;font-size:15px;font-weight:700;cursor:pointer}#gate button:disabled{opacity:.6}
#gate .e{color:#ff9fb6;min-height:1.2em}</style><form><h1></h1><p>パスワードを入れてください</p><input type="password" autocomplete="current-password" aria-label="パスワード" autofocus><button>ひらく</button><p class="e" role="status"></p></form>`;
     w.querySelector('h1').textContent=__SITE__; document.documentElement.appendChild(w);
     const f=w.querySelector('form'), i=w.querySelector('input'), e=w.querySelector('.e'), bt=w.querySelector('button'); setTimeout(()=>i.focus(),50);
     f.onsubmit=ev=>{ev.preventDefault(); if(!i.value)return; bt.disabled=true; e.textContent='確かめています…'; res({pw:i.value,fail:m=>{bt.disabled=false;e.textContent=m;i.select()},done:()=>w.remove()})} };
   if(document.body)go(); else addEventListener('DOMContentLoaded',go);
 });
 const unlock=async D=>{ const g=D.gate;
   for(;;){ const t=await ask();
     try{ const base=await crypto.subtle.importKey('raw',new TextEncoder().encode(t.pw),'PBKDF2',false,['deriveKey']);
       const wk=await crypto.subtle.deriveKey({name:'PBKDF2',salt:b64d(g.salt),iterations:g.iter,hash:'SHA-256'},base,{name:'AES-GCM',length:256},false,['decrypt']);
       const raw=new Uint8Array(await crypto.subtle.decrypt({name:'AES-GCM',iv:b64d(g.iv)},wk,b64d(g.wk)));
       const K=await crypto.subtle.importKey('raw',raw,'AES-GCM',false,['decrypt']);
       const data=JSON.parse(new TextDecoder().decode(await open1(K,b64d(D.enc))));
       const img=async u=>{ if(typeof u!=='string'||!/^img\/.*\.bin(#c)?$/.test(u))return u; const c=u.endsWith('#c'), p=c?u.slice(0,-2):u;
         try{const b=new Uint8Array(await (await fetch(p,{cache:'no-cache'})).arrayBuffer()); return URL.createObjectURL(new Blob([await open1(K,b)]))+(c?'#c':'')}catch(_){return ''} };
       await Promise.all([...data.images.map(async v=>{v.data=await img(v.data)}), ...Object.values(data.covers).flatMap(v=>['data','avatar'].map(async k=>{if(v[k])v[k]=await img(v[k])}))]);
       t.done(); return data;
     }catch(_){ t.fail('パスワードが違います') } }
 };
 const P=fetch('data.json',{cache:'no-cache'}).then(r=>r.json()).then(D=>D&&D.gate?unlock(D):D).catch(()=>({posts:{},covers:{},images:[]}));
 const snap=rows=>({docs:rows.map(([id,v])=>({id,data:()=>JSON.parse(JSON.stringify(v))})),size:rows.length,empty:!rows.length});
 const rowsOf=(D,name)=>name==='posts'?Object.entries(D.posts):name==='covers'?Object.entries(D.covers):name==='images'?D.images.map(v=>[v.id,v]):[];
 const deny=()=>Promise.reject({code:'not_granted',message:'閲覧専用です'});
 const col=(name,filt)=>{const q={
   orderBy:()=>q,limit:()=>q,
   where:(f,op,val)=>col(name,v=>(!filt||filt(v))&&(op==='=='?v[f]===val:true)),
   get:async()=>{const D=await P;return snap(rowsOf(D,name).filter(([,v])=>!filt||filt(v)))},
   onSnapshot:(cb,err)=>{P.then(D=>cb(snap(rowsOf(D,name).filter(([,v])=>!filt||filt(v))))).catch(e=>err&&err(e));return()=>{}},
   doc:id=>({id:id||Math.random().toString(36).slice(2),get:async()=>{const D=await P;const r=rowsOf(D,name).find(([k])=>k===id);return{exists:!!r,id,data:()=>r?r[1]:undefined}},set:deny,update:deny,delete:deny,onSnapshot:()=>()=>{}})};return q};
 const db={collection:n=>col(n)};
 window.claude={use:async n=>n==='db'?db:null};
})();
</script>'''

SHIM = SHIM.replace('__SITE__', json.dumps(SITE, ensure_ascii=False))
src = open(SRC, encoding='utf8').read()
# 一覧のジャンルのタブから「夢創作」を外す
g_old = "const GENRES=[['niji','二次オリ'],['yume','夢創作']]"
if g_old in src: src = src.replace(g_old, "const GENRES=[['niji','二次オリ']]", 1)
else: print('注意: ジャンルのタブの書き換え箇所が見つかりませんでした')
meta = f'''<meta name="robots" content="noindex,nofollow,noarchive,noai,noimageai"><meta property="og:type" content="website"><meta property="og:site_name" content="{esc(SITE)}"><meta property="og:title" content="{esc(SITE)}"><meta property="og:description" content="{esc(SUB or SITE)}"><meta property="og:url" content="{esc(BASE)}"><meta property="og:image" content="{esc(BASE)}og/site.jpg"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{esc(BASE)}og/site.jpg">'''
src = re.sub(r'<title>.*?</title>', lambda m: meta + '<title>' + esc(SITE) + '</title>', src, count=1, flags=re.S)   # タブに出る名前も今のサイト名にする
# 公開版では記事の共有ボタン（Xで共有・リンクをコピー）を出さない
src = src.replace('</head>', '<style>.shr{display:none!important}</style></head>', 1) if '</head>' in src else '<style>.shr{display:none!important}</style>' + src
i = src.index('<script>')
src = src[:i] + SHIM + src[i:]
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf8').write(src)

# 記事ごとの共有用ページ：Xなどが読むカード情報だけを持ち、開いた人は元のページのその記事へ移る
def dt(p):
    s = p.get('madeAt') or p.get('createdAt') or ''
    try: return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(JST)
    except Exception: return None
def excerpt(p, n): return re.sub(r'\s+', ' ', re.sub(r'[\[［](?:改ページ|区切り線|画像\d+)[\]］]', ' ', p.get('body') or '')).strip()[:n]   # 本文の印は説明文に出さない
def title(p): return (p.get('title') or '').strip() or ('無題' if KEY else excerpt(p, 30)) or '無題'   # パスワードつきの時は、タイトルの無い記事の本文をカードに出さない
first_img = {}
for im in sorted(images, key=lambda v: int(v.get('i') or 0)):
    if im.get('data'): first_img.setdefault(im['post'], im['data'].replace('#c', ''))
jobs = []
for pid, p in posts.items():
    t = title(p); desc = 'パスワードで保護されています' if KEY else (('合言葉を入れると読めます' if p.get('vis') == 'pass' else excerpt(p, 110)) or SITE); url = f'{BASE}p/{pid}.html'; img = f'{BASE}og/{pid}.jpg'; to = f'../#p-{pid}'
    jobs.append((pid, t, '' if KEY else ('🔒 合言葉を入れると読めます' if p.get('vis') == 'pass' else excerpt(p, 80)), '' if KEY else CAT.get(p.get('cat'), ''), '' if KEY else (p.get('album') or ''), '' if KEY else first_img.get(pid, '')))   # パスワードつきの時は、カードにタイトルだけ
    open(os.path.join(OUT, 'p', pid + '.html'), 'w', encoding='utf8').write(f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(t)} | {esc(SITE)}</title><meta name="robots" content="noindex,nofollow,noarchive,noai,noimageai"><meta name="description" content="{esc(desc)}">
<meta property="og:type" content="article"><meta property="og:site_name" content="{esc(SITE)}"><meta property="og:title" content="{esc(t)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{esc(url)}"><meta property="og:image" content="{esc(img)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(t)}"><meta name="twitter:description" content="{esc(desc)}"><meta name="twitter:image" content="{esc(img)}">
<meta http-equiv="refresh" content="0;url={esc(to)}"><script>location.replace({json.dumps(to)})</script>
<style>body{{margin:0;background:#0f0a1a;color:#f5f2ff;font:14px sans-serif;display:grid;place-items:center;min-height:100vh}}a{{color:#d9c5ff}}</style></head>
<body><a href="{esc(to)}">記事を開く</a></body></html>''')

av = (covers.get('site~avatar') or {}).get('avatar') or ''
if KEY and av.endswith('.bin'):   # カード画像用に、暗号化前のアイコンを作業場所から使う
    _n = os.path.basename(av)[:-4]; _c = [x for x in glob.glob(os.path.join(OUT, '..', f'plain_{_n}.*'))]
    av = os.path.relpath(_c[0], OUT) if _c else ''
json.dump({'site': SITE, 'sub': SUB, 'av': av, 'jobs': jobs}, open(os.path.join(OUT, '..', 'og_jobs.json'), 'w', encoding='utf8'), ensure_ascii=False)
open(os.path.join(OUT, 'robots.txt'), 'w').write(''.join(f'User-agent: {b}\nAllow: /\n\n' for b in ['Twitterbot', 'facebookexternalhit', 'Discordbot', 'Slackbot', 'LinkedInBot', 'Line', 'TelegramBot', 'misskey', 'Mastodon', 'Bluesky']) + 'User-agent: *\nDisallow: /\n')
open(os.path.join(OUT, '.nojekyll'), 'w').write('')
print('posts', len(posts), 'images', len(images), 'covers', len(covers))
