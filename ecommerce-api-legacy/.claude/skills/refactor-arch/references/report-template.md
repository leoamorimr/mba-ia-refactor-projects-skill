# Audit Report Template (Phase 2)

Use this exact structure for the audit report, both for the terminal summary and for the saved Markdown file. Don't add extra top-level sections and don't remove any of these.

## Rules

- **Sort findings CRITICAL → HIGH → MEDIUM → LOW.** Within the same severity, order by the file they appear in.
- **Every finding needs an exact file and line range.** `models.py:1-350` or `AppManager.js:37-78` — never a vague "somewhere in the models".
- **The summary counts must match the findings list exactly.** Count them, don't estimate.
- **Minimum 5 findings**, including at least one CRITICAL or HIGH. In practice, a real legacy project reviewed against the full catalog in `anti-pattern-catalog.md` will surface well more than 5 — report everything you actually find with a concrete file:line, don't stop at 5.
- Write the finding titles using the catalog's anti-pattern names (e.g. "SQL Injection via String Concatenation", "God Class / God File") so the report and the catalog stay traceable to each other.

## Template

```markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <project directory name>
Stack:   <language + framework>
Files:   <N> analyzed | ~<LOC> lines of code

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### [CRITICAL] <Anti-pattern name>
File: <path>:<line-start>-<line-end>
Description: <what the code actually does, in concrete terms>
Impact: <what can go wrong because of it>
Recommendation: <the transformation to apply — name the playbook pattern if one matches>

### [HIGH] <Anti-pattern name>
File: <path>:<line-start>-<line-end>
Description: ...
Impact: ...
Recommendation: ...

... (continue for every finding, grouped by severity in the CRITICAL → HIGH → MEDIUM → LOW order)

================================
Total: <n> findings
================================
```

After printing/saving this report, the orchestrator (not this subagent) must pause and ask the human user for real confirmation before Phase 3 touches any file:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```
