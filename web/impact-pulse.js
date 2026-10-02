(() => {
  'use strict';

  const PULSE_TABLE = '/rest/v1/gfi_usefulness_pulse';
  const PULSE_LAST_KEY = 'gfi-impact-pulse-last-v1';
  const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

  function recentSubmission() {
    try {
      const value = Number(localStorage.getItem(PULSE_LAST_KEY) || 0);
      return value && (Date.now() - value) < THIRTY_DAYS_MS;
    } catch (_) {
      return false;
    }
  }

  function markSubmitted() {
    try { localStorage.setItem(PULSE_LAST_KEY, String(Date.now())); } catch (_) {}
  }

  function cleanCode(value) {
    const code = String(value || '').trim().toUpperCase();
    return /^[A-Z]{2}$/.test(code) ? code : null;
  }

  function valueOrNull(form, name) {
    const value = form.elements[name]?.value?.trim?.() || '';
    return value || null;
  }

  function buildPulse() {
    if (!document.getElementById('opportunities') || document.getElementById('gfiImpactPulse')) return;

    const section = document.createElement('section');
    section.id = 'gfiImpactPulse';
    section.className = 'impact-pulse';
    section.innerHTML = `
      <div class="impact-pulse__head">
        <div>
          <p class="eyebrow">30-SECOND IMPACT PULSE</p>
          <h2>Did Global Funding Intelligence help?</h2>
          <p>Anonymous, optional feedback used to improve the service and demonstrate public-interest impact to potential sponsors. No name, email, proposal text or contact details are requested.</p>
        </div>
        <button type="button" class="impact-pulse__toggle" aria-expanded="false" aria-controls="gfiImpactPulseForm">Give feedback</button>
      </div>
      <form id="gfiImpactPulseForm" class="impact-pulse__form" hidden>
        <fieldset>
          <legend>Core outcome measures</legend>
          <label>Did you find a funding opportunity relevant to you?
            <select name="found_relevant_opportunity" required>
              <option value="">Choose…</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </label>
          <label>How useful was GFI today?
            <select name="usefulness" required>
              <option value="">Choose…</option>
              <option value="5">5 — Extremely useful</option>
              <option value="4">4 — Very useful</option>
              <option value="3">3 — Moderately useful</option>
              <option value="2">2 — Slightly useful</option>
              <option value="1">1 — Not useful</option>
            </select>
          </label>
          <label>Would you use GFI again?
            <select name="would_return" required>
              <option value="">Choose…</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </label>
        </fieldset>

        <details class="impact-pulse__context">
          <summary>Optional context — helps us assess reach and equity</summary>
          <div class="impact-pulse__grid">
            <label>Country code
              <input name="country_code" maxlength="2" inputmode="latin" autocomplete="off" placeholder="e.g. GB, ZA, KE">
            </label>
            <label>World region
              <select name="world_region">
                <option value="">Prefer not to say</option>
                <option>Africa</option>
                <option>Asia</option>
                <option>Europe</option>
                <option>Latin America and the Caribbean</option>
                <option>Middle East and North Africa</option>
                <option>North America</option>
                <option>Oceania</option>
                <option>Other / mixed</option>
              </select>
            </label>
            <label>Organisation type
              <select name="organisation_type">
                <option value="">Prefer not to say</option>
                <option value="university">University / higher education</option>
                <option value="healthcare">Health or care organisation</option>
                <option value="research_institute">Research institute</option>
                <option value="charity_ngo">Charity / NGO</option>
                <option value="startup_sme">Startup / SME</option>
                <option value="industry">Industry / company</option>
                <option value="independent">Independent researcher / innovator</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label>Career stage
              <select name="career_stage">
                <option value="">Prefer not to say</option>
                <option value="student_trainee">Student / trainee</option>
                <option value="early_career">Early career</option>
                <option value="mid_career">Mid career</option>
                <option value="senior">Senior / established</option>
                <option value="not_applicable">Not applicable</option>
              </select>
            </label>
            <label>Sector
              <select name="sector">
                <option value="">Prefer not to say</option>
                <option value="health">Health</option>
                <option value="mental_health">Mental health</option>
                <option value="social_care">Social care</option>
                <option value="science_technology">Science / technology</option>
                <option value="education">Education</option>
                <option value="global_development">Global development</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label>Institutional setting
              <select name="setting_identity">
                <option value="">Prefer not to say</option>
                <option value="global_majority">Global Majority setting / institution</option>
                <option value="high_income">High-income-country setting / institution</option>
                <option value="unsure">Unsure / mixed</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </label>
          </div>
        </details>

        <div class="impact-pulse__actions">
          <button type="submit" class="button primary">Submit anonymous feedback</button>
          <span class="impact-pulse__status" aria-live="polite"></span>
        </div>
      </form>
    `;

    document.getElementById('opportunities').insertAdjacentElement('afterend', section);

    const toggle = section.querySelector('.impact-pulse__toggle');
    const form = section.querySelector('#gfiImpactPulseForm');
    const status = section.querySelector('.impact-pulse__status');

    const open = () => {
      form.hidden = false;
      toggle.setAttribute('aria-expanded', 'true');
      toggle.textContent = 'Hide feedback';
    };
    const close = () => {
      form.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
      toggle.textContent = 'Give feedback';
    };

    toggle.addEventListener('click', () => form.hidden ? open() : close());

    if (recentSubmission()) {
      status.textContent = 'Thank you — feedback was submitted from this browser recently.';
    }

    document.addEventListener('click', event => {
      const sourceLink = event.target.closest?.('a.source-link');
      if (sourceLink && !recentSubmission()) open();
    }, true);

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const submit = form.querySelector('button[type="submit"]');
      submit.disabled = true;
      status.textContent = 'Submitting…';

      const country = cleanCode(form.elements.country_code.value);
      const payload = {
        country_code: country,
        world_region: valueOrNull(form, 'world_region'),
        organisation_type: valueOrNull(form, 'organisation_type'),
        career_stage: valueOrNull(form, 'career_stage'),
        sector: valueOrNull(form, 'sector'),
        setting_identity: valueOrNull(form, 'setting_identity'),
        found_relevant_opportunity: form.elements.found_relevant_opportunity.value === 'true',
        usefulness: Number(form.elements.usefulness.value),
        would_return: form.elements.would_return.value === 'true',
        comment: null
      };

      if (form.elements.country_code.value.trim() && !country) {
        status.textContent = 'Country code must be two letters, or leave it blank.';
        submit.disabled = false;
        return;
      }

      try {
        const response = await fetch(`${GFI_SUPABASE_URL}${PULSE_TABLE}`, {
          method: 'POST',
          headers: {
            'apikey': GFI_SUPABASE_PUBLISHABLE_KEY,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
          },
          body: JSON.stringify(payload),
          keepalive: true
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        markSubmitted();
        if (typeof gfiTrack === 'function') gfiTrack('pulse_submitted', {completed:true});
        form.reset();
        status.textContent = 'Thank you. Your anonymous feedback was recorded.';
        submit.disabled = false;
        setTimeout(close, 1500);
      } catch (_) {
        status.textContent = 'Feedback could not be recorded just now. Please try again.';
        submit.disabled = false;
      }
    });
  }

  buildPulse();
})();
