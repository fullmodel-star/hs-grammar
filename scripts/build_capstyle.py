# -*- coding: utf-8 -*-
"""把 master.json 產出「cap-english 分頁瀏覽版」單檔 index.html。
沿用 05_高中會考複習 的視覺(capstyle.css)，改成資料驅動：文法重點卡 / 單字 / 練習。
用法: python scripts/build_capstyle.py  (需先有 data/master.json 與 app/capstyle.css)"""
import json, os, sys, hashlib, html as _html
try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, 'app')

# ===== 可調參數(每支App不同) =====
APP_TITLE = '高中英語文法'
HERO_SUB = '學測進階文法 <b>18 主題</b>・每個主題白話重點＋原創例句＋即時練習'
HERO_SRC = '內容 AI 原創・依高中課綱與學測範圍編寫・非任何出版社教材'
NS = 'enghs'            # localStorage 命名空間(避免同源撞資料)
THEME = '#4338ca'      # 主題色(靛藍)
VOCAB_TITLE = '高中 6000 單字'
VOCAB_BADGE = '大考中心 6 級'
VOCAB_DESC = '依級別分組，附詞性、中文與例句'
VOCAB_CMP = '依大考中心 6 級分組，點開級別載入單字卡（含詞性、中文、例句）。'
WELCOME_EMOJI = '📘'
WELCOME_TAGLINE = '學測進階文法・重點＋閱讀＋練習一次到位'

master = json.load(open(os.path.join(ROOT, 'data', 'master.json'), encoding='utf-8'))
css = open(os.path.join(APP, 'capstyle.css'), encoding='utf-8').read()

notes = master['notes']
topics = master['taxonomy']['grammarTopics']
GROUP_ORDER = []
for t in topics:
    if t['group'] not in GROUP_ORDER:
        GROUP_ORDER.append(t['group'])

# 統計每主題題數
qcount = {}
for q in master['questions']:
    if q['type'] == 'grammar':
        qcount[q['unit']] = qcount.get(q['unit'], 0) + 1

# groups -> topics(+note)
groups = []
for g in GROUP_ORDER:
    ts = []
    for t in topics:
        if t['group'] != g:
            continue
        ts.append({'key': t['key'], 'label': t['label'],
                   'qCount': qcount.get(t['label'], 0), 'note': notes.get(t['key'], {})})
    groups.append({'name': g, 'topics': ts})

# vocab -> 精簡欄位
vocab = [{'w': v['word'], 'p': v.get('pos', ''), 'z': v.get('zh', ''),
          'e': v.get('example', ''), 'lv': v.get('level', 1)} for v in master.get('vocab', [])]

# 練習題(文法)
pq = []
for q in master['questions']:
    if q['type'] != 'grammar':
        continue
    pq.append({'k': q.get('topicKey', ''), 'u': q['unit'], 'd': q['difficulty'],
               's': q['stem'], 'o': q['options'], 'a': q['answer'], 'e': q.get('explanation', '')})

# 閱讀(文章+題目)
rq_by_pid = {}
for q in master['questions']:
    if q['type'] == 'reading':
        rq_by_pid.setdefault(q.get('passageId'), []).append(q)
reading = []
for p in master.get('passages', []):
    if not p.get('hasText') or not (p.get('text') or '').strip():
        continue
    qs = rq_by_pid.get(p['passageId'], [])
    reading.append({'g': p.get('genre', '文章'), 't': p.get('title', ''), 'x': p.get('text', ''),
                    'qs': [{'s': q['stem'], 'o': q['options'], 'a': q['answer'], 'e': q.get('explanation', '')} for q in qs]})
HAS_READING = len(reading) > 0

DATA = {'groups': groups, 'vocab': vocab, 'questions': pq, 'reading': reading}
data_js = 'const DATA=' + json.dumps(DATA, ensure_ascii=False, separators=(',', ':')) + ';'

