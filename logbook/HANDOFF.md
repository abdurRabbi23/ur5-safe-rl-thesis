# HANDOFF — paste this into a new session

Updated 2026-08-02 (Day 25, late evening). Overwrite whenever the next action changes.

> **READ FIRST — bibliography is DONE, Chapter 2 is UNBLOCKED (2026-08-02 evening).**
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
> **The only remaining hard-error blocker in the whole book** is six `\todo{}` markers in
> `frontmatter/approval.tex` — name/designation/department for Board of Examiners members 2
> and 3. `[final]` fails on exactly those and nothing else.
>
> SUBMISSION IS 06 AUGUST. Chapters 3 and 6 are written. 1, 2, 4, 5, 7 are stubs.

```
Read logbook/00_INDEX.md first for project background, but note its "Current status" section is
STALE — last dated Day 19/23. Everything below post-dates it and is the real current state.
Then read this whole block before doing anything.

=============================================================================
STATE — TRAINING IS OVER. Thesis is now in pure writing/formatting phase.
=============================================================================
Decision made 2026-08-02: no further training runs. The matrix-v2 partial batch (commit
567e4c0, tag matrix-v2 — ppo/ctrl/cppo, 10 seeds each, 30,000 eval episodes/arm) is the FINAL
experimental result set for this thesis. The two pre-registered arms that were never trained,
cppo10 (actively-binding budget) and sac (off-policy comparison), are CUT — not paused, cut.
Do not suggest running them. The results write-up already states this as Limitation #1
(Thesis_Documentation/Results_Chapter_Layer1.md §4.7) — that limitation is now permanent, not
provisional.

Full results + provenance: Thesis_Documentation/Results_Chapter_Layer1.md.
Open citation placeholders in that chapter, still unresolved: [TODO-A] (Yoshikawa manipulability
measure, needed at §4.5) and [TODO-B] (PPO-Lagrangian / constrained policy optimisation, needed
at §4.1). Source both before submission — see logbook/06_writing.md.

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
(`latexmk -pdf`, 34 pages, 0 LaTeX errors, 0 undefined refs, 0 bibtex errors). Chapters 3 and 4
are ported from the Markdown drafts. `references.bib` is seeded. `.gitignore` and
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

BLOCKER 1 — the official KUET .cls/.sty is still not in the repo. Touhid said he would attach it
and the session ended before he did. Everything in `Thesis_LaTeX/thesis-format.sty` and
`frontmatter/titlepage.tex` is a stand-in built from logbook/06_writing.md + 08_project_context.md.
`thesis-format.sty` is the single swap point — main.tex and chapters/*.tex are written so they
should not need to change when the real template arrives. ASK FOR THE FILE FIRST.

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
04 Aug         split Chapter 3 -> 3/4/5; per-seed cost figure; longtables -> captioned floats.
05 Aug         Chapter 7, Chapter 5 SDG section, front matter, full build, proofread.
06 Aug         submit.

Needs Touhid, not the assistant — chase these first, they have lead time:
  - Board of Examiners members 2 and 3 (last hard-error blocker).
  - Font size 12 vs 14, open since Day 7. One line in main.tex, but if it lands on the 5th
    you are reflowing a finished book.
```
