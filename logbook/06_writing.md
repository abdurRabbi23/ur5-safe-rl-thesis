# Module 06 — Thesis Writing, Figures, Defense

Status: ◻ ongoing (writing runs throughout)
Chat type: writing / figures
Last updated: 2026-08-01 (Day 24)

## ▶ Chapter drafts that exist (2026-08-01)
| Chapter | File | State |
|---|---|---|
| 3 — Research Methodology (Layer 1) | `Thesis_Documentation/Methods_Chapter_Layer1.md` | draft, 2026-07-19 — **predates the Day-23 audit**; check whether it narrates the withdrawal, §4.2 of the Results chapter assumes it does |
| 4 — Results & Discussion (Layer 1) | `Thesis_Documentation/Results_Chapter_Layer1.md` | draft, 2026-08-01, from the matrix-v2 3-arm/10-seed partial batch |

Convention: thesis-book **prose** chapters live in `Thesis_Documentation/` as
`*_Chapter_Layer1.md`. The numbered `NN_*.md` files in that folder are reproducibility /
documentation pages, **not** chapter drafts — don't write book prose into them.

## 🛑 Withdrawn writing material — do not quote
The pre-audit Day-19 results prose and figures are withdrawn (banners in place, files kept as a
dated record): the "Results-chapter write-up (draft prose)" section and the calibration/headline
tables in `Thesis_Documentation/06_Results_and_Experiments.md`, plus all four figures in
`Thesis_Documentation/assets/`. **Figures must be regenerated from matrix-v2 before Chapter 4 is
typeset** — highest value is a per-seed episodic-cost plot (Table 4.5), the variance finding reads
far better graphically than as a ten-column table.

## Open writing blockers
- Times New Roman **12 vs 14** still unresolved (Day 7). Don't let a chapter lock it in.
- `[TODO-A]` (Yoshikawa manipulability) and `[TODO-B]` (PPO-Lagrangian) are citation placeholders
  live in the Results chapter — neither is in the project bibliography. Same class of problem as
  the missing Xia 2024 (`08_project_context.md`). Source before submission.
- Chapter 5 (**Relation with a Real-World Problem + SDG mapping**) is KUET-specific, has no
  equivalent in a generic ML thesis, and is not started.

## Goal
Draft chapters as work completes, build figures from real results, prep the defense.

## Formatting rules (from project preferences)
- Documents/PDFs: Times New Roman, justified, 1.25 line spacing, full page width.
  (Project instructions say size 12; a personal note says 14 — confirm before drafting.)
- Figures/tables + their captions: centre-aligned.
- A few purposeful colours; keep it clean, not decorative.

## Material ready to write up
- Layer 1 method + the env-build story (asset merge, gripper linkage, stability fixes) —
  good "implementation & challenges" content. See `logbook/02_grasp_env.md`.
- PPO baseline results (curves in `IsaacLab/logs/rsl_rl/ur5e_lift/`).

## Next steps
- ~~Draft the methodology + system-setup chapter from Modules 01–02.~~ done (Layer 1), but predates
  the audit — review against `ALGORITHM_AUDIT.md` and the recalibrated thresholds.
- ~~Results chapter once the cPPO vs PPO benchmark produces numbers.~~ done for the 3-arm partial
  batch; must be revisited when `cppo10` + `sac` land, since §4.3/§4.7 currently record the
  pre-registered safe-RL claim as unanswered.
- Regenerate Chapter 4 figures from matrix-v2.
- Source `[TODO-A]` / `[TODO-B]`.

## run_log.md refs
- 2026-08-01 (Day 24, cont.) — Results chapter drafted; `MATRIX_V2_PARTIAL_3ARM.md` §4.1 λ
  sentence corrected; Day-19 prose + figures marked withdrawn.