# ===== 首頁 cats：4 群組卡 + 單字卡 =====
CAT_COLORS = ['t-gram', 't-pattern', 't-phrase', 't-vocab']
cats_html = ''
for i, g in enumerate(groups):
    cls = CAT_COLORS[i % len(CAT_COLORS)]
    tnames = '、'.join(t['label'] for t in g['topics'][:4])
    cats_html += (f'<div class="cat-tile {cls}" data-view="gram" tabindex="0" role="button" aria-label="{_html.escape(g["name"])}">'
                  f'<span class="ci">🧩</span><h3>{_html.escape(g["name"])}</h3>'
                  f'<span class="badge">{len(g["topics"])} 主題</span>'
                  f'<p class="cd">{_html.escape(tnames)}…</p></div>')

reading_tab = '<button data-view="reading">📖 閱讀</button>' if HAS_READING else ''
reading_tile = (f'<div class="cat-tile t-phrase" data-view="reading" tabindex="0" role="button" aria-label="閱讀">'
                f'<span class="ci">📖</span><h3>閱讀短文</h3><span class="badge">{len(reading)} 篇</span>'
                f'<p class="cd">原創短文＋題目，附詳解</p></div>') if HAS_READING else ''
reading_view = ('<div class="view" id="v-reading">'
                '<div class="sec-head"><span class="ic">📖</span><h2>閱讀短文</h2>'
                f'<span class="cnt">{len(reading)} 篇</span></div>'
                '<div class="cmp">點開每篇載入文章與題目，正解已標示並附解析。</div>'
                '<div id="readingBody"></div>'
                '<div style="text-align:center"><button class="backtop" data-view="home">🏠 回首頁</button></div></div>') if HAS_READING else ''

# 歡迎卡步驟(依實際分頁)
steps = [('🧩', '文法重點', '每個主題先讀綠色「白話重點」，再看原創例句。')]
if HAS_READING:
    steps.append(('📖', '閱讀', '短文＋題目，正解已標示並附解析。'))
steps.append(('🔤', '單字', f'{VOCAB_TITLE}依級別分組，點開看單字卡。'))
steps.append(('✏️', '練習', '各主題選擇題，答完即時看解析，答錯自動進「錯題複習」。'))
steps.append(('📲', '安裝到桌面', '首頁按安裝，之後免開瀏覽器、可離線使用。'))
steps_html = ''.join(
    f'<div class="wc-step"><span class="wc-i">{ic}</span><div><b>{t}</b><div>{d}</div></div></div>'
    for ic, t, d in steps)
welcome_overlay = (f'<div class="wc-overlay" id="welcome"><div class="wc-card">'
                   f'<div class="wc-emoji">{WELCOME_EMOJI}</div>'
                   f'<h2>歡迎使用 {APP_TITLE}</h2>'
                   f'<div class="wc-sub">{WELCOME_TAGLINE}</div>'
                   f'{steps_html}'
                   f'<button class="wc-start" onclick="closeWelcome()">開始使用 ▶</button></div></div>')

