# Run checklist — matrix v2 (post-audit)

Written 2026-07-31 (Day 23). Everything below runs **on the lab PC**, from inside
`Comparison_test/` as cwd. Each step states what you should see. If you see something else,
stop at that step — do not continue on the assumption it will sort itself out.

Total: ~35-40 min of checks, ~5 h of training, ~1.5 h of evaluation.

**Reordered same day (Day 23, cont.):** freeze used to be Step 0, first. It's now Step 5,
after the sanity checks and the recalibration step. Reason: recalibration (Step 4) can produce
a real code change (`MANIP_FLOOR` in `ur5e_lift_env.py` or `cost_limit` in
`agents/rsl_rl_cppo_cfg.py`), and the freeze's whole job is to tag the exact commit run 1
trains against. Freezing before a step that might still edit tracked files would tag the wrong
commit — the fairness protocol needs the *final* calibrated code stamped, not an intermediate
version.

---

## Step 1 — the arms resolve at all (~3-5 min, headless Kit boot, no training)

This catches a typo in an entry point before it costs you a 3-hour batch.

**Day 23 (cont.) fix:** the snippet below now launches Isaac Sim's Kit runtime
(`AppLauncher(headless=True)`) before importing anything from `isaaclab_rl`/`isaaclab.controllers`.
`omni.*` modules (e.g. `omni.log`, pulled in transitively by `isaaclab.controllers.differential_ik`)
are only importable **after** Kit has started — they are not plain pip-importable like a normal
package. `import ur5_grasp.tasks` alone doesn't need this (gym registration is just strings), but
the direct `rsl_rl_cppo_cfg` import does. Pattern confirmed against Isaac Lab's own test suite
(`isaaclab/test/controllers/test_differential_ik.py` and others all open with
`simulation_app = AppLauncher(headless=True).app`), not guessed. This adds Kit's boot time
(~20-60 s) to the step.

```bash
cd ~/Abdur_Rabbi_THESIS/Comparison_test
../IsaacLab/isaaclab.sh -p - <<'PY'
from isaaclab.app import AppLauncher
app_launcher = AppLauncher(headless=True)
simulation_app = app_launcher.app

import gymnasium as gym
import ur5_grasp.tasks  # noqa
spec = gym.spec("Isaac-Lift-Cube-UR5e-v0")
for k in ["rsl_rl_cfg_entry_point", "rsl_rl_cppo_cfg_entry_point",
          "rsl_rl_cppo10_cfg_entry_point", "rsl_rl_ctrl_cfg_entry_point",
          "skrl_sac_cfg_entry_point"]:
    print(f"{k:34s} -> {spec.kwargs.get(k)}")

from ur5_grasp.tasks.lift.agents.rsl_rl_cppo_cfg import (
    UR5eLiftCPPORunnerCfg, UR5eLiftCPPO10RunnerCfg, UR5eLiftCtrlRunnerCfg)
for cls in (UR5eLiftCPPORunnerCfg, UR5eLiftCPPO10RunnerCfg, UR5eLiftCtrlRunnerCfg):
    c = cls()
    print(f"{c.experiment_name:20s} cost_limit={c.algorithm.cost_limit:5.1f} "
          f"lambda_max={c.algorithm.lambda_max:6.1f} lr={c.algorithm.learning_rate}")

simulation_app.close()
PY
```

**Expect exactly:**

```
ur5e_lift_cppo       cost_limit= 25.0 lambda_max= 100.0 lr=0.0001
ur5e_lift_cppo10     cost_limit= 10.0 lambda_max= 100.0 lr=0.0001
ur5e_lift_ctrl       cost_limit= 25.0 lambda_max=   0.0 lr=0.0001
```

Three distinct `experiment_name`s (otherwise two arms overwrite each other's log
directory — the Day-22 SimpleGripper collision, repeated), and `lambda_max = 0.0` on `ctrl`
only.

---

## Step 2 — smoke trains, 50 iterations each (~8 min)

