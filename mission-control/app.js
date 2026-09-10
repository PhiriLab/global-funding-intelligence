(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const state = {data:null, rotX:-7, rotY:0, zoom:1, dragging:false, x:0, y:0, paused:false};
  const colors = {green:'#5dffb0', amber:'#ffc65c', red:'#ff6262', cyan:'#65ddff'};

  function escapeHTML(v=''){return String(v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
  function setClock(){ $('#clock').textContent = new Intl.DateTimeFormat('en-GB',{dateStyle:'medium',timeStyle:'medium'}).format(new Date()).toUpperCase(); }
  setClock(); setInterval(setClock,1000);

  async function loadData(){
    try{
      const res = await fetch('./data/portfolio.json',{cache:'no-store'});
      if(!res.ok) throw new Error(`HTTP ${res.status}`);
      state.data = await res.json();
      render();
      $('#sourceStatus').textContent = `EVIDENCE SNAPSHOT ${new Date(state.data.generated_at).toLocaleString('en-GB')}`;
      liveGitHubRefresh();
    }catch(err){
      $('#sourceStatus').textContent = `DATA LOAD DEGRADED · ${err.message}`;
      $('#liveState').textContent='DEGRADED'; $('#livePulse').style.background=colors.red;
    }
  }

  function render(){
    renderMetrics(); renderScene(); renderTelemetry(); renderActions(); renderEvents();
    const ageH=Math.max(0,(Date.now()-new Date(state.data.generated_at).getTime())/36e5);
    $('#dataAge').textContent = `${ageH.toFixed(1)}H SNAPSHOT AGE`;
  }

  function renderMetrics(){
    const d=state.data; $('#healthScore').textContent=`${d.health_score}%`;
    $('#metrics').innerHTML = Object.entries(d.metrics).map(([k,v])=>`<div class="metric"><b>${escapeHTML(v)}</b><span>${escapeHTML(k.toUpperCase())}</span></div>`).join('');
  }

  function renderScene(){
    const layer=$('#orbitLayer'), projects=state.data.projects; layer.innerHTML='';
    const radiusX=34, radiusY=31;
    projects.forEach((p,i)=>{
      const a=(i/projects.length)*Math.PI*2 - Math.PI/2;
      const depth=Math.sin(a*1.35)*180;
      const x=50+Math.cos(a)*radiusX;
      const y=50+Math.sin(a)*radiusY;
      const el=document.createElement('button');
      el.className='node'; el.dataset.id=p.id; el.dataset.state=p.state; el.dataset.type=p.type; el.dataset.status=p.status.toLowerCase();
      el.style.left=`${x}%`; el.style.top=`${y}%`; el.style.transform=`translateZ(${depth}px) scale(${.92 + (depth+180)/1100})`;
      el.innerHTML=`<span><span class="n-title">${escapeHTML(p.name)}</span><span class="n-sub">${escapeHTML(p.status)}</span></span>`;
      el.addEventListener('click',(e)=>{e.stopPropagation(); inspect(p.id);}); layer.appendChild(el);
    }); applyTransform();
  }

  function inspect(id){
    const p=state.data.projects.find(x=>x.id===id); if(!p)return;
    $$('.node').forEach(n=>n.classList.toggle('active',n.dataset.id===id));
    $('#intelPanel').innerHTML=`
      <h2>${escapeHTML(p.name)}</h2><p>${escapeHTML(p.status)}</p>
      <div class="intel-meta">
        <div><label>OWNER</label><strong>${escapeHTML(p.owner)}</strong></div>
        <div><label>CONFIDENCE</label><strong>${Math.round(p.confidence*100)}%</strong></div>
        <div><label>READINESS</label><strong>${p.readiness}%</strong></div>
        <div><label>EVIDENCE</label><strong>${escapeHTML(p.evidence)}</strong></div>
      </div>
      <label class="kicker">READINESS VECTOR</label><div class="progress"><i style="width:${p.readiness}%"></i></div>
      <p><strong>Next milestone</strong><br>${escapeHTML(p.milestone)}</p>
      <p><strong>Constraint</strong><br>${escapeHTML(p.blocker)}</p>
      <div class="evidence ${p.evidence.toLowerCase()}"><strong>PROVENANCE</strong><br>${escapeHTML(p.source)}</div>`;
    speak(`${p.name}. ${p.status}. Next milestone: ${p.milestone}`);
  }

  function filter(kind){
    $$('.node').forEach(n=>{
      const show = kind==='all' || (kind==='stalled'&&n.dataset.status.includes('stalled')) || (kind==='live'&&(n.dataset.status.includes('live')||n.dataset.status.includes('operational'))) || (kind==='release'&&n.dataset.type==='release');
      n.classList.toggle('dim',!show);
    });
  }

  function renderTelemetry(){
    $('#telemetryBars').innerHTML=state.data.telemetry.map(t=>`<div class="t-row ${t.freshness==='fresh'?'':'stale'}" title="${escapeHTML(t.detail)}"><span>${escapeHTML(t.name)}</span><div class="t-track"><i style="width:${t.value}%"></i></div><b>${t.value}%</b></div>`).join('');
  }
  function renderActions(){
    $('#actionQueue').innerHTML=state.data.actions.map(a=>`<div class="action"><div class="prio">${escapeHTML(a.priority)}</div><div><b>${escapeHTML(a.text)}</b><span>${escapeHTML(a.owner)}</span></div><em>QUEUED</em></div>`).join('');
  }
  function renderEvents(){
    $('#eventStream').innerHTML=state.data.events.map(e=>`<div class="event"><time>${escapeHTML(e.time)}</time><i style="background:${colors[e.kind]||colors.cyan}"></i><span>${escapeHTML(e.text)}</span></div>`).join('');
  }

  function applyTransform(){ $('#orbitLayer').style.transform=`rotateX(${state.rotX}deg) rotateY(${state.rotY}deg) scale(${state.zoom})`; }
  const scene=$('#scene');
  scene.addEventListener('pointerdown',e=>{state.dragging=true;state.x=e.clientX;state.y=e.clientY;scene.setPointerCapture(e.pointerId)});
  scene.addEventListener('pointermove',e=>{if(!state.dragging)return;state.rotY+=(e.clientX-state.x)*.22;state.rotX-=(e.clientY-state.y)*.16;state.rotX=Math.max(-55,Math.min(45,state.rotX));state.x=e.clientX;state.y=e.clientY;applyTransform()});
  scene.addEventListener('pointerup',()=>state.dragging=false); scene.addEventListener('pointercancel',()=>state.dragging=false);
  scene.addEventListener('wheel',e=>{e.preventDefault();state.zoom=Math.max(.65,Math.min(1.5,state.zoom+(e.deltaY<0?.06:-.06)));applyTransform()},{passive:false});
  $('#resetView').addEventListener('click',()=>{state.rotX=-7;state.rotY=0;state.zoom=1;applyTransform();filter('all')});
  $$('[data-view]').forEach(b=>b.addEventListener('click',()=>filter(b.dataset.view)));

  function command(raw){
    const q=raw.trim().toLowerCase(); if(!q)return;
    if(q.includes('stalled')||q.includes('blocked')) filter('stalled');
    else if(q.includes('release')) filter('release');
    else if(q.includes('live')) filter('live');
    else if(q.includes('all')||q.includes('reset')) filter('all');
    const p=state.data.projects.find(p=>q.includes(p.name.toLowerCase())||q.includes(p.id)); if(p) inspect(p.id);
    if(q.includes('summary')||q.includes('brief')) speak(`Portfolio health ${state.data.portfolio_health}. ${state.data.metrics.live} operational assets. ${state.data.metrics.stalled} stalled release items. Priority is deployment closure.`);
    if(q.includes('founder')) speak('No current founder action is required unless a verified human-only boundary appears.');
  }
  $('#commandInput').addEventListener('keydown',e=>{if(e.key==='Enter'){command(e.target.value);e.target.select();}});

  function speak(text){ if(!('speechSynthesis'in window))return; window.speechSynthesis.cancel(); const u=new SpeechSynthesisUtterance(text);u.rate=1.05;u.pitch=.82;u.volume=.72;window.speechSynthesis.speak(u); }
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(SR){const r=new SR();r.lang='en-GB';r.interimResults=false;r.onstart=()=>$('#voiceBtn').classList.add('listening');r.onend=()=>$('#voiceBtn').classList.remove('listening');r.onresult=e=>{const t=e.results[0][0].transcript;$('#commandInput').value=t;command(t)};$('#voiceBtn').addEventListener('click',()=>r.start());}
  else $('#voiceBtn').addEventListener('click',()=>speak('Voice recognition is not available in this browser. Type a command instead.'));

  $('#pauseEvents').addEventListener('click',e=>{state.paused=!state.paused;e.target.textContent=state.paused?'RESUME':'PAUSE'});

  async function liveGitHubRefresh(){
    const targets=[['gfi','global-funding-intelligence'],['emunah','emunah-intelligence'],['researchkit','research-kit'],['gmhkit','gmh-research-kit'],['articleb','Article-B-role-Generator']];
    let ok=0;
    for(const [id,repo] of targets){
      try{
        const r=await fetch(`https://api.github.com/repos/PhiriLab/${encodeURIComponent(repo)}/commits?per_page=1`,{headers:{Accept:'application/vnd.github+json'}});
        if(!r.ok) continue; const j=await r.json(); const p=state.data.projects.find(x=>x.id===id); if(p&&j[0]){p.github_latest={sha:j[0].sha.slice(0,7),date:j[0].commit.committer.date,message:j[0].commit.message.split('\n')[0]};ok++;}
      }catch(_){/* fail closed: static evidence remains visible */}
    }
    $('#sourceStatus').textContent += ` · GITHUB LIVE ${ok}/${targets.length}`;
  }

  const c=$('#space'),ctx=c.getContext('2d');let stars=[];
  function resize(){const d=Math.min(devicePixelRatio||1,2);c.width=innerWidth*d;c.height=innerHeight*d;c.style.width=innerWidth+'px';c.style.height=innerHeight+'px';ctx.setTransform(d,0,0,d,0,0);stars=Array.from({length:Math.min(260,Math.floor(innerWidth*innerHeight/6500))},()=>({x:Math.random()*innerWidth,y:Math.random()*innerHeight,z:Math.random()*1+.1,s:Math.random()*1.25+.2}));}
  function draw(){ctx.clearRect(0,0,innerWidth,innerHeight);for(const s of stars){s.y+=.035*s.z;if(s.y>innerHeight)s.y=0;ctx.globalAlpha=.18+.55*s.z;ctx.fillStyle='#9adfff';ctx.fillRect(s.x,s.y,s.s,s.s)}ctx.globalAlpha=1;requestAnimationFrame(draw)}
  addEventListener('resize',resize);resize();draw();loadData();
})();