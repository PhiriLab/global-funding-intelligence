const opportunityStyle = document.createElement('link');
opportunityStyle.rel = 'stylesheet';
opportunityStyle.href = 'opportunities.css';
document.head.appendChild(opportunityStyle);

const GFI_SUPABASE_URL = 'https://wuuuvutjudlotqrnakgj.supabase.co';
const GFI_SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_vmgTqhXjCAFq7EjoU0Vd3w_hIlEfWsT';
const GFI_ALLOWED_EVENTS = new Set([
  'page_ready', 'feed_ready', 'feed_unavailable', 'filter_change',
  'search_used', 'profile_ranked', 'primary_source_open', 'pulse_submitted'
]);

const toolbar = document.querySelector('.opportunity-toolbar');
if (toolbar) {
  const countryLabel = document.createElement('label');
  countryLabel.innerHTML = 'Country code<input id="opportunityCountry" type="text" inputmode="latin" maxlength="2" placeholder="e.g. GB, ZA, KE" autocomplete="off" />';
  const orgLabel = document.createElement('label');
  orgLabel.innerHTML = 'Organisation type<select id="opportunityOrganisation"><option value="all">All organisation types</option><option value="unknown">Not verified</option></select>';
  const gmLabel = document.createElement('label');
  gmLabel.innerHTML = 'Global Majority route<select id="opportunityGMRoute"><option value="all">All routes</option><option value="direct">Direct</option><option value="partner_only">Partner only</option><option value="restricted">Restricted</option><option value="unclear">Not verified</option><option value="not_applicable">Not applicable</option></select>';
  const certaintyLabel = document.createElement('label');
  certaintyLabel.innerHTML = 'Evidence threshold<select id="opportunityEvidence"><option value="include_unknown">Include unverified routes</option><option value="verified_only">Verified route evidence only</option></select>';
  const summary = toolbar.querySelector('.opportunity-summary');
  toolbar.insertBefore(countryLabel, summary);
  toolbar.insertBefore(orgLabel, summary);
  toolbar.insertBefore(gmLabel, summary);
  toolbar.insertBefore(certaintyLabel, summary);
}

const statusNode = document.getElementById('opportunityFeedStatus');
let sourceHealthNode = null;
if (statusNode) {
  sourceHealthNode = document.createElement('div');
  sourceHealthNode.id = 'opportunitySourceHealth';
  sourceHealthNode.className = 'source-health';
  sourceHealthNode.setAttribute('aria-label', 'Funding source health');
  statusNode.insertAdjacentElement('afterend', sourceHealthNode);
}

const opportunityEls = {
  section: document.getElementById('opportunities'),
  grid: document.getElementById('opportunityCards'),
  count: document.getElementById('opportunityCount'),
  status: statusNode,
  sourceHealth: sourceHealthNode,
  filter: document.getElementById('opportunityLifecycleFilter'),
  search: document.getElementById('opportunitySearch'),
  country: document.getElementById('opportunityCountry'),
  organisation: document.getElementById('opportunityOrganisation'),
  gmRoute: document.getElementById('opportunityGMRoute'),
  evidence: document.getElementById('opportunityEvidence')
};

const OPPORTUNITY_STALE_HOURS = 36;
let opportunityFeed = [];
let matcherPanel = null;
let matcherResults = null;
let matcherConsortium = null;
let matcherPartner = null;

