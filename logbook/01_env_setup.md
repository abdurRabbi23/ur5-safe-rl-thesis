# Module 01 — Environment Setup & RL Validation

Status: ✅ done
Chat type: environment / infra
Last updated: 2026-07-12 (Day 7)

## Goal
Working Isaac stack on the lab PC + a validated RL training loop before any task work.

## Current state — done
- Frozen stack: Isaac Sim 5.0.0 · Isaac Lab release/2.3.0 · Python 3.11 conda `isaaclab`
  · PyTorch 2.7.0+cu128 (Blackwell/RTX 5090, sm_120) · driver 580.
- Validated RL loop end-to-end: Cartpole (converged ~150 iters), Franka-Reach (reward
  climbs, TensorBoard reaches laptop). num_envs sweet spot ~8192 for Reach.

## Key facts / gotchas
- Headless-first: train `--headless`, monitor via TensorBoard; GUI only for debugging.
- `TiledCamera` hangs on Blackwell → use `Camera`.
- Session start: `conda activate isaaclab`; `sudo cpupower frequency-set -g performance`;
  run in tmux.
- Nucleus asset library is version 5.1 (assets), stack sim is 5.0 — fine.

## Next steps
- None. Foundation complete; work moved to Module 02.

## run_log.md refs
Day 1–6.