body = f'''<div class="wrap">
<div class="tabbar">
  <button data-view="home">🏠 首頁</button>
  <button data-view="gram">🧩 文法重點</button>
  {reading_tab}
  <button data-view="vocab">🔤 單字</button>
  <button data-view="practice">✏️ 練習</button>
  <button class="helpbtn" onclick="location.href='https://fullmodel-star.github.io/english-hub/'" aria-label="回入口">⬅ 入口</button>
  <button class="helpbtn" onclick="showWelcome()" aria-label="使用說明">❓ 說明</button>
</div>
{welcome_overlay}

<div class="view active" id="v-home">
  <header class="top">
    <h1>📘 {APP_TITLE}</h1>
    <p>{HERO_SUB}</p>
    <span class="src">{HERO_SRC}</span>
  </header>
  <div id="installBar" style="margin:10px 0"></div>
  <p style="text-align:center;color:var(--soft);font-size:14.5px;margin:2px 0 4px">👇 點一類開始複習</p>
  <div class="cats">{cats_html}
    {reading_tile}
    <div class="cat-tile t-vocab" data-view="vocab" tabindex="0" role="button" aria-label="單字">
      <span class="ci">🔤</span><h3>{VOCAB_TITLE}</h3><span class="badge">{VOCAB_BADGE}</span>
      <p class="cd">{VOCAB_DESC}</p></div>
  </div>
  <div class="pr-cta" data-view="practice" tabindex="0" role="button">
    <span class="pi">✏️</span><div><b>讀完了？來練習！</b><span>各主題選擇題，答完即時看解析</span></div>
    <span class="go">開始練習 →</span>
  </div>
  <div class="howto" style="margin-top:20px">
    <b>怎麼用？</b>　① 上方<b>分頁列</b>切換文法／單字／練習。
    ② 文法每個主題先讀綠色<b>白話重點</b>，再看例句。
    ③ 要印按右下「列印」會自動展開全部。
  </div>
</div>

<div class="view" id="v-gram"><div id="gramBody"></div>
  <div style="text-align:center"><button class="backtop" data-view="home">🏠 回首頁</button></div></div>

{reading_view}

<div class="view" id="v-vocab">
  <div class="sec-head"><span class="ic">🔤</span><h2>{VOCAB_TITLE}</h2><span class="cnt">{len(vocab)} 字</span></div>
  <div class="cmp">{VOCAB_CMP}</div>
  <div id="vocabBody"></div>
  <div style="text-align:center"><button class="backtop" data-view="home">🏠 回首頁</button></div></div>

<div class="view" id="v-practice"><div id="practiceBody"></div></div>

<button class="printbtn" onclick="window.print()">🖨️ 列印 / 存 PDF</button>
<div class="toast" id="toast"></div>
</div>'''

