/* Global Funding Intelligence — lightweight, dependency-free bilingual UI (EN/FR).
 *
 * Scope: this translates the interface *chrome* (navigation, hero, section
 * headings, trust principles, footer). It deliberately does NOT machine-translate
 * funder records, opportunity facts, or eligibility text — those stay in their
 * verified source language, because mistranslating an eligibility or funding fact
 * would break the project's "eligibility is never guessed / verify at source"
 * principle. The English text in the HTML is the no-JS fallback; this dictionary
 * is authoritative when JS runs.
 *
 * Preference: user choice persists in localStorage('gfi-lang'); default follows
 * the browser language (French browsers open in French). User-changeable anytime.
 */
(function () {
  const SUPPORTED = ['en', 'fr'];
  const DICT = {
    en: {
      nav_opportunities: 'Opportunities', nav_funders: 'Funders',
      nav_resources: 'Grant resources', nav_how: 'How it works',
      nav_about: 'About', nav_partner: 'Partner / Sponsor', nav_ecosystem: 'Ecosystem',
      hero_eyebrow: 'GLOBAL MAJORITY-FIRST • PRIMARY SOURCE-FIRST',
      hero_h1: 'Find funding opportunities with evidence, provenance and clear uncertainty.',
      hero_lead: 'A public funding intelligence hub for researchers, innovators, charities, universities, clinicians and community organisations. Search trusted funders, understand what has actually been verified, and go directly to the authoritative source before you invest time in a bid.',
      hero_cta1: 'Explore verified opportunities', hero_cta2: 'Browse funding sources',
      trust_1: 'Eligibility is never guessed', trust_2: 'Source states are visible',
      trust_3: 'Global Majority access is explicit', trust_4: 'Primary sources are one click away',
      panel_tracked: 'tracked funders', panel_structured: 'structured beta sources',
      panel_links: 'primary-source links',
      panel_note: 'A missing field means “not verified yet” — not “no restriction”.',
      opp_eyebrow: 'VERIFIED OPPORTUNITIES',
      opp_h2: 'Call-level intelligence, when the source supports it',
      opp_intro: 'Only trusted structured sources can publish call-level records here. Missing fields remain unknown, and eligibility is never inferred from unstructured source text.',
      footer_partnerships: 'Partnerships & sponsorship',
      footer_eligibility: 'Eligibility: not determined — verify at source.',
      lang_note: 'Interface language. Funder and opportunity details stay in their verified source language.'
    },
    fr: {
      nav_opportunities: 'Opportunités', nav_funders: 'Financeurs',
      nav_resources: 'Ressources de financement', nav_how: 'Comment ça marche',
      nav_about: 'À propos', nav_partner: 'Partenaire / Sponsor', nav_ecosystem: 'Écosystème',
      hero_eyebrow: 'MAJORITÉ MONDIALE D’ABORD • SOURCE PRIMAIRE D’ABORD',
      hero_h1: 'Trouvez des financements avec des preuves, une traçabilité et une incertitude clairement indiquée.',
      hero_lead: 'Un centre public de veille sur les financements pour les chercheurs, innovateurs, associations, universités, cliniciens et organisations communautaires. Recherchez des financeurs de confiance, comprenez ce qui a réellement été vérifié, et accédez directement à la source officielle avant d’investir du temps dans une candidature.',
      hero_cta1: 'Explorer les opportunités vérifiées', hero_cta2: 'Parcourir les financeurs',
      trust_1: 'L’éligibilité n’est jamais devinée', trust_2: 'L’état des sources est visible',
      trust_3: 'L’accès pour la Majorité mondiale est explicite', trust_4: 'Les sources primaires sont à un clic',
      panel_tracked: 'financeurs suivis', panel_structured: 'sources en bêta structurée',
      panel_links: 'liens vers les sources primaires',
      panel_note: 'Un champ manquant signifie « pas encore vérifié » — et non « aucune restriction ».',
      opp_eyebrow: 'OPPORTUNITÉS VÉRIFIÉES',
      opp_h2: 'Renseignements au niveau des appels, lorsque la source le permet',
      opp_intro: 'Seules les sources structurées de confiance peuvent publier des enregistrements au niveau des appels ici. Les champs manquants restent inconnus, et l’éligibilité n’est jamais déduite d’un texte source non structuré.',
      footer_partnerships: 'Partenariats et parrainage',
      footer_eligibility: 'Éligibilité : non déterminée — à vérifier à la source.',
      lang_note: 'Langue de l’interface. Les détails des financeurs et des opportunités restent dans leur langue source vérifiée.'
    }
  };

  function detect() {
    try {
      const saved = localStorage.getItem('gfi-lang');
      if (SUPPORTED.includes(saved)) return saved;
    } catch (_e) { /* storage may be blocked */ }
    const nav = (navigator.language || 'en').slice(0, 2).toLowerCase();
    return SUPPORTED.includes(nav) ? nav : 'en';
  }

  let lang = detect();
  function t(key) {
    return (DICT[lang] && DICT[lang][key] != null) ? DICT[lang][key]
         : (DICT.en && DICT.en[key] != null) ? DICT.en[key] : null;
  }

  function apply(root) {
    const scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll('[data-i18n]').forEach(el => { const v = t(el.getAttribute('data-i18n')); if (v != null) el.textContent = v; });
    scope.querySelectorAll('[data-i18n-ph]').forEach(el => { const v = t(el.getAttribute('data-i18n-ph')); if (v != null) el.setAttribute('placeholder', v); });
    scope.querySelectorAll('[data-i18n-aria]').forEach(el => { const v = t(el.getAttribute('data-i18n-aria')); if (v != null) el.setAttribute('aria-label', v); });
    document.documentElement.lang = lang;
  }

  let toggle = null;
  function syncToggle() {
    if (!toggle) return;
    toggle.querySelectorAll('button').forEach(b => {
      const on = b.dataset.lang === lang;
      b.setAttribute('aria-pressed', String(on));
      b.classList.toggle('active', on);
    });
  }

  function setLang(next) {
    if (!SUPPORTED.includes(next)) return;
    lang = next;
    try { localStorage.setItem('gfi-lang', next); } catch (_e) { /* ignore */ }
    apply(document);
    syncToggle();
  }

  window.gfiApplyI18n = () => apply(document);
  window.gfiLang = () => lang;
  window.gfiSetLang = setLang;

  function buildToggle() {
    const actions = document.querySelector('.top-actions');
    if (!actions) return;
    toggle = document.createElement('div');
    toggle.className = 'lang-switch';
    toggle.setAttribute('role', 'group');
    toggle.setAttribute('aria-label', 'Language / Langue');
    toggle.title = t('lang_note') || 'Language';
    SUPPORTED.forEach(code => {
      const b = document.createElement('button');
      b.type = 'button';
      b.dataset.lang = code;
      b.textContent = code.toUpperCase();
      b.setAttribute('aria-label', code === 'fr' ? 'Français' : 'English');
      b.addEventListener('click', () => setLang(code));
      toggle.appendChild(b);
    });
    actions.insertBefore(toggle, actions.firstChild);
    syncToggle();
  }

  function init() {
    buildToggle();
    apply(document);
    // Safety net: translate any chrome injected later that carries data-i18n.
    try {
      new MutationObserver(muts => {
        for (const m of muts) {
          for (const n of m.addedNodes) {
            if (n.nodeType === 1 && (n.matches?.('[data-i18n],[data-i18n-ph],[data-i18n-aria]') || n.querySelector?.('[data-i18n],[data-i18n-ph],[data-i18n-aria]'))) {
              apply(n);
            }
          }
        }
      }).observe(document.body, { childList: true, subtree: true });
    } catch (_e) { /* MutationObserver unavailable */ }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