Never launch 25 runs against code that has never executed — and today especially, this is the
first time the widened goal-pose box and the new reward functions actually run.

```bash
for AGENT in rsl_rl_cfg_entry_point rsl_rl_ctrl_cfg_entry_point \
             rsl_rl_cppo_cfg_entry_point rsl_rl_cppo10_cfg_entry_point; do
  ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
      --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 512 \
      --max_iterations 50 --seed 1 --run_name "smoke_$(date +%H%M%S)" --agent "$AGENT"
done
```

**Expect:** four runs finishing without traceback. In the cPPO/ctrl/cppo10 output you should
see `Cost Critic MLP: ...` printed once at startup, and per-iteration lines including
`Mean cost_value_function loss`, `cost_lambda`, `mean_episode_cost`.

**Check the new logging is live:**

```bash
grep -c "cost_episodes_in_estimate\|cost_budget_used" /dev/null; \
../IsaacLab/isaaclab.sh -p ur5_grasp/tools/summarize_runs.py 2>/dev/null | tail -5
```

**If a cost run crashes on `_base_params`:** the gradient-clip fix did not pick up the
cost critic. Read `safe_rl/ppo_lagrangian.py::__init__` and confirm
`self.policy.cost_critic` exists at that point.

**If any run crashes on `rewards.py` / `object_lifted_toward_goal`:** that's today's new
reward-term code, never executed before this step. Check the traceback against the function
signatures in `tasks/lift/rewards.py` first — most likely cause is a `SceneEntityCfg`/command
lookup mismatch, not a math error (the threshold arithmetic was hand-checked, not run).

---

## Step 3 — SAC smoke, separately (~5 min)

`skrl_sac_cfg.yaml` has **never been executed anywhere**. Prove it boots before the batch.

```bash
../IsaacLab/isaaclab.sh -p -c "import skrl; print(skrl.__version__)"
```
**Expect:** `1.4.3` or higher. Below that, stop — the config is written against 1.4.x, and
skrl 2.x renames `state_preprocessor`.

> **Correction (Day 23, cont. — run attempt).** The override below used to read
> `trainer.timesteps=200` and fails with `Could not override 'trainer.timesteps'. Key 'trainer'
> is not in struct`. Root cause, checked directly against
> `isaaclab_tasks/utils/hydra.py::register_task_to_hydra`: the composed Hydra config is
> `{"env": ..., "agent": ...}`, so everything inside `skrl_sac_cfg.yaml` — including its
> top-level `trainer:` block — actually lives under `agent.` in the struct Hydra overrides
> resolve against. Fixed below to `agent.trainer.timesteps=200`. **Do not use `--max_iterations`
> as an alternative for SAC** — `train_skrl.py` line ~181 does
> `agent_cfg["agent"]["rollouts"]`, a PPO-only key SAC's yaml doesn't define (see that yaml's
> own header comment), so `--max_iterations` raises `KeyError('rollouts')` for this arm.

```bash
../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train_skrl.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 128 \
    --algorithm SAC --seed 1 agent.trainer.timesteps=200
```

**Expect:** five model sources printed (`policy`, `critic_1`, `critic_2`, `target_critic_1`,
`target_critic_2`), then training lines.

**Known failure and its cause:**

| symptom | cause | fix |
|---|---|---|
| `KeyError: 'rollouts'` | `memory_size` got set back to `-1`; the Runner then looks up a PPO-only key | restore the explicit `memory_size: 8000` |
| a model role is `None` | one of the five roles missing from `models:` | add it; targets are not auto-created |
| CUDA OOM at startup | 1.02 M-transition buffer too big for this GPU | lower `memory_size` to 4000 and note it in the results table |

---

## Step 4 — recalibrate safety thresholds (goal-pose box + rewards + collision/joint-limit margins, Day 23 cont.) (~15-20 min)

