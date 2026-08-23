const watchStyle = document.createElement('link');
watchStyle.rel = 'stylesheet';
watchStyle.href = 'saved-opportunity-watch.css';
document.head.appendChild(watchStyle);

const GFI_WATCH_FIELDS = [
  ['closing_at','Deadline'],
  ['lifecycle','Lifecycle'],
  ['status','Status'],
  ['source_state','Source state'],
  ['global_majority_access','Global Majority route'],
  ['applicant_types','Applicant types'],
  ['eligible_countries','Eligible countries'],
  ['excluded_countries','Excluded countries'],
  ['lead_countries','Lead countries'],
  ['partner_countries','Partner countries'],
  ['consortium_required','Consortium requirement'],
  ['local_partner_required','Local partner requirement'],
  ['lead_location_rule','Lead-location rule'],
  ['equity_or_lmic_requirement','Equity / LMIC requirement'],
  ['eligibility','Eligibility notice'],
  ['provenance_note','Source evidence note']
];

function canonicalWatchValue(value) {
  if (Array.isArray(value)) return [...value].map(item => String(item)).sort();
  if (value === undefined) return null;
  return value;
}

function watchSnapshot(opportunity) {
  if (!opportunity) return null;
  const fields = {};
  for (const [key] of GFI_WATCH_FIELDS) fields[key] = canonicalWatchValue(opportunity[key]);
  return {
    captured_at: new Date().toISOString(),
    source_checked_at: opportunity.source_checked_at || null,
    primary_url: opportunity.primary_url || null,
    fields
  };
}

function valuesEqual(a, b) {
  return JSON.stringify(canonicalWatchValue(a)) === JSON.stringify(canonicalWatchValue(b));
}

function classifyWatchChange(key, before, after) {
  if (key === 'closing_at') {
    if (!before && after) return 'deadline_added';
    if (before && !after) return 'deadline_removed';
    return 'deadline_changed';
  }
  if ((key === 'lifecycle' || key === 'status') && String(after).toLowerCase() === 'closed') return 'closed';
  if (['eligible_countries','excluded_countries','lead_countries','partner_countries','applicant_types','consortium_required','local_partner_required','lead_location_rule','equity_or_lmic_requirement','global_majority_access','eligibility','provenance_note'].includes(key)) return 'eligibility_changed';
  return 'source_changed';
}

function compareWatchSnapshots(previous, current) {
  if (!previous || !current) return [];
  const changes = [];
  for (const [key,label] of GFI_WATCH_FIELDS) {
    const before = previous.fields?.[key] ?? null;
    const after = current.fields?.[key] ?? null;
    if (!valuesEqual(before, after)) {
      changes.push({field:key,label,type:classifyWatchChange(key,before,after),before,after});
    }
  }
  return changes;
}

function ensureWatchState(journey) {
  if (!journey.watch || typeof journey.watch !== 'object') journey.watch = {};
  if (!Array.isArray(journey.watch.history)) journey.watch.history = [];
  if (typeof journey.watch.acknowledged_at !== 'string') journey.watch.acknowledged_at = '';
  return journey.watch;
}

function syncSavedOpportunityWatch() {
  let changed = false;
  for (const journey of journeys) {
    const opportunity = readinessOpportunity(journey);
    if (!opportunity) continue;
    const watch = ensureWatchState(journey);
    const current = watchSnapshot(opportunity);
    if (!watch.last_snapshot) {
      watch.last_snapshot = current;
      watch.acknowledged_at = current.captured_at;
      changed = true;
      continue;
    }
    const differences = compareWatchSnapshots(watch.last_snapshot, current);
    if (!differences.length) {
      watch.last_snapshot = current;
      changed = true;
      continue;
    }
    const material = {
      detected_at: current.captured_at,
      previous_snapshot: watch.last_snapshot,
      current_snapshot: current,
      changes: differences,
      acknowledged: false
    };
    watch.history.unshift(material);
    watch.history = watch.history.slice(0, 20);
    watch.last_snapshot = current;
    changed = true;
  }
  if (changed) saveJourneys();
  injectWatchPanels();
  if (typeof renderPortfolio === 'function') renderPortfolio();
}

function unacknowledgedWatchChanges(journey) {
  const watch = ensureWatchState(journey);
  return watch.history.filter(item => item && item.acknowledged === false);
}

