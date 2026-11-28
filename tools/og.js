// Xなどに貼ったときのカード画像（1200x630）を記事ごとに作る
const {chromium}=require('playwright'); const fs=require('fs'), path=require('path');
const OUT=process.argv[2]; const J=JSON.parse(fs.readFileSync(path.join(OUT,'..','og_jobs.json'),'utf8'));
const esc=s=>String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const dataUrl=p=>p?'data:image/'+(p.endsWith('png')?'png':'jpeg')+';base64,'+fs.readFileSync(path.join(OUT,p)).toString('base64'):'';
const av=dataUrl(J.av);
const card=(t,ex,cat,alb,img)=>`<html><body style="margin:0"><div class="c">
<div class="bg"></div><div class="tx">
<div class="top">${av?`<img class="av" src="${av}">`:''}<span>${esc(J.site)}</span></div>
<div class="chips">${cat?`<b>${esc(cat)}</b>`:''}${alb?`<i>${esc(alb)}</i>`:''}</div>
<h1>${esc(t)}</h1>${ex&&!ex.startsWith(t)?`<p>${esc(ex)}</p>`:''}</div>
${img?`<div class="im"><img src="${dataUrl(img)}"></div>`:''}</div>
<style>*{box-sizing:border-box}.c{position:relative;width:1200px;height:630px;overflow:hidden;display:flex;gap:40px;padding:64px 70px;font-family:'Noto Sans CJK JP',sans-serif;color:#f5f2ff;background:#0f0a1a}
.bg{position:absolute;inset:0;background:radial-gradient(700px 500px at 0% 0%,rgba(109,40,217,.55),transparent 70%),radial-gradient(700px 500px at 100% 100%,rgba(192,38,211,.4),transparent 70%),radial-gradient(500px 400px at 100% 0%,rgba(8,145,178,.35),transparent 70%)}
.tx{position:relative;flex:1;min-width:0;display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:16px;font-size:30px;font-weight:700;color:#e9ddff}
.av{width:68px;height:68px;border-radius:50%;object-fit:cover;box-shadow:0 0 0 4px rgba(185,139,255,.6)}
.chips{display:flex;gap:12px;margin:34px 0 18px;flex-wrap:wrap}.chips b,.chips i{font-style:normal;font-size:24px;padding:6px 18px;border-radius:999px;background:rgba(185,139,255,.22);color:#efe6ff}
.chips b{border-radius:10px;font-weight:700}
h1{margin:0;font-size:${img?54:62}px;line-height:1.35;font-weight:700;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;word-break:break-all}
p{margin:20px 0 0;font-size:28px;line-height:1.6;color:#d6cdf0;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.im{position:relative;flex:none;width:380px;height:502px;border-radius:28px;overflow:hidden;box-shadow:0 20px 50px rgba(0,0,0,.5),0 0 0 2px rgba(255,255,255,.15)}.im img{width:100%;height:100%;object-fit:cover;object-position:top}</style></body></html>`;
(async()=>{const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1200,height:630}});
 fs.mkdirSync(path.join(OUT,'og'),{recursive:true});
 const shot=async(h,f)=>{await p.setContent(h,{waitUntil:'load'}); await p.screenshot({path:path.join(OUT,'og',f),type:'jpeg',quality:86})};
 await shot(card(J.site,J.sub,'','',''),'site.jpg');
 for(const [pid,t,ex,cat,alb,img] of J.jobs)await shot(card(t,ex,cat,alb,img),pid+'.jpg');
 await b.close(); console.log('og cards',J.jobs.length+1)})();
