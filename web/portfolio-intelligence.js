const portfolioStyle = document.createElement('link');
portfolioStyle.rel = 'stylesheet';
portfolioStyle.href = 'portfolio-intelligence.css';
document.head.appendChild(portfolioStyle);

let portfolioPanel = null;
let portfolioBody = null;

function portfolioPriority(journey) {
  const readiness = computeReadiness(journey);
  let score = 0;
  const watchChanges = typeof unacknowledgedWatchChanges === 'function' ? unacknowledgedWatchChanges(journey) : [];
  if (watchChanges.length) score += 650;
  if (readiness.state === 'blocked') score += 500;
  else if (readiness.state === 'verify') score += 420;
  else if (readiness.state === 'action_needed') score += 340;
  else if (readiness.state === 'ready') score += 220;
  else score += 100;
  if (readiness.deadline.days != null) {
    if (readiness.deadline.days < 0) score += 300;
    else if (readiness.deadline.days <= 7) score += 250;
    else if (readiness.deadline.days <= 21) score += 160;
    else if (readiness.deadline.days <= 45) score += 80;
  } else {
    score += 120;
  }
  const stageIndex = GFI_STAGE_ORDER.indexOf(journey.stage);
  if (stageIndex >= 0 && stageIndex < GFI_STAGE_ORDER.indexOf('submitted')) score += Math.max(0, 70 - stageIndex * 6);
  return {score, readiness, watchChanges};
}

function recommendedNextAction(journey, result) {
  const watchChanges = typeof unacknowledgedWatchChanges === 'function' ? unacknowledgedWatchChanges(journey) : [];
  if (watchChanges.length) return 'Review and acknowledge the detected primary-source change before relying on the previous application plan.';
  if (result.blockers.length) return result.blockers[0];
  if (result.unknowns.length) return result.unknowns[0];
  if (result.incomplete.length) {
    const key = result.incomplete[0];
    const label = GFI_READINESS_CHECKS.find(([item]) => item === key)?.[1] || key;
    return `Complete: ${label}.`;
  }
  if (journey.stage === 'saved') return 'Review eligibility and move the journey to Eligibility checked when verified.';
  if (journey.stage === 'eligibility_checked') return 'Decide whether to pursue, partner or stop before investing in drafting.';
  if (journey.stage === 'partner_building') return 'Confirm required partners and consortium roles.';
  if (journey.stage === 'decision_to_apply') return 'Begin the core application narrative and budget.';
  if (journey.stage === 'drafting') return 'Complete the draft, costing and supporting documents.';
  if (journey.stage === 'internal_review') return 'Secure internal approvals and portal readiness.';
  if (journey.stage === 'submitted') return 'Record interview, rebuttal or outcome updates when they occur.';
  if (journey.stage === 'interview_rebuttal') return 'Record the declared outcome when known.';
  if (journey.stage === 'pending') return 'Await the funder decision; do not infer an outcome from inactivity.';
  return 'No further action is inferred for this declared outcome.';
}

function deadlineForReminder(journey) {
  const opportunity = readinessOpportunity(journey);
  const checks = ensureReadiness(journey);
  const raw = opportunity?.closing_at || checks.manual_deadline || journey.closing_at || null;
  if (!raw) return null;
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? null : date;
}

function icsEscape(value) {
  return String(value || '').replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/,/g, '\\,').replace(/;/g, '\\;');
}

function icsUtc(date) {
  return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
}