Four task-defining changes landed the same day, before any run against any of them: (1) the
goal-pose sampling box in `ur5e_lift_env_cfg.py` was widened twice (old `pos_x=(0.4,0.6),
pos_y=(-0.25,0.25), pos_z=(0.25,0.5)` -> current `pos_x=(0.22,0.60), pos_y=(-0.30,0.30),
pos_z=(0.10,0.50)`, far corner 0.84 m, ~13 mm inside the UR5e's ~0.85 m reach — see the comment
above `self.commands.object_pose.ranges`); (2) `lifting_object` / `object_goal_tracking` /
`object_goal_tracking_fine_grained` were re-weighted (15/16/5 -> 10/15/5) and their "lifted" gate
switched from a fixed 0.04 m to 50% of the climb from the table to each episode's goal height
(`rewards.py`, new); (3) `COLLISION_Z_FLOOR` widened 0.0 -> 0.05 m (a 5 cm standoff above the
table, not just literal penetration); (4) `JOINT_LIMIT_MARGIN` widened 0.10 -> 0.175 rad (both
in `ur5e_lift_env.py`). All four change how the policy is shaped to move or how strict the
"monitored but satisfied" constraints are — run this recalibration against the FINAL config
(all four applied, and after Steps 1-3 have confirmed nothing crashes), not partway through.
`MANIP_FLOOR`, `cost_limit`, and the Day-9 "collision/joint-limit are INACTIVE by construction"
conclusion were all reached against the OLD box, OLD reward shape, and OLD (tighter) margins.
**Do this before Step 5 (freeze) and Step 6 (the matrix)** — recalibrating after a 5-hour matrix
has already run against stale thresholds means redoing it, and freezing before this step would
tag a commit that's about to change.

```bash
../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/calibrate_manipulability.py
```

This script already reports (Day 9) manipulability `w`, joint-limit clearance, AND min link
height distributions + baseline violation rates — read all three, not just `w`:

- **`MANIP_FLOOR = 0.045`** — still at roughly the same percentile (~p10-p25) it was calibrated
  to on Day 9?
- **`JOINT_LIMIT_MARGIN = 0.175` rad** — Day 9 baseline had min joint clearance 1.39 rad, so the
  old 0.10 rad margin was "INACTIVE by construction." Is min clearance still comfortably above
  0.175 rad? If the closer-reaching goal box brings it near or below, this constraint may have
  gone live for the first time — that's a real finding, not a bug, but it changes what "monitored
  vs active" means in the results.
- **`COLLISION_Z_FLOOR = 0.05` m** — Day 9 baseline had min link height 0.125 m above the table,
  so the old 0.0 floor was "INACTIVE by construction." Is min link height still above 0.05 m? The
  goal box's `pos_z` now reaches down to 0.10 m, so this is the most likely of the four changes
  to actually move a number.

If any has shifted meaningfully, treat it the same as any other calibrated constant — a one-line
diff in the owning file, recorded with the old and new value and why.

```bash
../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096 \
    --max_iterations 50 --seed 1 --run_name cost_probe_v2
```

**Check:** the Day-9-style natural-cost probe. Read `mean_episode_cost` from this run's TB
scalars — does it still sit meaningfully above 10 and roughly around 25-70, the range `cost_limit`
(10/25) was set against? Also read the per-term breakdown (`safety/cost_collision`,
`safety/cost_joint_limit`, `safety/cost_singularity`) — if collision or joint-limit are no longer
~0, `cost_limit` is now being spent across three terms instead of one, which changes what the
thesis can claim `cost_limit` is actually constraining. If the new config pushes total natural
cost much higher or lower, `cost_limit` needs revisiting the same way — one-line diff, recorded,
sensitivity analysis intact.

**If everything comes back close to the Day-9 numbers:** none of today's four changes moved the
task's safety geometry much in practice; proceed to Step 5 with the existing thresholds and note
that this was checked, not assumed. **Either way**, any calibration edit made here must land
*before* Step 5, so the freeze captures it.

---

## Step 5 — freeze (2 min)

The fairness protocol requires the env stamped before run 1, so the provenance line in the
results table is true — including any calibration edit from Step 4.

