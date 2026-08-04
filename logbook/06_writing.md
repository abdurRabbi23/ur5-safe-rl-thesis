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

## ▶ Per-chapter PDF export (new, 2026-08-04, Day 27)
`Thesis_LaTeX/tools/build_chapter_pdfs.py` hands out any single chapter, a requested
combination, the cover page, or the bibliography as its own PDF, without shipping the whole
book. Usage:
```
python3 tools/build_chapter_pdfs.py 3          # Chapter_3_Research_Methodology.pdf
python3 tools/build_chapter_pdfs.py 3 4        # Chapters_3-4_..._..._.pdf, combined
python3 tools/build_chapter_pdfs.py --cover        # Cover_Page.pdf alone
python3 tools/build_chapter_pdfs.py --bibliography # Bibliography.pdf alone
python3 tools/build_chapter_pdfs.py --all      # every chapter + cover + bibliography
```
Output: `Thesis_LaTeX/chapter_pdfs/`. Always `[final]` (no draft notes/TODO markers), no title
page (dropped on Touhid's instruction, 2026-08-04). **Chapter PDFs carry no bibliography either
(same instruction)** — the reference list is a separate deliverable, `Bibliography.pdf`, built
from `main.bbl` verbatim so it's always the *full book's* reference list (every chapter's
`\cite`s), not just whatever's in the chapters being exported alongside it. Chapter number is
preserved even standalone (a lone Ch. 3 PDF still says "CHAPTER 3"). `Cover_Page.pdf` is
`frontmatter/coverpage.tex` alone (the unnumbered KUET cover, distinct from the fuller
`titlepage.tex`, which this tool does not currently expose separately).

Cross-chapter `\ref`/`\pageref` (e.g. Ch. 1 pointing at Ch. 4) resolve by importing `\newlabel`
entries from `main.aux`; the bibliography needs a compiled `main.bbl`. **Run a full `latexmk
-pdf main.tex` first if a chapter or a citation changed** — otherwise this tool is working off a
stale table and could silently print outdated page numbers or an outdated reference list (it
still hard-fails on a genuinely unresolved `??`, just not on a stale-but-present value).
Does not touch `main.tex` or any chapter file. All 6 chapters + cover + bibliography built and
verified 2026-08-04.

## ▶ Offline rebuild procedure — do this yourself, no chat needed (2026-08-05, Day 28)
Whenever you edit a chapter (or add a new one), everything in `chapter_pdfs/` is stale until you
rebuild. Full procedure:

**0. One-time check** — `latexmk -v`, `pdflatex -v`, `python3 --version` all need to work. If
`latexmk`/`pdflatex` aren't found, TeX Live isn't installed on that machine yet; that's a
separate install, not covered here.

**1. If you added a genuinely new chapter file** (not just new sections inside an existing one):
   - Name it `chapters/NN_name.tex`, first line exactly `\chapter{Title}\label{ch:something}`.
   - Add `\input{chapters/NN_name}` to `main.tex` in the right position among the other
     `\input{chapters/...}` lines. Skip this and the chapter silently never enters the book or
     `main.aux` — the most common way this goes wrong.

**2. Rebuild the full book once** (refreshes `main.aux`/`main.bbl`, which several of the
`chapter_pdfs/` outputs read from):
```bash
cd Thesis_LaTeX
latexmk -pdf main.tex
```
Check it actually worked: `grep -i undefined main.log` should print nothing. If `latexmk` exits
non-zero, open `main.log` and search for lines starting with `!` — that's the real error
(unmatched brace, bad `\cite` key, etc.), usually a few lines above a `l.<number>` pointer to the
offending line.

**3. Regenerate the PDFs:**
```bash
python3 tools/build_chapter_pdfs.py --all           # 6 chapters + Cover_Page.pdf + Bibliography.pdf
python3 tools/build_chapter_pdfs.py --submission     # one-file supervisor copy
python3 tools/build_chapter_pdfs.py 3 4              # any custom combo you want, by chapter number
```
The script hard-fails (non-zero exit, error printed) on a leaked draft note or an unresolved `??`
reference — a clean exit means it already checked itself. `pdfinfo chapter_pdfs/NAME.pdf | grep
Pages` is a quick manual spot-check if you want to eyeball that a page count moved the way you
expected.

### Troubleshooting (both hit for real, 2026-08-05)
- **"File X.sty not found" / font not loadable, even though the package is clearly installed** —
  stale TeX filename cache, common right after a fresh machine/container. Fix: `mktexlsr`
  (`sudo mktexlsr` if it complains about permissions on some paths — the main tree still updates),
  then rebuild.
- **"Missing \begin{document}" pointing into `main.aux`, especially after trying `latexmk -C`** —
  the aux/bbl files got corrupted by an interrupted clean (this happens if the filesystem allows
  overwriting a file but not deleting it — `rm` fails silently-ish, clean only half-runs). Fix:
  empty the derived files and rebuild from scratch, don't try to `rm` them:
  ```bash
  > main.aux; > main.bbl; > main.blg; > main.toc; > main.lof; > main.lot; > main.out
  latexmk -pdf main.tex
  ```
- **A `.swp` file sitting next to a chapter** (e.g. `chapters/.02_literature_review.tex.swp`) —
  an editor session on that file didn't close cleanly. Page count not moving after you thought you
  edited that chapter is the tell. `vim -r chapters/FILE.tex` offers recovery if there's anything
  unsaved.

**4. End of session** — usual routine: update this file / the relevant `logbook/NN_*.md` +
`run_log.md`, then `git add -A && git commit -m "..." && git push` (see `logbook/07_documentation.md`).

## ▶ Submission build (new, 2026-08-04, Day 27)
`python3 tools/build_chapter_pdfs.py --submission` builds cover page + every chapter (1-6, in
order) + a real bibliography into one PDF, `Thesis_Report_Body_Submission.pdf` (used for the
first supervisor hand-off). `[final]`. No other front matter (title page/declaration/approval
/acknowledgement/abstract/TOC/LOF/LOT/abbreviations all skipped, Touhid's choice) — cover page
added back the same day so it opens on the title rather than straight into Chapter 1. `main.tex`
stays on `[draft]` for ongoing work; this is a one-off build, not a mode switch. Self-contained
(every chapter present in the same run), so unlike the other modes in this tool it does not
depend on a fresh `main.aux`/`main.bbl`.

## ▶ Chapter drafts that exist (updated 2026-08-02, Day 25 night)
| Chapter | File | State |
|---|---|---|
| 1 — Introduction | `Thesis_LaTeX/chapters/01_introduction.tex` | **drafted 2026-08-02, expanded and then audit-corrected 2026-08-03 (Day 26)** — 6 pp. in `[final]`. Unheaded opening section on manipulators and the UR5e (specs sourced to `universalrobots2023ur5e`, interim photo Fig. 1.1 pending Touhid's own), then 1.1 Background, 1.2 Problem Description, 1.3 Objectives, 1.4 Scope. **Audit pass fixed a real self-contradiction:** §1.2 had named the three arms baseline/control/constrained while §1.4 named them baseline + two budgets. §1.2 now matches the scope lock and Chapter 3 Table 3.11 (`ctrl`/`cppo` d=25/`cppo15` d=15, 5 seeds), and records that the control arm reproduced the baseline byte-identically so the two collapse into one reported arm. Objectives now state five seeds, cover both budgets, and end outcome-framed. Humanizer pass done, 0 em dashes, builds clean in both `[draft]` and `[final]`. **Open: §1.1's opening argument still duplicates Chapter 2 §2.2 almost beat for beat** — needs a decision on which chapter keeps it. |
| 2 — Literature Review (file is `02_literature_review.tex`, **not** `02_background.tex` — see HANDOFF) | `Thesis_LaTeX/chapters/02_literature_review.tex` | **rewritten and expanded 2026-08-03 (Day 26)** — 12 sections, pp. 20–41 of the `[draft]` build (22 pp., ~21 in `[final]` once the draftnote drops). Written against the 12 PDFs in `source_papers/`: 4 reproduced figures, 8 tables, 10 display equations, new §2.1 reading guide + key-findings box, new §2.8 comparative methodology table, boxed research gaps in §2.11, long narrative summary in §2.12. Humanizer pass done, 0 em dashes. **Stale "ten seeds" language fixed to five (1,3,4,52,54).** **Cut back to 18 pp. later the same day**, colour and framing removed, figure captions shortened, research gap converted into a figure plus a matrix table. **Then reconciled against the rewritten Chapter 3 (same day):** Fig. 2.6 redrawn to match Table 3.11 (`ctrl`/`cppo`/`cppo15`, not PPO/ctrl/cPPO); `cppo15` and budget sensitivity added as Gap 3; §2.9 hedged because joint-limit proximity carries ~86 % of realised cost; CMDP and PPO-clip equations dropped in favour of cross-references to Eq. (3.1) and (3.3); new original Fig. 2.3 (`lit_twolink_w.pdf`). Now pp. 21–39. **Open: §2.2 still overlaps Chapter 1 §1.2; Chapter 3 §3.8 still calls the singularity term "the operative constraint" against its own Table 3.9.** |
| 3 — Research Methodology (Layer 1) | `Thesis_LaTeX/chapters/03_methodology.tex` | **written 2026-08-03 (Day 26)** — 8 sections + 3 subsections, body pp. 30–40. New §3.3 Software framework (package architecture as Table 3.1, cost computer, Lagrangian runner, train/eval pipeline) and §3.3.1 The gradient-clip audit, which is what §4.2 of the Results chapter assumes is set up here. Every Day-19 number replaced with the frozen `matrix-v2` values (goal box, reward weights, `MANIP_FLOOR` 0.06, `JOINT_LIMIT_MARGIN` 0.175 rad now ACTIVE, `COLLISION_Z_FLOOR` 0.05 m, natural cost ~105, eval protocol). New §3.7.1 states 3 arms / 5 seeds and carries the required "PPO (baseline)" footnote. 8 claim-map citations added; the three tooling entries were the last uncited ones in `references.bib`. Table M1 is now a real captioned float (Table 3.2). Humanizer pass done, 0 em dashes, builds clean. **Expanded later the same day to 20 pp. (body pp. 30–49):** new §3.1 Preliminaries (Isaac Sim/Lab, on- vs off-policy and why this study is on-policy, PPO and cPPO, UR5e spec table), §3.2 problem formulation roughly tripled with the expectation-not-worst-case, undiscounted-episodic and one-scalar-over-three-hazards caveats, six captioned tables, and nine plain "Key points" blocks. Sub-section headings now bold italic, a recorded deviation from the template (see `KUET_FORMAT_SPEC.md` D1). **Open:** Chapter 4 still says ten seeds and names the arms `ppo`/`ctrl`/`cppo`, so the two chapters disagree until Ch. 4 is re-derived. |
| 4 — Results & Discussion (Layer 1) | `Thesis_LaTeX/chapters/04_results.tex` | **RE-DERIVED FROM SCRATCH 2026-08-03 night (Day 26)**, body pp. 61–73 (13 pp.). Rebuilt from `Comparison_test/final_results/` via two new scripts, `results/scripts/summarize_final.py` (all tables + the ppo/ctrl identity check) and `make_ch4_figs.py` (both figures) — no number is hand-typed. Three arms and five seeds throughout; **`cppo15` reported for the first time**, with a new §4.8 answering Chapter 2's Gap 3. **New §4.7 measures the λ trajectories** from `cost_lambda.csv` (single peak at iters 47–58, decaying to 0), which discharges the old Limitation 2. Principal finding survives with a narrower qualification: one seed of five rises, not six of ten. New unanticipated result: the variance collapse appears in task precision as well (goal-reach sd 7.52 → 1.04 → 0.95 points). Humanizer pass done, 44 em dashes → 0. Builds clean. **Open:** SAC arm never trained (stated as a limitation). |
| 5 — Relation with a Real-World Problem | `Thesis_LaTeX/chapters/05_real_world.tex` | **written 2026-08-04 (Day 27)** — pp. 68–69 of the `[draft]` build (2 pp., matching the accepted book), no sub-sections. Four beats in order: industrial relevance, engineering contribution (stated cost budget vs reward weight, illustrated with the Ch. 4 joint-limit/singularity numbers), socio-economic argument (reusing the §4.6 seed-lottery finding, not re-derived), SDG mapping. Claims only **SDG 9 and SDG 8** (Target 8.8) — SDG 12 named and explicitly declined rather than copied from the exemplar's four. One citation, `brunke2022safe`, at the worst-case-severity counter-result. States plainly that nothing ran on hardware. Humanizer pass done, 0 em dashes. Introduces no number absent from Chapter 4. |
| 6 — Conclusions and Future Works | `Thesis_LaTeX/chapters/06_conclusion.tex` | **written 2026-08-04 (Day 27)** — pp. 70–72 of the `[draft]` build (3 pp.). §6.1 Conclusion answers the general objective and all six specific objectives from `chapters/01_introduction.tex` §`sec:i-objectives`, in order, each pointing at the Ch. 4 section that settled it; no new findings, only Chapter 4's own summary claims quoted. §6.2 Future Works covers five positioned gaps: Layer 2 IBVS (`khan2025csrt_ibvs`), Layer 3 sim-to-real (RH-P12-RN vs. the simulated 2F-85 named as a real transfer gap), the cut `sac` arm (`shahid2022continuous_grasping`), PID-Lagrangian as the direct response to the measured λ overshoot (`stooke2020pid`), and the seed-count limitation. Humanizer pass done, 0 em dashes. Introduces no number absent from Chapter 4. |
| Abstract | `Thesis_LaTeX/frontmatter/abstract.tex` | **written 2026-08-04 (Day 27)**, last, after Chapters 1 and 6 both existed. One paragraph, 297 words, no citations. Headline is the §4.6 result: the constrained agent holds task performance while collapsing seed-to-seed safety variance from more than twentyfold to roughly two-to-fivefold. Humanizer pass done, 0 em dashes. |

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
- ~~Chapter 5 (**Relation with a Real-World Problem + SDG mapping**) is KUET-specific, has no
  equivalent in a generic ML thesis, and is not started.~~ **Written 2026-08-04 (Day 27).** See
  the chapter table above.
- **The book now has all six chapters, the abstract, and no stub files left.** `[draft]` builds
  90 pages / 0 errors / 0 undefined refs; `[final]` builds 87 pages / 0 errors / 0 undefined refs,
  both confirmed stable on a second consecutive `latexmk` run. Remaining open items are the
  pre-existing ones below (Chapter 3 §3.8, the Chapter 1/2 §2.2 overlap, font size, Examiner 2),
  none of them touched by the Chapter 5/6/Abstract session.

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
- ~~Write Chapters 4 (re-derivation, not just prose), 5, 6 (all stubbed or superseded).~~ **All
  done.** Chapter 4 re-derived 2026-08-03; Chapters 5, 6 and the Abstract written 2026-08-04
  (Day 27), see the chapter table above and `run_log.md` Day 27 continued.
- Regenerate the per-seed episodic-cost figure. Confirmed 2026-08-02 that
  `Comparison_test/results/tb_csv/` (2035 files) is in the repo, so this can be done on the
  laptop without the lab PC.

## run_log.md refs
- 2026-08-01 (Day 24, cont.) — Results chapter drafted; `MATRIX_V2_PARTIAL_3ARM.md` §4.1 λ
  sentence corrected; Day-19 prose + figures marked withdrawn.
- 2026-08-02 (Day 25) — `Thesis_LaTeX/` built and compiling; Chapters 3 and 4 ported;
  `references.bib` seeded; `[final]` build now enforces the citation blockers.
