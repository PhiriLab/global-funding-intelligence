const readinessStyle = document.createElement('link');
readinessStyle.rel = 'stylesheet';
readinessStyle.href = 'application-readiness.css';
document.head.appendChild(readinessStyle);

const GFI_READINESS_CHECKS = [
  ['guidance_reviewed','Primary call guidance reviewed'],
  ['eligibility_verified','Eligibility verified at the primary source'],
  ['internal_go_no_go','Internal go/no-go decision completed'],
  ['consortium_ready','Required consortium / partners confirmed'],
  ['local_partner_ready','Required local partner confirmed'],
  ['narrative_ready','Core application narrative prepared'],
  ['budget_ready','Budget / costing prepared'],
  ['documents_ready','Required supporting documents prepared'],
  ['internal_approval_ready','Institutional / internal approvals completed'],
  ['portal_ready','Submission portal access confirmed']
];

const GFI_STAGE_ORDER = ['saved','eligibility_checked','partner_building','decision_to_apply','drafting','internal_review','submitted','interview_rebuttal','pending','awarded','unsuccessful','withdrawn','not_disclosed'];
const GFI_TERMINAL_STAGES = new Set(['submitted','interview_rebuttal','pending','awarded','unsuccessful','withdrawn','not_disclosed']);

function readinessOpportunity(journey) {
  return opportunityFeed.find(item => journeyOpportunityKey(item) === journey.opportunity_key) ||
    opportunityFeed.find(item => item.source_id === journey.source_id && item.title === journey.title) || null;
}

function ensureReadiness(journey) {
  if (!journey.readiness || typeof journey.readiness !== 'object') journey.readiness = {};
  for (const [key] of GFI_READINESS_CHECKS) {
    if (typeof journey.readiness[key] !== 'boolean') journey.readiness[key] = false;
  }
  return journey.readiness;
}

function deadlineIntelligence(journey, opportunity) {
  const raw = opportunity?.closing_at || journey.closing_at || null;
  if (!raw) return {state:'unknown', label:'Deadline not verified', days:null, blocker:'Verify the actionable deadline at the primary call source.'};
  const deadline = new Date(raw);
  if (Number.isNaN(deadline.getTime())) return {state:'unknown', label:'Deadline not verified', days:null, blocker:'Verify the actionable deadline at the primary call source.'};
  const days = Math.ceil((deadline.getTime() - Date.now()) / 86400000);
  if (days < 0) return {state:'expired', label:`Deadline passed ${Math.abs(days)} day${Math.abs(days) === 1 ? '' : 's'} ago`, days, blocker:'The verified deadline has passed.'};
  if (days === 0) return {state:'urgent', label:'Deadline is today', days, blocker:null};
  if (days <= 7) return {state:'urgent', label:`${days} day${days === 1 ? '' : 's'} remaining`, days, blocker:null};
  if (days <= 21) return {state:'soon', label:`${days} days remaining`, days, blocker:null};
  return {state:'workable', label:`${days} days remaining`, days, blocker:null};
}

function stageRequiredChecks(journey, opportunity) {
  const stageIndex = Math.max(0, GFI_STAGE_ORDER.indexOf(journey.stage));
  const required = new Set(['guidance_reviewed','eligibility_verified']);
  if (stageIndex >= GFI_STAGE_ORDER.indexOf('decision_to_apply')) required.add('internal_go_no_go');
  if (opportunity?.consortium_required === true || stageIndex >= GFI_STAGE_ORDER.indexOf('partner_building')) required.add('consortium_ready');
  if (opportunity?.local_partner_required === true) required.add('local_partner_ready');
  if (stageIndex >= GFI_STAGE_ORDER.indexOf('drafting')) {
    required.add('narrative_ready');
    required.add('budget_ready');
    required.add('documents_ready');
  }
  if (stageIndex >= GFI_STAGE_ORDER.indexOf('internal_review')) required.add('internal_approval_ready');
  if (stageIndex >= GFI_STAGE_ORDER.indexOf('submitted')) required.add('portal_ready');
  return required;
}

function sourceUnknowns(opportunity) {
  const unknowns = [];
  if (!opportunity) {
    unknowns.push('Current structured opportunity record is unavailable; re-verify the call at source.');
    return unknowns;
  }
  if (!opportunity.closing_at && !opportunity.rolling) unknowns.push('Actionable deadline is not structured.');
  if (!hasRouteEvidence(opportunity)) unknowns.push('Applicant-route evidence is not structured.');
  if (!(opportunity.applicant_types || []).length) unknowns.push('Eligible organisation types are not structured.');
  if (opportunity.consortium_required == null) unknowns.push('Consortium requirement is not verified.');
  if (opportunity.local_partner_required == null) unknowns.push('Local-partner requirement is not verified.');
  return unknowns;
}