RENDER_JS = r'''
const G=DATA.groups, VOCAB=DATA.vocab, Q=DATA.questions;
const $=id=>document.getElementById(id);
const VMAP={};VOCAB.forEach(v=>{VMAP[String(v.w).toLowerCase()]=v;});
function lookupV(k){return VMAP[k]||VMAP[k.replace(/s$/,'')]||VMAP[k.replace(/es$/,'')]||VMAP[k.replace(/ed$/,'')]||VMAP[k.replace(/ing$/,'')]||VMAP[k.replace(/ies$/,'y')];}
function wrapWords(t){return t.replace(/([A-Za-z][A-Za-z'\-]*)/g,'<span class="wtap" onclick="tapWord(this)">$1</span>');}
function tapWord(el){const w=el.textContent;const k=w.toLowerCase().replace(/[^a-z'\-]/g,'');if(k.length<2){return;}const v=lookupV(k);
  const added=window.EngReview&&EngReview.addWord(w,v?v.z:'',v?(v.p||''):'','閱讀生字');
  toast(added?('⭐ 已加入生字：'+w+(v&&v.z?'　'+v.z:'（待查，可到入口→我的複習補中文）')):('「'+w+'」已在生字本'));
  el.classList.add('wdone');}
const esc=s=>(s==null?'':String(s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
function splitEg(x){const m=x.match(/[一-鿿]/);if(!m)return{en:x,zh:''};const i=x.indexOf(m[0]);return{en:x.slice(0,i).trim(),zh:x.slice(i).trim()};}

function renderGram(){let h='';G.forEach(g=>{
  h+=`<section><div class="sec-head"><span class="ic">🧩</span><h2>${esc(g.name)}</h2><span class="cnt">${g.topics.length} 主題</span></div>`;
  g.topics.forEach((t,ti)=>{const n=t.note||{};
    h+=`<details class="pt"${ti===0?' open':''}><summary><span class="freq ${t.qCount>=34?'hi':'mid'}">共 ${t.qCount} 題</span>${esc(t.label)}<span class="arrow">▶</span></summary><div class="body">`;
    if(n.summary)h+=`<div class="say"><b>重點：</b>${esc(n.summary)}</div>`;
    (n.sections||[]).forEach(s=>{h+=`<div class="grp-title">🔹 ${esc(s.h)}</div>`;
      if(s.body)h+=`<div style="font-size:14.5px;margin:2px 0 7px;color:#4a4a55">${esc(s.body)}</div>`;
      (s.examples||[]).forEach(e=>{const o=splitEg(e);h+=`<div class="eg"><span class="en">${esc(o.en)}</span>${o.zh?`<span class="zh">${esc(o.zh)}</span>`:''}</div>`;});});
    if(n.mistakes&&n.mistakes.length){h+=`<div class="say" style="background:var(--no-bg);border-left-color:var(--no)"><b style="color:#c0435a">常見錯誤：</b><ul style="margin:5px 0 0;padding-left:18px;font-size:14px">`;n.mistakes.forEach(m=>h+=`<li>${esc(m)}</li>`);h+=`</ul></div>`;}
    if(n.tip)h+=`<div class="tip">${esc(n.tip)}</div>`;
    h+=`</div></details>`;});
  h+=`</section>`;});
  $('gramBody').innerHTML=h;}

function renderVocab(){const levels=[...new Set(VOCAB.map(v=>v.lv))].sort((a,b)=>a-b);let h='';
  levels.forEach(lv=>{const c=VOCAB.filter(v=>v.lv===lv).length;
    h+=`<details class="pt"><summary><span class="freq lo">${c} 字</span>第 ${lv} 級<span class="arrow">▶</span></summary><div class="body" data-lv="${lv}"><div class="say">點開載入…</div></div></details>`;});
  $('vocabBody').innerHTML=h;
  $('vocabBody').querySelectorAll('details').forEach(d=>d.addEventListener('toggle',()=>{
    if(!d.open)return;const body=d.querySelector('.body');if(body.dataset.done)return;
    const lv=+body.dataset.lv, ws=VOCAB.filter(v=>v.lv===lv);let hh='<div class="wlist">';
    ws.forEach(v=>{hh+=`<div class="wcard"><div class="wh"><span class="w">${esc(v.w)}</span>${v.p?`<span class="wp">${esc(v.p)}</span>`:''}<span class="wz">${esc(v.z)}</span></div>${v.e?`<div class="wex">${esc(v.e)}</div>`:''}</div>`;});
    hh+='</div>';body.innerHTML=hh;body.dataset.done='1';}));}

function renderReading(){const R=DATA.reading||[];if(!R.length||!$('readingBody'))return;
  const byG={};R.forEach((p,i)=>{(byG[p.g]=byG[p.g]||[]).push(i);});
  let h='';Object.keys(byG).forEach(g=>{h+=`<div class="grp-title">📖 ${esc(g)}（${byG[g].length} 篇）</div>`;
    byG[g].forEach(i=>{const p=R[i];const snip=esc((p.t||p.x).slice(0,30));
      h+=`<details class="pt"><summary><span class="freq lo">${p.qs.length} 題</span>${snip}…<span class="arrow">▶</span></summary><div class="body" data-ri="${i}"><div class="say">點開載入…</div></div></details>`;});});
  $('readingBody').innerHTML=h;
  $('readingBody').querySelectorAll('details').forEach(d=>d.addEventListener('toggle',()=>{
    if(!d.open)return;const body=d.querySelector('.body');if(body.dataset.done)return;
    const p=R[+body.dataset.ri];const L=['A','B','C','D'];
    let hh=`<div class="passage"><div class="wtip">💡 點文章中不會的單字，可加入「生字本」（到入口→我的複習）</div>${p.t?`<div class="pg">${esc(p.t)}</div>`:''}${wrapWords(esc(p.x)).replace(/\n/g,'<br>')}</div>`;
    p.qs.forEach((q,qi)=>{hh+=`<div class="qcard"><div class="stem">${qi+1}. ${esc(q.s)}</div><div class="opts">`;
      q.o.forEach((o,oi)=>{hh+=`<div class="opt ${oi===q.a?'ok':'dis'}"><span class="lab">${L[oi]}</span><span>${esc(o)}</span></div>`;});
      hh+=`</div><div class="fb show good"><div class="kp">✅ 正解 ${L[q.a]}</div>${esc(q.e)}</div></div>`;});
    body.innerHTML=hh;body.dataset.done='1';}));}

// ===== 練習 =====
let pool=[],idx=0,score=0,wrongList=[];
const LS=localStorage, WKEY='__NS__.cap.wrong';
function loadWrong(){try{return JSON.parse(LS.getItem(WKEY))||[]}catch(e){return[]}}
function practiceHome(){let h=`<div class="topbar"><h2>✏️ 練習</h2></div>`;
  const wb=loadWrong();
  h+='<div class="prcats">';
  h+=`<div class="prcat" onclick="startQuiz('__all__')" style="border-left-color:#e8899f"><span class="pci">🎲</span><div><h3>綜合隨機測驗</h3><div class="pcn">從全部 ${Q.length} 題隨機抽 12 題</div></div><span class="arrowr">▶</span></div>`;
  if(wb.length)h+=`<div class="prcat" onclick="startQuiz('__wrong__')" style="border-left-color:#e0a94a"><span class="pci">❌</span><div><h3>錯題複習</h3><div class="pcn">${wb.length} 題待複習</div></div><span class="arrowr">▶</span></div>`;
  G.forEach(g=>g.topics.forEach(t=>{h+=`<div class="prcat" onclick="startQuiz('${t.key}')"><span class="pci">🧩</span><div><h3>${esc(t.label)}</h3><div class="pcn">${t.qCount} 題</div></div><span class="arrowr">▶</span></div>`;}));
  h+='</div>';$('practiceBody').innerHTML=h;}
function shuffle(a){a=a.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
function startQuiz(key){let src;
  if(key==='__all__')src=shuffle(Q).slice(0,12);
  else if(key==='__wrong__'){const w=loadWrong();src=Q.filter(q=>w.includes(q.s)).slice(0,20);}
  else src=shuffle(Q.filter(q=>q.k===key)).slice(0,12);
  if(!src.length){toast('這個主題沒有題目');return;}
  pool=src;idx=0;score=0;wrongList=[];document.body.classList.add('quizzing');renderQ();}
function renderQ(){if(idx>=pool.length)return renderScore();
  const q=pool[idx];const labs=['A','B','C','D'];
  let h=`<div class="topbar"><button class="back" onclick="quitQuiz()">← 結束</button><h2>第 ${idx+1} / ${pool.length} 題</h2></div>`;
  h+=`<div class="qcard"><div class="qtag">${esc(q.u)}・難度 ${q.d}</div><div class="stem">${esc(q.s)}</div><div class="opts" id="opts">`;
  q.o.forEach((o,i)=>{h+=`<button class="opt" data-i="${i}" onclick="pick(${i})"><span class="lab">${labs[i]}</span><span>${esc(o)}</span></button>`;});
  h+=`</div><div class="fb" id="fb"></div><div class="btnrow" id="nextrow" style="display:none"><button class="btn primary" onclick="nextQ()">${idx+1>=pool.length?'看成績 →':'下一題 →'}</button></div></div>`;
  $('practiceBody').innerHTML=h;}
function pick(i){const q=pool[idx];const ok=(i===q.a);
  document.querySelectorAll('#opts .opt').forEach((b,bi)=>{b.classList.add('dis');b.onclick=null;
    if(bi===q.a)b.classList.add('ok');else if(bi===i)b.classList.add('no');});
  const fb=$('fb');fb.className='fb show '+(ok?'good':'bad');
  fb.innerHTML=`<div class="kp">${ok?'✅ 答對了':'❌ 答錯了，正解 '+['A','B','C','D'][q.a]}</div>${esc(q.e)}`;
  if(ok)score++;else{if(!wrongList.includes(q.s))wrongList.push(q.s);try{window.EngReview&&EngReview.addWrong({cat:q.u,stem:q.s,options:q.o,your:i,ans:q.a,expl:q.e});}catch(e){}}
  $('nextrow').style.display='flex';}
function nextQ(){idx++;renderQ();}
function renderScore(){document.body.classList.remove('quizzing');
  // 存錯題
  let w=loadWrong();const done=pool.map(q=>q.s);
  w=w.filter(s=>!done.includes(s)).concat(wrongList);LS.setItem(WKEY,JSON.stringify(w));
  const pct=Math.round(score/pool.length*100);
  let h=`<div class="scorebox"><div class="big">${score} / ${pool.length}</div><div class="sub">答對率 ${pct}%${pct>=80?'　太棒了 🎉':(pct>=60?'　不錯，再加油！':'　多看重點再練一次 💪')}</div></div>`;
  h+=`<div class="btnrow"><button class="btn primary" onclick="practiceHome()">回練習選單</button><button class="btn ghost" onclick="show('gram')">看文法重點</button></div>`;
  h+=`<div style="margin-top:16px"><b>本次題目回顧</b></div>`;
  pool.forEach((q,i)=>{const bad=wrongList.includes(q.s);
    h+=`<div class="rev"><div class="rh"><span class="mark ${bad?'no':'ok'}">${bad?'✗':'✓'}</span><span>${esc(q.u)}</span></div><div class="rq">${esc(q.s)}</div><div class="ra">正解：${['A','B','C','D'][q.a]}. ${esc(q.o[q.a])}</div><div class="rex">${esc(q.e)}</div></div>`;});
  $('practiceBody').innerHTML=h;window.scrollTo(0,0);}
function quitQuiz(){document.body.classList.remove('quizzing');practiceHome();}
function toast(m){const t=$('toast');t.textContent=m;t.classList.add('show');clearTimeout(t._t);t._t=setTimeout(()=>t.classList.remove('show'),1400);}
'''.replace('__NS__', NS)

