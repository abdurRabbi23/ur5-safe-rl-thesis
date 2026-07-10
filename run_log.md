# UR5 Safe RL Grasping — Run Log

## Session-start checklist (every NoMachine session)
- `conda activate isaaclab`  (fresh terminals open in base)
- `sudo cpupower frequency-set -g performance`  (governor resets on reboot)
- Launch training/TensorBoard inside tmux so a dropped connection doesn't kill runs

## Day 1 — Machine prep + compatibility check
- Lab PC: i9, 64 GB, RTX 5090 (Blackwell sm_120), driver 580.159.03.

## Day 2 — Stack install + validation
- Frozen stack: Isaac Sim 5.0.0 · Isaac Lab release/2.3.0 · Python 3.11 conda env `isaaclab` · PyTorch 2.7.0+cu128 (torchvision 0.22.0, torchaudio 2.7.0) · numpy 1.26.0.
- Validated: torch sees RTX 5090 (no sm_120 warning); Isaac Sim GUI launches over NoMachine; headless smoke test create_empty.py --headless printed "Setup complete", no traceback.
- Gotcha: TiledCamera hangs on Blackwell — use Camera instead.
- NOTE: git/run_log claimed done on Day 2 but were NOT actually created; set up for real on Day 3.

## Day 3 — Cartpole pipeline validation
- Isaac-Cartpole-v0, rsl_rl, headless. Converged 150 iters / ~17s on 5090.
- Mean episode length 300 (cap), time_out 0.999 / cart_out_of_bounds 0.001 — learned.
- TensorBoard served with --bind_all, reached laptop over Tailscale (100.109.10.66:6006). Curves render.
- Debug lesson: "connection refused" = process down; hang = network/firewall.
- Git initialised, .gitignore added (excludes IsaacLab clone + logs/checkpoints), first real commit.
Day 4: Isaac-Reach-Franka-v0 headless trained, reward climbs sharply then plateaus ~400 iters, ep length stable, TB verified from laptop

## Day 5 — num_envs scale test (Reach-Franka, 100 iters each)

| num_envs         | wall time | it/s | throughput (env·it/s) | peak VRAM |
|------------------|-----------|------|-----------------------|-----------|
| 4096 (default)   | 40.9s     | 2.44 | ~10.0k                | 4600 MiB  |
| 8192             | 50.5s     | 1.98 | ~16.2k                | 5059 MiB  |
| 16384            | 74.1s     | 1.35 | ~22.1k                | 7554 MiB  |

Sweet spot: 8192 (best throughput/time balance, trivial VRAM). Note: UR5 grasping env is heavier per-env — re-time before setting real training budgets.
