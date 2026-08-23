const journeyStyle = document.createElement('link');
journeyStyle.rel = 'stylesheet';
journeyStyle.href = 'application-journey.css';
document.head.appendChild(journeyStyle);

const GFI_JOURNEY_STORAGE_KEY = 'gfi-application-journeys-v1';
const GFI_JOURNEY_STAGES = [
  ['saved','Saved'],
  ['eligibility_checked','Eligibility checked'],
  ['partner_building','Partner / consortium building'],
  ['decision_to_apply','Decision to apply'],
  ['drafting','Drafting'],
  ['internal_review','Internal review'],
  ['submitted','Submitted'],
  ['interview_rebuttal','Interview / rebuttal'],
  ['pending','Outcome pending'],
  ['awarded','Awarded'],
  ['unsuccessful','Unsuccessful'],
  ['withdrawn','Withdrawn'],
  ['not_disclosed','Outcome not disclosed']
];
const GFI_OUTCOME_STAGES = new Set(['pending','awarded','unsuccessful','withdrawn','not_disclosed']);
let journeyPanel = null;
let journeyList = null;
let journeys = loadJourneys();

function loadJourneys() {
  try {
    const parsed = JSON.parse(localStorage.getItem(GFI_JOURNEY_STORAGE_KEY) || '[]');
    return Array.isArray(parsed) ? parsed.filter(item => item && item.journey_id && item.opportunity_key) : [];
  } catch (_error) {
    return [];
  }
}

function saveJourneys() {
  try {
    localStorage.setItem(GFI_JOURNEY_STORAGE_KEY, JSON.stringify(journeys));
    return true;
  } catch (_error) {
    return false;
  }
}

function newJourneyId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

function journeyOpportunityKey(item) {
  const stable = item.identity_key || item.external_id || item.title || item.primary_url || 'unknown';
  return `${item.source_id || 'unknown'}:${stable}`.slice(0, 300);
}

function findOpportunityForCard(card) {
  const title = card.querySelector('h3')?.textContent?.trim();
  const sourceId = card.querySelector('.source-link')?.dataset?.sourceId;
  if (!title) return null;
  return opportunityFeed.find(item => item.title === title && (!sourceId || item.source_id === sourceId)) || null;
}

function journeyForOpportunity(item) {
  const key = journeyOpportunityKey(item);
  return journeys.find(journey => journey.opportunity_key === key) || null;
}

function installJourneyPanel() {
  if (journeyPanel || !opportunityEls.section) return;
  journeyPanel = document.createElement('section');
  journeyPanel.id = 'applicationJourney';
  journeyPanel.className = 'application-journey';
  journeyPanel.innerHTML = `
    <div class="journey-head">
      <div><p class="eyebrow">APPLICATION JOURNEY</p><h3>Saved opportunities and application trajectory</h3></div>
      <p>Track opportunities from discovery to a user-declared outcome. Your saved portfolio stays in this browser. Anonymous trajectory sharing is optional and can be switched on separately for each application.</p>
    </div>
    <div class="journey-privacy"><strong>Privacy boundary:</strong> no name, email, proposal text, collaborator details or reviewer comments are requested. Clearing this browser's site data removes the local portfolio. Cross-device sync is not enabled in v1.</div>
    <div id="journeyList" class="journey-list" aria-live="polite"></div>`;
  const matcher = document.querySelector('.profile-matcher');
  if (matcher) matcher.insertAdjacentElement('afterend', journeyPanel);
  else opportunityEls.sourceHealth?.insertAdjacentElement('afterend', journeyPanel);
  journeyList = journeyPanel.querySelector('#journeyList');
  renderJourneyPanel();
}

function addSaveButtons() {
  document.querySelectorAll('.opportunity-card:not([data-journey-wired])').forEach(card => {
    card.dataset.journeyWired = 'true';
    const item = findOpportunityForCard(card);
    if (!item) return;
    const bottom = card.querySelector('.card-bottom');
    if (!bottom) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'journey-save-button';
    button.textContent = journeyForOpportunity(item) ? 'Tracking application ✓' : 'Save / track application';
    button.addEventListener('click', () => saveOpportunityJourney(item, button));
    bottom.appendChild(button);
  });
}

