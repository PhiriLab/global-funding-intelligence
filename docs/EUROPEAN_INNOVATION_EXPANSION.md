# European innovation, startup and spin-out expansion

Status: implementation tranche started 26 August 2026.

## Why this exists

GFI is expanding from research-grant discovery into a broader research-to-innovation-to-company funding intelligence layer. The expansion must preserve the existing evidence rule: **eligibility is never guessed; unknown stays unknown**.

The supplied source set contains different opportunity types. They are therefore not represented as a flat list of interchangeable funders.

## Programme classes

- `direct_funding` — direct or recurring funding programme.
- `eu_programme_pipeline` — a programme-specific view over EU Funding & Tenders records; the EU topic ID is the deduplication key and the Funding & Tenders topic remains the system of record.
- `cascade_funding` — Financial Support for Third Parties (FSTP); a funding opportunity class issued by EU-funded projects/consortia, not a single funder.
- `watcher` — authoritative programme monitored for a current round; opportunity-level publication waits for a verified live call.
- `meta_source` — mixed opportunity index containing funding and non-funding offers; records must be classified before publication.
- `ecosystem_access` — investor/accelerator/ecosystem support; must never be presented as a grant unless a separate funding instrument is verified.

## P1 activation tranche

1. Eurostars / Eureka
2. Women TechEU
3. Innosuisse Start-up Innovation Projects
4. GO-Bio next
5. aws Preseed / Seedfinancing Deep Tech
6. Innobooster
7. EIC Pathfinder
8. LIFE Programme / CINEA
9. EU Cascade Funding / FSTP

P1 does **not** mean every programme is immediately promoted into the live structured opportunity feed. P1 means it is first in the adapter/verification queue. Each source must pass its own extraction, provenance and regression tests before `structured_beta` publication.

## P2/P3 watch and ecosystem tranche

- ZIM
- CDTI NEOTEC
- Bpifrance i-Nov
- France i-Lab
- EIT Opportunities
- ESA BIC Booster
- French Tech 2030
- French Tech Rise (ecosystem/investor access; P3)

## Innovation metadata contract

The first migration tranche introduces a separate evidence-gated innovation metadata contract rather than weakening the core grant schema. It covers:

- opportunity class
- venture stage
- spin-out route
- startup age limit
- company-country requirements
- cross-border requirement
- women-led targeting
- co-funding rate
- funding instrument
- programme family
- parent/deduplication route
- TRL range

Adapters may populate these values only from authoritative programme or call evidence. Missing values remain unknown.

## EU deduplication rules

EIC Pathfinder and LIFE are programme views, not duplicate sources. When a call exists in the EU Funding & Tenders feed, deduplicate by the authoritative EU topic identifier. CINEA/EIC pages may contribute programme context and provenance but do not create a second call record.

FSTP is different: the issuing project/consortium is the call authority. GFI may use the Commission FSTP page for discovery, but a promoted record must resolve to the issuing consortium's primary call and preserve the parent EU-project context.

## Global Majority handling

Eurostars is the standout cross-border route in this tranche because participating-country structure can include both UK and South African organisations. That does **not** mean one national funding agency finances every consortium member. GFI must retain the national funding rule for each participant.

For ZIM, foreign partners may participate in international cooperation calls but generally require their own national funding route. GFI must never infer that ZIM directly funds a non-German partner without call-specific evidence.

## Promotion gates

A new programme can be promoted from registry/watcher to structured opportunity publication only when:

1. the authoritative source is stable and machine-collectable or deterministically parseable;
2. open/upcoming status can be established without inference;
3. title and primary call URL are stable;
4. deadline semantics are explicit;
5. money semantics do not confuse total programme budget with per-award funding;
6. applicant route/eligibility remains unknown unless explicitly evidenced;
7. duplicate identity is stable across refreshes;
8. source errors fail closed and cannot blank the wider GFI feed;
9. unit/regression tests pass;
10. the live Chromium acceptance gate remains green after deployment.

## Next engineering sequence

1. Implement P1 source adapters in small source-specific PRs.
2. Start with Eurostars and Women TechEU because they add the strongest new cross-border/inclusion signal.
3. Add Innosuisse, GO-Bio next, aws and Innobooster direct-programme adapters.
4. Add EIC Pathfinder and LIFE as filtered/deduped EU programme views rather than parallel call stores.
5. Add the FSTP discovery/issuing-consortium resolver.
6. Add P2 watchers once the P1 path is stable.
7. Extend the public UI with innovation-specific filters only after structured data coverage is sufficient to avoid misleading empty/unknown filters.