NAV_JS = r'''
function show(v){document.querySelectorAll('.view').forEach(x=>x.classList.toggle('active',x.id==='v-'+v));
  document.querySelectorAll('.tabbar button').forEach(b=>b.classList.toggle('active',b.dataset.view===v));
  if(v==='practice')practiceHome();
  window.scrollTo({top:0,behavior:'auto'});}
document.querySelectorAll('[data-view]').forEach(el=>{el.addEventListener('click',()=>show(el.dataset.view));
  el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();show(el.dataset.view);}});});
function showWelcome(){document.getElementById('welcome').classList.add('show');}
function closeWelcome(){document.getElementById('welcome').classList.remove('show');try{localStorage.setItem('__NS__.onboarded','1');}catch(e){}}
document.getElementById('welcome').addEventListener('click',function(e){if(e.target.id==='welcome')closeWelcome();});
renderGram();renderVocab();renderReading();practiceHome();show('home');
try{if(!localStorage.getItem('__NS__.onboarded'))setTimeout(showWelcome,350);}catch(e){}
let _saved=[];
window.addEventListener('beforeprint',()=>{_saved=[];document.querySelectorAll('details.pt').forEach(d=>{_saved.push(d.open);d.open=true;});});
window.addEventListener('afterprint',()=>{document.querySelectorAll('details.pt').forEach((d,i)=>{d.open=_saved[i];});});
if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js').catch(()=>{});}
'''.replace('__NS__', NS)

