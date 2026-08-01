# Next-session prompt — `cppo15` arm (cost_limit = 15)

Written 2026-08-01 (Day 24, cont.). Paste the block below into a new Cowork chat with this folder
connected. Everything above the line is context for you, not for the prompt.

**Why 15 and not 10 — have this ready, it is the first thing a supervisor will ask.**
`ALGORITHM_AUDIT.md` §A2 justified `cppo10` as "below the natural cost on every observed seed",
but that was written against 3 seeds. Against the 10-seed data in `MATRIX_V2_PARTIAL_3ARM.md`
§4.1, `ctrl`'s natural costs are 102.1, 7.7, 162.3, 30.0, 19.1, 8.6, 1.8, 106.9, 18.8, 7.9.
A budget of **15 binds on 6 of 10 seeds** (1, 3, 4, 5, 52, 53) and is slack on 4 (2, 50, 51, 54).
A budget of **10 binds on exactly the same 6 seeds** and is slack on the same 4 — the partition is
identical. So 10 would *not* have met its own stated criterion either; only a budget below 1.8
binds on every seed, and that is far below the achievable operating point. **15 and 10 differ in
depth of bind, not in breadth.** That makes 15 a defensible replacement rather than a weakening,
and it should be recorded as a deviation from the registered design *with this reasoning*, not
silently substituted.

---

## PROMPT — copy from here

Continuing the UR5e safe-RL thesis. This session runs the binding-budget arm that the whole
comparison has been building toward.

Read first, in this order:

1. `logbook/00_INDEX.md`, then `logbook/09_comparison_test.md` — the Day-24 EXECUTION STATUS
   pick-up block, including the two notes appended to it about the λ retraction and the 164.5 vs
   162.3 discrepancy.
2. `Comparison_test/results/MATRIX_V2_PARTIAL_3ARM.md` — source of truth for the completed 3-arm
   batch. Note §4.1 now carries a dated correction about λ.
3. `Comparison_test/results/ALGORITHM_AUDIT.md` — §A2 (why a binding budget was needed) and §4
   (the registered arm design and what each comparison is licensed to claim).
4. `Comparison_test/RUN_CHECKLIST_v2.md` — the 9-step protocol. We are re-entering it at Step 6.
5. `run_log.md` — the two Day-24 entries.

### Decision already made — do not re-open, but do record it properly

The pre-registered `cppo10` arm is **replaced by a `cppo15` arm at `cost_limit = 15`**, trained on
**all 10 seeds (1-5 and 50-54)** to match the existing batch. This is a deviation from
`ALGORITHM_AUDIT.md` §4's registered design and must be written down as one, with this
justification, before the arm runs:

> §A2 justified `cost_limit = 10` as "below the natural cost on every observed seed", measured
> against 3 seeds. Against the 10-seed data (`MATRIX_V2_PARTIAL_3ARM.md` §4.1), a budget of 15
> binds on 6 of 10 seeds (1, 3, 4, 5, 52, 53) and is slack on 4 (2, 50, 51, 54). A budget of 10
> binds on exactly the same 6 and is slack on the same 4 — the partition is identical, so 10 would
> not have met its own criterion either. Only a budget below 1.8 binds on every seed, which is far
> below the achievable operating point. 15 and 10 differ in depth of bind, not breadth.

Verify that arithmetic against §4.1's table yourself before writing it anywhere — do not take my
word for it. If it does not hold, stop and tell me before running anything.

**Push back if you think 10 is still the better choice given what you find.** I would rather change
my mind now than defend an arbitrary-looking number at the viva.

### The work

1. **Create the arm.** New agent entry point `rsl_rl_cppo15_cfg_entry_point`, differing from the
   existing `cppo` cfg by `cost_limit` **only** — 15 instead of 25. Nothing else. The whole design
   depends on each arm differing from its neighbour by exactly one variable; check this by
   diffing the two cfg files and show me the diff before training. Update the inline comment on
   `cost_limit` the same way the Day-24 recalibration did: recheck, old value, new value, reason,
   source run.

2. **Freeze.** The env must not change. Confirm the working tree matches tag `matrix-v2` apart
   from the new cfg, commit, and tag (`matrix-v2-cppo15` or similar). If anything else has drifted
   since `567e4c0`, stop and tell me what.

3. **Smoke first.** 50 iterations, seed 1, before committing to 10 full runs. Confirm
   `Loss/cost_lambda` actually departs from 0 — at a budget of 15 on seed 1 (natural cost 102.1)
   it must. If λ stays at 0 through the smoke, something is wrong with the entry point and the
   full matrix must not launch.

4. **Train.** 10 seeds (1-5, 50-54), 1500 iterations, `num_envs = 4096`, from
   `Comparison_test/` as cwd. Verify all 10 checkpoints on disk, not clean logs.

5. **Log λ per iteration this time.** The last batch recorded only final λ, which is why §4.1 had
   to be retracted. Extract the full `Loss/cost_lambda` trajectory for every seed from the event
   files as part of this run, not afterward. **Also extract it retrospectively for the existing
   `cppo` (budget 25) runs** — that closes the open item from Day 24 and lets the two budgets be
   compared as trajectories rather than endpoints.

6. **Evaluate** on the same protocol as the last batch so the numbers are comparable: eval seeds
   101/102/103, 1000 episodes each, `num_envs = 128`, deterministic policy. Do not reuse
   `run_eval_matrix_v2_3arm.sh` unmodified — it is scoped to 3 arms. Before touching
   `eval_policy_results.csv`, remember it is append-only and already carried 20 stale rows once;
   filter by checkpoint path date, never by label.

7. **Report** in a new `Comparison_test/results/` file, in the same shape as
   `MATRIX_V2_PARTIAL_3ARM.md`. Lead with `cppo15` vs `ctrl` — per `ALGORITHM_AUDIT.md` §4 this,
   and only this, is the licensed safe-RL claim, and it is the first time this project has been
   in a position to make it. Report per-seed cost as a table like §4.1, because the variance
   finding is per-seed. The key questions: does a binding budget tighten the 9.5-24.1 band
   further, or was 25 already doing the work? Does it cost task performance where 25 did not?
   Does it finally reduce the *worst-case* manipulability depth, which 25 did not?

8. **Update the thesis chapter.** `Thesis_Documentation/Results_Chapter_Layer1.md` §4.3 and §4.7
   currently state the pre-registered safe-RL claim as unanswered. If this arm answers it, those
   sections change substantially — do not just append a paragraph.

9. **Track it.** Update `logbook/09_comparison_test.md` and add a dated `run_log.md` entry, per
   the convention in `CLAUDE.md`.

### Rules

- Do not introduce any number that is not in the run data or in
  `MATRIX_V2_PARTIAL_3ARM.md`. Ask me before assuming one.
- `sac` stays out of scope this session unless the training finishes early and I say otherwise.
- The 3 superseded pre-audit `cppo_s1/s2/s3` run dirs in `logs/rsl_rl/ur5e_lift_cppo/` are still
  sitting there under the same labels as the good runs. Archive them **before** training anything
  new, so the new arm is not landing beside two generations of stale runs.
- Push back if anything in the results reads as overclaiming past what the data supports —
  especially if `cppo15` comes out indistinguishable from `cppo`, which is a real possibility and
  is a perfectly good result. A null here means a budget of 25 was already sufficient, and that is
  worth reporting plainly rather than rescuing.

## PROMPT — copy to here