```bash
cd ~/Abdur_Rabbi_THESIS
git add -A
git commit -m "Day 23: algorithm audit; gradient-clip fix; matrix v2 arms (ctrl, cppo10, SAC); widened goal-pose box; reward re-weighting; recalibrated thresholds"
git tag matrix-v2
git rev-parse --short HEAD
```

**Expect:** a short SHA. Write it down — it goes in the results table.
**If `git status` still shows modified files afterwards:** something is in `.gitignore` that
should not be. Check before continuing.

---

## Step 6 — the matrix (~5 h, unattended)

```bash
tmux new -s thesis_abrabbi        # standing project rule: never run a long batch bare
./run_matrix_v2.sh
```

Detach with `Ctrl-b d`. The script writes `logs/batch_report_v2.txt` flushed, so you can
tail it from another shell.

**Expect at the end:** `ALL 25 RUNS OK`. Any `FAILED` line names the run and the exit code;
the batch does not abort, so a single failure costs you one run, not the night.

**Order is deliberate:** `ppo` and `ctrl` run first. If the machine dies at 2 a.m. you still
have the pair that settles the audit question.

---

## Step 7 — the one check that decides everything (5 min)

**Do this before generating a single table.**

```bash
../IsaacLab/isaaclab.sh -p ur5_grasp/tools/summarize_runs.py
```

Then read two numbers:

**(a) Did the tight budget actually bind?** Look at `Loss/cost_lambda` for the `cppo10` runs.

- λ climbs away from 0 and stays positive → good, the constraint is active, proceed.
- λ still pinned at 0 → **`cost_limit = 10` is still slack.** Do not proceed to evaluation.
  Lower the budget again (5, then 2) using the same one-line-diff pattern as
  `UR5eLiftCPPO10RunnerCfg` and rerun that arm only. Record every budget you tried; the
  sequence is itself the calibration evidence.

**(b) Is `ctrl` indistinguishable from `ppo`?** Compare `Train/mean_reward` tail means across
the five seeds of each.

- Distributions overlap → the A1 fix worked, the arms are now clean, proceed.
- `ctrl` still systematically beats or trails `ppo` → **stop.** Something other than the
  gradient clip still couples the cost critic to the actor, the audit is incomplete, and no
  cPPO-vs-PPO claim can be made yet. Report this rather than working around it.

---

## Step 8 — evaluation (~90 min)

```bash
./run_eval_policy_v2.sh sac
```

**Expect:** two preflight OKs, then 75 launches. `ALL 75 EVALS OK` at the end.

Results append to `ur5_grasp/tools/eval_policy_results.csv` (one row per checkpoint × eval
seed) and `ur5_grasp/tools/eval_episodes/*.csv` (one row per episode — this is what makes the
distribution reconstructable; do not delete it).

---

## Step 9 — report

Lead with the decomposition, not the headline:

```
(cppo − ppo)  =  (ctrl − ppo)          +  (cppo − ctrl)
                  the implementation       the constraint
                  artifact                 ← the only part that is a safe-RL result
```

Reporting rules carried over from the audit:

- Goal-reach: report the **distance distribution** plus success at 1 / 2 / 5 cm. A single
  threshold saturates at 0 % or 100 % because the weld makes the cube's pose the TCP's pose
  (audit finding A6). Never headline "100 % vs 0 %".
- Safety: lead with **episodes that reached an actual singularity** (w < 1e-4) and with the
  **mean episode-minimum manipulability**. The step-fraction below `MANIP_FLOOR` is a binary
  test on a soft margin and exaggerates differences.
- SAC: state that the comparison is matched on **gradient steps**, not environment samples.
- Provenance: git SHA + tag `matrix-v2` from Step 5, plus the seed count and eval protocol.

Mark `results/LAYER1_RESULTS_3seed.md` and `results/LAYER1_FINDINGS.md` as **SUPERSEDED** at
the top rather than deleting them — the fact that a large apparent effect turned out to be an
artifact is part of the thesis's diagnostic-discipline narrative, and the superseded files are
the evidence for it.
