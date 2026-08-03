# Withdrawn runs — do not use, do not cite

This is not "excluded" data in the seed-selection sense; it is **retracted**. Kept only for
audit-trail purposes.

## What's here

`results/tb_csv/` — 207 TensorBoard CSVs from the **2026-07-30 pilot batch**: `ppo_s1`,
`ppo_s2`, `ppo_s3`, `cppo_s1`, `cppo_s2`, `cppo_s3` (6 runs, seeds 1/2/3 only, no `ctrl`/
`cppo15` arms existed yet).

**Correction (2026-08-02, same day):** the `s2` pair (`ppo_s2`, `cppo_s2`, 69 files) was
initially missed and sat inside `../excluded_seeds/results/tb_csv/` for a few hours, because
seed 2 is also a non-selected seed — it got swept there by the *seed*-based filter before the
*batch*-based filter caught it. Found and moved here while reorganizing `excluded_seeds/` into
algorithm/seed folders (the even per-seed file counts didn't match: seed 2 had 66 `ppo` files
where every other excluded seed had 33). Same lesson as below, generalized: **the withdrawn
batch must be filtered out by run timestamp before *any* other split (by seed, by algorithm,
by anything) — filtering by one axis alone will not catch it if the batch overlaps that axis.**

## Why

Per `logbook/09_comparison_test.md` ("Day 23, LATE — THE 2026-07-30 MATRIX IS WITHDRAWN"): an
algorithm audit (`results/ALGORITHM_AUDIT.md`) found the cPPO-vs-PPO comparison in this batch
confounded. `Loss/cost_lambda` sat at 0.0 for nearly every iteration of every cPPO run, so the
Lagrangian constraint was algebraically inert — the entire measured gap was actually a global
`clip_grad_norm_` spanning the cost critic quietly shrinking the actor's step in the cPPO arm
only. Separately, `cost_limit=25` sat above the converged natural cost, so the constraint never
bound even if it had been active. The logbook is explicit: **"Do not quote any number from
`results/LAYER1_RESULTS_3seed.md` or `results/LAYER1_FINDINGS.md`."**

The real benchmark was rerun from scratch on 2026-08-01 (the "matrix-v2" batch, tag
`matrix-v2`/`matrix-v2-cppo15`, commits `567e4c0`/`684c595`) with a bug fix, a `ctrl` arm added
to isolate the artifact, and 10 seeds. **That is the only valid data.** It lives in
`../results/tb_csv/` (source) and `../final_results/training/` (clean copy, 5 selected seeds).

## Note on why this matters for file management

These files share filenames-by-seed-number with the valid Aug-1 runs (e.g. both batches have a
`..._ppo_s1__...` run), distinguished only by the date/time prefix. Before this cleanup they sat
in the same folder as the valid data — any script or person filtering `results/tb_csv/` by seed
number alone (as the seed-selection reorganization on 2026-08-02 initially did) would have
silently pulled in both the retracted and the valid run for seeds 1 and 3. Moved out here on
2026-08-02 specifically to close that risk.

Withdrawn 2026-07-31 (Day 23), quarantined into this folder 2026-08-02.
