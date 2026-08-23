const opportunityStyle=document.createElement('link');
opportunityStyle.rel='stylesheet';
opportunityStyle.href='opportunities.css';
document.head.appendChild(opportunityStyle);

const toolbar=document.querySelector('.opportunity-toolbar');
if(toolbar){
  const countryLabel=document.createElement('label');
  countryLabel.innerHTML='Country code<input id="opportunityCountry" type="text" inputmode="latin" maxlength="2" placeholder="e.g. GB, ZA, KE" autocomplete="off" />';
  const orgLabel=document.createElement('label');
  orgLabel.innerHTML='Organisation type<select id="opportunityOrganisation"><option value="all">All organisation types</option><option value="unknown">Not verified</option></select>';
  const gmLabel=document.createElement('label');
  gmLabel.innerHTML='Global Majority route<select id="opportunityGMRoute"><option value="all">All routes</option><option value="direct">Direct</option><option value="partner_only">Partner only</option><option value="restricted">Restricted</option><option value="unclear">Not verified</option><option value="not_applicable">Not applicable</option></select>';
  const certaintyLabel=document.createElement('label');
  certaintyLabel.innerHTML='Evidence threshold<select id="opportunityEvidence"><option value="include_unknown">Include unverified routes</option><option value="verified_only">Verified route evidence only</option></select>';
  const summary=toolbar.querySelector('.opportunity-summary');
  toolbar.insertBefore(countryLabel,summary);
  toolbar.insertBefore(orgLabel,summary);
  toolbar.insertBefore(gmLabel,summary);
  toolbar.insertBefore(certaintyLabel,summary);
}

const opportunityEls={
  section:document.getElementById('opportunities'),
  grid:document.getElementById('opportunityCards'),
  count:document.getElementById('opportunityCount'),
  status:document.getElementById('opportunityFeedStatus'),
  filter:document.getElementById('opportunityLifecycleFilter'),
  search:document.getElementById('opportunitySearch'),
  country:document.getElementById('opportunityCountry'),
  organisation:document.getElementById('opportunityOrganisation'),
  gmRoute:document.getElementById('opportunityGMRoute'),
  evidence:document.getElementById('opportunityEvidence')
};

const OPPORTUNITY_STALE_HOURS=36;
let opportunityFeed=[];

