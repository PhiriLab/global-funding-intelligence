# PhiriLab Mission Control v1

A security-first, browser-native spatial telemetry interface for the PhiriLab portfolio.

## Acceptance criteria

- Interactive spatial project topology with drag, zoom and project drill-down.
- Evidence states remain explicit: VERIFIED, INFERRED, UNKNOWN.
- Stillpoint represented as LIVE, not awaiting submission.
- PAACS and Xcode Apps 3/4 exposed as release blockers until verified evidence changes.
- Operational telemetry freshness is visible rather than silently treated as current.
- Command input supports portfolio filtering and drill-down.
- Voice input/output uses browser-native Web Speech APIs when available.
- No API keys, tokens, OAuth credentials, third-party scripts or external runtime packages are embedded.
- Public GitHub repositories may refresh read-only commit metadata client-side; failures degrade to the evidence snapshot.
- Google Drive/private repository data remains snapshot-based until a server-side credential boundary is implemented.

## Security and provenance

The interface deliberately avoids third-party frontend dependencies. Browser-side GitHub calls are read-only and unauthenticated. Private telemetry and Google Drive data must be refreshed through a trusted server or director-agent pipeline; never ship OAuth or GitHub credentials to the browser.

## Next integration boundary

1. Generate `data/portfolio.json` from the Director evidence model on each 08:00 cycle and on critical events.
2. Add a server-side read-only aggregator for authenticated Drive/private GitHub telemetry.
3. Feed Stillpoint App Store/analytics and PAACS runtime signals through the same typed evidence schema.
4. Add temporal replay and scenario simulation only after source freshness and provenance are reliable.