INSTALL_JS = r'''(function(){var deferredPrompt=null;
function isStandalone(){return (window.matchMedia&&window.matchMedia("(display-mode: standalone)").matches)||navigator.standalone===true;}
function isIOS(){return /iphone|ipad|ipod/i.test(navigator.userAgent)||(navigator.platform==="MacIntel"&&navigator.maxTouchPoints>1);}
function render(){var el=document.getElementById("installBar");if(!el)return;if(isStandalone()){el.innerHTML="";return;}
  if(deferredPrompt)el.innerHTML='<button class="install-btn" onclick="__inst()">📲 安裝到桌面（免開瀏覽器） ➕</button>';
  else if(isIOS())el.innerHTML='<button class="install-btn sec" onclick="__instIOS()">📲 安裝到主畫面（iPad / iPhone） ›</button>';
  else el.innerHTML="";}
window.addEventListener("beforeinstallprompt",function(e){e.preventDefault();deferredPrompt=e;render();});
window.addEventListener("appinstalled",function(){deferredPrompt=null;render();});
window.__inst=function(){if(!deferredPrompt)return;deferredPrompt.prompt();deferredPrompt.userChoice.finally(function(){deferredPrompt=null;render();});};
window.__instIOS=function(){var el=document.getElementById("installBar");if(el)el.innerHTML='<div class="install-tip">📲 <b>加到桌面：</b>用 <b>Safari</b> 開啟 → 分享 ⬆️ → 加入主畫面 ➕ → 新增。<span class="install-x" onclick="__instClose()">知道了 ✓</span></div>';};
window.__instClose=function(){render();};render();})();'''