function refreshSaveButtonLabels() {
  document.querySelectorAll('.opportunity-card').forEach(card => {
    const item = findOpportunityForCard(card);
    const button = card.querySelector('.journey-save-button');
    if (item && button) button.textContent = journeyForOpportunity(item) ? 'Tracking application ✓' : 'Save / track application';
  });
}

function saveOpportunityJourney(item, button) {
  let journey = journeyForOpportunity(item);
  if (!journey) {
    journey = {
      journey_id: newJourneyId(),
      opportunity_key: journeyOpportunityKey(item),
      source_id: item.source_id || null,
      title: item.title,
      funder: item.funder || '',
      primary_url: item.primary_url || '',
      closing_at: item.closing_at || null,
      stage: 'saved',
      role: 'unknown',
      outcome: null,
      gfi_helped_discover: false,
      gfi_helped_assess: false,
      award_value_band: null,
      share_evaluation: false,
      saved_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    journeys.push(journey);
    if (!saveJourneys()) {
      journeys = journeys.filter(saved => saved.journey_id !== journey.journey_id);
      button.textContent = 'Browser storage unavailable';
      return;
    }
  }
  button.textContent = 'Tracking application ✓';
  renderJourneyPanel();
  journeyPanel?.scrollIntoView({behavior:'smooth', block:'nearest'});
}

function stageOptions(current) {
  return GFI_JOURNEY_STAGES.map(([value,label]) => `<option value="${value}"${value === current ? ' selected' : ''}>${label}</option>`).join('');
}

function outcomeFromStage(stage) {
  return GFI_OUTCOME_STAGES.has(stage) ? stage : null;
}

function renderJourneyPanel() {
  if (!journeyList) return;
  if (!journeys.length) {
    journeyList.innerHTML = '<div class="journey-empty"><strong>No saved opportunities yet.</strong><span>Use “Save / track application” on any verified opportunity to start a trajectory.</span></div>';
    return;
  }
  journeyList.innerHTML = journeys.map(journey => `
    <article class="journey-card" data-journey-id="${opportunityEscape(journey.journey_id)}">
      <div class="journey-title"><div><strong>${opportunityEscape(journey.title)}</strong><span>${opportunityEscape(journey.funder)}</span></div><a href="${opportunityEscape(journey.primary_url)}" target="_blank" rel="noreferrer">Primary call ↗</a></div>
      <div class="journey-grid">
        <label>Current stage<select data-field="stage">${stageOptions(journey.stage)}</select></label>
        <label>Your role<select data-field="role"><option value="unknown"${journey.role === 'unknown' ? ' selected' : ''}>Not specified</option><option value="lead"${journey.role === 'lead' ? ' selected' : ''}>Lead applicant</option><option value="partner"${journey.role === 'partner' ? ' selected' : ''}>Partner / co-applicant</option><option value="not_disclosed"${journey.role === 'not_disclosed' ? ' selected' : ''}>Prefer not to disclose</option></select></label>
        <label>Award value if awarded<select data-field="award_value_band"><option value=""${!journey.award_value_band ? ' selected' : ''}>Not specified</option><option value="under_50k"${journey.award_value_band === 'under_50k' ? ' selected' : ''}>Under 50k</option><option value="50k_249k"${journey.award_value_band === '50k_249k' ? ' selected' : ''}>50k–249k</option><option value="250k_999k"${journey.award_value_band === '250k_999k' ? ' selected' : ''}>250k–999k</option><option value="1m_plus"${journey.award_value_band === '1m_plus' ? ' selected' : ''}>1m+</option><option value="not_disclosed"${journey.award_value_band === 'not_disclosed' ? ' selected' : ''}>Prefer not to disclose</option></select></label>
      </div>
      <div class="journey-checks">
        <label><input type="checkbox" data-field="gfi_helped_discover"${journey.gfi_helped_discover ? ' checked' : ''}> GFI helped me discover this opportunity</label>
        <label><input type="checkbox" data-field="gfi_helped_assess"${journey.gfi_helped_assess ? ' checked' : ''}> GFI helped me assess whether to pursue it</label>
        <label class="journey-share"><input type="checkbox" data-field="share_evaluation"${journey.share_evaluation ? ' checked' : ''}> Share anonymous stage transitions with the GFI evaluation</label>
      </div>
      <div class="journey-meta"><span>Saved ${opportunityEscape(opportunityDate(journey.saved_at))}</span>${journey.closing_at ? `<span>Call deadline ${opportunityEscape(opportunityDate(journey.closing_at))}</span>` : '<span>Deadline not verified</span>'}</div>
      <div class="journey-actions"><button type="button" class="journey-update button primary">Update journey</button><button type="button" class="journey-remove text-button">Remove from this browser</button><span class="journey-status" aria-live="polite"></span></div>
    </article>`).join('');
  wireJourneyControls();
}

function wireJourneyControls() {
  journeyList.querySelectorAll('.journey-card').forEach(card => {
    card.querySelector('.journey-update')?.addEventListener('click', () => updateJourney(card));
    card.querySelector('.journey-remove')?.addEventListener('click', () => removeJourney(card.dataset.journeyId));
  });
}

async function updateJourney(card) {
  const journey = journeys.find(item => item.journey_id === card.dataset.journeyId);
  if (!journey) return;
  const get = field => card.querySelector(`[data-field="${field}"]`);
  const previousShare = journey.share_evaluation;
  journey.stage = get('stage').value;
  journey.role = get('role').value || 'unknown';
  journey.outcome = outcomeFromStage(journey.stage);
  journey.award_value_band = get('award_value_band').value || null;
  journey.gfi_helped_discover = get('gfi_helped_discover').checked;
  journey.gfi_helped_assess = get('gfi_helped_assess').checked;
  journey.share_evaluation = get('share_evaluation').checked;
  journey.updated_at = new Date().toISOString();
  const status = card.querySelector('.journey-status');
  if (!saveJourneys()) {
    status.textContent = 'Browser storage unavailable; update was not persisted.';
    return;
  }
  if (!journey.share_evaluation) {
    status.textContent = 'Saved locally only.';
    return;
  }
  status.textContent = previousShare ? 'Saving anonymous trajectory update…' : 'Anonymous trajectory sharing enabled…';
  const sent = await sendJourneyEvent(journey);
  status.textContent = sent ? 'Journey updated and anonymous stage recorded.' : 'Saved locally; anonymous stage could not be recorded just now.';
}

function removeJourney(journeyId) {
  journeys = journeys.filter(item => item.journey_id !== journeyId);
  saveJourneys();
  renderJourneyPanel();
  refreshSaveButtonLabels();
}

async function sendJourneyEvent(journey) {
  const body = {
    journey_id: journey.journey_id,
    opportunity_key: journey.opportunity_key,
    source_id: journey.source_id,
    stage: journey.stage,
    role: journey.role,
    outcome: journey.outcome,
    gfi_helped_discover: journey.gfi_helped_discover,
    gfi_helped_assess: journey.gfi_helped_assess,
    award_value_band: journey.award_value_band,
    schema_version: 1
  };
  try {
    const response = await fetch(`${GFI_SUPABASE_URL}/rest/v1/gfi_application_journey_events`, {
      method: 'POST',
      headers: {'apikey':GFI_SUPABASE_PUBLISHABLE_KEY, 'Content-Type':'application/json', 'Prefer':'return=minimal'},
      body: JSON.stringify(body),
      keepalive: true
    });
    return response.ok;
  } catch (_error) {
    return false;
  }
}

function observeOpportunityCards() {
  if (!opportunityEls.grid) return;
  const observer = new MutationObserver(() => addSaveButtons());
  observer.observe(opportunityEls.grid, {childList:true, subtree:false});
  addSaveButtons();
}

installJourneyPanel();
observeOpportunityCards();
