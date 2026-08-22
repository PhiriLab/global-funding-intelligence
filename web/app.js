const sources = [
  {id:'science_for_africa',name:'Science for Africa Foundation',region:'Africa',state:'structured_beta_detail',priority:'critical',access:'direct',url:'https://scienceforafrica.foundation/funding',note:'African-led funding and Grand Challenges Africa. Detail pages are structured beta; index state alone is not treated as proof a call is open.'},
  {id:'idrc',name:'International Development Research Centre',region:'global_majority',state:'structured_beta',priority:'high',access:'direct',url:'https://idrc-crdi.ca/en/funding',note:'Research funding focused on development priorities, with source-specific parsing for call fields and explicit budget ambiguity handling.'},
  {id:'tdr_who',name:'WHO/TDR',region:'global_majority',state:'index_only',priority:'critical',access:'direct',url:'https://tdr.who.int/grants',note:'Global health research and training. Open calls route through the eTDR portal and are therefore link-only until a structured portal adapter is available.'},
  {id:'cepi',name:'CEPI',region:'global',state:'partial',priority:'high',access:'mixed',url:'https://cepi.net/calls-for-proposals',note:'Vaccine and epidemic-preparedness funding. Call index is authoritative; some specifications are PDF-backed and remain gated.'},
  {id:'elrha',name:'Elrha',region:'global',state:'index_only',priority:'high',access:'direct',url:'https://www.elrha.org/funding-opportunities/',note:'Humanitarian research and innovation. Current listings can include procurement/consultancy notices, so call type must be verified.'},
  {id:'grand_challenges_canada',name:'Grand Challenges Canada',region:'global_majority',state:'index_only',priority:'high',access:'direct',url:'https://www.grandchallenges.ca/apply-for-funding/',note:'Innovation funding with a strong Global Majority focus. Fluxx-based application routes require dedicated call-level normalization.'},
  {id:'global_innovation_fund',name:'Global Innovation Fund',region:'global_majority',state:'partial',priority:'high',access:'direct',url:'https://www.globalinnovation.fund/apply/about/',note:'Development innovation finance. Application-portal state and eligibility remain authoritative.'},
  {id:'gates_foundation',name:'Gates Foundation',region:'global',state:'partial',priority:'high',access:'mixed',url:'https://www.gatesfoundation.org/about/how-we-work/grant-opportunities',note:'Public RFPs coexist with invitation-only funding. The interface never presents invitation-only programmes as open applications.'},
  {id:'grand_challenges',name:'Grand Challenges Network',region:'global',state:'index_only',priority:'high',access:'mixed',url:'https://grandchallenges.org/challenges/',note:'Discovery network. Final eligibility must resolve to the primary issuing partner.'},
  {id:'fogarty',name:'Fogarty International Center',region:'global',state:'index_only',priority:'critical',access:'direct',url:'https://www.fic.nih.gov/Funding/Pages/default.aspx',note:'NIH-linked global health research and training; final notice rules come from the NIH notice or Grants.gov.'},
  {id:'nih',name:'US National Institutes of Health',region:'global',state:'partial',priority:'critical',access:'mixed',url:'https://grants.nih.gov/funding',note:'Large global research funding ecosystem. Foreign-organisation eligibility is kept separate from foreign-component participation.'},
  {id:'novo_nordisk_foundation',name:'Novo Nordisk Foundation',region:'global',state:'index_only',priority:'high',access:'mixed',url:'https://novonordiskfonden.dk/en/grants/',note:'Major philanthropic science funder; tracked at the authoritative grants index pending deeper call normalization.'},
  {id:'pfizer_independent_grants',name:'Pfizer Independent Grants',region:'global',state:'partial',priority:'high',access:'mixed',url:'https://www.pfizer.com/about/programs-policies/grants',note:'Independent medical education, quality improvement and research opportunities are kept distinct.'},
  {id:'gsk_supported_studies',name:'GSK Supported Studies',region:'global',state:'manual_verify',priority:'high',access:'mixed',url:'https://iss.gsk.com/',note:'Investigator-sponsored studies vary by disease area and submission window and require portal-level verification.'},
  {id:'gavi',name:'Gavi, the Vaccine Alliance',region:'global_majority',state:'partial',priority:'high',access:'direct',url:'https://www.gavi.org/investing-gavi/funding',note:'Country financing, market-shaping and research/innovation opportunities are distinguished rather than pooled.'},
  {id:'ukri',name:'UK Research and Innovation',region:'UK',state:'structured_beta',priority:'critical',access:'mixed',url:'https://www.ukri.org/opportunity/',note:'Structured Funding Finder coverage with deterministic extraction of status, funder, award and deadline fields.'},
  {id:'nihr',name:'NIHR Research Funding',region:'UK',state:'structured_beta',priority:'critical',access:'mixed',url:'https://www.nihr.ac.uk/research-funding',note:'UK health and care research funding; Global Health opportunities are especially relevant to LMIC partnerships.'},
  {id:'wellcome',name:'Wellcome',region:'global',state:'structured_beta',priority:'critical',access:'direct',url:'https://wellcome.org/research-funding/schemes',note:'Major biomedical and health research funder with direct eligibility for many LMIC-based organisations.'},
  {id:'eu',name:'EU Funding & Tenders',region:'Europe',state:'structured_beta',priority:'critical',access:'mixed',url:'https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search',note:'Horizon Europe and related calls normalized from the European Commission public REST API rather than scraping the SPA.'}
];