function computeReadiness(journey) {
  const opportunity = readinessOpportunity(journey);
  const checks = ensureReadiness(journey);
  const deadline = deadlineIntelligence(journey, opportunity);
  const required = stageRequiredChecks(journey, opportunity);
  const incomplete = [...required].filter(key => !checks[key]);
  const unknowns = sourceUnknowns(opportunity);
  const blockers = [];
  if (deadline.blocker) blockers.push(deadline.blocker);
  if (opportunity?.status === 'closed' || opportunity?.lifecycle === 'closed') blockers.push('The source currently marks this opportunity closed.');

  let state = 'action_needed';
  let label = 'Action needed';
  if (GFI_TERMINAL_STAGES.has(journey.stage)) {
    state = 'submitted'; label = 'Application progressed';
  } else if (blockers.length) {
    state = 'blocked'; label = 'Blocked';
  } else if (!checks.eligibility_verified || unknowns.length) {
    state = 'verify'; label = 'Verify evidence';
  } else if (!incomplete.length) {
    state = 'ready'; label = 'Ready for current stage';
  }
  return {state,label,deadline,required,incomplete,unknowns,blockers,opportunity};
}

function readinessChecklistHtml(journey, result) {
  const checks = ensureReadiness(journey);
  return GFI_READINESS_CHECKS.map(([key,label]) => {
    const required = result.required.has(key);
    return `<label class="readiness-check${required ? ' required' : ''}"><input type="checkbox" data-readiness-field="${key}"${checks[key] ? ' checked' : ''}> <span>${opportunityEscape(label)}${required ? ' <strong>required now</strong>' : ''}</span></label>`;
  }).join('');
}

function readinessMessages(result) {
  const rows = [];
  for (const blocker of result.blockers) rows.push(`<li class="blocker">${opportunityEscape(blocker)}</li>`);
  for (const unknown of result.unknowns) rows.push(`<li class="unknown">${opportunityEscape(unknown)}</li>`);
  for (const key of result.incomplete) {
    const label = GFI_READINESS_CHECKS.find(([item]) => item === key)?.[1] || key;
    rows.push(`<li>${opportunityEscape(label)} remains incomplete.</li>`);
  }
  return rows.length ? `<ul class="readiness-messages">${rows.join('')}</ul>` : '<p class="readiness-clear">No unresolved readiness items for the current stage.</p>';
}

function readinessEvidenceSummary(result) {
  const opportunity = result.opportunity;
  if (!opportunity) return 'Saved call snapshot only — current structured evidence unavailable.';
  const pieces = [];
  pieces.push(hasRouteEvidence(opportunity) ? 'Applicant-route evidence available' : 'Applicant route unverified');
  if (opportunity.consortium_required === true) pieces.push('Consortium required');
  else if (opportunity.consortium_required === false) pieces.push('Consortium not required');
  else pieces.push('Consortium rule unknown');
  if (opportunity.local_partner_required === true) pieces.push('Local partner required');
  else if (opportunity.local_partner_required === false) pieces.push('Local partner not required');
  else pieces.push('Local-partner rule unknown');
  return pieces.join(' • ');
}

function injectReadinessCards() {
  if (!journeyList) return;
  journeyList.querySelectorAll('.journey-card').forEach(card => {
    const journey = journeys.find(item => item.journey_id === card.dataset.journeyId);
    if (!journey) return;
    card.querySelector('.readiness-panel')?.remove();
    const result = computeReadiness(journey);
    const panel = document.createElement('section');
    panel.className = 'readiness-panel';
    panel.innerHTML = `
      <div class="readiness-top">
        <div><span class="readiness-state ${opportunityEscape(result.state)}">${opportunityEscape(result.label)}</span><strong>Application readiness</strong></div>
        <span class="deadline-chip ${opportunityEscape(result.deadline.state)}">${opportunityEscape(result.deadline.label)}</span>
      </div>
      <p class="readiness-evidence">${opportunityEscape(readinessEvidenceSummary(result))}</p>
      ${readinessMessages(result)}
      <details class="readiness-checklist"><summary>Current-stage readiness checklist</summary><div class="readiness-check-grid">${readinessChecklistHtml(journey,result)}</div></details>
      <p class="readiness-boundary"><strong>Decision boundary:</strong> “Ready” means the locally recorded checklist is complete for this stage and no current structured blocker is known. It is not a funder eligibility determination.</p>`;
    const meta = card.querySelector('.journey-meta');
    if (meta) meta.insertAdjacentElement('beforebegin', panel);
    panel.querySelectorAll('[data-readiness-field]').forEach(input => input.addEventListener('change', () => updateReadiness(journey, input.dataset.readinessField, input.checked)));
  });
}

function updateReadiness(journey, field, value) {
  const checks = ensureReadiness(journey);
  if (!GFI_READINESS_CHECKS.some(([key]) => key === field)) return;
  checks[field] = Boolean(value);
  journey.updated_at = new Date().toISOString();
  saveJourneys();
  injectReadinessCards();
}

function installReadinessObserver() {
  if (!journeyList) return;
  const observer = new MutationObserver(() => injectReadinessCards());
  observer.observe(journeyList, {childList:true, subtree:false});
  injectReadinessCards();
}

installReadinessObserver();
