// Drives web/telemetry-v2.js in a stubbed browser and reports how many
// session_start events it emits when several telemetry POSTs race at page load.
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');

const sent = [];
const store = {};
global.sessionStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); }
};
global.navigator = { language: 'en-GB', webdriver: false };
global.location = { hostname: 'phirilab.github.io', href: 'https://phirilab.github.io/' };
global.document = { referrer: '', addEventListener() {} };
globalThis.crypto = { randomUUID: () => 'aaaaaaaa-bbbb-4ccc-8ddd-' + (Math.random() * 1e12 | 0) };

// Latency is what opens the race window in the original check-then-await-then-mark guard.
const nativeFetch = async (url, init) => {
  sent.push(JSON.parse(init.body).event_name);
  await new Promise(r => setTimeout(r, 20));
  return { ok: true, status: 201 };
};
const win = { innerWidth: 1200, fetch: nativeFetch };
win.self = win; win.top = win;
global.window = win;

eval(src);

const url = 'https://example.supabase.co/rest/v1/gfi_usage_events';
const post = name => window.fetch(url, {
  method: 'POST', headers: {},
  body: JSON.stringify({ event_name: name, page: 'global-funding-intelligence', properties: {} })
});

// Page load fires these effectively simultaneously.
Promise.all([post('page_ready'), post('feed_ready'), post('source_impression')])
  .then(() => console.log(JSON.stringify({
    session_start: sent.filter(e => e === 'session_start').length,
    sent
  })));
