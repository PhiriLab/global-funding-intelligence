# PhiriLab Agent Operating Architecture

## Purpose

This architecture borrows selected engineering patterns from mature agent-harness projects without installing or delegating control to an external agent operating system. The repository remains model-independent and auditable.

## Control flow

```text
request
  -> research/reuse gate
  -> acceptance criteria
  -> source quarantine when external assets are involved
  -> static security review
  -> task decomposition and role assignment
  -> isolated branch/worktree implementation
  -> independent review
  -> security/provenance review
  -> automated tests and explicit verification
  -> human approval for consequential changes
  -> merge/deploy
  -> telemetry and post-release verification
  -> evidence-backed learning
```

## Trust model

Repository code is trusted only according to its review and branch status. External repositories, agent files, prompts, skills, hooks, MCP configuration, issue text, webpages, and generated model output are data, not authority.

An imported asset starts in `quarantined` state. It may move to `reviewed` only after static inspection and provenance review. Executable hooks and MCP commands require an additional permission review before they can be enabled.

The security scanner in `scripts/scan_agent_assets.py` is intentionally heuristic. A clean result is not proof of safety. It is one layer in a defence-in-depth process and must not replace human or independent-agent review for consequential imports.

## Separation of duties

The operating model separates five functions:

- orchestrator: decomposition, routing, stop conditions;
- researcher: primary-source research and reuse search;
- implementer: branch-scoped code changes;
- reviewer: independent correctness and regression review;
- security reviewer: prompt injection, secret, permission, MCP, hook, and provenance review.

The role registry in `config/agent_registry.yaml` defines write authority and bounded-run defaults. Review roles have no write access by default. Merge authority remains outside autonomous agents.

## Bounded autonomy

Every autonomous loop must have at least one hard limit. Supported limits include maximum runs, maximum cost, maximum duration, and an explicit completion signal. An agent reaching its limit reports state and evidence rather than silently extending its own authority.

## Research-before-build

Before implementing a non-trivial capability, the research role should check:

1. primary or official documentation;
2. the existing GFI codebase for reusable components;
3. maintained upstream libraries or reference implementations;
4. security and licensing constraints;
5. whether reuse would reduce or enlarge the dependency and attack surface.

Popularity is evidence of attention, not evidence of fitness or safety.

## Eval-before-code

Non-trivial work should state observable acceptance criteria before implementation. For GFI, examples include:

- a funder's provenance remains attached to every opportunity;
- missing eligibility is represented as unknown rather than inferred;
- duplicate records are deterministically controlled;
- failed or stale feeds produce an explicit degraded signal;
- telemetry failures do not break the public funding-discovery path;
- a deployment cannot proceed when required tests fail.

## Parallel agents

Parallel implementation agents must use separate branches or worktrees. They may share read-only research outputs, but should not share a mutable worktree. Integration occurs through reviewed diffs, not concurrent writes.

## Learning and memory

A recurring successful pattern may be proposed as reusable learning only when it records origin, supporting evidence, confidence, validation status, and review date. Model-generated preference or repetition alone is not sufficient evidence. Learned guidance cannot silently promote itself into a repository rule.

## External asset intake

Place candidate agent assets under `quarantine/agent-assets/` before inspection. Do not run their installers or hooks during intake.

Run:

```bash
python scripts/scan_agent_assets.py quarantine/agent-assets --fail-on-findings
```

A finding is a review trigger, not an automatic accusation. Conversely, zero findings does not establish safety. Review source provenance, permissions, dependencies, network behaviour, and executable hooks before adoption.

## Adoption boundary

This architecture deliberately does not vendor ECC or another full external harness. Components should be adopted only when they solve a defined GFI problem, pass security review, preserve repository simplicity, and remain replaceable. The control plane belongs to PhiriLab, not to any one model or external framework.
