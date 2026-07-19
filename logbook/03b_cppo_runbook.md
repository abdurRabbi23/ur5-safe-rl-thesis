# Module 03 — cPPO Runbook (Day 9+)

Step-by-step to take the freshly-coded cPPO from "compiles" to "benchmarked".
Run everything on the **lab PC** (RTX 5090), from `~/Abdur_Rabbi_THESIS/IsaacLab`, inside tmux.
Nothing here has touched a GPU yet — treat every step as "verify, don't assume".

---

## Step 0 — Session hygiene (every machine day)
```
conda activate isaaclab
sudo cpupower frequency-set -g performance
tmux new -s thesis        # or: tmux attach -t thesis
cd ~/Abdur_Rabbi_THESIS/IsaacLab
```
Watch: fresh NoMachine terminals start in `(base)` — confirm the prompt shows `(isaaclab)`.

---

## Step 1 — Retrain the PPO baseline on the weld env  (Module 02, must be first)
The old checkpoint is reward-hacked/dead; cPPO reuses this exact env, so the baseline
must be re-trained on the weld before any comparison.
```
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096
```
Monitor (TensorBoard `100.109.10.66:6006`, or the printed block):

| Signal | Pass | Fail |
|---|---|---|
| `Train/mean_reward` | climbs 0.7 → ~8+ and holds | flat, or NaN |
| `Episode/...lifting_object` | rises over training | stays ~0 |
| First ~20 iters it/s | note it — re-time num_envs on this heavier env | — |
| Any NaN / `std >= 0.0` crash | none | crash → the obs clamp firewall should prevent this |

Stop at ~1500 iters. Don't chase convergence.

---

## Step 2 — Visually verify the baseline grasp
```
./isaaclab.sh -p ../ur5_grasp/scripts/play.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 9 --real-time
```
Pass = real reach → close-near → lift-to-goal. **No flinging the cube.** If it flings,
stop — the reward/weld needs a look before cPPO is meaningful.

---

## Step 3 — cPPO smoke test (5 iters, cheap bug-catcher)  ← the new code's first run
```
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --agent rsl_rl_cppo_cfg_entry_point \
    --headless --num_envs 64 --max_iterations 5
```

### PASS checklist (all must hold)
- [ ] Startup prints **`Cost Critic MLP: Sequential(...)`** (once) — the 2nd critic was built.
- [ ] "Resolved observation sets:" shows `policy: ['policy']` and `critic: ['policy']`.
- [ ] Runs all 5 iterations with **no Python traceback**.
- [ ] The printed log block shows these extra lines (rsl_rl wraps each as "Mean … loss"):
      `cost_value_function`, `cost_lambda`, `mean_episode_cost`.
- [ ] `safety/cost_total`, `safety/viol_joint_limit`, `safety/manipulability_mean` appear
      (TensorBoard scalars, or in the printed block).
- [ ] `mean_reward` is a finite number (no NaN).

### Expected-but-fine (NOT failures at 5 iters)
- `cost_lambda = 0.0` and `mean_episode_cost = 0.0` — episodes rarely finish in 5×24 steps
  and the placeholder `cost_limit=25` is high, so λ hasn't moved yet. Plumbing is what's
  under test here, not learning.
- `safety/manipulability_mean` some positive number — its actual value is calibrated in Step 4.

### FAIL → likely cause → tell me
| Symptom | Likely cause |
|---|---|
| `KeyError: 'cost'` in process_env_step | env not emitting cost (COST_ENABLED / extras overwritten) |
| Traceback in `_manipulability` / index error | Jacobian body-axis index wrong for this asset |
| shape mismatch in `add_transitions` / `costs.view(-1,1)` | cost tensor shape |
| `ActorCritic … got unexpected arguments` | a cost knob leaked into the policy cfg |
| `NameError: LagrangianRunner` | import path in train.py |
| `manipulability_mean` ~0 or absurdly huge | Jacobian extraction wrong (still "runs", but wrong) |

If any FAIL row hits, paste me the traceback + the ~20 lines above it.

---

## Step 4 — Calibrate the two scene-specific thresholds
**4a. Collision floor.** Confirm the table-top height. Quick check: in the Step-2 play GUI,
or probe `robot.data.body_pos_w[...,2]` at rest. If the table top isn't z≈0, set
`COLLISION_Z_FLOOR` in `ur5_grasp/tasks/lift/ur5e_lift_env.py` accordingly.

**4b. Manipulability floor** (needs the Step-1 checkpoint):
```
./isaaclab.sh -p ../ur5_grasp/scripts/calibrate_manipulability.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 64 --steps 400
```
- Read the printed percentiles. Set `MANIP_FLOOR` = p05–p10 value.
- Sanity: w should be a smooth spread of small positive numbers (e.g. 0.01–0.1-ish), NOT
  all-zero and NOT 1e6. If it's degenerate → Jacobian index bug → tell me.

---

## Step 5 — Set the cost budget from the baseline
Run cPPO ~50 iters (or reuse the smoke run longer) and read `safety/cost_total` /
`mean_episode_cost` that the **baseline-like** policy incurs. Set `cost_limit` (in
`rsl_rl_cppo_cfg.py`) to a fraction of it — the target the arm must get under. Start ~25–50%
of the measured mean episodic cost; tighten later.

---

## Step 6 — Full cPPO run
```
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --agent rsl_rl_cppo_cfg_entry_point \
    --headless --num_envs 4096
```
Monitor the **Lagrangian dynamics** — this is the story of the thesis:

| Scalar | Healthy behaviour |
|---|---|
| `Loss/mean_episode_cost` | starts high, **trends down toward `cost_limit`** |
| `Loss/cost_lambda` | rises while cost > budget, settles as cost approaches budget (don't want it pinned at `lambda_max=100`) |
| `Train/mean_reward` | still learns to grasp — lower than PPO is OK, collapse to ~0 is not |
| `safety/viol_*` | violation rates drop vs the PPO baseline |

Red flags: λ railed at 100 (budget too tight, or `lambda_lr` too high) → loosen `cost_limit`
or drop `lambda_lr`. Reward collapses to 0 while cost→0 (over-constrained) → same fix.

---

## Step 7 — The benchmark deliverable
```
tensorboard --logdir logs/rsl_rl --port 6006
```
`logs/rsl_rl/ur5e_lift` (PPO) and `logs/rsl_rl/ur5e_lift_cppo` (cPPO) overlay automatically.
Report per run: **success rate**, **sample efficiency** (reward vs steps), and
**constraint-violation rate/cost** (`safety/viol_*`). The headline: cPPO keeps violations
under budget while still grasping; PPO grasps but violates freely.

---

## What to do RIGHT NOW
Step 1 (retrain PPO). While it trains in tmux, nothing else is blocked — but don't smoke-test
cPPO (Step 3) until Step 2 confirms the baseline grasp is real, because cPPO inherits the same env.
