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

Structured public-feed capability includes EU Funding & Tenders plus source-specific UKRI, NIHR and Wellcome collection, with deterministic labelled-field eligibility extraction where those primary pages expose stable structured fields. IDRC and Science for Africa detail-page normalization remain part of the wider source engine. Additional global-health, African, Global Majority, philanthropic and life-sciences funders continue to be expanded and promoted through source states only when their authoritative data can be handled safely.

## Getting started

```bash
git clone https://github.com/PhiriLab/global-funding-intelligence.git
cd global-funding-intelligence
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src pytest -q
```

The public package has no required API keys or private model credentials. Network-facing source adapters use primary funder endpoints; unit tests use local fixtures and deterministic parser inputs.

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
- structured applicant organisation, country, lead/partner, income-group, ODA, consortium and local-partner fields only when deterministically verified
- source hash/provenance metadata
- eligibility status: `Not determined — verify at source`

No applicant-specific private data, private digests, or confidential research-observatory content is part of the public repository.

## Security and provenance

External funding pages and documents are treated as untrusted data. Retrieved text cannot directly control eligibility decisions, privileged actions, or repository writes. The fetching layer enforces HTTPS, redirect validation, public-network checks and response-size limits. Source text is fenced and sanitised before any downstream language-model use.

## Global Majority design principle

The engine is designed to make Global Majority access explicit rather than hidden in free text. Lead-country, partner-country, ODA/income-group and consortium rules are represented separately when verified. Unknown rules stay unknown rather than being guessed.

## Partnerships, sponsorship and independence

Global Funding Intelligence is an independent public-interest PhiriLab initiative. Funders, research organisations, foundations, technology partners and sponsors are welcome to support wider source coverage, infrastructure, accessibility, capacity-building and Global Majority reach.

Financial, technical or institutional support **does not confer influence over opportunity verification, eligibility assessment, source-state decisions or ranking**. Sponsored relationships should be disclosed transparently, and funders remain the final authority for their own calls.

Partnership and sponsorship enquiries can be submitted through the repository's structured `Partnership & sponsorship enquiry` issue form. This avoids publishing a personal email address while creating an auditable professional contact route.

## Status

This is a beta public companion to a private research-control plane. The public repository is intentionally conservative: a missing field means the engine has not verified it, not that the restriction does not exist.

## Contributing

Contributions are welcome for new authoritative funder adapters, source verification, parser fixtures, accessibility/localisation and security tests. Please do not submit scraped eligibility guesses or aggregator-only funding records as authoritative opportunities.
