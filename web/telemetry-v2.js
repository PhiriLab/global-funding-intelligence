(() => {
  'use strict';

  const TELEMETRY_PATH = '/rest/v1/gfi_usage_events';
  const SESSION_KEY = 'gfi_session_v2';
  const SESSION_STARTED_KEY = 'gfi_session_started_v2';
  const nativeFetch = window.fetch.bind(window);
  let lastSourceId = null;

  function uuid() {
    return globalThis.crypto?.randomUUID ? crypto.randomUUID() : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }

  function sessionId() {
    try {
      let id = sessionStorage.getItem(SESSION_KEY);
      if (!id) {
        id = uuid();
        sessionStorage.setItem(SESSION_KEY, id);
      }
      return id;
    } catch (_) {
      return uuid();
    }
  }

  const session = sessionId();

  function trafficClass() {
    if (navigator.webdriver) return 'automated';
    const h = location.hostname.toLowerCase();
    if (h === 'localhost' || h === '127.0.0.1' || h.endsWith('.local')) return 'development';
    return 'production';
  }

  function surface() {
    if (window.self === window.top) return 'direct';
    try {
      const h = new URL(document.referrer).hostname.toLowerCase();
      if (h.includes('wixsite.com') || h.includes('wix.com')) return 'wix_embed';
    } catch (_) {}
    return 'other_embed';
  }

  function referrerClass() {
    if (!document.referrer) return 'direct';
    try {
      const h = new URL(document.referrer).hostname.toLowerCase();
      if (h === location.hostname.toLowerCase()) return 'internal';
      if (/google\.|bing\.|duckduckgo\.|yahoo\.|ecosia\./.test(h)) return 'search';
      if (/linkedin\.|t\.co$|twitter\.|x\.com$|facebook\.|instagram\.|bsky\.|threads\.|tiktok\./.test(h)) return 'social';
      if (/mail\.|outlook\.|proton\.|hey\./.test(h)) return 'email';
      return 'referral';
    } catch (_) {
      return 'unknown';
    }
  }

  function entryHost() {
    if (!document.referrer) return null;
    try { return new URL(document.referrer).hostname.toLowerCase().slice(0, 200); }
    catch (_) { return null; }
  }

  function enrich(body) {
    body.session_id = session;
    body.client_event_id = uuid();
    body.event_version = 2;
    body.traffic_class = trafficClass();
    body.surface = surface();
    body.referrer_class = referrerClass();
    body.entry_host = entryHost();
    if (!body.properties || typeof body.properties !== 'object' || Array.isArray(body.properties)) body.properties = {};
    if (body.event_name === 'primary_source_open' && (!body.properties.source_id || body.properties.source_id === 'unknown') && lastSourceId) {
      body.properties.source_id = lastSourceId;
    }
    if (body.event_name === 'page_ready') body.event_name = 'page_view';
    return body;
  }

  function telemetryRequest(input, init) {
    const url = typeof input === 'string' ? input : input?.url || '';
    return url.includes(TELEMETRY_PATH) && String(init?.method || 'GET').toUpperCase() === 'POST';
  }

  async function sendSessionStart(url, headers) {
    let started = false;
    try { started = sessionStorage.getItem(SESSION_STARTED_KEY) === '1'; } catch (_) {}
    if (started) return;
    const body = enrich({
      event_name: 'session_start',
      page: 'global-funding-intelligence',
      embedded: window.self !== window.top,
      language: (navigator.language || 'unknown').split('-')[0],
      viewport: window.innerWidth < 680 ? 'mobile' : window.innerWidth < 1080 ? 'tablet' : 'desktop',
      properties: {}
    });
    try {
      await nativeFetch(url, {method:'POST', headers, body:JSON.stringify(body), keepalive:true});
      try { sessionStorage.setItem(SESSION_STARTED_KEY, '1'); } catch (_) {}
    } catch (_) {}
  }

  window.fetch = async function(input, init = {}) {
    if (!telemetryRequest(input, init)) return nativeFetch(input, init);
    let body;
    try { body = typeof init.body === 'string' ? JSON.parse(init.body) : init.body; }
    catch (_) { return nativeFetch(input, init); }
    if (!body || typeof body !== 'object') return nativeFetch(input, init);
    const url = typeof input === 'string' ? input : input.url;
    const headers = init.headers || {};
    await sendSessionStart(url, headers);
    const enriched = enrich(body);
    return nativeFetch(input, {...init, body: JSON.stringify(enriched)});
  };

  document.addEventListener('click', event => {
    const link = event.target.closest?.('a.source-link');
    if (!link) return;
    const explicit = link.dataset.sourceId;
    if (explicit) {
      lastSourceId = explicit;
      return;
    }
    try {
      const host = new URL(link.href, location.href).hostname.toLowerCase();
      lastSourceId = host || 'unknown';
    } catch (_) {
      lastSourceId = 'unknown';
    }
  }, true);
})();
