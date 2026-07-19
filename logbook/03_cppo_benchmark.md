# Module 03 — Safety Constraints + cPPO vs PPO (Layer 1 deliverable)

Status: ▶ cPPO IMPLEMENTED + smoke/probe PASSED + thresholds calibrated; **pending the 2 full runs**
Chat type: safe-RL / benchmarking
Last updated: 2026-07-16 (Day 9)

## ⚡ Pick-up-here (for a new session)
Everything is coded, smoke-tested, and calibrated. Two things remain: run the full cPPO and a
matched full PPO baseline, then overlay. Exact commands + what-to-watch: `logbook/03b_cppo_runbook.md`
Steps 6–7. Verified working: Jacobian/manipulability correct, Lagrangian mechanism engages
(cost↑ as it grasps, λ self-rises, reward trades off). Locked settings below — do NOT re-tune.

### Locked settings (calibrated Day 9, don't re-litigate)
- `MANIP_FLOOR = 0.045` — the ONE active constraint (baseline w: min .021/mean .055; ~20% violation).
- `cost_limit = 25` — validated by the 50-iter probe (λ controlled, ~17% reward dip, ~65% cost cut).
- Joint-limit & collision constraints are INACTIVE by construction in this workspace (arm never
  nears limits/table) — keep them as monitored-but-satisfied; report, don't force.
- `num_envs = 4096` (~200k steps/s, re-timed on this env).

## Goal
The must-pass Layer 1 contribution: add hard safety constraints to the grasp env and
train constrained PPO (Lagrangian CMDP), then benchmark **cPPO vs unconstrained PPO** —
showing cPPO respects safety limits while still learning to grasp.

## Decisions (Day 9)
- **Library: rsl_rl-Lagrangian**, NOT OmniSafe/skrl. Reason: baseline is rsl_rl 3.0.1;
  keeping cPPO on the same trainer/hyperparameters means the comparison differs by the
  constraint alone (an examiner can't attribute a gap to two different PPO impls).
- **Variant: separate cost critic** (textbook PPO-Lagrangian), chosen over the single-critic
  adaptive-penalty shortcut. Matches the Khan/OmniSafe cPPO formulation literally.
- Built as thin subclasses of rsl_rl 3.0.1 so the PPO baseline stays the untouched control.

## What was implemented (`ur5_grasp/safe_rl/`)
- `costs.py` — per-step safety cost, 3 soft terms (0 when safe):
  1. collision keep-out: monitored arm links below the table plane (`COLLISION_Z_FLOOR`);
  2. joint-limit margin: arm joints inside the last `JOINT_LIMIT_MARGIN` rad (=0.10);
  3. singularity: Yoshikawa w=sqrt(det(J Jᵀ)) below `MANIP_FLOOR`.
  Aggregate cost → one Lagrange multiplier; per-term means + violation rates logged.
- `actor_critic_cost.py` — ActorCritic + a 2nd (cost) critic head, reuses the critic obs set.
- `rollout_storage_cost.py` — RolloutStorage + cost stream + cost-GAE + extended minibatch gen.
- `ppo_lagrangian.py` — PPO + combined advantage (A_r − λ·A_c)/(1+λ) + cost value loss +
  projected dual ascent on λ vs `cost_limit`. Metrics (λ, mean_episode_cost, cost_value) → TB.
- `lagrangian_runner.py` — OnPolicyRunner subclass that builds the three above.
- Env: `tasks/lift/ur5e_lift_env.py` now emits `extras["cost"]` every step (both agents;
  cost params are class attrs on `UR5eCubeLiftEnv`).
- Cfg: `tasks/lift/agents/rsl_rl_cppo_cfg.py` (`UR5eLiftCPPORunnerCfg`, experiment `ur5e_lift_cppo`).
- Registered `rsl_rl_cppo_cfg_entry_point` on both gym ids; `train.py`/`play.py` gained a
  `LagrangianRunner` branch. Baseline path byte-for-byte unchanged.
- All 12 files pass `py_compile` (sandbox can't import torch/isaaclab — needs a lab-PC smoke test).

## Constraint thresholds — status (all CALIBRATED Day 9; see run_log + logbook/calib.log)
- `JOINT_LIMIT_MARGIN=0.10 rad` — monitored-but-satisfied: baseline min clearance 1.39 rad, arm
  never nears limits in tabletop grasp → INACTIVE by construction. ✅
- `COLLISION_Z_FLOOR=0.0` — VERIFIED: baseline min link height 0.125 m above table → arm links
  never near the table → INACTIVE by construction. Kept as monitored-but-satisfied. ✅
- `MANIP_FLOOR=0.045` — CALIBRATED (baseline w: min .021 / mean .055 / max .114; p10–p25 → ~20%
  baseline violation). This is the ONE active constraint (near-singular Jacobian). ✅
- `cost_limit=25.0` (undiscounted episodic-cost budget) — VALIDATED by the 50-iter probe
  (λ→6.85 controlled, ~17% reward dip, ~65% cost cut vs natural ~70+). ✅

## Next steps (order matters)
0. ✅ (Module 02) PPO retrained on the weld env; play-verified. cPPO reuses that env.
1. ✅ Lab-PC smoke test — cost critic built, runs, logs `Loss/cost_lambda` (logbook/smoke_cppo.log).
2. ✅ `COLLISION_Z_FLOOR` verified + `calibrate_manipulability.py` run → `MANIP_FLOOR=0.045`.
3. ✅ 50-iter probe read episodic cost → `cost_limit=25`.
4. ▶ **IMMEDIATE NEXT — full cPPO run + matched full PPO baseline at floor 0.045 (1500 iters,
   num_envs=4096); overlay in TB (`--logdir logs/rsl_rl`).** Commands: `03b_cppo_runbook.md` Steps 6–7.
5. ◻ Collect success rate + per-term violation rate/cost; fill results table; write up.

## Open questions — RESOLVED
- Jacobian body-axis indexing on this fixed-base UR5e → **RESOLVED**: probe gave
  `manipulability_mean=0.11` (smooth small-positive w), so `costs.py` auto-detect picked the
  right index. Biggest untested risk cleared.
- `cost_limit` — undiscounted episodic cost vs per-step rate → **RESOLVED**: kept undiscounted
  episodic; probe-validated at 25.

## run_log.md refs
Day 9.
