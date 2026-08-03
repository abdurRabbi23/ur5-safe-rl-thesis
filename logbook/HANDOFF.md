# HANDOFF — paste this into a new session

Updated 2026-08-02 (Day 25, night). Overwrite whenever the next action changes.

> **READ FIRST, ABOVE EVERYTHING ELSE BELOW — the results scope was LOCKED DOWN and
> NARROWED again, later on Day 25 than the rest of this file. This supersedes every mention
> of "10 seeds", "ppo/ctrl/cppo", and `MATRIX_V2_PARTIAL_3ARM.md`/`Results_Chapter_Layer1.md`
> below and in `04_results.tex`.**
>
> **Final scope: 5 seeds (1, 3, 4, 52, 54), 3 arms (`ctrl`, `cppo`, `cppo15`).** `ppo` is
> DROPPED (bitwise-identical to `ctrl` — checkpoint-hash-verified — so `ctrl` stands in for it
> everywhere, including `mean_episode_cost` which the plain ppo runner never logged). **In
> thesis text/figures, `ctrl` is labeled "PPO (baseline)"**, with a one-time footnote pointing
> at `Comparison_test/ppo_redundant/README.md`. Full rule: `CLAUDE.md`'s "Results scope"
> section — read that section before writing a single number into Chapter 4.
>
> **All thesis data now lives in `Comparison_test/final_results/{training,evaluation}/`,
> organized as `<algo_folder>/seed_<N>/*.csv`** (on-disk folder names are `PPO_baseline` = ctrl,
> `CPPO_25` = cppo, `CPPO15` = cppo15 — not the literal algo names). This is a MOVE, not a
> copy-alongside — `results/tb_csv/` and `ur5_grasp/tools/eval_episodes/` (the flat sources)
> still exist but are also filtered to the same 3 arms/5 seeds now (eval side reorganized into
> the same folder structure too; training source deliberately left flat). Full provenance:
> `Comparison_test/final_results/README.md`.
>
> **`Thesis_Documentation/Results_Chapter_Layer1.md` and
> `Comparison_test/results/MATRIX_V2_PARTIAL_3ARM.md` are SUPERSEDED — do not read them for
> thesis content anymore**, even though the line further down in this file still calls the
> first one the "frozen record" for Chapter 4. Both describe the old 10-seed/`ppo`-named
> scope. **`Thesis_LaTeX/chapters/04_results.tex` (554 lines, fully drafted) was ported from
> that now-superseded source and needs substantive re-derivation, not just a wording pass** —
> every number, the arm-naming convention, and the seed count are all out of date. This is real
> new work, not caught by the existing critical path below (which predates this scope lock) —
> flag the schedule risk to Touhid rather than silently absorbing it into "03 Aug: Chapter 2."
>
> Two other loose corrections found while auditing this file on 2026-08-02, not yet fixed
> anywhere except here: (1) `logbook/06_writing.md` and `logbook/10_references.md` call
> Chapter 2's file `02_background.tex` — the real file is `02_literature_review.tex`. (2) page
> counts disagree across files (this file says 47, `06_writing.md`/`10_references.md` say 34) —
> don't trust either without rebuilding and checking.
>
> **READ SECOND — bibliography is DONE, Chapter 2 is UNBLOCKED (2026-08-02 evening).**
> `Thesis_LaTeX/references.bib` holds 21 verified entries. `[TODO-A]` and `[TODO-B]` are
> RESOLVED and deleted from the prose; `\nocite{*}` is gone; both `[draft]` and `[final]`
> build clean (0 errors, 0 undefined citations). **Read `logbook/10_references.md` — the claim
> map — before writing any chapter.** It says which source licenses which claim and where it
> goes, and holds the agreed Chapter 2 spine. Rule: don't cite anything not in the claim map.
>
> The Chapter 2 stub still says "BLOCKED: no reference PDFs are in this repo." **That is
> superseded — ignore it.** A background chapter needs verified metadata and an argument, not
> twenty PDFs, and with the deadline this close reading them all is the wrong trade.
>
> ~~**The only remaining hard-error blocker in the whole book** is six `\todo{}` markers in
> `frontmatter/approval.tex`.~~ **CLOSED 2026-08-03 (Day 26).** The board is two examiners, not
> three; member 2 is not announced yet and that block is now deliberately blank for hand
> completion. Supervisor corrected to **Priyo Nath Roy, Assistant Professor, Department of
> Mechatronics Engineering** in `frontmatter/_thesis_details.tex` (single source for the title
> page, declaration and Examiner 1). **`[final]` builds clean: exit 0, 68 pages, 0 errors, 0
> undefined citations or references. The book has no hard-error blockers left.** Remaining risk is
> content, not build: Chapter 4's re-derivation, and Chapters 5 and 6.
>
> **WRITING RULE, MANDATORY (2026-08-02).** Every piece of thesis prose goes through the
> `humanizer` skill before it is written to a file. Not optional. See `CLAUDE.md` and
> `logbook/11_writing_style.md`. Two calibrations: the skill's PERSONALITY AND SOUL section does
> NOT apply (a thesis is technical writing, plain neutral prose is the correct human voice), and
> LaTeX `---` is cut everywhere while `--` in numeric ranges is kept. Check before saving:
> `grep -c '\-\-\-' chapters/NN_*.tex` must be 0. Chapters 1 and 2 are done (0 em dashes each,
> builds clean, 48 pages); Chapter 4 has 44 left (recounted, was logged as 45); Chapter 3 has 8
> (recounted, was logged as 9).
>
> **2026-08-02, Day 25 night (Cowork):** Chapter 1 written in full (1.1 Background, 1.2 Problem
> Description, 1.3 Objectives, 1.4 Scope), citations against the Chapter 1 claim map in
> `logbook/10_references.md`, humanizer pass done. Two things worth knowing before the next
> session touches Chapters 1 or 2: (1) Chapter 2 §2.1 turned out to be near-verbatim the same
> prose Chapter 1 was drafted from, not a forward-pointer as previously assumed — the two
> chapters now overlap in their opening framing, not trimmed, Touhid's call. (2) Chapter 1
> deliberately does not cite `shen2022reactive` or `altman1999cmdp` even though the claim map
> licenses them there, since Chapter 2 already argues both in full; flag if that framing is
> wanted earlier in the book too. Full detail: `run_log.md`, same date.
>
> SUBMISSION IS 06 AUGUST.

