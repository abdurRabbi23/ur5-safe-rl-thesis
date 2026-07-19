# Module 07 — Beginner Documentation (replicate-from-scratch guide)

Status: ▶ ongoing, written parallel to the thesis
Chat type: documentation
Last updated: 2026-07-19 (Day 9)

## Goal
Maintain `Thesis_Documentation/` — a beginner-facing guide that lets someone with no context
replicate the whole thesis from an empty machine to final results. Every step: the command, why/when
to run it, and the expected output. Written alongside the work, not at the end.

## Where it lives
`Thesis_Documentation/` (front door: `00_START_HERE.md`). This is the cleaned-up, beginner version
of the `logbook/` notes + `run_log.md`; nothing here duplicates the deep working state — it
translates it for a fresh reader.

## Current state (Day 9)
- 10 pages built. 01 env-setup + 02 grasp-env fully written (done work); 03 cppo-benchmark
  documented to the calibrated state (MANIP_FLOOR=0.045, cost_limit=25) with runbook Steps 6-7 as
  PENDING; 04 IBVS + 05 sim2real are planned outlines; 06 results, 07 troubleshooting (all bugs+
  fixes), 08 glossary, 09 changelog.
- All script/asset paths referenced in the docs verified to exist in the repo.

## Working convention (keep it in sync)
When work happens in a module → update the matching `Thesis_Documentation/NN_*.md` page AND append a
dated line to `Thesis_Documentation/09_Changelog.md` (in addition to the usual module-file +
run_log.md update).

## Page ↔ module map
- 01_Environment_Setup  ← Module 01
- 02_Grasp_Environment  ← Module 02
- 03_Safety_and_cPPO_Benchmark ← Module 03 (+ 03b runbook)
- 04_Layer2_IBVS        ← Module 04
- 05_Layer3_SimToReal   ← Module 05
- 06_Results_and_Experiments, 07_Troubleshooting, 08_Glossary, 09_Changelog ← cross-cutting

## Next steps
- After the two full runs (Module 03 Steps 6-7): fill the benchmark table in 06 + real curves in 03.
- Begin 04/05 pages when those layers start.

## run_log.md refs
Day 9 (2026-07-19): documentation folder created.