function watchValueText(value) {
  if (Array.isArray(value)) return value.length ? value.join(', ') : 'none listed';
  if (value === null || value === undefined || value === '') return 'not verified';
  if (typeof value === 'boolean') return value ? 'yes' : 'no';
  if (String(value).length > 220) return `${String(value).slice(0,217)}…`;
  return String(value);
}

function changeSeverity(changes) {
  if (changes.some(item => item.type === 'closed')) return 'critical';
  if (changes.some(item => item.type.startsWith('deadline_'))) return 'high';
  if (changes.some(item => item.type === 'eligibility_changed')) return 'high';
  return 'normal';
}

function watchSummary(changes) {
  if (changes.some(item => item.type === 'closed')) return 'Call closure detected';
  if (changes.some(item => item.type.startsWith('deadline_'))) return 'Deadline change detected';
  if (changes.some(item => item.type === 'eligibility_changed')) return 'Eligibility evidence changed';
  return 'Source record changed';
}

function injectWatchPanels() {
  if (!journeyList) return;
  journeyList.querySelectorAll('.journey-card').forEach(card => {
    const journey = journeys.find(item => item.journey_id === card.dataset.journeyId);
    if (!journey) return;
    card.querySelector('.source-watch-panel')?.remove();
    const pending = unacknowledgedWatchChanges(journey);
    const watch = ensureWatchState(journey);
    const panel = document.createElement('section');
    panel.className = `source-watch-panel${pending.length ? ' has-alert' : ''}`;
    if (!watch.last_snapshot) {
      panel.innerHTML = '<p><strong>Source watch:</strong> waiting for a current structured record to establish a baseline.</p>';
    } else if (!pending.length) {
      panel.innerHTML = `<p><strong>Source watch:</strong> no unacknowledged material changes. Last compared ${opportunityEscape(opportunityDate(watch.last_snapshot.captured_at))}.</p>`;
    } else {
      const latest = pending[0];
      const severity = changeSeverity(latest.changes);
      panel.innerHTML = `
        <div class="watch-alert-head"><span class="watch-alert ${severity}">${opportunityEscape(watchSummary(latest.changes))}</span><strong>${pending.length} unacknowledged change${pending.length === 1 ? '' : 's'}</strong></div>
        <p class="watch-audit">Detected ${opportunityEscape(opportunityDate(latest.detected_at))}. The previous evidence snapshot has been retained for audit.</p>
        <ul class="watch-change-list">${latest.changes.map(change => `<li><strong>${opportunityEscape(change.label)}</strong><span>Before: ${opportunityEscape(watchValueText(change.before))}</span><span>Now: ${opportunityEscape(watchValueText(change.after))}</span></li>`).join('')}</ul>
        <div class="watch-actions"><a href="${opportunityEscape(journey.primary_url)}" target="_blank" rel="noreferrer">Verify at primary source ↗</a><button type="button" class="watch-ack button">Acknowledge reviewed change</button></div>`;
      panel.querySelector('.watch-ack')?.addEventListener('click', () => acknowledgeWatchChanges(journey.journey_id));
    }
    const readiness = card.querySelector('.readiness-panel');
    if (readiness) readiness.insertAdjacentElement('afterend', panel);
    else card.querySelector('.journey-meta')?.insertAdjacentElement('beforebegin', panel);
  });
}

function acknowledgeWatchChanges(journeyId) {
  const journey = journeys.find(item => item.journey_id === journeyId);
  if (!journey) return;
  const watch = ensureWatchState(journey);
  const now = new Date().toISOString();
  for (const item of watch.history) {
    if (item && item.acknowledged === false) {
      item.acknowledged = true;
      item.acknowledged_at = now;
    }
  }
  watch.acknowledged_at = now;
  journey.updated_at = now;
  saveJourneys();
  injectWatchPanels();
  if (typeof renderPortfolio === 'function') renderPortfolio();
}

function installSavedOpportunityWatch() {
  if (!journeyList) return;
  const observer = new MutationObserver(() => injectWatchPanels());
  observer.observe(journeyList, {childList:true, subtree:false});
  const gridObserver = new MutationObserver(() => syncSavedOpportunityWatch());
  if (opportunityEls.grid) gridObserver.observe(opportunityEls.grid, {childList:true, subtree:false});
  window.addEventListener('gfi-opportunity-feed-ready', syncSavedOpportunityWatch);
  syncSavedOpportunityWatch();
}

installSavedOpportunityWatch();