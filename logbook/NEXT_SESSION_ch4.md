# NEXT SESSION — Chapter 4 (Results and Discussion)

## ✅ DONE 2026-08-03, same evening. This file is a record, not a task list.

Touhid asked for the work to be done immediately rather than in a later session, so all of
items A to J below were carried out. See `run_log.md` "Day 26, night" for what changed and what
the recomputation did to the principal finding. The chapter now builds clean at pp. 61–73.

Two scripts were written and are the reproduction path for every number:
`Comparison_test/results/scripts/summarize_final.py` and `make_ch4_figs.py`.

**Still open after that pass:** the SAC arm was never trained (a genuine limitation, stated as
one); Chapter 3 §3.8 still calls the singularity term "the operative constraint" against its own
Table 3.9; Chapter 2 §2.2 still overlaps Chapter 1 §1.2; Chapters 5 and 6 are stubs; the six
examiner-name TODOs in `frontmatter/approval.tex` still block the `[final]` build.

## ⚠️ 2026-08-04 — figure work landed on top of this pass. Rule 7 below is WITHDRAWN.

Chapter 4's prose is unchanged and still correct; only figures were added. What changed:

- **Rule 7's "no colour" clause no longer applies to figures** (it still applies to prose: no
  boxes, no background tint). Touhid asked for a colour scheme on 2026-08-04 and chose to
  recolour Chapter 2 to match rather than keep the book split. Fixed palette: `ctrl` red
  `#D11A1A`, `cppo` blue `#1257A8`, `cppo15` green `#17803D`, applied book-wide.
  **Do not revert figures to black line art without asking.** Full note:
  `Thesis_LaTeX/figures/README.md`.
- **Chapter 4 now has 11 figures, not 2** (4.1 to 4.11). All from one script,
  `Comparison_test/results/scripts/make_final_results_figs.py`.
- **`make_ch4_figs.py` is superseded** and must not be re-run: it would overwrite
  `per_seed_cost.pdf` and `lambda_traj.pdf` with the black-line-art versions.
- Figures render in **true Times New Roman** loaded from `Thesis_LaTeX/fonts/`, which is
  gitignored for licensing. A clone without those files falls back to Liberation Serif and says
  so on stdout.
- Build re-verified: exit 0, 86 pages, 0 errors, 0 undefined references, em-dash count still 0.

---

Original brief, written 2026-08-03 (Day 26) after the Chapter 2 reconciliation pass, kept for
the record.