const els = {
  cards: document.getElementById('cards'), resultCount: document.getElementById('resultCount'),
  sourceCount: document.getElementById('sourceCount'), structuredCount: document.getElementById('structuredCount'),
  region: document.getElementById('regionFilter'), state: document.getElementById('stateFilter'),
  priority: document.getElementById('priorityFilter'), search: document.getElementById('searchInput'), reset: document.getElementById('resetFilters')
};

function escapeHTML(value){return String(value).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function labelRegion(region){return ({global_majority:'Global Majority',global:'Global',UK:'United Kingdom',Europe:'Europe',Africa:'Africa'})[region]||region;}
function render(){
  const q = els.search.value.trim().toLowerCase();
  const filtered = sources.filter(s =>
    (els.region.value==='all'||s.region===els.region.value) &&
    (els.state.value==='all'||s.state===els.state.value) &&
    (els.priority.value==='all'||s.priority===els.priority.value) &&
    (!q||`${s.name} ${s.note} ${s.region} ${s.state} ${s.access}`.toLowerCase().includes(q))
  );
  els.resultCount.textContent=filtered.length;
  els.cards.innerHTML = filtered.length ? filtered.map(s=>`
    <article class="funding-card">
      <div class="card-top"><span class="badge ${escapeHTML(s.state)}">${escapeHTML(s.state)}</span><span class="priority">${escapeHTML(s.priority)}</span></div>
      <h3>${escapeHTML(s.name)}</h3>
      <div class="meta">${escapeHTML(labelRegion(s.region))} • Global Majority access: ${escapeHTML(s.access)}</div>
      <p>${escapeHTML(s.note)}</p>
      <div class="card-bottom"><span class="meta">Eligibility: verify at source</span><a class="source-link" href="${escapeHTML(s.url)}" target="_blank" rel="noreferrer">Open primary source ↗</a></div>
    </article>`).join('') : `<div class="funding-card"><h3>No matching sources</h3><p>Try broadening a filter. Unknown coverage is not treated as ineligibility.</p></div>`;
}

els.sourceCount.textContent=sources.length;
els.structuredCount.textContent=sources.filter(s=>s.state.startsWith('structured_beta')).length;
[els.region,els.state,els.priority].forEach(el=>el.addEventListener('change',render));
els.search.addEventListener('input',render);
els.reset.addEventListener('click',()=>{els.region.value='all';els.state.value='all';els.priority.value='all';els.search.value='';render();});
render();