function opportunityEscape(value){return String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function opportunityLifecycleLabel(value){return({closing_soon:'Closing soon',open:'Open',rolling:'Rolling',upcoming:'Upcoming',closed:'Closed',unknown:'Unknown'})[value]||value;}
function opportunityDate(value){if(!value)return 'Not verified';const date=new Date(value);return Number.isNaN(date.getTime())?'Not verified':new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short',timeZoneName:'short'}).format(date);}
function opportunityAmount(item){const currency=item.currency?`${item.currency} `:'';if(item.min_award!=null&&item.max_award!=null)return `${currency}${Number(item.min_award).toLocaleString()}–${Number(item.max_award).toLocaleString()}`;if(item.max_award!=null)return `Up to ${currency}${Number(item.max_award).toLocaleString()}`;if(item.total_fund!=null)return `Total fund ${currency}${Number(item.total_fund).toLocaleString()}`;return 'Amount not verified';}
function opportunityFreshness(value){const generated=new Date(value);if(Number.isNaN(generated.getTime()))return {stale:true,label:'Feed timestamp unavailable'};const ageHours=Math.max(0,(Date.now()-generated.getTime())/3600000);return ageHours>OPPORTUNITY_STALE_HOURS?{stale:true,label:`Feed is stale (${Math.floor(ageHours)}h old)`}:{stale:false,label:`Feed checked ${opportunityDate(value)}`};}
function hasRouteEvidence(item){return Boolean((item.applicant_types||[]).length||(item.eligible_countries||[]).length||(item.excluded_countries||[]).length||(item.lead_countries||[]).length||(item.partner_countries||[]).length||(item.eligible_income_groups||[]).length||item.oda_only!=null||item.consortium_required!=null||item.local_partner_required!=null||item.lead_location_rule||item.equity_or_lmic_requirement||(item.global_majority_access&&item.global_majority_access!=='unclear'));}
function countryRoute(item,country){
  if(!country)return 'all';
  const code=country.toUpperCase();
  if((item.excluded_countries||[]).includes(code))return 'excluded';
  if((item.lead_countries||[]).includes(code))return 'lead';
  if((item.partner_countries||[]).includes(code))return 'partner';
  if((item.eligible_countries||[]).includes(code))return 'eligible';
  if((item.lead_countries||[]).length||(item.partner_countries||[]).length||(item.eligible_countries||[]).length||(item.excluded_countries||[]).length)return 'not_listed';
  return 'unknown';
}
function routeSummary(item,country){
  const route=countryRoute(item,country);
  return ({all:'No country selected',lead:'Verified lead route',partner:'Verified partner route',eligible:'Verified eligible route',excluded:'Explicitly excluded by structured source',not_listed:'Not listed in structured country route',unknown:'Country route not verified'})[route]||route;
}
function populateOrganisationOptions(){
  if(!opportunityEls.organisation)return;
  const current=opportunityEls.organisation.value;
  const values=[...new Set(opportunityFeed.flatMap(item=>item.applicant_types||[]))].sort((a,b)=>a.localeCompare(b));
  opportunityEls.organisation.innerHTML='<option value="all">All organisation types</option><option value="unknown">Not verified</option>'+values.map(value=>`<option value="${opportunityEscape(value)}">${opportunityEscape(value.replaceAll('_',' '))}</option>`).join('');
  if([...opportunityEls.organisation.options].some(option=>option.value===current))opportunityEls.organisation.value=current;
}

function renderOpportunities(){
  if(!opportunityEls.grid)return;
  const lifecycle=opportunityEls.filter?.value||'all';
  const q=(opportunityEls.search?.value||'').trim().toLowerCase();
  const country=(opportunityEls.country?.value||'').trim().toUpperCase();
  const organisation=opportunityEls.organisation?.value||'all';
  const gmRoute=opportunityEls.gmRoute?.value||'all';
  const evidence=opportunityEls.evidence?.value||'include_unknown';
  const rows=opportunityFeed.filter(item=>{
    if(lifecycle!=='all'&&item.lifecycle!==lifecycle)return false;
    if(q&&!`${item.title} ${item.funder} ${item.programme||''} ${item.source_id} ${item.lifecycle} ${(item.applicant_types||[]).join(' ')}`.toLowerCase().includes(q))return false;
    if(gmRoute!=='all'&&(item.global_majority_access||'unclear')!==gmRoute)return false;
    const itemHasEvidence=hasRouteEvidence(item);
    if(evidence==='verified_only'&&!itemHasEvidence)return false;
    if(organisation==='unknown'&&(item.applicant_types||[]).length)return false;
    if(organisation!=='all'&&organisation!=='unknown'&&!(item.applicant_types||[]).includes(organisation))return false;
    if(country){
      const route=countryRoute(item,country);
      if(route==='excluded'||route==='not_listed')return false;
      if(evidence==='verified_only'&&route==='unknown')return false;
    }
    return true;
  });
  if(opportunityEls.count)opportunityEls.count.textContent=String(rows.length);
  opportunityEls.grid.innerHTML=rows.length?rows.map(item=>`<article class="opportunity-card"><div class="card-top"><span class="lifecycle-badge ${opportunityEscape(item.lifecycle)}">${opportunityEscape(opportunityLifecycleLabel(item.lifecycle))}</span><span class="badge ${opportunityEscape(item.source_state)}">${opportunityEscape(item.source_state)}</span></div><h3>${opportunityEscape(item.title)}</h3><p class="meta">${opportunityEscape(item.funder)}${item.programme?` • ${opportunityEscape(item.programme)}`:''}</p><dl class="opportunity-facts"><div><dt>Deadline</dt><dd>${opportunityEscape(opportunityDate(item.closing_at))}</dd></div><div><dt>Funding</dt><dd>${opportunityEscape(opportunityAmount(item))}</dd></div><div><dt>Global Majority route</dt><dd>${opportunityEscape(item.global_majority_access||'unclear')}</dd></div><div><dt>${country?`Route for ${country}`:'Applicant route'}</dt><dd>${opportunityEscape(country?routeSummary(item,country):(hasRouteEvidence(item)?'Structured route evidence available':'Not yet verified'))}</dd></div></dl><p class="opportunity-warning">${opportunityEscape(item.eligibility||'Not determined — verify at source')}</p><div class="card-bottom"><span class="meta">Checked ${opportunityEscape(opportunityDate(item.source_checked_at))}</span><a class="source-link" href="${opportunityEscape(item.primary_url)}" target="_blank" rel="noreferrer">Primary call ↗</a></div></article>`).join(''):`<div class="opportunity-empty"><h3>No verified opportunities match this view</h3><p>${opportunityFeed.length?'Broaden a filter or switch Evidence threshold to include unverified routes. Unknown is not treated as ineligible.':'The opportunity feed is ready but currently contains no published structured records. The funder directory below remains fully available.'}</p></div>`;
}

async function loadOpportunityFeed(){
  if(!opportunityEls.grid)return;
  try{
    const response=await fetch('data/opportunities.json',{cache:'no-store'});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const payload=await response.json();
    if(payload?.schema_version!==1||!Array.isArray(payload.opportunities))throw new Error('Unsupported opportunity feed schema');
    opportunityFeed=payload.opportunities;
    populateOrganisationOptions();
    const freshness=opportunityFreshness(payload.generated_at);
    if(opportunityEls.status){
      opportunityEls.status.dataset.freshness=freshness.stale?'stale':'current';
      opportunityEls.status.textContent=freshness.stale?`${freshness.label} • verify current status at each primary call before acting`:(opportunityFeed.length?`${freshness.label} • ${opportunityFeed.length} structured opportunities`:`${freshness.label} • no structured opportunities published yet`);
    }
    renderOpportunities();
  }catch(error){
    opportunityFeed=[];
    if(opportunityEls.status){opportunityEls.status.dataset.freshness='unavailable';opportunityEls.status.textContent='Live opportunity feed is temporarily unavailable; the verified funder directory remains available below.';}
    opportunityEls.grid.innerHTML='<div class="opportunity-empty"><h3>Opportunity feed unavailable</h3><p>Nothing has been inferred or cached as current. Use the funder directory and primary-source links while the feed is unavailable.</p></div>';
    if(opportunityEls.count)opportunityEls.count.textContent='0';
    console.warn('Opportunity feed unavailable',error);
  }
}

[opportunityEls.filter,opportunityEls.organisation,opportunityEls.gmRoute,opportunityEls.evidence].forEach(el=>el?.addEventListener('change',renderOpportunities));
opportunityEls.search?.addEventListener('input',renderOpportunities);
opportunityEls.country?.addEventListener('input',()=>{opportunityEls.country.value=opportunityEls.country.value.replace(/[^a-z]/gi,'').slice(0,2).toUpperCase();renderOpportunities();});
loadOpportunityFeed();