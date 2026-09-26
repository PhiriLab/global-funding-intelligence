// Drives web/opportunities.js in a stubbed browser and reports the source_id values
// it emits when the same funder is present on both surfaces (curated directory card
// and live feed card, which name that funder differently).
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');

const sent = [];

function makeEl(extra = {}) {
  return {
    dataset: {}, style: {}, classList: {add(){}, remove(){}},
    appendChild() {}, addEventListener() {}, removeEventListener() {},
    querySelector: () => null, querySelectorAll: () => [],
    closest: () => null, insertAdjacentHTML() {}, remove() {},
    set innerHTML(_v) {}, get innerHTML() { return ''; },
    ...extra
  };
}

global.document = {
  head: makeEl(), body: makeEl(),
  createElement: () => makeEl(),
  querySelector: () => null,
  querySelectorAll: () => [],
  getElementById: () => null,
  addEventListener() {}
};
global.navigator = { language: 'en-GB', doNotTrack: null };
global.location = { hostname: 'phirilab.github.io', href: 'https://phirilab.github.io/' };

// Fire on observe, so an impression is recorded the moment a card is watched.
global.IntersectionObserver = class {
  constructor(cb) { this.cb = cb; }
  observe(target) { this.cb([{ isIntersecting: true, target }], this); }
  unobserve() {}
};

const win = {
  innerWidth: 1200,
  fetch: (url, init) => {
    const body = JSON.parse(init.body);
    sent.push({ event: body.event_name, source_id: (body.properties || {}).source_id });
    return Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve({}) });
  }
};
win.self = win; win.top = win;
global.window = win;
global.fetch = win.fetch;
global.IntersectionObserver = global.IntersectionObserver;

eval(src);

// Two cards, one funder: the publisher's connector id and the directory's funder id.
const links = [
  makeEl({ dataset: { sourceId: 'ukri_funding_finder' } }),
  makeEl({ dataset: { sourceId: 'ukri' } }),
  makeEl({ dataset: { sourceId: 'eu_funding_tenders' } }),
  makeEl({ dataset: { sourceId: 'idrc' } })
];
const clicks = [];
links.forEach(l => { l.addEventListener = (evt, fn) => { if (evt === 'click') clicks.push(fn); }; });
document.querySelectorAll = () => links;

wireSourceLinkTelemetry();
clicks.forEach(fn => fn());

const impressions = sent.filter(e => e.event === 'source_impression').map(e => e.source_id);
const opens = sent.filter(e => e.event === 'primary_source_open').map(e => e.source_id);
console.log(JSON.stringify({ impressions, opens }));