INSTALL_CSS = '''
  #installBar:empty{display:none}
  #installBar .install-btn{display:block;width:100%;border:0;border-radius:14px;padding:13px 15px;font-size:15px;font-weight:800;cursor:pointer;background:__THEME__;color:#fff;box-shadow:0 6px 16px rgba(67,56,202,.28)}
  #installBar .install-btn.sec{background:#e6e6fb;color:#3f38b8}
  #installBar .install-tip{background:#fff7e6;border:1px solid #ffe0a3;border-radius:14px;padding:13px;font-size:13px;line-height:1.85;color:#5a4a1a}
  #installBar .install-x{display:inline-block;margin-top:6px;color:#3f38b8;font-weight:800;cursor:pointer}
'''.replace('__THEME__', THEME)

WELCOME_CSS = '''
  .helpbtn{flex:0 0 auto;border:1.5px solid var(--line);background:#fff;border-radius:999px;padding:8px 13px;font-size:14.5px;font-weight:700;color:var(--ink);cursor:pointer;font-family:inherit}
  .wc-overlay{position:fixed;inset:0;background:rgba(30,30,42,.55);-webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px);z-index:100;display:none;align-items:center;justify-content:center;padding:18px}
  .wc-overlay.show{display:flex}
  .wc-card{background:#fff;border-radius:22px;max-width:400px;width:100%;padding:24px 22px 20px;box-shadow:0 20px 50px rgba(0,0,0,.32);max-height:88vh;overflow:auto;animation:wcIn .25s ease}
  @keyframes wcIn{from{opacity:0;transform:translateY(12px) scale(.98)}to{opacity:1;transform:none}}
  .wc-emoji{font-size:46px;text-align:center;line-height:1}
  .wc-card h2{text-align:center;margin:8px 0 2px;font-size:22px}
  .wc-sub{text-align:center;color:var(--soft);font-size:14px;margin-bottom:16px;line-height:1.5}
  .wc-step{display:flex;gap:11px;align-items:flex-start;background:var(--bg);border:1px solid var(--line);border-radius:13px;padding:11px 13px;margin-bottom:9px}
  .wc-step .wc-i{font-size:22px;flex:0 0 auto;line-height:1.3}
  .wc-step b{font-size:15px}.wc-step>div>div{font-size:13px;color:var(--soft);line-height:1.55;margin-top:1px}
  .wc-start{width:100%;border:0;border-radius:14px;padding:14px;font-size:16px;font-weight:800;color:#fff;background:__THEME__;cursor:pointer;margin-top:8px;font-family:inherit}
'''.replace('__THEME__', THEME)