```
Read logbook/00_INDEX.md, then CLAUDE.md's "Results scope" section, then THIS file's context
below. Note that 00_INDEX's "Current status" is STALE and that logbook/HANDOFF.md predates the
Chapter 3 rewrite. This file is the current word on Chapter 4.

=============================================================================
THE JOB
=============================================================================
Re-derive Thesis_LaTeX/chapters/04_results.tex from scratch against the locked scope.
This is NOT a wording pass. Every number, the arm naming, the seed count and the principal
finding of Section 4.6 are all out of date and must be recomputed from the CSVs.

Success criterion: every numeral in Chapter 4 is reproducible by re-running a script in
Comparison_test/results/scripts/ against Comparison_test/final_results/, and Chapter 4 contains
no reference to ten seeds, to seeds 2/5/50/51/53, or to MATRIX_V2_PARTIAL_3ARM.md.

=============================================================================
WHAT IS WRONG WITH THE CURRENT CHAPTER
=============================================================================
04_results.tex (555 lines, fully drafted) was ported from a now-superseded source. Specifically:

1. SEEDS. It reports ten seeds (1-5, 50-54). The locked scope is FIVE: 1, 3, 4, 52, 54.
   Seeds 2, 5, 50, 51 and 53 are excluded and must be treated as if never run.

2. ARMS. It reports ppo / ctrl / cppo. The locked scope is THREE arms:
       ctrl    -> labelled "PPO (baseline)" in all thesis text and figures
       cppo    -> d = 25
       cppo15  -> d = 15
   The plain ppo arm is dropped as redundant (checkpoint-hash-verified byte-identical to ctrl).
   *** cppo15 IS COMPLETELY ABSENT FROM CHAPTER 4. An entire arm, 5 of the 15 trained
   policies, is missing from the results chapter. ***

3. SOURCE. Its draftnote names Comparison_test/results/MATRIX_V2_PARTIAL_3ARM.md as the source
   of truth. That file is superseded. The only permitted source is
   Comparison_test/final_results/{training,evaluation}/.

4. THE PRINCIPAL FINDING IS BUILT ON EXCLUDED SEEDS. Section 4.6 says "on six of the ten seeds
   --- 2, 5, 50, 51, 53 and 54 --- the constrained agent's episodic cost is HIGHER". Four of
   those six are excluded seeds. The "band is entered from both directions" claim, the
   ninety-fold spread, the two-and-a-half-fold band and the tenfold variance collapse must ALL
   be recomputed on the five surviving seeds before a word of that section is kept. The
   qualification may strengthen, weaken or reverse. Do not assume it survives.

5. EPISODE COUNTS. Every "30,000 evaluation episodes per arm" is now 15,000
   (5 training seeds x 3 evaluation seeds x 1000 episodes). "Thirty trained policies" is now 15.

6. EM DASHES. 44 instances, the highest in the book, and this is the chapter an examiner reads
   hardest. See logbook/11_writing_style.md for why this needs a deliberate supervised pass
   with the results open, not a cleanup sweep.

=============================================================================
WHAT THE DATA ACTUALLY SUPPORTS — verified on disk 2026-08-03
=============================================================================
Comparison_test/final_results/
  training/{PPO_baseline,CPPO_25,CPPO15}/seed_{1,3,4,52,54}/   38 metric CSVs each
  evaluation/{PPO_baseline,CPPO_25,CPPO15}/seed_{1,3,4,52,54}/ 3 CSVs each (eval seeds 101/2/3)

Evaluation CSVs are PER-EPISODE, 1000 rows each, with columns:
  goal_dist_final, obj_z_final, lift_max_z, goal_z, lift_rel, lift_rel_ever, lift_abs,
  sing_frac, joint_frac, coll_frac, min_w, cost_sum, ep_len
So every safety and task number in Tables 4.3 and 4.4 is recomputable directly, WITH per-seed
dispersion, which the current chapter says is unavailable for the task rates. It is available.

*** BIGGEST WIN AVAILABLE: cost_lambda.csv EXISTS for every constrained seed. ***
Chapter 4's Limitation 2 currently says the "lambda engaged then relaxed" reading is "a
deduction from the converged costs, not a measurement". It can now be measured. Verified peaks:
    cppo  (d=25): seed 1 peak 15.84, seed 3 peak 40.46, seed 4 peak 30.30,
                  seed 52 peak 46.32, seed 54 peak 48.05 — all relax to 0.000 at the last step
    cppo15 (d=15): peaks 17.62 / 35.47 / 40.83 / 27.13 / 38.56, four of five relax to 0,
                  seed 1 ends at 0.0528
This converts a deduction into direct evidence, and it is exactly the dual-ascent
engage-and-overshoot behaviour Chapter 2 Section 2.5 sets up via Stooke et al. Plot it.

=============================================================================
WORK LIST, IN ORDER
=============================================================================
A. Write ONE summarisation script under Comparison_test/results/scripts/ that reads
   final_results/ and emits every table in the chapter, per-arm and per-seed. Do not hand-copy
   numbers. Existing scripts (summarize_eval.py, make_per_seed_tables.py,
   make_per_seed_cost_fig.py) predate the scope lock — check what each reads before reusing it.

B. Rebuild Tables 4.1 to 4.5 with three arms and five seeds. Table 4.5 goes from ten columns to
   five. Add per-seed dispersion to the task table, which the data supports and the current
   chapter wrongly says it does not.

C. Re-derive Section 4.6 from the new per-seed numbers. Then rewrite it. The direction of the
   "both directions" qualification is an empirical question now, not a known one.

D. ADD cppo15 THROUGHOUT. It is the budget-sensitivity arm. Chapter 2 Section 2.11 now promises
   it as Gap 3 ("one budget only") and Table 2.5 says Chapter 4 answers it. Chapter 4 currently
   does not. Either deliver the d=25 against d=15 comparison or change the Chapter 2 promise;
   do not leave them contradicting.

E. Rewrite Limitation 1. It says the pre-registered binding-budget arm (cppo10) is absent. With
   a natural episodic cost near 105 on the baseline, d = 15 IS an actively binding budget on
   every seed, so cppo15 substantially answers the claim the chapter says is unanswered.

F. Convert Limitation 2 into a result using cost_lambda.csv, with a lambda-trajectory figure.
   Cite stooke2020pid there, as Chapter 2 Section 2.5 sets up.

G. Regenerate figures/per_seed_cost.pdf from the five-seed data and rewrite its caption. The
   current caption asserts "Six of the ten seeds finish higher under the constraint".

H. Fix the 33.7 % sourcing note. That number now lives in Chapter 3's calibration table
   (Section 3.9, tab:m-calib), so cite Chapter 3 rather than a logbook entry. The
   "Draft notes for revision" draftonly block at the end can then be deleted.

I. Humanizer pass, supervised, with the results open. 44 em dashes. Verify
   grep -c -- '---' returns 0 and no unicode dashes survive.

J. Full latexmk build. Confirm 0 errors, 0 undefined citations or references, and that
   Chapter 2's forward references into Chapter 4 (sec:r-validity, sec:r-variance,
   sec:r-safety, sec:r-limits, sec:r-design) all still resolve.

=============================================================================
RULES THAT GOVERN THIS CHAPTER
=============================================================================
1. CLAUDE.md "Results scope" is binding: final_results/ only, 5 seeds, 3 arms, ctrl labelled
   "PPO (baseline)" with the one-time footnote pointing at ppo_redundant/README.md.
2. The 2026-07-30 pilot batch is RETRACTED, not merely unselected. Never cite it.
3. Humanizer rule is mandatory on all thesis prose (logbook/11_writing_style.md). Em dashes are
   cut; numeric ranges (pp. 483--498) are kept. PERSONALITY AND SOUL does not apply to a thesis.
4. Do not cite anything absent from the claim map in logbook/10_references.md.
5. Never cite khan2026 as the origin of PPO-Lagrangian. ray2019 is the origin.
6. Formatting: Times New Roman 12, justified, 1.25 spacing, tables and figures centred with
   centred captions. Table captions above, figure captions below (kuettable / kuetfigure).
7. NO COLOUR AND NO BOXES in chapter prose — set 2026-08-03. Black text only, no frames, no
   background tint. Table hline rules are fine.

=============================================================================
ALSO OPEN, SMALL, DO IF TIME ALLOWS
=============================================================================
- Chapter 3 Section 3.8 calls the singularity term "the operative constraint of this thesis",
  which contradicts its own Table 3.9 (joint limit ~86 % of realised cost, singularity ~14 %).
  Chapter 2 Section 2.9 was hedged on 2026-08-03; Chapter 3 was left alone. Hedge it the same way.
- Chapter 2 Section 2.2 still overlaps Chapter 1 Section 1.2 closely. Trim one of them.

=============================================================================
STATE OF THE BOOK, 2026-08-03 EVENING
=============================================================================
Build: latexmk exit 0, 78 pages, 0 errors, 0 undefined citations or references.
  Ch 1 Introduction        pp. 14-20   done
  Ch 2 Literature Review   pp. 21-39   done, reconciled against Ch 3
  Ch 3 Methodology         pp. 40-60   done (expanded separately, five seeds, three arms)
  Ch 4 Results             pp. 61-73   ** THIS JOB — stale, ten seeds, missing an arm **
  Ch 5 Real-World Relation pp. 74      stub
  Ch 6 Conclusion          pp. 75      stub

DEADLINE: submission 06 August, defence 08 August.
```
