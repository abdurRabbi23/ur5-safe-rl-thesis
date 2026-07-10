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
