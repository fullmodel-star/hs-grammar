/* ===== 複習引擎 v2（RV2）— 家族共用核心 =====
   目標：解決「單元 100%、總複習只剩 75%」= 集中練習的熟練錯覺。
   兩大系統：
   (A) 總複習：跨單元加權抽題＋交錯排＋延後＋診斷熱力圖＋「精熟」閘門(≠當天通過)
   (B) 嚴格錯題本：完整度(每面向都要清)＋難度階梯(識別→提示→產出/概念變體)＋跨場次才畢業＋答錯退階
   純資料/演算法層，不綁 DOM；各 App 用 adapter 提供題目與渲染。單一 localStorage key。 */
(function(root){
'use strict';
var DAY=86400000;
/* box 1..6 的到期天數（SRS 間隔）；index 0 未用。
   2026-10-24：原本只到 index 5，box 6(最高級)取到 undefined 退回 1 天、權重反比 box 5 高。
   _docs 沒寫最高級間隔 → 暫定與 box 5 相同(35 天，最保守：不短於上一級)，之後可再調。
   規則：陣列必須「不遞減」，同樣天數沒看時等級高的權重才不會比等級低的高。 */
var BOX_DAYS=[0,1,3,7,16,35,35];
var MAXBOX=6;

function RV2(){}
var P=RV2.prototype;

/* ---- 初始化：key=localStorage 鍵；opts.topStepOf(type) 各題型最難階 ---- */
P.init=function(key,opts){
  this.key=key; this.opts=opts||{};
  this.topStepOf=this.opts.topStepOf||function(type){ return type==='vocab'?3 : type==='reading'?2 : type==='mcq'?2 : 3; };
  this.load(); return this;
};
/* 是不是「一般物件」（排除 null、陣列、字串、數字、布林） */
function isObj(x){ return !!x && typeof x==='object' && !Array.isArray(x); }
P.load=function(){
  var raw=this._get(this.key), d=null, bad=false;
  try{ d=JSON.parse(raw); }catch(e){ d=null; bad=true; }
  // 存檔是 JSON 但不是物件("字串"/數字/true/[])：當作沒有存檔重新開始。
  // 原始內容(壞 JSON 或非物件)先不覆寫，等使用者真的作答才存新檔(保留復原機會)，見 save()/_touch()
  if(!isObj(d)){ if(d!==null) bad=true; d={}; }
  this._holdRaw=!!(bad && raw); this._dirty=false;
  d.ver=2;
  // 各區塊型別不對(例如陣列)就換成空物件；正常存檔不受影響(逐字相同)
  if(!isObj(d.items)) d.items={};       // 累積複習用：{id:{unit,tag,seen,correct,wrong,box,lastSeen,lastResult}}
  if(!isObj(d.wrong)) d.wrong={};       // 嚴格錯題本
  if(!isObj(d.retained)) d.retained={}; // {unit:true} 精熟(延後混合複習存活)
  if(!isObj(d.roll)) d.roll={};         // {unit:{r:EWMA, n}} 保留率滾動
  if(!isObj(d.sess)) d.sess={id:null, started:0, ans:0}; // 當前總複習/錯題場次
  if(!isObj(d.stats)) d.stats={reviews:0};
  this.db=d; this._repairWrong(); return d;
};
/* 修補錯題本裡壞掉的單筆：整筆缺 facets(或型別不對)且題型已知 → 依題型重建面向(重新從 step 1、立即到期)。
   題型也沒有的整筆壞資料留著不動，到期數/完整度/建場次都會跳過它(見 facetKeys)。只動壞掉那一筆。 */
P._repairWrong=function(){
  var wr=this.db.wrong, self=this;
  Object.keys(wr).forEach(function(id){ var w=wr[id];
    if(isObj(w) && !isObj(w.facets) && typeof w.type==='string'){ w.facets={}; self._initFacets(w); }
  });
};
P._initFacets=function(w){
  var faces=(w.type==='vocab')?['recog','prod']:['concept'];
  var top=this.topStepOf(w.type);
  faces.forEach(function(f){ w.facets[f]={step:1, streak:0, cleared:false, due:0, lastPassDay:-1, lastPassAt:0, lastPassAns:-1, sessionLock:null, top:top}; });
};
/* 讀錯題用：壞掉的單筆(不是物件、沒有 facets、面向不是物件)回傳空清單＝跳過，不讓整個錯題本崩潰 */
function facetKeys(w){
  if(!isObj(w) || !isObj(w.facets)) return [];
  return Object.keys(w.facets).filter(function(k){ return isObj(w.facets[k]); });
}
/* 標記「使用者真的作答了」：之後 save() 才會覆寫原本壞掉的存檔 */
P._touch=function(){ this._dirty=true; };
P.save=function(){
  if(this._holdRaw){ if(!this._dirty) return; this._holdRaw=false; }  // 壞存檔：使用者作答前不覆寫
  try{ this._set(this.key, JSON.stringify(this.db)); }catch(e){}
};
/* 儲存後端（測試時可覆寫） */
P._get=function(k){ return (typeof localStorage!=='undefined')?localStorage.getItem(k):(this._mem&&this._mem[k]); };
P._set=function(k,v){ if(typeof localStorage!=='undefined'){ localStorage.setItem(k,v); } else { this._mem=this._mem||{}; this._mem[k]=v; } };

/* 現在時間（可注入，測試用） */
P.now=function(){ return this._now?this._now:Date.now(); };
/* 今天＝台北(UTC+8)日曆日的日序號。2026-10-24 前用 UTC 日(日界線落在台北早上 08:00)。
   存檔的時間戳(lastSeen/due/lastPassAt…)仍是 UTC 毫秒不變；只有 lastPassDay 這種「日序號」受影響，
   舊存檔的 lastPassDay 只用來比「是不是同一天」，換算後最多讓一次台北 00:00–08:00 的同日作答被當隔日放行，不會清掉任何進度。 */
var TZ_OFFSET=8*3600000;
P.today=function(){ return Math.floor((this.now()+TZ_OFFSET)/DAY); };

/* ============ (A) 總複習：加權 + 交錯 ============ */
/* 每題權重：過去錯的最重、太久沒看次之、SRS 逾期再加、學習近時輕微 */
P.reviewWeight=function(it){
  var now=this.now();
  var days=(now-(it.lastSeen||0))/DAY;
  var errRate=it.seen? it.wrong/it.seen : 0.5;   // 未測=0.5(不確定)
  var box=it.box||1;
  var overdue=Math.max(0, days-(BOX_DAYS[Math.min(box,MAXBOX)]||1));
  return 0.50*(1+3*errRate)          // 過去錯的權重最高
       + 0.35*Math.min(days/7,3)     // 太久沒看(staleness)
       + 0.15*(1+overdue/7);         // SRS 逾期加成（原 recency 項因 unitOrder 未寫入失效，已移除）
};
/* 從 pool(含所有已完成單元的題 id) 加權抽 N 題，單元不超額、交錯排 */
P.buildReview=function(pool, N){
  var self=this, now=this.now();
  var items=pool.map(function(id){ var it=self.db.items[id]||{}; it.id=id; return {id:id, unit:it.unit, w:self.reviewWeight(it)}; });
  var units={}; items.forEach(function(x){ units[x.unit]=1; });
  var nUnits=Math.max(1, Object.keys(units).length);
  var capPerUnit=Math.max(2, Math.ceil(N/nUnits*1.8));
  var picked=[], per={};
  var bag=items.slice();
  while(picked.length<N && bag.length){
    var tot=0,i; for(i=0;i<bag.length;i++) tot+=bag[i].w;
    var r=this._rand()*tot, acc=0, sel=0;
    for(i=0;i<bag.length;i++){ acc+=bag[i].w; if(acc>=r){ sel=i; break; } }
    var it=bag[sel]; bag.splice(sel,1);
    if((per[it.unit]||0)<capPerUnit){ picked.push(it); per[it.unit]=(per[it.unit]||0)+1; }
  }
  return this.interleave(picked).map(function(x){ return x.id; });
};
/* 交錯：相鄰盡量不同單元 */
P.interleave=function(arr){
  var out=[], pool=arr.slice(), lastUnit=null, guard=0;
  while(pool.length){
    var i=0; while(i<pool.length && pool[i].unit===lastUnit && pool.length>1 && guard<9999){ i++; guard++; }
    if(i>=pool.length) i=0;
    lastUnit=pool[i].unit; out.push(pool.splice(i,1)[0]);
  }
  return out;
};
P._rand=function(){ return this._rng?this._rng():Math.random(); };

/* 記錄一題總複習結果（更新 SRS box + 統計） */
P.recordReview=function(id, unit, ok, tag){
  this._touch(); this._ownTick=null;
  var it=this.db.items[id]||{unit:unit, tag:tag, seen:0, correct:0, wrong:0, box:1, lastSeen:0};
  it.unit=unit; if(tag)it.tag=tag;
  it.seen=(it.seen||0)+1;
  if(ok){ it.correct=(it.correct||0)+1; it.box=Math.min(MAXBOX,(it.box||1)+1); }
  else  { it.wrong=(it.wrong||0)+1; it.box=1; }
  it.lastResult=ok?1:0; it.lastSeen=this.now();
  this.db.items[id]=it;
};
/* 一場總複習結束：算每單元保留率(EWMA)、更新精熟、回傳診斷 */
P.finishReview=function(results){
  // results: [{id,unit,tag,ok}]
  this._touch();
  var byUnit={}, byTag={};
  results.forEach(function(r){
    (byUnit[r.unit]=byUnit[r.unit]||{c:0,n:0}); byUnit[r.unit].n++; if(r.ok)byUnit[r.unit].c++;
    if(r.tag){ (byTag[r.tag]=byTag[r.tag]||{c:0,n:0}); byTag[r.tag].n++; if(r.ok)byTag[r.tag].c++; }
  });
  var self=this, alpha=0.3;                        // 較平滑(原0.5太跳、一場手氣就翻band)
  Object.keys(byUnit).forEach(function(u){
    var ret=byUnit[u].c/byUnit[u].n;
    var cur=self.db.roll[u]||{r:ret, n:0};
    cur.r=cur.n? (alpha*ret+(1-alpha)*cur.r) : ret;
    cur.n=(cur.n||0)+1; cur.last=ret; cur.attempted=(cur.attempted||0)+byUnit[u].n;
    self.db.roll[u]=cur;
    // 精熟閘門：延後混合複習 rolling≥85% 且累計≥10題≥2場最近一場≥80%(提高可靠度、少發假精熟)
    if(cur.r>=0.85 && cur.attempted>=10 && cur.n>=2 && ret>=0.80) self.db.retained[u]=true;
    else if(cur.r<0.85) self.db.retained[u]=false;
  });
  this.db.stats.reviews=(this.db.stats.reviews||0)+1;
  this.save();
  return this.diagnosis(byTag);
};
/* 診斷：每單元保留率分級 + 最弱單元/主題 */
P.diagnosis=function(byTag){
  var self=this, units=[];
  Object.keys(this.db.roll).forEach(function(u){
    var r=self.db.roll[u].r, band=r>=0.85?'master':r>=0.6?'shaky':'weak';
    units.push({unit:u, r:r, band:band, retained:!!self.db.retained[u]});
  });
  units.sort(function(a,b){ return a.r-b.r; });
  var weakUnits=units.filter(function(x){ return x.band!=='master'; }).slice(0,5);
  var weakTag=null;
  if(byTag){ var wt=Object.keys(byTag).map(function(t){ return {tag:t, r:byTag[t].c/byTag[t].n}; }).sort(function(a,b){return a.r-b.r;}); weakTag=wt[0]||null; }
  return {units:units, weakUnits:weakUnits, weakTag:weakTag};
};
P.retainedCount=function(totalUnits){ var n=0,self=this; Object.keys(this.db.retained).forEach(function(u){ if(self.db.retained[u])n++; }); return {retained:n, total:totalUnits}; };

/* ============ (B) 嚴格錯題本 ============ */
/* facets: vocab→{recog,prod}; 其餘→{concept}。needClears 隨 misses 升；起始 step 隨 misses 升 */
P.recalcDifficulty=function(w){
  var m=w.misses||1;                       // 拆掉「只增不減的棘輪」：封頂 3，避免弱生門柱一直後退而放棄
  w.needClears=m>=3?3:2;                    // 1-2→2, ≥3→3(不再到4)
  w.startStep=m>=3?2:1;                     // 錯 ≥3 次直接從難階起跳
};
P.addWrong=function(id, type, unit, tag){
  this._touch();
  var w=this.db.wrong[id];
  if(!isObj(w)){
    w={type:type, unit:unit, tag:tag, misses:0, addedAt:this.now(), variantRotate:0, facets:{}};
    this._initFacets(w);
  } else if(!isObj(w.facets)){
    // 壞掉的單筆(缺 facets、載入時又沒題型可修補)：用這次的題型補建面向，misses 等其他欄位保留
    if(typeof w.type!=='string') w.type=type;
    w.facets={}; this._initFacets(w);
  } else if(w.graduated || (facetKeys(w).length && facetKeys(w).every(function(k){ return w.facets[k].cleared; }))){
    // 復發：更難。第二個條件＝舊版留下的死題(graduated=false 但面向全 cleared)，學生再錯時一併救回
    w.graduated=false;
    // 畢業後再錯：各面向重新進入待複習(否則 cleared 仍為 true，建場次/到期數都跳過＝死題)。
    // 退一階(同 gradeFacet 答錯規則)、streak 歸零、立即到期、解除本場鎖；lastPassDay 保留(同日仍需插題才算)
    facetKeys(w).forEach(function(k){ var f=w.facets[k];
      f.cleared=false; f.streak=0; f.due=0; f.sessionLock=null; f.step=Math.max(1,(f.step||1)-1); });
  }
  w.misses=(w.misses||0)+1; this.recalcDifficulty(w);
  // 復發或加難：起始 step 套到未清面向
  var ss=w.startStep;
  facetKeys(w).forEach(function(f){ if(!w.facets[f].cleared) w.facets[f].step=Math.max(w.facets[f].step, ss===2?2:w.facets[f].step); });
  this.db.wrong[id]=w; this.save();
  return w;
};
/* 一個「合格正確」是否可累積 streak：跨場次(隔日) 或 同日中間插 ≥3 題。考前衝刺模式直接放行 */
P.canScorePass=function(f){
  if(this.cram) return true;                              // 考前衝刺：不套跨場次閘門(學生要求，考前一晚放行)
  var s=this.db.sess;
  if(f.sessionLock===s.id) return false;                 // 本場已推進(防當場連點硬背)
  var day=this.today();
  if(f.lastPassDay!==day) return true;                    // 隔日 OK
  // 同日：中間插 ≥3 題即可(移除 20 分鐘牆，太硬會退化成只能明天)。
  // 2026-10-24：改用跨場次累計題數 db.tick(tickSession 遞增、開新場次不歸零)，前一場剩下的題也算。
  // 舊版合格的面向沒有 lastPassTick → 沿用舊算法(本場題數−lastPassAns)，最多影響換版當天一次。
  if(typeof f.lastPassTick==='number') return ((this.db.tick||0)-f.lastPassTick)>=3;
  return (s.ans-(f.lastPassAns||0))>=3;
};
P.setCram=function(on){ this.cram=!!on; };
/* 放生：把死題/不想理的題移出錯題本 */
P.retireWrong=function(id){ if(isObj(this.db.wrong[id])){ this._touch(); this.db.wrong[id].graduated=true; this.db.wrong[id].retired=true; this.save(); } };
/* 對一個面向作答：ok=該步答對；opts.confident=學生自評「我確定」(非用刪的)；opts.typed=產出型作答。
   自評閘門：純選擇題在最難階，只有「我確定＋答對」才累積 streak；打字產出題天然算數。
   回傳 {cleared, graduated, msg, step, xp} */
P.gradeFacet=function(id, facet, ok, opts){
  opts=opts||{}; var confident=opts.confident, typed=!!opts.typed;
  var w=this.db.wrong[id]; if(!isObj(w)) return {err:'no-item'};
  var f=isObj(w.facets)?w.facets[facet]:null; if(!isObj(f)) return {err:'no-facet'};
  this._touch(); this._ownTick=null;
  var top=this.topStepOf(w.type);
  if(!ok){
    // 答錯：退階(只退一階、給手滑容錯)、streak 歸零、misses++、變更難
    f.step=Math.max(1, f.step-1); f.streak=0;
    w.misses=(w.misses||0)+1; this.recalcDifficulty(w);
    this.save();
    return {cleared:false, graduated:false, wrong:true, step:f.step, msg:'退回上一階，這題變更難了'};
  }
  // 答對但在最難階、是選擇題、且自評「用刪的」→ 不算數(堵四選一刪去法矇混)
  if(f.step>=top && !typed && confident===false){
    this.save();
    return {cleared:false, graduated:false, notsure:true, step:f.step, msg:'用刪的不算——要「我確定」答對才算徹底會了'};
  }
  if(f.step<top){ f.step++; this.save(); return {cleared:false, graduated:false, step:f.step, msg:'升到更難的一階'}; }
  // 已在最難階：需跨場次(或考前衝刺)才計 streak
  if(this.canScorePass(f)){
    f.streak++; f.sessionLock=this.db.sess.id; f.lastPassDay=this.today(); f.lastPassAt=this.now(); f.lastPassAns=this.db.sess.ans; f.lastPassTick=this.db.tick||0;
    this._ownTick={f:f, sess:this.db.sess.id, tick:f.lastPassTick};  // App 慣例：gradeFacet 後緊接 tickSession＝這題自己的計數，不算「中間插的題」
    f.due=this.now()+(f.streak>=2?3*DAY:f.streak>=1?DAY:10*60000);
    var xp=(typed?3:confident?2:1);                       // 打字/自評確定給較多 XP(誘因據實回報)
    if(f.streak>=w.needClears){ f.cleared=true; w.misses=Math.max(1,(w.misses||1)-1); }  // 清除→misses 衰退(門柱不再只進不退)
    var grad=facetKeys(w).every(function(k){ return w.facets[k].cleared; });
    if(grad){ w.graduated=true; this.save(); return {cleared:true, graduated:true, step:f.step, xp:xp+3, msg:'這題徹底畢業 🎓'}; }
    this.save();
    return {cleared:f.cleared, graduated:false, step:f.step, xp:xp, msg:f.cleared?'這個面向清除了':('跨場次 '+f.streak+'/'+w.needClears)};
  } else {
    this.save();
    return {cleared:false, graduated:false, spaced:true, step:f.step, msg:'答對了！明天(或間隔後)再答對一次就徹底畢業'};
  }
};
/* 今天到期該複習的錯題面向數(供每日碎量推送) */
P.dueCount=function(){ var n=0,now=this.now(),self=this; Object.keys(this.db.wrong).forEach(function(id){ var w=self.db.wrong[id]; if(!isObj(w) || w.graduated)return; facetKeys(w).forEach(function(k){ var f=w.facets[k]; if(!f.cleared && (f.due||0)<=now) n++; }); }); return n; };
/* 完整度：以「面向」為分母 */
P.completeness=function(){
  var items=this.db.wrong, byType={}, totF=0, clrF=0, self=this;
  Object.keys(items).forEach(function(id){ var w=items[id]; if(!isObj(w) || w.graduated) return;
    var ks=facetKeys(w); if(!ks.length) return;             // 壞掉的單筆跳過，其他題照算
    var t=w.type; byType[t]=byType[t]||{c:0,n:0};
    ks.forEach(function(k){ var f=w.facets[k]; totF++; byType[t].n++; if(f.cleared){ clrF++; byType[t].c++; } });
  });
  return {clearedFacets:clrF, totalFacets:totF, pct: totF? Math.round(clrF/totF*100):100, byType:byType};
};
/* 建一場錯題複習：到期優先、頑固(misses≥4)置頂、同題面向不連續 */
P.buildWrongSession=function(limit){
  var self=this, now=this.now(), rows=[];
  Object.keys(this.db.wrong).forEach(function(id){ var w=self.db.wrong[id]; if(!isObj(w) || w.graduated) return;
    facetKeys(w).forEach(function(fk){ var f=w.facets[fk]; if(f.cleared) return;
      var due=(f.due||0)<=now?0:1;
      rows.push({id:id, facet:fk, misses:w.misses, due:due, stubborn:(w.misses>=4)?0:1, step:f.step});
    });
  });
  rows.sort(function(a,b){ return a.stubborn-b.stubborn || a.due-b.due || b.misses-a.misses; });
  // 同題面向不相鄰
  var out=[], last=null;
  while(rows.length){ var i=0; while(i<rows.length && rows[i].id===last && rows.length>1) i++; if(i>=rows.length)i=0; last=rows[i].id; out.push(rows.splice(i,1)[0]); }
  return limit? out.slice(0,limit) : out;
};
/* 開一個新場次（總複習/錯題複習共用） */
P.startSession=function(){ this._ownTick=null; this.db.sess={id:'s'+this.today()+'_'+Math.floor(this._rand()*1e6), started:this.now(), ans:0}; this.save(); };
/* tick＝跨場次累計題數(同日插題判斷用，開新場次不歸零)。
   合格那題在同一場、緊接著的第一次 tick 是「它自己」的計數 → 併入合格點，之後的才算中間插的題 */
P.tickSession=function(){
  this._touch();
  var t0=this.db.tick||0, o=this._ownTick; this._ownTick=null;
  this.db.sess.ans=(this.db.sess.ans||0)+1; this.db.tick=t0+1;
  if(o && o.sess===this.db.sess.id && o.tick===t0 && o.f.lastPassTick===t0) o.f.lastPassTick=t0+1;
};

/* 匯出 */
if(typeof module!=='undefined' && module.exports){ module.exports=RV2; }
root.RV2=RV2;
})(typeof window!=='undefined'?window:globalThis);
