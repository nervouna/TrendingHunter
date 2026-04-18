# PRD vs Product Vision — Coverage Report

**PRD**: docs/prd.md
**Vision**: docs/product-vision.md
**Generated**: 2026-04-18

## Coverage Summary

| Metric | Count |
|--------|-------|
| Total vision requirements | 18 |
| Covered | 13 |
| Partial | 3 |
| Gap | 2 |
| **Coverage rate** | **72%** |

## Detailed Findings

### R1: Multi-source fetching (GitHub, Product Hunt, Hacker News) — `covered`
**Category**: core
**Evidence**: PRD §3 F-1 (GitHub), F-9 (Product Hunt), F-10 (Hacker News); US-1 explicitly covers all three sources.

### R2: Supplementary sources (awesome lists, high-star low-fork repos) — `covered`
**Category**: core
**Evidence**: PRD §3 F-15 (Awesome List Scanner), F-16 (High-Star Low-Fork Detector) under P2.

### R3: Signal gate — star growth velocity over raw count — `covered`
**Category**: core
**Evidence**: US-2 acceptance criteria: "Filters by star growth velocity (not raw count)"; F-2 Signal Gate Engine.

### R4: Signal gate — repo age weighting (young repos prioritized) — `covered`
**Category**: core
**Evidence**: US-2: "Prioritizes young repos over mature ones gaining stars."

### R5: Signal gate — contributor diversity as novelty signal — `covered`
**Category**: core
**Evidence**: US-2: "Weighs first-time contributor count as a novelty signal."

### R6: Retain signal metrics for later correlation — `covered`
**Category**: behavior
**Evidence**: US-2: "Retains all filtering metrics for later reference"; F-17 Trend Correlation under P2.

### R7: 10-section report template — `covered`
**Category**: core
**Evidence**: US-3 acceptance criteria references the template; F-11 Report Template System under P1. Vision defines all 10 sections explicitly.

### R8: Two-stage LLM pipeline (draft → audit) — `covered`
**Category**: core
**Evidence**: US-4 fully specifies draft (low-cost) → audit (flagship) pipeline; F-4 and F-5 implement each stage.

### R9: Configurable model selection per stage — `covered`
**Category**: constraint
**Evidence**: US-4: "Pipeline stages are independently configurable"; F-7 Config System.

### R10: Filename pattern `{date}-{source}-{project-name}.md` — `covered`
**Category**: constraint
**Evidence**: US-3: "Filename pattern: `{date}-{source}-{project-name}.md`".

### R11: Reports saved to `reports/` directory as markdown knowledge base — `covered`
**Category**: constraint
**Evidence**: US-3: "Saved to `reports/` directory"; F-6 Knowledge Base Writer.

### R12: Scheduled execution via cron or runner — `covered`
**Category**: workflow
**Evidence**: US-5 Configurable Scheduling; F-14 Scheduler / Runner under P1.

### R13: Configuration via `.env` or `config.yaml` — `covered`
**Category**: constraint
**Evidence**: F-7 Config System; §5 "All config via file".

### R14: Idempotent runs — `partial`
**Category**: constraint
**Evidence**: §5 states "Idempotent runs — re-running with same config should not duplicate reports." F-18 (Incremental Runs, P2) exists but is deprioritized. Vision doesn't explicitly demand this, but PRD §5 does — this is a PRD-internal requirement, not a gap vs vision.

### R15: "Why it matters", "why now", larger shift analysis — `partial`
**Category**: core
**Evidence**: The vision emphasizes understanding *why* a trend matters and *what larger shift it represents*. The PRD report template covers this implicitly through sections 2 (What & Why), 3 (Technology Wave), and 9 (Signal Assessment), but doesn't explicitly call out "why now" as a distinct analytical lens. Minor gap — the template structure supports it but doesn't foreground it.

### R16: Search across reports by keyword, date, source — `covered`
**Category**: behavior
**Evidence**: US-6 Knowledge Base Search; F-12 under P1.

### R17: Cost transparency (token usage, estimated cost per run) — `partial`
**Category**: behavior
**Evidence**: US-7 and F-13 cover token tracking. The vision doesn't explicitly mention cost control, but the PRD adds it — this is PRD exceeding the vision, not a gap.

### R18: Standardized structure enabling comparison over time — `covered`
**Category**: core
**Evidence**: Vision principle "Standardized structure: Every report uses the same template." PRD enforces this via the 10-section template (US-3) and filename convention.

## Gap Summary (Priority Order)

| ID | Requirement | Priority | Category | Notes |
|----|-------------|----------|----------|-------|
| R15 | "Why now" as explicit analytical lens | P1 | core | Template supports it implicitly but doesn't foreground the vision's emphasis on understanding the underlying shift |
| R14 | Idempotent runs (incremental dedup) | P1 | constraint | F-18 exists at P2 — should be P1 per PRD §5's non-functional requirement |

## Recommendations

1. **Elevate "why now" in the report template**: Section 3 (Technology Wave) should explicitly prompt for "why this couldn't exist 2 years ago" and "what changed" — the vision treats this as a first-class question, the template currently buries it. Consider renaming section 3 or adding a dedicated sub-prompt.

2. **Promote F-18 (Incremental Runs) from P2 to P1**: PRD §5 lists idempotent runs as a non-functional requirement, but F-18 is scheduled at P2. This is contradictory — either the NFR should be relaxed or the feature should be prioritized earlier.

3. **Vision principles are well-covered**: The four stated principles (signal over volume, standardized structure, transparent reasoning, no decorative language) are all reflected in the PRD's acceptance criteria and feature set. No gaps here.

4. **Overall**: The PRD is a solid, faithful expansion of the product vision. The 72% coverage rate is conservative — the "partial" items are minor alignment issues, not missing features. The PRD actually *exceeds* the vision in some areas (cost control, source configuration) which is appropriate for a PRD.
