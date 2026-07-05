const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(__dirname+'/../app/index.html','utf8');
const errors=[];const log=(...a)=>console.log('  ',...a);
const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,url:'https://local/',
  beforeParse(w){w.scrollTo=()=>{};w.matchMedia=()=>({matches:false});}});
const w=dom.window;
w.addEventListener('error',e=>errors.push(e.error?e.error.stack:e.message));
setTimeout(()=>{try{
  const d=w.document;
  log('分頁按鈕:',d.querySelectorAll('.tabbar button').length);
  log('文法重點卡(details.pt):',d.querySelectorAll('#gramBody details.pt').length);
  log('首頁類別卡:',d.querySelectorAll('#v-home .cat-tile').length);
  log('單字級別:',d.querySelectorAll('#vocabBody details').length);
  // 展開第一個單字級別(懶載入)
  const v1=d.querySelector('#vocabBody details');v1.open=true;v1.dispatchEvent(new w.Event('toggle'));
  log('第1級單字卡:',d.querySelectorAll('#vocabBody .wcard').length);
  // 切到練習
  w.show('reading');log('閱讀分頁篇數:',d.querySelectorAll('#readingBody details').length);var r1=d.querySelector('#readingBody details');if(r1){r1.open=true;r1.dispatchEvent(new w.Event('toggle'));log('第1篇載入題數:',r1.querySelectorAll('.qcard').length);}w.show('practice');
  log('練習主題列:',d.querySelectorAll('#practiceBody .prcat').length);
  // 開始一個主題測驗
  w.startQuiz('subjunctive');
  log('題目選項:',d.querySelectorAll('#opts .opt').length);
  const q=d.querySelectorAll('#opts .opt');if(q.length){w.pick(0);log('作答後有回饋:',d.querySelector('#fb.show')!=null);}
  w.nextQ&&w.nextQ();
  // 綜合測驗跑完看成績
  w.startQuiz('__all__');for(let i=0;i<12;i++){if(d.querySelector('#opts .opt'))w.pick(1);w.nextQ();}
  log('成績頁:',d.querySelector('.scorebox')!=null);
  log('列印展開:',(()=>{w.dispatchEvent(new w.Event('beforeprint'));return d.querySelectorAll('details.pt[open]').length;})());
}catch(e){errors.push('FLOW: '+e.stack);}
if(errors.length)console.log('✗ 錯誤:\n'+errors.join('\n---\n'));else console.log('✓ cap版面煙霧測試通過：分頁/重點卡/單字懶載入/練習作答/成績/列印 全程無崩潰');
process.exit(errors.length?1:0);
},500);