function opportunityEscape(value) {
  return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function opportunityLifecycleLabel(value) {
  return ({closing_soon:'Closing soon',open:'Open',rolling:'Rolling',upcoming:'Upcoming',closed:'Closed',unknown:'Unknown'})[value] || value;
}

function opportunityDate(value) {
  if (!value) return 'Not verified';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Not verified' : new Intl.DateTimeFormat(undefined, {dateStyle:'medium', timeStyle:'short', timeZoneName:'short'}).format(date);
}

function opportunityAmount(item) {
  const currency = item.currency ? `${item.currency} ` : '';
  if (item.min_award != null && item.max_award != null) return `${currency}${Number(item.min_award).toLocaleString()}–${Number(item.max_award).toLocaleString()}`;
  if (item.max_award != null) return `Up to ${currency}${Number(item.max_award).toLocaleString()}`;
  if (item.total_fund != null) return `Total fund ${currency}${Number(item.total_fund).toLocaleString()}`;
  return 'Amount not verified';
}

function opportunityFreshness(value) {
  const generated = new Date(value);
  if (Number.isNaN(generated.getTime())) return {stale:true, label:'Feed timestamp unavailable'};
  const ageHours = Math.max(0, (Date.now() - generated.getTime()) / 3600000);
  return ageHours > OPPORTUNITY_STALE_HOURS
    ? {stale:true, label:`Feed is stale (${Math.floor(ageHours)}h old)`}
    : {stale:false, label:`Feed checked ${opportunityDate(value)}`};
}

function sourceHealthLabel(sourceId) {
  return ({
    eu_funding_tenders:'EU Funding & Tenders', ukri_funding_finder:'UKRI', nihr_funding:'NIHR',
    wellcome_funding:'Wellcome', science_for_africa:'Science for Africa', idrc:'IDRC', fogarty:'Fogarty',
    grand_challenges_canada:'Grand Challenges Canada', edctp3:'EDCTP3'
  })[sourceId] || sourceId.replaceAll('_', ' ');
}

function renderSourceHealth(items) {
  if (!opportunityEls.sourceHealth) return;
  const rows = Array.isArray(items) ? items : [];
  opportunityEls.sourceHealth.innerHTML = rows.map(item => {
    const title = item.last_error ? ` title="${opportunityEscape(item.last_error)}"` : '';
    const lkg = item.using_last_known_good ? ' • LKG' : '';
    return `<span class="source-health-item"${title}><strong>${opportunityEscape(sourceHealthLabel(item.source_id))}</strong><span class="source-health-state ${opportunityEscape(item.health)}">${opportunityEscape(item.health)}</span><span>${Number(item.accepted || 0)}/${Number(item.discovered || 0)} accepted${item.error_count ? ` • ${Number(item.error_count)} error${Number(item.error_count) === 1 ? '' : 's'}` : ''}${lkg}</span></span>`;
  }).join('');
}

function hasRouteEvidence(item) {
  return Boolean(
    (item.applicant_types || []).length || (item.eligible_countries || []).length ||
    (item.excluded_countries || []).length || (item.lead_countries || []).length ||
    (item.partner_countries || []).length || (item.eligible_income_groups || []).length ||
    item.oda_only != null || item.consortium_required != null || item.local_partner_required != null ||
    item.lead_location_rule || item.equity_or_lmic_requirement ||
    (item.global_majority_access && item.global_majority_access !== 'unclear')
  );
}

function sourceEvidenceHtml(item) {
  const note = item.provenance_note || '';
  if (!note.includes('Primary-source eligibility wording captured') && !note.includes('invitation-only')) return '';
  return `<details class="opportunity-evidence"><summary>Source evidence</summary><p>${opportunityEscape(note)}</p></details>`;
}

function countryRoute(item, country) {
  if (!country) return 'all';
  const code = country.toUpperCase();
  if ((item.excluded_countries || []).includes(code)) return 'excluded';
  if ((item.lead_countries || []).includes(code)) return 'lead';
  if ((item.partner_countries || []).includes(code)) return 'partner';
  if ((item.eligible_countries || []).includes(code)) return 'eligible';
  if ((item.lead_countries || []).length || (item.partner_countries || []).length || (item.eligible_countries || []).length || (item.excluded_countries || []).length) return 'not_listed';
  return 'unknown';
}

function routeSummary(item, country) {
  const route = countryRoute(item, country);
  return ({
    all:'No country selected', lead:'Verified lead route', partner:'Verified partner route', eligible:'Verified eligible route',
    excluded:'Explicitly excluded by structured source', not_listed:'Not listed in structured country route', unknown:'Country route not verified'
  })[route] || route;
}

function populateOrganisationOptions() {
  if (!opportunityEls.organisation) return;
  const current = opportunityEls.organisation.value;
  const values = [...new Set(opportunityFeed.flatMap(item => item.applicant_types || []).filter(value => typeof value === 'string'))].sort((a,b) => a.localeCompare(b));
  opportunityEls.organisation.innerHTML = '<option value="all">All organisation types</option><option value="unknown">Not verified</option>' +
    values.map(value => `<option value="${opportunityEscape(value)}">${opportunityEscape(value.replaceAll('_',' '))}</option>`).join('');
  if ([...opportunityEls.organisation.options].some(option => option.value === current)) opportunityEls.organisation.value = current;
}

function renderOpportunities() {
  if (!opportunityEls.grid) return;
  const lifecycle = opportunityEls.filter?.value || 'all';
  const q = (opportunityEls.search?.value || '').trim().toLowerCase();
  const country = (opportunityEls.country?.value || '').trim().toUpperCase();
  const organisation = opportunityEls.organisation?.value || 'all';
  const gmRoute = opportunityEls.gmRoute?.value || 'all';
  const evidence = opportunityEls.evidence?.value || 'include_unknown';
  const rows = opportunityFeed.filter(item => {
    if (lifecycle !== 'all' && item.lifecycle !== lifecycle) return false;
    if (q && !`${item.title} ${item.funder} ${item.programme || ''} ${item.source_id} ${item.lifecycle} ${(item.applicant_types || []).join(' ')}`.toLowerCase().includes(q)) return false;
    if (gmRoute !== 'all' && (item.global_majority_access || 'unclear') !== gmRoute) return false;
    const itemHasEvidence = hasRouteEvidence(item);
    if (evidence === 'verified_only' && !itemHasEvidence) return false;
    if (organisation === 'unknown' && (item.applicant_types || []).length) return false;
    if (organisation !== 'all' && organisation !== 'unknown' && !(item.applicant_types || []).includes(organisation)) return false;
    if (country) {
      const route = countryRoute(item, country);
      if (route === 'excluded' || route === 'not_listed') return false;
      if (evidence === 'verified_only' && route === 'unknown') return false;
    }
    return true;
  });
  if (opportunityEls.count) opportunityEls.count.textContent = String(rows.length);
  opportunityEls.grid.innerHTML = rows.length ? rows.map(item => `<article class="opportunity-card"><div class="card-top"><span class="lifecycle-badge ${opportunityEscape(item.lifecycle)}">${opportunityEscape(opportunityLifecycleLabel(item.lifecycle))}</span><span class="badge ${opportunityEscape(item.source_state)}">${opportunityEscape(item.source_state)}</span></div><h3>${opportunityEscape(item.title)}</h3><p class="meta">${opportunityEscape(item.funder)}${item.programme ? ` • ${opportunityEscape(item.programme)}` : ''}</p><dl class="opportunity-facts"><div><dt>Deadline</dt><dd>${opportunityEscape(opportunityDate(item.closing_at))}</dd></div><div><dt>Funding</dt><dd>${opportunityEscape(opportunityAmount(item))}</dd></div><div><dt>Global Majority route</dt><dd>${opportunityEscape(item.global_majority_access || 'unclear')}</dd></div><div><dt>${country ? `Route for ${country}` : 'Applicant route'}</dt><dd>${opportunityEscape(country ? routeSummary(item,country) : (hasRouteEvidence(item) ? 'Structured route evidence available' : 'Not yet verified'))}</dd></div></dl><p class="opportunity-warning">${opportunityEscape(item.eligibility || 'Not determined — verify at source')}</p>${sourceEvidenceHtml(item)}<div class="card-bottom"><span class="meta">Checked ${opportunityEscape(opportunityDate(item.source_checked_at))}</span><a class="source-link" data-source-id="${opportunityEscape(item.source_id)}" href="${opportunityEscape(item.primary_url)}" target="_blank" rel="noreferrer">Primary call ↗</a></div></article>`).join('') : `<div class="opportunity-empty"><h3>No verified opportunities match this view</h3><p>${opportunityFeed.length ? 'Broaden a filter or switch Evidence threshold to include unverified routes. Unknown is not treated as ineligible.' : 'The opportunity feed is ready but currently contains no published structured records. The funder directory below remains fully available.'}</p></div>`;
  wireSourceLinkTelemetry();
}

function gfiViewportBucket() {
  const w = window.innerWidth || 0;
  return w < 680 ? 'mobile' : w < 1080 ? 'tablet' : 'desktop';
}

function gfiSafeProperties(properties) {
  const allowed = ['opportunity_count','source_health_count','filter','value','query_length_bucket','result_count','apply_count','partner_count','verify_count','skip_count','source_id','completed'];
  return Object.fromEntries(Object.entries(properties || {}).filter(([key, value]) => allowed.includes(key) && ['string','number','boolean'].includes(typeof value)));
}

function gfiTrack(event, properties = {}) {
  if (!GFI_ALLOWED_EVENTS.has(event) || navigator.doNotTrack === '1') return;
  const body = {
    event_name: event,
    page: 'global-funding-intelligence',
    embedded: window.self !== window.top,
    language: (navigator.language || 'unknown').split('-')[0],
    viewport: gfiViewportBucket(),
    properties: gfiSafeProperties(properties)
  };
  fetch(`${GFI_SUPABASE_URL}/rest/v1/gfi_usage_events`, {
    method: 'POST',
    headers: {
      'apikey': GFI_SUPABASE_PUBLISHABLE_KEY,
      'Content-Type': 'application/json',
      'Prefer': 'return=minimal'
    },
    body: JSON.stringify(body),
    keepalive: true
  }).catch(() => {});
}

async function loadOpportunityFeed() {
  if (!opportunityEls.grid) return;
  let payload;
  try {
    const response = await fetch('data/opportunities.json', {cache:'no-store'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    payload = await response.json();
    if (payload?.schema_version !== 1 || !Array.isArray(payload.opportunities)) throw new Error('Unsupported opportunity feed schema');
  } catch (error) {
    opportunityFeed = [];
    renderSourceHealth([]);
    if (opportunityEls.status) {
      opportunityEls.status.dataset.freshness = 'unavailable';
      opportunityEls.status.textContent = 'Live opportunity feed is temporarily unavailable; the verified funder directory remains available below.';
    }
    opportunityEls.grid.innerHTML = '<div class="opportunity-empty"><h3>Opportunity feed unavailable</h3><p>Nothing has been inferred or cached as current. Use the funder directory and primary-source links while the feed is unavailable.</p></div>';
    if (opportunityEls.count) opportunityEls.count.textContent = '0';
    gfiTrack('feed_unavailable', {});
    console.warn('Opportunity feed unavailable', error);
    return;
  }
  // The feed was retrieved and validated: it IS available. Render each view independently so a
  // fault in one section cannot blank the feed or mislabel a retrieved feed as unavailable.
  opportunityFeed = payload.opportunities;
  const renderStep = (label, fn) => { try { fn(); } catch (error) { console.warn(`Opportunity feed render step failed: ${label}`, error); } };
  renderStep('organisation-options', populateOrganisationOptions);
  renderStep('source-health', () => renderSourceHealth(payload.source_health));
  const freshness = opportunityFreshness(payload.generated_at);
  if (opportunityEls.status) {
    opportunityEls.status.dataset.freshness = freshness.stale ? 'stale' : 'current';
    opportunityEls.status.textContent = freshness.stale
      ? `${freshness.label} • verify current status at each primary call before acting`
      : (opportunityFeed.length ? `${freshness.label} • ${opportunityFeed.length} structured opportunities` : `${freshness.label} • no structured opportunities published yet`);
  }
  renderStep('opportunity-cards', renderOpportunities);
  renderStep('profile-ranking', renderProfileRanking);
  gfiTrack('feed_ready', {opportunity_count:opportunityFeed.length, source_health_count:Array.isArray(payload.source_health) ? payload.source_health.length : 0});
}

[opportunityEls.filter, opportunityEls.organisation, opportunityEls.gmRoute, opportunityEls.evidence].forEach(el => el?.addEventListener('change', renderOpportunities));
opportunityEls.search?.addEventListener('input', renderOpportunities);
opportunityEls.country?.addEventListener('input', () => {
  opportunityEls.country.value = opportunityEls.country.value.replace(/[^a-z]/gi,'').slice(0,2).toUpperCase();
  renderOpportunities();
});

function installProfileMatcher() {
  if (!opportunityEls.sourceHealth || matcherPanel) return;
  matcherPanel = document.createElement('section');
  matcherPanel.className = 'profile-matcher';
  matcherPanel.setAttribute('aria-label','Applicant profile ranking');
  matcherPanel.innerHTML = '<div class="profile-matcher-head"><div><p class="eyebrow">MATCH MY PROFILE</p><h3>Rank opportunities using verified applicant-route evidence</h3></div><p>Uses the country and organisation filters above. Unknown evidence stays <strong>verify</strong>; it never becomes an eligibility assumption.</p></div><div class="profile-matcher-controls"><label><input id="matcherConsortium" type="checkbox" checked> Can form a consortium</label><label><input id="matcherPartner" type="checkbox"> Required local partner already available</label><button id="matcherRun" class="button primary" type="button">Rank for this profile</button></div><p class="matcher-boundary">Ranking is eligibility- and feasibility-led. It is not a thematic-fit score until structured topic/stage fields are available.</p><div id="matcherResults" class="matcher-results" aria-live="polite"></div><p class="analytics-note"><strong>Usage evaluation:</strong> aggregate interaction events only; no session recording, persistent visitor ID or inferred sensitive demographics. Geographic reach is evaluated through Wix Analytics.</p>';
  opportunityEls.sourceHealth.insertAdjacentElement('afterend', matcherPanel);
  matcherResults = matcherPanel.querySelector('#matcherResults');
  matcherConsortium = matcherPanel.querySelector('#matcherConsortium');
  matcherPartner = matcherPanel.querySelector('#matcherPartner');
  matcherPanel.querySelector('#matcherRun')?.addEventListener('click', () => renderProfileRanking(true));
}

function profileDecision(item, country, organisation) {
  const blockers = [];
  const unknowns = [];
  const route = countryRoute(item, country);
  if (route === 'excluded' || route === 'not_listed') blockers.push('country route');
  else if (route === 'unknown' || route === 'all') unknowns.push('country route');
  if (organisation === 'all' || organisation === 'unknown') unknowns.push('organisation type');
  else if ((item.applicant_types || []).length && !item.applicant_types.includes(organisation)) blockers.push('organisation type');
  else if (!(item.applicant_types || []).length) unknowns.push('organisation type');
  if (item.consortium_required === true && !matcherConsortium?.checked) blockers.push('consortium requirement');
  if (item.local_partner_required === true && !matcherPartner?.checked) blockers.push('local partner requirement');
  if (item.closing_at && new Date(item.closing_at) < new Date()) blockers.push('deadline passed');
  let decision = 'verify';
  if (blockers.length) decision = 'skip';
  else if (unknowns.length) decision = 'verify';
  else if (route === 'partner') decision = 'partner';
  else decision = 'apply';
  let priority = decision === 'apply' ? 400 : decision === 'partner' ? 300 : decision === 'verify' ? 200 : 0;
  if (item.global_majority_access === 'direct') priority += 25;
  if (item.global_majority_access === 'partner_only') priority += 10;
  if (item.lifecycle === 'closing_soon') priority += 15;
  else if (item.lifecycle === 'open') priority += 10;
  else if (item.lifecycle === 'upcoming') priority += 5;
  if (item.max_award != null) priority += Math.min(20, Math.log10(Math.max(1, Number(item.max_award))) * 2);
  return {decision, route, blockers, unknowns, priority};
}

function renderProfileRanking(track = false) {
  if (!matcherResults) return;
  const country = (opportunityEls.country?.value || '').trim().toUpperCase();
  const organisation = opportunityEls.organisation?.value || 'all';
  if (country.length !== 2 || organisation === 'all' || organisation === 'unknown') {
    matcherResults.innerHTML = '<p class="matcher-empty">Enter a two-letter country code and choose a specific organisation type above to generate a ranked view.</p>';
    return;
  }
  const ranked = opportunityFeed.map(item => ({item, match:profileDecision(item,country,organisation)})).sort((a,b) => b.match.priority - a.match.priority).slice(0,8);
  const counts = {apply:0, partner:0, verify:0, skip:0};
  ranked.forEach(row => counts[row.match.decision]++);
  matcherResults.innerHTML = ranked.length ? ranked.map(({item,match}) => `<article class="matcher-row"><div><span class="match-decision ${opportunityEscape(match.decision)}">${opportunityEscape(match.decision)}</span><strong>${opportunityEscape(item.title)}</strong><small>${opportunityEscape(item.funder)} • ${opportunityEscape(routeSummary(item,country))}</small></div><div class="matcher-row-actions"><span class="match-index">${Math.round(match.priority)} index</span><a class="source-link" data-source-id="${opportunityEscape(item.source_id)}" href="${opportunityEscape(item.primary_url)}" target="_blank" rel="noreferrer">Verify source ↗</a></div></article>`).join('') : '<p class="matcher-empty">No opportunities are available to rank.</p>';
  wireSourceLinkTelemetry();
  if (track) gfiTrack('profile_ranked', {result_count:ranked.length, apply_count:counts.apply, partner_count:counts.partner, verify_count:counts.verify, skip_count:counts.skip});
}

function wireSourceLinkTelemetry() {
  document.querySelectorAll('.source-link:not([data-telemetry-wired])').forEach(link => {
    link.dataset.telemetryWired = 'true';
    link.addEventListener('click', () => gfiTrack('primary_source_open', {source_id:link.dataset.sourceId || 'unknown'}));
  });
}

function wireAggregateUsageTelemetry() {
  const filterMap = [[opportunityEls.filter,'lifecycle'],[opportunityEls.organisation,'organisation'],[opportunityEls.gmRoute,'gm_route'],[opportunityEls.evidence,'evidence']];
  filterMap.forEach(([el,name]) => el?.addEventListener('change', () => {
    const value = name === 'organisation' ? (el.value === 'all' ? 'all' : 'selected') : el.value;
    gfiTrack('filter_change', {filter:name, value});
    renderProfileRanking();
  }));
  opportunityEls.country?.addEventListener('change', () => {
    gfiTrack('filter_change', {filter:'country', value:opportunityEls.country.value ? 'selected' : 'empty'});
    renderProfileRanking();
  });
  let searchTimer = null;
  opportunityEls.search?.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const n = (opportunityEls.search.value || '').trim().length;
      gfiTrack('search_used', {query_length_bucket:n === 0 ? '0' : n < 5 ? '1-4' : n < 15 ? '5-14' : '15+', result_count:Number(opportunityEls.count?.textContent || 0)});
    }, 700);
  });
}

