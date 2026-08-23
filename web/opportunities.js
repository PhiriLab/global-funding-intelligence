const opportunityStyle=document.createElement('link');
opportunityStyle.rel='stylesheet';
opportunityStyle.href='opportunities.css';
document.head.appendChild(opportunityStyle);

const opportunityEls={
  section:document.getElementById('opportunities'),
  grid:document.getElementById('opportunityCards'),
  count:document.getElementById('opportunityCount'),
  status:document.getElementById('opportunityFeedStatus'),
  filter:document.getElementById('opportunityLifecycleFilter'),
  search:document.getElementById('opportunitySearch')
};

let opportunityFeed=[];

function opportunityEscape(value){return String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function opportunityLifecycleLabel(value){return({closing_soon:'Closing soon',open:'Open',rolling:'Rolling',upcoming:'Upcoming',closed:'Closed',unknown:'Unknown'})[value]||value;}
function opportunityDate(value){if(!value)return 'Not verified';const date=new Date(value);return Number.isNaN(date.getTime())?'Not verified':new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short',timeZoneName:'short'}).format(date);}
function opportunityAmount(item){const currency=item.currency?`${item.currency} `:'';if(item.min_award!=null&&item.max_award!=null)return `${currency}${Number(item.min_award).toLocaleString()}–${Number(item.max_award).toLocaleString()}`;if(item.max_award!=null)return `Up to ${currency}${Number(item.max_award).toLocaleString()}`;if(item.total_fund!=null)return `Total fund ${currency}${Number(item.total_fund).toLocaleString()}`;return 'Amount not verified';}

function renderOpportunities(){
  if(!opportunityEls.grid)return;
  const lifecycle=opportunityEls.filter?.value||'all';
  const q=(opportunityEls.search?.value||'').trim().toLowerCase();
  const rows=opportunityFeed.filter(item=>(lifecycle==='all'||item.lifecycle===lifecycle)&&(!q||`${item.title} ${item.funder} ${item.programme||''} ${item.source_id} ${item.lifecycle}`.toLowerCase().includes(q)));
  if(opportunityEls.count)opportunityEls.count.textContent=String(rows.length);
  opportunityEls.grid.innerHTML=rows.length?rows.map(item=>`<article class="opportunity-card"><div class="card-top"><span class="lifecycle-badge ${opportunityEscape(item.lifecycle)}">${opportunityEscape(opportunityLifecycleLabel(item.lifecycle))}</span><span class="badge ${opportunityEscape(item.source_state)}">${opportunityEscape(item.source_state)}</span></div><h3>${opportunityEscape(item.title)}</h3><p class="meta">${opportunityEscape(item.funder)}${item.programme?` • ${opportunityEscape(item.programme)}`:''}</p><dl class="opportunity-facts"><div><dt>Deadline</dt><dd>${opportunityEscape(opportunityDate(item.closing_at))}</dd></div><div><dt>Funding</dt><dd>${opportunityEscape(opportunityAmount(item))}</dd></div><div><dt>Global Majority route</dt><dd>${opportunityEscape(item.global_majority_access||'unclear')}</dd></div></dl><p class="opportunity-warning">${opportunityEscape(item.eligibility||'Not determined — verify at source')}</p><div class="card-bottom"><span class="meta">Checked ${opportunityEscape(opportunityDate(item.source_checked_at))}</span><a class="source-link" href="${opportunityEscape(item.primary_url)}" target="_blank" rel="noreferrer">Primary call ↗</a></div></article>`).join(''):`<div class="opportunity-empty"><h3>No verified opportunities match this view</h3><p>${opportunityFeed.length?'Try another lifecycle or search term.':'The opportunity feed is ready but currently contains no published structured records. The funder directory below remains fully available.'}</p></div>`;
}

async function loadOpportunityFeed(){
  if(!opportunityEls.grid)return;
  try{
    const response=await fetch('data/opportunities.json',{cache:'no-store'});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const payload=await response.json();
    if(payload?.schema_version!==1||!Array.isArray(payload.opportunities))throw new Error('Unsupported opportunity feed schema');
    opportunityFeed=payload.opportunities;
    if(opportunityEls.status)opportunityEls.status.textContent=opportunityFeed.length?`Feed checked ${opportunityDate(payload.generated_at)} • ${opportunityFeed.length} structured opportunities`:`Feed checked ${opportunityDate(payload.generated_at)} • no structured opportunities published yet`;
    renderOpportunities();
  }catch(error){
    opportunityFeed=[];
    if(opportunityEls.status)opportunityEls.status.textContent='Live opportunity feed is temporarily unavailable; the verified funder directory remains available below.';
    opportunityEls.grid.innerHTML='<div class="opportunity-empty"><h3>Opportunity feed unavailable</h3><p>Nothing has been inferred or cached as current. Use the funder directory and primary-source links while the feed is unavailable.</p></div>';
    if(opportunityEls.count)opportunityEls.count.textContent='0';
    console.warn('Opportunity feed unavailable',error);
  }
}

opportunityEls.filter?.addEventListener('change',renderOpportunities);
opportunityEls.search?.addEventListener('input',renderOpportunities);
loadOpportunityFeed();