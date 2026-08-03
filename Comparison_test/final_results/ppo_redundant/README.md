# ppo — redundant, not a separate arm

`ppo` and `ctrl` are **bitwise-identical policies**, checkpoint-hash-verified: all 68 actor and
reward-critic tensors byte-for-byte equal, on all 10 trained seeds, confirmed independently
again at evaluation time (`../results/MATRIX_V2_PARTIAL_3ARM.md` §2,
`logbook/09_comparison_test.md` Step 7). This is expected, not a bug: `ctrl` is a Lagrangian
run with the cost multiplier pinned to 0, which is algebraically identical to stock PPO — it
exists specifically to *also* log `Loss/mean_episode_cost` and the `safety/*` cost channels,
which the plain PPO runner never writes.

## Decision (2026-08-02)

Going forward, **`ppo` is dropped as a separate arm.** The benchmark is `ctrl` / `cppo` /
`cppo15`. `ctrl`'s numbers (reward, safety, everything) are used everywhere `ppo`'s would have
been, including `mean_episode_cost`, which `ppo` never logged in the first place.

**In the thesis text and figures, `ctrl` is labeled "PPO (baseline)"** — it *is* the PPO
policy, just run through the instrumented Lagrangian-at-λ=0 path so the cost metrics exist.
Say so once in the Methods section (this file is that justification) so an examiner comparing
against the raw files isn't confused by a "ctrl" column that's actually reported as "PPO."

## What's here

Moved out of the working set on 2026-08-02, kept for the audit trail — **not deleted, but not
used**. Organized 2026-08-02 into algorithm/seed folders for browsability, same convention as
`../final_results/training/`:

```
results/tb_csv/PPO/seed_{1,3,4,52,54}/            (33 CSVs each, 165 total)
ur5_grasp/tools/eval_episodes/PPO/seed_{1,3,4,52,54}/   (3 CSVs each, 15 total)
```

**Note on the folder name:** this is called `PPO` (not `PPO_baseline`) deliberately —
`PPO_baseline` is reserved elsewhere (`../final_results/`, `../excluded_seeds/`) for `ctrl`,
which is what's actually reported as "PPO (baseline)" in the thesis. This folder holds the
real, unmodified `ppo` runs that are *not* used, so it gets the plain name to avoid the two
being confused with each other.

`ppo` runs for the 5 non-selected seeds (2, 5, 50, 51, 53) are in `../excluded_seeds/` instead,
grouped there with the other excluded-seed data, not here.

Created 2026-08-02. Reorganized into algo/seed folders 2026-08-02.