function installUsefulnessPulse() {
  const cta = document.querySelector('.cta');
  if (!cta || document.getElementById('usefulnessPulse')) return;
  const section = document.createElement('section');
  section.id = 'usefulnessPulse';
  section.className = 'section usefulness-pulse';
  section.innerHTML = `
    <div class="section-head">
      <div><p class="eyebrow">HELP US MEASURE EQUITABLE REACH</p><h2>Was this resource useful to you?</h2></div>
      <p>This optional anonymous pulse helps us understand whether Global Funding Intelligence is reaching researchers and organisations across underserved settings. We do not ask for your name, email, ethnicity, disability, religion or other sensitive identity information.</p>
    </div>
    <form id="usefulnessPulseForm" class="pulse-form">
      <div class="pulse-grid">
        <label>Country code <span>optional</span><input name="country_code" maxlength="2" inputmode="latin" placeholder="e.g. ZA, KE, GB"></label>
        <label>World region <select name="world_region"><option value="">Prefer not to say</option><option>Africa</option><option>Asia</option><option>Latin America & Caribbean</option><option>Middle East & North Africa</option><option>Europe</option><option>North America</option><option>Oceania</option></select></label>
        <label>Organisation type <select name="organisation_type"><option value="">Prefer not to say</option><option>University / research institute</option><option>Healthcare organisation</option><option>NGO / charity / community organisation</option><option>Government / public agency</option><option>Startup / SME</option><option>Industry</option><option>Independent researcher</option><option>Other</option></select></label>
        <label>Career stage <select name="career_stage"><option value="">Prefer not to say</option><option>Student / trainee</option><option>Early career</option><option>Mid-career</option><option>Senior / independent</option><option>Not applicable</option></select></label>
        <label>Primary sector <select name="sector"><option value="">Prefer not to say</option><option>Mental / global health</option><option>Health / biomedical</option><option>Public health / social science</option><option>Technology / innovation</option><option>Climate / environment</option><option>Education</option><option>Other</option></select></label>
        <label>Working / research setting <select name="setting_identity"><option value="prefer_not_to_say">Prefer not to say</option><option value="global_majority">Global Majority / LMIC setting</option><option value="high_income">High-income setting</option><option value="unsure">Unsure</option></select></label>
        <label>Did you find a relevant opportunity? <select name="found_relevant_opportunity"><option value="">Prefer not to say</option><option value="true">Yes</option><option value="false">No</option></select></label>
        <label>Would you use this resource again? <select name="would_return"><option value="">Prefer not to say</option><option value="true">Yes</option><option value="false">No</option></select></label>
        <label>Overall usefulness <select name="usefulness" required><option value="">Choose 1–5</option><option value="1">1 — Not useful</option><option value="2">2</option><option value="3">3 — Moderately useful</option><option value="4">4</option><option value="5">5 — Very useful</option></select></label>
      </div>
      <label class="pulse-comment">Optional comment <span>Do not include personal, confidential or sensitive information.</span><textarea name="comment" maxlength="500" rows="3" placeholder="What helped, or what should we improve?"></textarea></label>
      <div class="pulse-actions"><button class="button primary" type="submit">Submit anonymous feedback</button><p id="pulseStatus" aria-live="polite">Voluntary and anonymous. Responses are not linked to a visitor ID.</p></div>
    </form>`;
  cta.insertAdjacentElement('beforebegin', section);
  const form = section.querySelector('#usefulnessPulseForm');
  const countryInput = form.elements.country_code;
  countryInput.addEventListener('input', () => { countryInput.value = countryInput.value.replace(/[^a-z]/gi,'').slice(0,2).toUpperCase(); });
  form.addEventListener('submit', submitUsefulnessPulse);
}

