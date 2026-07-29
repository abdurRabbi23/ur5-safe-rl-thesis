# Comparison Test

This folder is a self-contained redo of the Layer 1 4-algorithm benchmark (PPO, SAC, TD3, cPPO).
Full context, current status, and exact commands: `../logbook/09_comparison_test.md`.

Quick orientation:
- `ur5_grasp/` — working copy of the frozen env code (from the main folder's `layer1-env-freeze`
  tag). Train against this copy, not the main folder's.
- `logs/` — NOT created yet. Appears automatically the first time you train, as
  `logs/rsl_rl/<experiment_name>/<timestamp>_<run_name>/`. This is where real run data lives.
- `configs/` — skrl YAML configs (SAC/TD3/PPO-bridge) go here once written.
- `results/` — results table + figures; `results/scripts/make_layer1_figs.py` is a starting point,
  still scoped for 2 series (needs extending to 4 + seed bands).
- `runs/` — leftover placeholder, not used. Ignore.

Always run commands with this folder's path quoted (it has a space in the name).
