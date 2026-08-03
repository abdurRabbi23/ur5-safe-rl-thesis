# Final results — the ONLY data used for this thesis

**Working rule (set 2026-08-02): all thesis analysis, tables, and figures are generated from
this folder, and only this folder. Do not read `results/tb_csv/` or
`ur5_grasp/tools/eval_episodes/` directly when producing something that goes in the thesis —
those still hold data outside scope (see below); this folder is the filtered, safe-to-use
copy.** Treat the excluded seeds, the withdrawn batch, and the redundant `ppo` arm as if they
had never been trained or evaluated.

- `training/` — 570 TensorBoard scalar CSVs, organized as
  `training/<algo_folder>/seed_<N>/<original_filename>.csv` (reorganized 2026-08-02 for
  browsability; moved, not copied, out of the old flat layout):
  ```
  training/
  ├── PPO_baseline/   (= ctrl runs)
  │   ├── seed_1/    (38 CSVs, one per metric)
  │   ├── seed_3/
  │   ├── seed_4/
  │   ├── seed_52/
  │   └── seed_54/
  ├── CPPO_25/        (= cppo runs, cost_limit=25)
  │   └── seed_{1,3,4,52,54}/  (38 CSVs each)
  └── CPPO15/         (= cppo15 runs, cost_limit=15)
      └── seed_{1,3,4,52,54}/  (38 CSVs each)
  ```
  Filenames were kept exactly as exported (e.g.
  `2026-08-01_01-56-53_cppo_s1__Train__mean_reward.csv` lives under `CPPO_25/seed_1/`) — the
  algorithm/seed is now redundant with the folder path but the run timestamp is still useful,
  so nothing was renamed, only moved.
- `evaluation/` — 45 per-episode evaluation CSVs, same `<algo_folder>/seed_<N>/` layout as
  `training/` (reorganized 2026-08-02, moved not copied):
  ```
  evaluation/
  ├── PPO_baseline/seed_{1,3,4,52,54}/  (3 CSVs each — one per eval seed 101/102/103)
  ├── CPPO_25/seed_{1,3,4,52,54}/       (3 CSVs each)
  └── CPPO15/seed_{1,3,4,52,54}/        (3 CSVs each)
  ```
  Filenames unchanged (`<algo>_s<seed>_seed<eval_seed>.csv`, e.g. `cppo_s1_seed101.csv` under
  `CPPO_25/seed_1/`).

**Scope: 3 algorithms × 5 seeds.**
- Seeds: **1, 3, 4, 52, 54** only.
- Algorithms: **`ctrl`, `cppo`, `cppo15`** only. `ppo` is deliberately excluded — it is
  bitwise-identical to `ctrl` (see `../ppo_redundant/README.md`), so `ctrl` stands in for it.
  **In thesis text/figures, label the `ctrl` arm "PPO (baseline)"**, with a one-time footnote
  pointing back to that README so the relabeling is traceable.

## Not included here, and why

- **`../excluded_seeds/`** — seeds 2, 5, 50, 51, 53 (all 4 algorithms) + smoke-test runs. Not
  selected for the thesis.
- **`../withdrawn_runs/`** — the 2026-07-30 pilot batch (`ppo_s1`/`s2`/`s3`, `cppo_s1`/`s2`/`s3`).
  **Retracted as scientifically invalid** (confounded by a gradient-clipping bug — see that
  folder's README). Never valid data, regardless of seed selection. None of its seeds (1, 2, 3)
  fully overlap the thesis's selected seeds anyway (only seed 1 and 3 do, and those are the
  valid Aug-1 reruns, not this batch) — but it's flagged here because a script filtering by
  seed number alone could otherwise pull it in by mistake.
- **`../ppo_redundant/`** — `ppo`'s raw files for the 5 selected seeds. Kept for audit trail;
  `ctrl` is used in its place everywhere.
- Aggregate documents that still mix in all of the above — `PER_SEED_TRAINING_TABLES.*`,
  `MATRIX_V2_PARTIAL_3ARM.*`, `ALGORITHM_AUDIT.md`, `EVAL_RESULTS_*.pdf`,
  `eval_policy_results.csv`, etc. — were intentionally left as-is, not filtered. Do not quote
  numbers from them; regenerate the equivalent table from `training/`/`evaluation/` instead.

## Note

This is a **copy**, not the source of truth. `results/tb_csv/` and
`ur5_grasp/tools/eval_episodes/` remain the originals (also already filtered down to the same
3 algorithms × 5 seeds as of 2026-08-02). If a run is regenerated or re-exported, re-copy it
here too, or this folder goes stale.

**Asymmetry to be aware of:** `ur5_grasp/tools/eval_episodes/` (the evaluation source) was
also reorganized into the same `<algo_folder>/seed_<N>/` structure on 2026-08-02. `results/
tb_csv/` (the training source) was deliberately left flat — only its `final_results/training/`
copy got the folder structure. If that inconsistency ever becomes a problem, it's a one-line
ask to fix, not a redesign.

Created 2026-08-02. Scope tightened 2026-08-02 (ppo dropped, withdrawn batch removed).
Reorganized into algo/seed folders 2026-08-02 (training first, evaluation same day).
