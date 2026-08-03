# Module 06 — Thesis Writing, Figures, Defense

Status: ◻ ongoing (writing runs throughout)
Chat type: writing / figures
Last updated: 2026-08-02 (Day 25)

## ▶ Where the book is typeset (new, 2026-08-02)
`Thesis_LaTeX/` — LaTeX project, compiles clean (`latexmk -pdf`, 34 pages, 0 errors, 0 undefined
refs). Read `Thesis_LaTeX/README.md` before touching it. Engine pdflatex + newtx.

Two switches, both in `main.tex`:
- **font size** — one commented line, `12pt` ↔ `14pt`, nothing else moves. Still unresolved.
- **`[draft]` / `[final]`** — `final` hides all draft apparatus and turns any surviving
  `\todocite` into a *hard build error*. Verified: it currently fails on exactly the two known
  placeholders. This is now the enforcement mechanism for the citation blockers below.

Porting rule: `Thesis_Documentation/*_Chapter_Layer1.md` is the source of truth **until** the
chapter has a `.tex`; after that the `.tex` is authoritative and the `.md` is a frozen dated
record. Chapters 3 and 4 are ported. Do not re-run `Thesis_LaTeX/tools/` over an edited chapter.

## ▶ Chapter drafts that exist (updated 2026-08-02, Day 25 night)
| Chapter | File | State |
|---|---|---|
| 1 — Introduction | `Thesis_LaTeX/chapters/01_introduction.tex` | **drafted 2026-08-02, expanded and then audit-corrected 2026-08-03 (Day 26)** — 6 pp. in `[final]`. Unheaded opening section on manipulators and the UR5e (specs sourced to `universalrobots2023ur5e`, interim photo Fig. 1.1 pending Touhid's own), then 1.1 Background, 1.2 Problem Description, 1.3 Objectives, 1.4 Scope. **Audit pass fixed a real self-contradiction:** §1.2 had named the three arms baseline/control/constrained while §1.4 named them baseline + two budgets. §1.2 now matches the scope lock and Chapter 3 Table 3.11 (`ctrl`/`cppo` d=25/`cppo15` d=15, 5 seeds), and records that the control arm reproduced the baseline byte-identically so the two collapse into one reported arm. Objectives now state five seeds, cover both budgets, and end outcome-framed. Humanizer pass done, 0 em dashes, builds clean in both `[draft]` and `[final]`. **Open: §1.1's opening argument still duplicates Chapter 2 §2.2 almost beat for beat** — needs a decision on which chapter keeps it. |
| 2 — Literature Review (file is `02_literature_review.tex`, **not** `02_background.tex` — see HANDOFF) | `Thesis_LaTeX/chapters/02_literature_review.tex` | **rewritten and expanded 2026-08-03 (Day 26)** — 12 sections, pp. 20–41 of the `[draft]` build (22 pp., ~21 in `[final]` once the draftnote drops). Written against the 12 PDFs in `source_papers/`: 4 reproduced figures, 8 tables, 10 display equations, new §2.1 reading guide + key-findings box, new §2.8 comparative methodology table, boxed research gaps in §2.11, long narrative summary in §2.12. Humanizer pass done, 0 em dashes. **Stale "ten seeds" language fixed to five (1,3,4,52,54).** **Cut back to 18 pp. later the same day**, colour and framing removed, figure captions shortened, research gap converted into a figure plus a matrix table. **Then reconciled against the rewritten Chapter 3 (same day):** Fig. 2.6 redrawn to match Table 3.11 (`ctrl`/`cppo`/`cppo15`, not PPO/ctrl/cPPO); `cppo15` and budget sensitivity added as Gap 3; §2.9 hedged because joint-limit proximity carries ~86 % of realised cost; CMDP and PPO-clip equations dropped in favour of cross-references to Eq. (3.1) and (3.3); new original Fig. 2.3 (`lit_twolink_w.pdf`). Now pp. 21–39. **Open: §2.2 still overlaps Chapter 1 §1.2; Chapter 3 §3.8 still calls the singularity term "the operative constraint" against its own Table 3.9.** |
| 3 — Research Methodology (Layer 1) | `Thesis_LaTeX/chapters/03_methodology.tex` | **written 2026-08-03 (Day 26)** — 8 sections + 3 subsections, body pp. 30–40. New §3.3 Software framework (package architecture as Table 3.1, cost computer, Lagrangian runner, train/eval pipeline) and §3.3.1 The gradient-clip audit, which is what §4.2 of the Results chapter assumes is set up here. Every Day-19 number replaced with the frozen `matrix-v2` values (goal box, reward weights, `MANIP_FLOOR` 0.06, `JOINT_LIMIT_MARGIN` 0.175 rad now ACTIVE, `COLLISION_Z_FLOOR` 0.05 m, natural cost ~105, eval protocol). New §3.7.1 states 3 arms / 5 seeds and carries the required "PPO (baseline)" footnote. 8 claim-map citations added; the three tooling entries were the last uncited ones in `references.bib`. Table M1 is now a real captioned float (Table 3.2). Humanizer pass done, 0 em dashes, builds clean. **Expanded later the same day to 20 pp. (body pp. 30–49):** new §3.1 Preliminaries (Isaac Sim/Lab, on- vs off-policy and why this study is on-policy, PPO and cPPO, UR5e spec table), §3.2 problem formulation roughly tripled with the expectation-not-worst-case, undiscounted-episodic and one-scalar-over-three-hazards caveats, six captioned tables, and nine plain "Key points" blocks. Sub-section headings now bold italic, a recorded deviation from the template (see `KUET_FORMAT_SPEC.md` D1). **Open:** Chapter 4 still says ten seeds and names the arms `ppo`/`ctrl`/`cppo`, so the two chapters disagree until Ch. 4 is re-derived. |
| 4 — Results & Discussion (Layer 1) | `Thesis_LaTeX/chapters/04_results.tex` | ported 2026-08-02; md frozen at 2026-08-01, from the matrix-v2 3-arm/10-seed partial batch. Confirmed 2026-08-02 night: "ten seeds"/"10 seeds" language survives at 10+ locations — this chapter still needs the full re-derivation HANDOFF.md flags, not started. |

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
- ~~`[TODO-A]` (Yoshikawa manipulability) and `[TODO-B]` (PPO-Lagrangian) are citation
  placeholders live in the Results chapter.~~ **RESOLVED 2026-08-02 (Day 25, evening).** Both
  sourced, verified against the publisher record, cited in the prose, and the placeholders
  deleted. The missing Xia 2024 is closed too. See `logbook/10_references.md`.
- ~~**NEW hard-error blocker, and now the only one:** six `\todo{}` markers in
  `frontmatter/approval.tex`.~~ **CLOSED 2026-08-03 (Day 26).** The board turned out to be two
  examiners, not three, and member 2 has not been announced, so that block is now deliberately
  blank for hand completion rather than a `\todo`. Supervisor also corrected to **Priyo Nath Roy,
  Assistant Professor, Department of Mechatronics Engineering** (was Dr. Md. Helal-An-Nahiyan,
  Professor, Mechanical Engineering) in `frontmatter/_thesis_details.tex`, which feeds the title
  page, the declaration and Examiner 1. **`[final]` now builds clean: exit 0, 68 pages, 0 errors,
  0 undefined citations or references.** The book has no remaining hard-error blockers.
- Chapter 5 (**Relation with a Real-World Problem + SDG mapping**) is KUET-specific, has no
  equivalent in a generic ML thesis, and is not started.

## ▶ Bibliography — see `logbook/10_references.md`
21 verified entries in `Thesis_LaTeX/references.bib`. **Read the claim map in `10_references.md`
before writing any chapter** — it binds each source to the claim it licenses and the chapter that
should carry it, and it holds the agreed Chapter 2 spine. Rule: don't cite anything that isn't in
the claim map; add the row first, then write the sentence.

Chapter 2 is **no longer blocked**. Its stub says nothing can be written until the PDFs are
uploaded — that is wrong and is superseded. A background chapter needs verified metadata and an
argument, both of which now exist.

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
  batch. **No longer revisitable via new runs** — `cppo10` and `sac` were cut on 2026-08-02, so
  §4.7 Limitation #1 is permanent, not provisional.
- ~~Set up the LaTeX writing environment.~~ done 2026-08-02, `Thesis_LaTeX/`.
- **Get the official KUET `.cls`/`.sty` into the repo** and swap it in for `thesis-format.sty`.
  Until then the title page and all formatting are stand-ins.
- Confirm font size 12 vs 14 with the supervisor, then set the one line in `main.tex`.
- Regenerate Chapter 4 figures from matrix-v2 → `Thesis_LaTeX/figures/`. Highest value is the
  per-seed episodic-cost plot for Table 4.5.
- Convert the ported `longtable`s into captioned floats so the List of Tables populates and
  "Table 4.1" becomes a real reference rather than bold text.
- ~~Source `[TODO-A]` / `[TODO-B]`, fill the skeletons in `references.bib`, replace the
  `\todocite` calls with `\cite`, then delete `\nocite{*}`.~~ **done 2026-08-02 evening.**
- Get the Board of Examiners details (members 2 and 3) and fill `frontmatter/approval.tex`.
  Last hard-error blocker on the `[final]` build.
- ~~Write Chapter 1.~~ **done 2026-08-02, Day 25 night; expanded 2026-08-03 (Day 26) to 6
  pages** — new §1.1 "The UR5e Manipulator and This Thesis" (platform specs, sourced to
  `universalrobots2023ur5e`; interim photo from `xia2024proactive` Fig. 1, pending Touhid's own
  photograph, see `Thesis_LaTeX/figures/README.md`), §1.2 Background expanded with a concrete
  worked example (the UR5e joint-speed penalty case), §1.5 Scope enlarged with two new bullets
  (Algorithms, Hardware validation). Problem Description and Objectives untouched at Touhid's
  request. Rebuilt clean: 0 em dashes, 0 undefined citations, figure renders. Chapter now 6
  pages (was 3).
- Write Chapters 4 (re-derivation, not just prose), 5, 6 (all stubbed or superseded). This line
  still uses the old seven-chapter numbering in places elsewhere in this file — the live book is
  six chapters, see HANDOFF.md.
- Regenerate the per-seed episodic-cost figure. Confirmed 2026-08-02 that
  `Comparison_test/results/tb_csv/` (2035 files) is in the repo, so this can be done on the
  laptop without the lab PC.

## run_log.md refs
- 2026-08-01 (Day 24, cont.) — Results chapter drafted; `MATRIX_V2_PARTIAL_3ARM.md` §4.1 λ
  sentence corrected; Day-19 prose + figures marked withdrawn.
- 2026-08-02 (Day 25) — `Thesis_LaTeX/` built and compiling; Chapters 3 and 4 ported;
  `references.bib` seeded; `[final]` build now enforces the citation blockers.