ENGREVIEW_SRC = r'''(function(){if(window.EngReview)return;
var WK='engreview.wrong',VK='engreview.words',APP=__APP__;
function load(k){try{return JSON.parse(localStorage.getItem(k)||'{}')}catch(e){return{}}}
function save(k,o){try{localStorage.setItem(k,JSON.stringify(o))}catch(e){}}
function hash(s){var h=0,i;for(i=0;i<s.length;i++){h=(h*31+s.charCodeAt(i))|0}return(h>>>0).toString(36)}
function now(){return Date.now()}
var BOX=[0,1,3,7,16,40];
function addWrong(r){var w=load(WK);var id=hash((r.app||APP.id)+'|'+r.stem+'|'+(r.options||[]).join('~'));var e=w[id]||{id:id,first:now(),n:0};
 e.app=r.app||APP.id;e.appName=r.appName||APP.name;e.cat=r.cat||'其他';e.stem=r.stem;e.options=r.options;e.your=r.your;e.ans=r.ans;e.expl=r.expl||'';
 e.box=0;e.streak=0;e.due=now();e.n=(e.n||0)+1;e.ts=now();w[id]=e;save(WK,w);}
function graded(id,ok){var w=load(WK),e=w[id];if(!e)return;if(ok){e.streak=(e.streak||0)+1;e.box=Math.min((e.box||0)+1,BOX.length-1);if(e.streak>=2){delete w[id];save(WK,w);return;}e.due=now()+BOX[e.box]*86400000;}else{e.streak=0;e.box=0;e.due=now();}e.ts=now();w[id]=e;save(WK,w);}
function addWord(word,zh,pos,cat){var v=load(VK),k=String(word||'').toLowerCase().trim();if(!k)return false;
 if(!v[k]){v[k]={word:word,zh:zh||'（待查）',pos:pos||'',app:APP.id,appName:APP.name,cat:cat||'',box:0,streak:0,due:now(),ts:now()};save(VK,v);return true;}
 else{if((!v[k].zh||v[k].zh==='（待查）')&&zh){v[k].zh=zh;save(VK,v);}return false;}}
function setWordZh(word,zh){var v=load(VK),k=String(word).toLowerCase();if(v[k]){v[k].zh=zh;v[k].box=0;save(VK,v);}}
function wordGraded(word,ok){var v=load(VK),k=String(word).toLowerCase(),e=v[k];if(!e)return;if(ok){e.streak=(e.streak||0)+1;e.box=Math.min((e.box||0)+1,BOX.length-1);if(e.streak>=2){e.mastered=1;}e.due=now()+BOX[e.box]*86400000;}else{e.streak=0;e.box=0;e.mastered=0;e.due=now();}save(VK,v);}
function removeWord(word){var v=load(VK);delete v[String(word).toLowerCase()];save(VK,v);}
function cnt(o,due){var n=0,k;for(k in o){if(!due||o[k].due<=now())n++;}return n;}
window.EngReview={app:APP,addWrong:addWrong,graded:graded,addWord:addWord,setWordZh:setWordZh,wordGraded:wordGraded,removeWord:removeWord,
 wrong:function(){return load(WK)},words:function(){return load(VK)},
 wrongCount:function(d){return cnt(load(WK),d)},wordCount:function(d){return cnt(load(VK),d)}};
})();'''
REVIEW_JS = ENGREVIEW_SRC.replace('__APP__', json.dumps({'id': NS, 'name': APP_TITLE}, ensure_ascii=False))

html_out = f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="{THEME}">
<link rel="manifest" href="manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{APP_TITLE}">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
<title>{APP_TITLE}</title>
<style>{css}{INSTALL_CSS}{WELCOME_CSS}</style>
</head>
<body>
{body}
<script>{REVIEW_JS}</script>
<script>{data_js}</script>
<script>{RENDER_JS}</script>
<script>{NAV_JS}</script>
<script>{INSTALL_JS}</script>
</body>
</html>'''

open(os.path.join(APP, 'index.html'), 'w', encoding='utf-8').write(html_out)

# sw.js (快取 index + 圖示)，版本用內容雜湊
ver = hashlib.md5(html_out.encode('utf-8')).hexdigest()[:8]
sw = ("const C='%scap-%s';const A=['index.html','manifest.json','icon-192.png','icon-512.png','apple-touch-icon.png'];" % (NS, ver)
      + "self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(C).then(c=>c.addAll(A)))});"
      + "self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))))});"
      + "self.addEventListener('fetch',e=>{e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)))});")
open(os.path.join(APP, 'sw.js'), 'w', encoding='utf-8').write(sw)

sz = os.path.getsize(os.path.join(APP, 'index.html')) / 1024
print('✓ 產出 cap-english 分頁瀏覽版 app/index.html %.0f KB' % sz)
print('  文法群組:', len(groups), '| 主題:', sum(len(g['topics']) for g in groups), '| 單字:', len(vocab), '| 練習題:', len(pq))
