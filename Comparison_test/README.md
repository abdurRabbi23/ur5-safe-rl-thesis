# Comparison Test

This folder is a self-contained redo of the Layer 1 4-algorithm benchmark. TD3 was CUT on 2026-07-31 (Day 23); the comparison is PPO, cPPO, SAC.
Full context, current status, and exact commands: `../logbook/09_comparison_test.md`.

Quick orientation:
- `ur5_grasp/` — working copy of the frozen env code (from the main folder's `layer1-env-freeze`
  tag). Train against this copy, not the main folder's.
- `logs/` — NOT created yet. Appears automatically the first time you train, as
  `logs/rsl_rl/<experiment_name>/<timestamp>_<run_name>/`. This is where real run data lives.
- `configs/` — (unused — skrl YAMLs live in ur5_grasp/tasks/lift/agents/, see Day 22 evening)
- `results/` — results table + figures; `results/scripts/make_layer1_figs.py` is a starting point,
  still scoped for 2 series (needs extending to 4 + seed bands).
- `runs/` — leftover placeholder, not used. Ignore.
- `excluded_seeds/` — raw per-run files for the 5 seeds (2, 5, 50, 51, 53) and smoke-test runs
  NOT used in the thesis, moved out of `results/tb_csv/` and `ur5_grasp/tools/eval_episodes/`
  on 2026-08-02. The thesis uses only seeds 1, 3, 4, 52, 54. See `excluded_seeds/README.md`.
- `withdrawn_runs/` — the 2026-07-30 pilot batch, **retracted as invalid** (confounded by a
  gradient-clip bug, not just unselected). See `withdrawn_runs/README.md`.
- `ppo_redundant/` — `ppo`'s raw files for the 5 selected seeds, pulled out because `ppo` and
  `ctrl` are bitwise-identical policies; `ctrl` (labeled "PPO (baseline)" in the thesis) stands
  in for it everywhere. See `ppo_redundant/README.md`.
- `final_results/` — **the only folder used to generate thesis results.** `training/` (tb_csv
  exports) + `evaluation/` (per-episode eval CSVs), filtered to exactly 3 algorithms (`ctrl`,
  `cppo`, `cppo15`) × 5 seeds (1, 3, 4, 52, 54). See `final_results/README.md` — read this one
  first if you're generating a figure or table.

Always run commands with this folder's path quoted (it has a space in the name).
