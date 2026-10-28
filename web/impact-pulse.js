(() => {
  'use strict';

  // The canonical usefulness form and its submission handler already live in
  // opportunities.js. Enhance discovery without creating a second form or
  // splitting sponsor-evidence denominators across two instruments.
  const opportunities = document.getElementById('opportunities');
  const existingPulse = document.getElementById('usefulnessPulse');
  const existingForm = document.getElementById('usefulnessPulseForm');
  if (!opportunities || !existingPulse || !existingForm ||
      document.getElementById('gfiImpactPulsePrompt')) return;

  const style = document.createElement('link');
  style.rel = 'stylesheet';
  style.href = 'impact-pulse.css';
  document.head.appendChild(style);

  const prompt = document.createElement('aside');
  prompt.id = 'gfiImpactPulsePrompt';
  prompt.className = 'impact-pulse';
  prompt.hidden = true;
  prompt.setAttribute('aria-label', 'Optional feedback about funding discovery');
  prompt.innerHTML = `
    <div class="impact-pulse__head">
      <div>
        <p class="eyebrow">OPTIONAL FEEDBACK</p>
        <h2>Did the funding source help?</h2>
        <p>Share feedback using the existing usefulness form. No name or
        email is requested. Please do not include personal or confidential information.</p>
      </div>
      <a class="button primary" href="#usefulnessPulse">Share feedback</a>
    </div>
  `;
  opportunities.insertAdjacentElement('afterend', prompt);

  // Reveal a navigation prompt after an authoritative source is opened.
  // The existing form remains the sole collection and submission pathway.
  document.addEventListener('click', event => {
    if (event.target.closest?.('a.source-link')) prompt.hidden = false;
  }, true);
})();
