# 06 — Results & Experiments

**Status:** ▶ IN PROGRESS — populated as runs finish.

This page collects the **reproducible experiment configs** and the **results** in one place, so a
reader can both re-run each experiment and see what it produced. Numbers marked `PENDING` are filled
in when the corresponding run completes.

---

## How to reproduce any run

All training uses the same launcher, differing only in flags. Run from
`~/Abdur_Rabbi_THESIS/IsaacLab` inside tmux, env `isaaclab` active.

| Experiment | Command (key flags) | Log dir |
|------------|---------------------|---------|
| Cartpole (stack validation) | `train.py --task Isaac-Cartpole-v0 --headless` | `logs/rsl_rl/cartpole` |
| Franka reach (loop validation) | `train.py --task Isaac-Reach-Franka-v0 --headless` | `logs/rsl_rl/…reach…` |
| PPO baseline (grasp, weld) | `../ur5_grasp/scripts/train.py --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096` | `logs/rsl_rl/ur5e_lift` |
| **cPPO (safe RL)** | `…train.py --task Isaac-Lift-Cube-UR5e-v0 --agent rsl_rl_cppo_cfg_entry_point --headless --num_envs 4096` | `logs/rsl_rl/ur5e_lift_cppo` |

View any of them: `tensorboard --logdir logs/rsl_rl --port 6006 --bind_all` (multiple runs overlay
automatically).

---

## Validation results (foundation) — ✅ done

| Test | Result |
|------|--------|
| Cartpole | Converged ~150 iters (~17 s on RTX 5090); mean episode length 300 (cap); learned (time_out 0.999) |
| Franka reach | Reward climbs sharply, plateaus ~400 iters; episode length stable |
| num_envs sweep (reach) | Sweet spot ~8192 (throughput vs VRAM); grasp env run at 4096 |

---

## Layer 1 — PPO baseline (grasp) — ✅ trained

- Weld env, 4096 envs, ~1500 iters, clean (no NaN).
- `mean_reward` 0.7 → ~8+ ; `lifting_object` term rises → arm grasps and lifts.
- **Visual `play.py` check must pass** (real reach-grasp-lift, no flinging) before the run is
  trusted.

---

## Layer 1 — Calibration — ✅ done

From a 25.6k-sample baseline rollout (`calibrate_manipulability.py`):

| Constraint | Baseline distribution | Threshold | Active? |
|------------|----------------------|-----------|:-------:|
| Manipulability `w` | min .021 / mean .055 / max .114 | `MANIP_FLOOR = 0.045` (~20% viol.) | **YES** |
| Joint-limit clearance | min 1.39 rad | margin 0.10 | monitored (satisfied) |
| Min link height | min 0.125 m | floor 0.0 | monitored (satisfied) |

Cost budget: **`cost_limit = 25`** (validated by a 50-iter probe; λ self-engaged 0 → 6.85,
controlled).

---

## Layer 1 — The headline benchmark (cPPO vs PPO) — ▶ PENDING

Result table lives in `results/03_cppo_vs_ppo_results.docx` (Times New Roman 14, centred caption).
Fill these once Steps 6–7 of section 03 finish:

| Metric | PPO (unconstrained, floor 0.045) | cPPO (`cost_limit = 25`) |
|--------|:--------------------------------:|:------------------------:|
| Grasp success rate | `PENDING` | `PENDING` |
| Final mean reward | `PENDING` | `PENDING` |
| Sample efficiency (reward @ N steps) | `PENDING` | `PENDING` |
| Singularity violation rate (`safety/viol_singularity`) | `PENDING` (expected higher) | `PENDING` (expected lower) |
| Mean episodic cost | `PENDING` | `PENDING` (expected ≤ 25) |
| Final `cost_lambda` | n/a | `PENDING` |

**Expected story:** cPPO keeps violations under budget while still grasping; PPO grasps but violates
freely.

---

## Figures to produce (for the write-up)

Save exported plots into `assets/` and reference them here:

- `assets/fig_reward_ppo_vs_cppo.png` — reward curves overlaid. `PENDING`
- `assets/fig_cost_vs_budget.png` — mean episodic cost vs `cost_limit` line. `PENDING`
- `assets/fig_lambda_dynamics.png` — `cost_lambda` self-tuning over training. `PENDING`
- `assets/fig_violation_rates.png` — `safety/viol_*` bar comparison. `PENDING`

> Formatting reminder for exported figures/tables: centre-aligned, centre-aligned captions, a few
> purposeful colours only.