```
Read logbook/00_INDEX.md first for project background, but note its "Current status" section is
STALE — last dated Day 19/23. Everything below post-dates it and is the real current state.
Then read this whole block before doing anything.

=============================================================================
STATE — TRAINING IS OVER. Thesis is now in pure writing/formatting phase.
=============================================================================
Decision made 2026-08-02: no further training runs. The matrix-v2 batch (commit 567e4c0, tag
matrix-v2/matrix-v2-cppo15) is the source all thesis numbers come from — but as of later Day 25
the SCOPE WITHIN it is locked to 5 of the 10 trained seeds (1, 3, 4, 52, 54) and 3 of the 4
trained arms (ctrl/cppo/cppo15, ppo dropped as redundant with ctrl). See the banner at the top
of this file — that is current, this paragraph is deliberately left for the training-is-over
decision, not the scope numbers. The two pre-registered arms that were never trained, cppo10
(actively-binding budget) and sac (off-policy comparison), are CUT — not paused, cut. Do not
suggest running them. The results write-up already states this as a Limitation — re-verify the
section number against the rewritten Chapter 4, don't assume it's still §4.7.

Full results + provenance: Comparison_test/final_results/README.md (current) and
Comparison_test/excluded_seeds/README.md, Comparison_test/withdrawn_runs/README.md,
Comparison_test/ppo_redundant/README.md (what got excluded and why, three separate reasons,
don't conflate them). Thesis_Documentation/Results_Chapter_Layer1.md is SUPERSEDED, kept only
as a historical record of the old 10-seed framing — the live chapter is
Thesis_LaTeX/chapters/04_results.tex, which itself now needs re-deriving against final_results/.
[TODO-A] and [TODO-B] are RESOLVED as of 2026-08-02 and no longer appear anywhere in the prose.
See logbook/10_references.md for the claim map.

=============================================================================
GIT / MACHINES — migration done 2026-08-02. Read this before touching git on either machine.
=============================================================================
What happened, in order:
1. Lab PC's `main` and GitHub's `origin/main` had SILENTLY DIVERGED since 2026-07-22. Reason,
   documented in run_log.md Day 18: on 2026-07-28 the whole repo was reset to the pre-Layer-2
   commit (8d4cb41), deliberately abandoning Layer 2 (IBVS) + Layer 3 (RH-P12-RN gripper) work.
   That abandoned history was tagged `backup/pre-layer1-reset` locally but GitHub's `main` was
   never force-updated to match — so origin/main sat frozen at the old pre-reset tip (0c320cf)
   while local main gained 19 new commits (all the matrix-v2 / Day 22-24 work) that GitHub never
   saw.
2. Fixed by: pushing the `backup/pre-layer1-reset` tag to origin (so the abandoned Layer 2/3
   work is preserved on GitHub too, just off the main line), then `git push origin main
   --force-with-lease` to make origin/main match local main. Verified: both now at cde5e0c.
3. Laptop cloned fresh from the corrected origin/main. Verified clean: HEAD/main/origin/main/
   origin/HEAD all at cde5e0c, all 5 tags present (backup/pre-layer1-reset, comparison-matrix-v0,
   layer1-env-freeze, matrix-v2, matrix-v2-cppo15).

Current machine roles:
- LAPTOP is now primary for writing. Full clone, correct history.
- LAB PC still holds the untracked working tree (IsaacLab/, checkpoints, logs — all correctly
  gitignored, never were in git). Treat it as the archive for raw artifacts only. If it's ever
  touched again for git ops, `git pull` first.
- Known loose end on the lab PC: a local branch `backup-before-merge-2026-08-02` (safety net
  from the fix above) is probably still sitting there unused. Harmless; delete with
  `git checkout main && git branch -d backup-before-merge-2026-08-02` next time that machine is
  used. Not urgent.

DO NOT merge origin/main into main again or vice versa without re-reading point 1 above — the
Layer 2/3 divergence is resolved and intentional; treating it as a normal merge conflict to
reconcile (as opposed to a deliberate historical fork) was already tried and caught before
damage was done. If `git status` on any machine ever shows unexpected divergence again, stop and
figure out why before pushing/pulling.

=============================================================================
NEXT ACTION — the LaTeX environment is BUILT. Two things block progress.
=============================================================================
Done 2026-08-02 (Day 25), committed and pushed: `Thesis_LaTeX/` exists and compiles clean
(`latexmk -pdf`, 47 pages as of 2026-08-02 evening, 0 LaTeX errors, 0 undefined refs, 0 bibtex
errors). `references.bib` holds 21 verified entries. `.gitignore` and
`.vscode/{settings,extensions}.json` are in place. Read `Thesis_LaTeX/README.md` before touching
any of it — do NOT re-derive the structure and do NOT re-run `Thesis_LaTeX/tools/` over a chapter
that has been edited since porting.

Settled this session, do not re-ask:
- Engine: pdflatex + newtx (falls back to mathptmx if newtx is absent; same metrics).
- Font size: NOT decided, and deliberately not locked. It is one commented line in `main.tex`
  (`\documentclass[12pt,...]{extbook}`). `extbook`, not `book`, because the standard classes
  cannot do 14pt. Currently sitting at 12pt as a placeholder value, not as a decision.
- Draft apparatus: `\usepackage[draft|final]{thesis-format}`. In `final`, any surviving
  `\todocite` is a HARD BUILD ERROR. This is now the enforcement mechanism for [TODO-A]/[TODO-B]
  — they cannot be forgotten. Verified: `final` currently fails on exactly those two.
- Porting rule: a chapter's `.md` in `Thesis_Documentation/` is the source of truth ONLY until it
  has a `.tex`. Chapters 3 and 4 now live in `Thesis_LaTeX/chapters/`; their `.md` files are
  frozen dated records. Edit the `.tex`.

BLOCKER 1 — RESOLVED. The official KUET template landed and the project was rebuilt against
it (commits 8ca50a9, 2ad57ab). Formatting is measured into KUET_FORMAT_SPEC.md. The book is now
SIX chapters, not seven: Introduction / Literature Review / Research Methodology / Results and
Discussion / Relation with a Real-World Problem / Conclusions and Future Works.
** Do NOT split Chapter 3. ** Under six chapters it correctly holds the whole methodology.

BLOCKER 2 — font size 12 vs 14, open since Day 7, needs the supervisor not the assistant.
KUET precedent (Masrul Khan's book) uses 12; a personal note says 14. One line, one rebuild.

Then, in rough order:
- Regenerate the Chapter 4 figures from matrix-v2 into `Thesis_LaTeX/figures/`. Highest value is
  the per-seed episodic-cost plot behind Table 4.5 — the variance finding reads far better
  graphically than as a ten-column table. The four old figures in `Thesis_Documentation/assets/`
  are WITHDRAWN (Day-19 single-seed data) and must not be used.
- Convert the ported tables. They came through pandoc as uncaptioned `longtable`s, so the List of
  Tables is empty and "Table 4.1" is bold body text rather than a real float reference.
- ~~Source [TODO-A] and [TODO-B].~~ **DONE 2026-08-02 evening.** Both resolved and verified;
  four further citations added (`stooke2020pid` and `henderson2018matters` at §4.6,
  `yoshikawa1985manipulability` into Chapter 3's cost function, plus the two literal bracketed
  numerals pandoc left as body text). `\nocite{*}` deleted. Reference list now shows 7 entries
  because 7 are cited — that is correct, not a fault; it grows as chapters land.
- Get the Board of Examiners details (members 2 and 3) into `frontmatter/approval.tex`.
- Write Chapters 1, 2, 5, 6 and the front-matter pages — all stubbed in `Thesis_LaTeX/`, all
  currently printing a red "not written yet" box. Chapter 5 (Relation with a Real-World Problem
  + SDG mapping) is the KUET-specific one that is easy to forget.
- When Chapters 1 and 2 are uncommented in `main.tex`, DELETE the `\setcounter{chapter}{2}` line
  that is currently holding Methodology at 3 and Results at 4.

Update run_log.md with a dated entry and refresh logbook/06_writing.md's "Next steps" whenever
any of the above lands.

=============================================================================
CRITICAL PATH TO 06 AUGUST — agreed 2026-08-02 evening
=============================================================================
02 Aug (done)  bibliography merged, TODO-A/B resolved, claim map written.
03 Aug         Chapter 2 (~8-10 pp, spine in 10_references.md), then Chapter 1.
04 Aug         [DONE 02 Aug] per-seed cost figure -> Thesis_LaTeX/figures/per_seed_cost.pdf,
               regenerate with Comparison_test/results/scripts/make_per_seed_cost_fig.py.
               [DONE 02 Aug] Ch4 longtables -> captioned kuettable floats; List of Tables now
               lists 2.1 and 4.1-4.5, List of Figures lists 4.1.
               REMAINING: Ch1, Ch5 (Real-World + SDG, not started), Ch6, front matter,
               and the Ch4 humanizer pass (45 em dashes).
               ** DO NOT SPLIT CHAPTER 3. ** That instruction belonged to the seven-chapter
               layout and is now WRONG. Under the six-chapter book there is no separate setup or
               implementation chapter, so Chapter 3 correctly holds the whole methodology:
               problem formulation, environment, cost function, cPPO, calibration, training and
               evaluation protocol. It is right as it stands. Splitting it would break the book.
05 Aug         Chapter 7, Chapter 5 SDG section, front matter, full build, proofread.
06 Aug         submit.

Needs Touhid, not the assistant — chase these first, they have lead time:
  - Board of Examiners members 2 and 3 (last hard-error blocker).
  - Font size 12 vs 14, open since Day 7. One line in main.tex, but if it lands on the 5th
    you are reflowing a finished book.
```