function downloadDeadlineReminder(journey) {
  const deadline = deadlineForReminder(journey);
  if (!deadline) return;
  const uid = `${journey.journey_id}@global-funding-intelligence`;
  const dtstamp = icsUtc(new Date());
  const dtstart = icsUtc(deadline);
  const title = `Funding deadline: ${journey.title}`;
  const description = `Verify final deadline and submission requirements at the primary funder source: ${journey.primary_url || ''}`;
  const content = [
    'BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//PhiriLab//Global Funding Intelligence//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH',
    'BEGIN:VEVENT',`UID:${icsEscape(uid)}`,`DTSTAMP:${dtstamp}`,`DTSTART:${dtstart}`,`DTEND:${dtstart}`,`SUMMARY:${icsEscape(title)}`,`DESCRIPTION:${icsEscape(description)}`,
    'BEGIN:VALARM','TRIGGER:-P14D','ACTION:DISPLAY','DESCRIPTION:Funding deadline in 14 days','END:VALARM',
    'BEGIN:VALARM','TRIGGER:-P7D','ACTION:DISPLAY','DESCRIPTION:Funding deadline in 7 days','END:VALARM',
    'BEGIN:VALARM','TRIGGER:-P2D','ACTION:DISPLAY','DESCRIPTION:Funding deadline in 2 days','END:VALARM',
    'END:VEVENT','END:VCALENDAR',''
  ].join('\r\n');
  const blob = new Blob([content], {type:'text/calendar;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `funding-deadline-${journey.journey_id.slice(0,8)}.ics`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function portfolioRow(journey) {
  const {readiness, watchChanges} = portfolioPriority(journey);
  const reminder = deadlineForReminder(journey);
  const watchBadge = watchChanges.length ? `<span class="portfolio-stage">${watchChanges.length} source change${watchChanges.length === 1 ? '' : 's'} to review</span>` : '';
  return `<article class="portfolio-row" data-portfolio-journey="${opportunityEscape(journey.journey_id)}">
    <div class="portfolio-main">
      <div class="portfolio-title"><strong>${opportunityEscape(journey.title)}</strong><span>${opportunityEscape(journey.funder)}</span></div>
      <div class="portfolio-badges"><span class="readiness-state ${opportunityEscape(readiness.state)}">${opportunityEscape(readiness.label)}</span><span class="deadline-chip ${opportunityEscape(readiness.deadline.state)}">${opportunityEscape(readiness.deadline.label)}</span><span class="portfolio-stage">${opportunityEscape((GFI_JOURNEY_STAGES.find(([value]) => value === journey.stage)?.[1]) || journey.stage)}</span>${watchBadge}</div>
      <p class="portfolio-action"><strong>Next action:</strong> ${opportunityEscape(recommendedNextAction(journey, readiness))}</p>
    </div>
    <div class="portfolio-actions"><button type="button" class="button portfolio-open">Open tracker</button>${reminder ? '<button type="button" class="button portfolio-reminder">Add deadline reminder</button>' : '<span class="portfolio-no-reminder">Verify a deadline to enable reminder</span>'}</div>
  </article>`;
}

function installPortfolioPanel() {
  if (portfolioPanel || !opportunityEls.section) return;
  portfolioPanel = document.createElement('section');
  portfolioPanel.id = 'applicationPortfolio';
  portfolioPanel.className = 'application-portfolio';
  portfolioPanel.innerHTML = `<div class="portfolio-head"><div><p class="eyebrow">ACTIVE APPLICATION PORTFOLIO</p><h3>What needs attention next?</h3></div><p>Prioritised from locally saved applications using source changes, verified deadline proximity, readiness, blockers and current journey stage. No application content is uploaded.</p></div><div id="portfolioBody" class="portfolio-body" aria-live="polite"></div>`;
  const journey = document.getElementById('applicationJourney');
  if (journey) journey.insertAdjacentElement('beforebegin', portfolioPanel);
  else opportunityEls.sourceHealth?.insertAdjacentElement('afterend', portfolioPanel);
  portfolioBody = portfolioPanel.querySelector('#portfolioBody');
  renderPortfolio();
}

function renderPortfolio() {
  if (!portfolioBody) return;
  if (!journeys.length) {
    portfolioBody.innerHTML = '<div class="portfolio-empty"><strong>No active applications yet.</strong><span>Save an opportunity to begin portfolio prioritisation.</span></div>';
    return;
  }
  const ranked = journeys.map(journey => ({journey, ...portfolioPriority(journey)})).sort((a,b) => b.score - a.score);
  portfolioBody.innerHTML = ranked.map(row => portfolioRow(row.journey)).join('');
  portfolioBody.querySelectorAll('.portfolio-row').forEach(row => {
    const journey = journeys.find(item => item.journey_id === row.dataset.portfolioJourney);
    if (!journey) return;
    row.querySelector('.portfolio-open')?.addEventListener('click', () => {
      const card = journeyList?.querySelector(`[data-journey-id="${journey.journey_id}"]`);
      card?.scrollIntoView({behavior:'smooth', block:'center'});
    });
    row.querySelector('.portfolio-reminder')?.addEventListener('click', () => downloadDeadlineReminder(journey));
  });
}

function installPortfolioObservers() {
  if (!journeyList) return;
  const observer = new MutationObserver(() => renderPortfolio());
  observer.observe(journeyList, {childList:true, subtree:true});
  renderPortfolio();
}

installPortfolioPanel();
installPortfolioObservers();