function optionalBoolean(value) {
  return value === 'true' ? true : value === 'false' ? false : null;
}

async function submitUsefulnessPulse(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById('pulseStatus');
  const submit = form.querySelector('button[type="submit"]');
  const data = new FormData(form);
  const body = {
    country_code: (data.get('country_code') || '').toString().trim().toUpperCase() || null,
    world_region: data.get('world_region') || null,
    organisation_type: data.get('organisation_type') || null,
    career_stage: data.get('career_stage') || null,
    sector: data.get('sector') || null,
    setting_identity: data.get('setting_identity') || 'prefer_not_to_say',
    found_relevant_opportunity: optionalBoolean(data.get('found_relevant_opportunity')),
    usefulness: Number(data.get('usefulness')),
    would_return: optionalBoolean(data.get('would_return')),
    comment: (data.get('comment') || '').toString().trim() || null
  };
  if (!Number.isInteger(body.usefulness) || body.usefulness < 1 || body.usefulness > 5) return;
  submit.disabled = true;
  status.textContent = 'Submitting anonymous feedback…';
  try {
    const response = await fetch(`${GFI_SUPABASE_URL}/rest/v1/gfi_usefulness_pulse`, {
      method: 'POST',
      headers: {'apikey':GFI_SUPABASE_PUBLISHABLE_KEY, 'Content-Type':'application/json', 'Prefer':'return=minimal'},
      body: JSON.stringify(body)
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    form.reset();
    status.textContent = 'Thank you — your anonymous feedback was recorded.';
    gfiTrack('pulse_submitted', {completed:true});
  } catch (_error) {
    status.textContent = 'Feedback could not be recorded just now. The funding resource remains fully available.';
  } finally {
    submit.disabled = false;
  }
}

installProfileMatcher();
wireAggregateUsageTelemetry();
installUsefulnessPulse();
gfiTrack('page_ready', {});
loadOpportunityFeed();
