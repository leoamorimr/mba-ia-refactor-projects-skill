---
name: refactor-arch
description: Audit a backend codebase for MVC/SOLID violations and security anti-patterns, produce a severity-ranked report, then refactor the project into a clean Model-View-Controller structure and verify it still boots and serves its original endpoints. Use this whenever the user runs /refactor-arch, or asks to audit/refactor a legacy backend's architecture, find code smells and anti-patterns with severity ratings, or restructure a Flask/Express/etc. project into MVC — regardless of the language or framework in use.
---

# Refactor Arch

A tech-agnostic, three-phase workflow that turns a messy backend into an audited, MVC-structured one. It works on any backend language/framework — the reference files below give the heuristics, catalog, and playbook needed to reason about an unfamiliar stack rather than hardcoding knowledge of one specific project.

The three phases run **strictly in order — never skip one** Don't let phase N re-derive from scratch what phase N-1 already established.

## Reference files

Read only what the current phase needs — don't load all five upfront:

- `references/project-analysis.md` — Phase 1 detection heuristics.
- `references/anti-pattern-catalog.md` — Phase 2 anti-pattern catalog with severities and detection signals.
- `references/report-template.md` — Phase 2 exact report format.
- `references/architecture-guidelines.md` — Phase 3 target MVC rules.
- `references/refactoring-playbook.md` — Phase 3 before/after transformation patterns.

## Working files

All intermediate phase reports live in a scratch folder inside the target project, so they survive between subagent invocations without polluting the deliverable:

```
<project-root>/.refactor-arch/
├── phase-1-analysis.md
├── phase-2-audit.md
└── phase-3-validation.md
```

The target project is the current working directory unless the user names a different path explicitly.

---

## Phase 1 — Analysis

Dispatch a subagent (general-purpose, read-only exploration is enough — it must not edit anything in this phase) with this brief:

> Read `references/project-analysis.md` from the skill and apply its heuristics to the project at `<project-root>`. Actually list files and read manifests/imports — don't guess. Determine: language, framework (+ version if pinned), notable dependencies, database, inferred domain, and current architecture shape (flat monolith / god class / partially layered), with a real file count backing every number you report. Write the findings to `<project-root>/.refactor-arch/phase-1-analysis.md` using the exact block format specified in that reference file. Return the same block as your final message.

Print the returned `PHASE 1: PROJECT ANALYSIS` block to the user verbatim — this is the user-visible deliverable for this phase.

## Phase 2 — Audit

Dispatch a subagent with this brief:

> Read `<project-root>/.refactor-arch/phase-1-analysis.md` (Phase 1's findings), then read `references/anti-pattern-catalog.md` and `references/report-template.md` from the skill. Systematically check the project's code against every entry in the catalog, plus anything else that clearly qualifies under the CRITICAL/HIGH/MEDIUM/LOW definitions even if it doesn't map to a named entry. For every hit, record the exact file and line range by actually reading the file — never approximate a line number. Produce the full report using the template's exact structure, sorted CRITICAL → HIGH → MEDIUM → LOW, with the summary counts matching the findings list exactly. Save the report to `<project-root>/.refactor-arch/phase-2-audit.md` and also to `<project-root>/reports/audit-<report-name>.md`, where `<report-name>` is a name explicitly given by whoever invoked this skill (e.g. `project-1`) if one was provided, otherwise the project's directory name lowercased and hyphenated. Return the full report text as your final message.

Print the full audit report to the user. Then **you must pause here** — this is a hard requirement, not a suggestion — and ask the human for real confirmation before any file is modified:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Use AskUserQuestion (or an equivalent explicit confirmation mechanism) to get a real answer from the person running the skill. If they decline or want changes first, stop here — do not dispatch the Phase 3 subagent, and do not treat silence or your own judgment as consent.

## Phase 3 — Refactoring

Only after explicit human confirmation, dispatch a subagent with this brief:

> Read `<project-root>/.refactor-arch/phase-2-audit.md` (the audit findings), then read `references/architecture-guidelines.md` and `references/refactoring-playbook.md` from the skill. Restructure `<project-root>` into the MVC layout described in the architecture guidelines — adapting folder names to this project's language/framework convention, and respecting the "adapting to a partially-organized project" section if the project already has some layering. For every finding in the audit report, apply the matching playbook transformation (or the closest one, using its intent, if no exact match exists). Preserve the original public API surface — same routes, methods, and request/response shapes — this is a structural refactor, not a contract change. Then actually validate the result: install dependencies if the manifest changed, boot the application in the background, hit every original endpoint with a real request (curl or an HTTP client), confirm each responds the same way it did before the refactor (or better, e.g. a previously-open admin endpoint now correctly requires auth), and stop the background process afterward. Write a validation report to `<project-root>/.refactor-arch/phase-3-validation.md` covering: the new directory tree, which findings were fixed, boot output, and the endpoint-by-endpoint check results. Return that report as your final message.

Print the returned report to the user as the `PHASE 3: REFACTORING COMPLETE` block, including the new tree and the validation checklist (app boots without errors / all endpoints respond / anti-patterns addressed). If validation fails, do not claim success — report exactly what broke and fix it before declaring the phase complete; re-run the boot+endpoint check after any fix.

---

## Notes for the orchestrator

- If the project has no dependency manifest changes needed for Phase 3 but does need new packages (e.g. `werkzeug`/`bcrypt` for password hashing, `python-dotenv` for env loading), the Phase 3 subagent should add them to the manifest and install them as part of the refactor, not leave that as a TODO.
- If this skill's folder was copied into a different project than the one it was authored against, nothing above should need adjustment — the reference files intentionally avoid hardcoding filenames or entity names from any one project.
- Re-running this skill on an already-refactored project is safe: Phase 1/2 will simply find fewer or no findings, and Phase 3 has nothing left to change.
