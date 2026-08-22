# Global Funding Intelligence

A public, primary-source-first funding intelligence resource for researchers, innovators, charities, universities, startups and Global Majority institutions.

## What this repository does

Global Funding Intelligence normalises verified funding opportunities from authoritative funder sources, preserves provenance and source state, and helps users discover opportunities without pretending that scraped text is a definitive eligibility decision.

The core rule is simple: **eligibility is not determined by this public repository. Always verify eligibility at the funder's primary source before applying.**

## Source-state badges

- `structured_beta` — structured fields are available from a verified source-specific adapter, but users must still verify at source.
- `structured_beta_detail` — verified detail pages can be structured, but the index/feed may not be a complete representation of currently open calls.
- `partial` — authoritative source is tracked, but structured call extraction is not yet complete. Presented as a source link, not as a verified open call.
- `index_only` — authoritative funding index is tracked; no structured call record is published from it.
- `manual_verify` — source or portal requires human verification and is never presented automatically as an open grant.

## Current beta coverage

Current structured beta coverage includes IDRC and Science for Africa detail pages. UKRI, NIHR, Wellcome and EU Funding & Tenders normalization code is also included in the public engine. Additional global-health, African, philanthropic and life-sciences funders remain explicitly gated according to their source state.

## Public record schema

Public structured records may include:

- funder
- title
- primary source URL
- source-state badge
- source checked timestamp
- programme/status where deterministically extracted
- deadlines, including warnings where timezone or stage needs verification
- currency and award range only where semantically unambiguous
- raw budget text when the amount cannot safely be classified as total-call versus per-award funding
- source hash/provenance metadata
- eligibility status: `Not determined — verify at source`

No applicant-specific scoring, private project data, private digests, or confidential research-observatory content is part of the public repository.

## Security and provenance

External funding pages and documents are treated as untrusted data. Retrieved text cannot directly control eligibility decisions, privileged actions, or repository writes. The fetching layer enforces HTTPS, redirect validation, public-network checks and response-size limits. Source text is fenced and sanitised before any downstream language-model use.

## Global Majority design principle

The engine is designed to make Global Majority access explicit rather than hidden in free text. Lead-country, partner-country, ODA/income-group and consortium rules are represented separately when verified. Unknown rules stay unknown rather than being guessed.

## Status

This is a beta public companion to a private research-control plane. The public repository is intentionally conservative: a missing field means the engine has not verified it, not that the restriction does not exist.

## Contributing

Contributions are welcome for new authoritative funder adapters, source verification, parser fixtures, accessibility/localisation and security tests. Please do not submit scraped eligibility guesses or aggregator-only funding records as authoritative opportunities.
