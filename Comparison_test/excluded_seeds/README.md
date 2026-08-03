# Excluded seeds — not used in the thesis

This folder holds the raw per-run files for the seeds and runs that were **not** selected
for the thesis results. They are kept for reference, not deleted.

**Selected seeds (used in the thesis, stay in the main `results/`/`ur5_grasp/` locations):
1, 3, 4, 52, 54** — applies to all four algorithms (`ppo`, `ctrl`, `cppo`, `cppo15`), both
training and evaluation.

**Excluded seeds (moved here): 2, 5, 50, 51, 53** — all four algorithms, training and eval.

**Also moved here:** smoke-test / sanity-check runs that were never part of the 10-seed
benchmark (`simplegripper_smoke`, `smoke_ppo`, `smoke_cppo`, `smoke_sg`, `smoke_202505` etc.,
`cppo15_smoke_*`). These aren't seed results at all, so they don't belong alongside the
selected-seed data either.

## What's here

Reorganized 2026-08-02 into algorithm/seed folders, same convention as `../final_results/` and
`../ppo_redundant/` — `PPO_baseline` = `ctrl`, `CPPO_25` = `cppo`, `CPPO15` = `cppo15`, `PPO` =
the actual unmodified `ppo` (not to be confused with `PPO_baseline`, see
`../ppo_redundant/README.md`).

```
results/tb_csv/
├── PPO_baseline/seed_{2,5,50,51,53}/   (38 CSVs each, 190 total)
├── CPPO_25/seed_{2,5,50,51,53}/        (38 CSVs each, 190 total)
├── CPPO15/seed_{2,5,50,51,53}/         (38 CSVs each, 190 total)
├── PPO/seed_{2,5,50,51,53}/            (33 CSVs each, 165 total)
└── smoke_tests/                        (358 files — sanity-check runs, no algo/seed identity,
                                          left flat: simplegripper_smoke, smoke_ppo, smoke_cppo,
                                          smoke_sg, smoke_202505 etc., cppo15_smoke_*)

ur5_grasp/tools/eval_episodes/
├── PPO_baseline/seed_{2,5,50,51,53}/   (3 CSVs each, 15 total)
├── CPPO_25/seed_{2,5,50,51,53}/        (3 CSVs each, 15 total)
├── CPPO15/seed_{2,5,50,51,53}/         (3 CSVs each, 15 total)
└── PPO/seed_{2,5,50,51,53}/            (3 CSVs each, 15 total)
```

Total: 1,093 tb_csv files (735 across the 4 algorithm folders + 358 smoke) + 60 eval_episodes
files. (Corrected from an initial 1,162/804 count — see the withdrawn-batch note below.)

**Filenames kept exactly as exported**, same rule as `../final_results/training/`.

## What was NOT moved (still mixes all 10 seeds — flagged, not edited)

These aggregate documents in `results/` and `ur5_grasp/tools/` report on all 10 seeds
together and were left untouched, per instruction. They'll need to be regenerated or
manually filtered to the 5 selected seeds before being cited in the thesis:

- `results/PER_SEED_TRAINING_TABLES.md` / `.pdf` / `per_seed_training_tables.json`
- `results/MATRIX_V2_PARTIAL_3ARM.md` / `_report.pdf`
- `results/ALGORITHM_AUDIT.md`
- `results/EVAL_RESULTS_FULL.pdf`, `results/EVAL_RESULTS_SUMMARY.pdf`
- `results/SUMMARY_BANGLA.md`
- `results/LAYER1_RESULTS_eval.md`, `results/LAYER1_RESULTS_3seed.md`, `results/LAYER1_FINDINGS.md`
- `ur5_grasp/tools/eval_policy_results.csv` (one row per seed/eval combo, all 10 seeds)
- `ur5_grasp/tools/eval_policy_report.txt`, `ur5_grasp/tools/summarize_runs_report.txt`

## Related, but kept separate (different reasons, don't conflate)

- **`../withdrawn_runs/`** — not a seed-selection exclusion. The 2026-07-30 pilot batch is
  retracted as scientifically invalid (confounded results), independent of which seeds it used.
  **Correction (2026-08-02):** while building the algorithm/seed folders above, seed 2's `ppo`
  and `cppo` counts came out roughly double every other excluded seed's (66/74 vs 33/38) —
  that seed's withdrawn-batch pilot files (`ppo_s2`, `cppo_s2`, 69 files) had been sitting in
  here since the very first reorganization, missed because the batch-based filter had only been
  applied to `results/tb_csv/` before seed 2's files were already moved out of it. Moved to
  `../withdrawn_runs/` now; see that folder's README for the general lesson.
- **`../ppo_redundant/`** — not a seed-selection exclusion either. `ppo`'s files for the
  *selected* seeds (1, 3, 4, 52, 54), pulled out because `ppo` is bitwise-identical to `ctrl`.

## Not covered by this reorganization

Raw `rsl_rl` training logs and model checkpoints (`logs/rsl_rl/...`, referenced by
`eval_policy_results.csv`) are not present in this repo — they live only on the lab PC and
are gitignored. This reorganization only covers the exported result files present here.

Reorganized 2026-08-02. See `../final_results/README.md` for the folder to actually work from.
