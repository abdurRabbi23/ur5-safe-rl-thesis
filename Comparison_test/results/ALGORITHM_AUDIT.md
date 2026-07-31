# Algorithm audit — PPO vs cPPO (PPO-Lagrangian)

Date: 2026-07-31 (Day 23). Auditor: line-by-line diff of
`ur5_grasp/safe_rl/*` against rsl_rl 3.0.1 upstream source
(`leggedrobotics/rsl_rl` tag `v3.0.1`: `algorithms/ppo.py`, `modules/actor_critic.py`,
`runners/on_policy_runner.py`, `utils/utils.py`), cross-checked against the TensorBoard
scalars actually written by the 2026-07-30 runs.

**Verdict: the PPO-Lagrangian mathematics is correct. The 2026-07-30 comparison is not.**
The gap between cPPO and PPO in `LAYER1_RESULTS_3seed.md` / `LAYER1_FINDINGS.md` cannot be
attributed to the safety constraint, because the constraint was inactive for essentially the
entire run. Those two files must not be quoted in the thesis until the v2 matrix replaces them.

---

## 0. The finding, in one table

`Loss/cost_lambda`, read directly from the run event files:

| run | iter 0 | 10% | 25% | 50% | 75% | final |
|---|---|---|---|---|---|---|
| cppo_s1 | 0.000 | 0.000 | 0.000 | 0.706 | 0.000 | 0.198 |
| cppo_s2 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **0.000** |
| cppo_s3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.272 |

The Lagrangian surrogate is

```
adv = (A_reward − λ·A_cost) / (1 + λ)
```

At λ = 0 this is `A_reward`, i.e. **the policy update is stock PPO**. `cppo_s2` never left
λ = 0 at any iteration, so `cppo_s2` is an unconstrained PPO run by construction. Yet:

| | ppo_s2 | cppo_s2 |
|---|---|---|
| train reward (tail mean) | 90.8 | **166.4** |
| reward at iteration 0 | 0.7152 | 0.7152 |
| cost/step | 1.773 | 0.039 |
| goal-reach @5 cm (Day-22 eval) | 0.00 % | 100.00 % |

Identical seed, identical env config (verified by `diff` of the dumped `params/env.yaml` —
the only differences are the two log-path strings), identical initial reward to four
decimals. Two runs of the same algorithm should not separate like this because of a
constraint that was switched off.

**Therefore something other than the constraint distinguishes the cPPO arm from the PPO
arm.** The rest of this document is the search for what.

---

## 1. Findings

### A1 — One global gradient clip spanning both critics  ·  **SEVERITY: HIGH · FIXED**

`ppo_lagrangian.py` inherited stock PPO's clipping line unchanged:

```python
nn.utils.clip_grad_norm_(self.policy.parameters(), self.max_grad_norm)
```

In the PPO baseline `self.policy.parameters()` is actor + reward critic. In cPPO it is
actor + reward critic **+ the cost critic**, because `ActorCriticCost` registers a third MLP
of the same size as the other two.

`clip_grad_norm_` does not clip parameters individually. It computes a single global norm
across every tensor handed to it and, if that norm exceeds the bound, multiplies **every**
gradient by `max_grad_norm / total_norm`. So the cost critic's MSE gradients enter the norm
and scale down the actor's and reward critic's gradients. With `max_grad_norm = 1.0` — tight
enough that the clip binds on most updates — cPPO was running a systematically smaller,
cost-loss-dependent effective step size than PPO.

This is not a property of PPO-Lagrangian. It is an artifact of putting two heads in one
optimiser and reusing the single-head clipping line. It was active at every iteration,
including all the iterations where λ = 0.

The mechanism also matches the *shape* of the observed result, which is why it is the prime
suspect and not merely a defect worth mentioning. A smaller effective step size is a
well-known stabiliser for PPO on shaped-reward manipulation tasks: it makes the run less
likely to fall into a degenerate optimum. "cPPO converges on 3/3 seeds, PPO converges on
1/3" is exactly what a quieter optimiser looks like — and it is exactly what the Day-22
write-up interpreted as the constraint buying reliability.

**Fix (applied):** partition the parameters once in `__init__` and clip the two groups
independently, so the actor and reward critic receive byte-identical treatment to the
baseline:

```python
nn.utils.clip_grad_norm_(self._base_params, self.max_grad_norm)
nn.utils.clip_grad_norm_(self._cost_critic_params, self.max_grad_norm)
```

**This fix is a hypothesis, not a proof.** It is confirmed only if the new `ctrl` arm
(cost critic present, λ pinned to 0) comes out indistinguishable from `ppo`. That
measurement is the point of the v2 matrix.

### A2 — The constraint never bound  ·  **SEVERITY: HIGH · ADDRESSED BY A NEW ARM**

`cost_limit = 25` was calibrated on Day 9 from a **50-iteration probe**, against a natural
episodic cost of ~70. Over a full 1500-iteration run the policy settles far lower —
`Loss/mean_episode_cost` for the cPPO seeds ranges over roughly 7–29. The budget therefore
sits at or above the unconstrained operating point, the dual update correctly drives
λ → 0, and the Lagrangian has nothing to do.

The Day-9 calibration is not *wrong*; it was measured against a policy that had barely
started learning. It simply does not describe the converged regime.

A constraint that is never exceeded cannot produce a constrained-RL result. Hence the new
`cppo10` arm at `cost_limit = 10`, below the natural cost on every observed seed.

Report both budgets as a sensitivity analysis. Do not quietly replace 25 with 10 — the fact
that the originally-calibrated budget turns out to be slack is itself a finding about
calibrating safety budgets from short probes, and it is worth a Methods paragraph.

### A3 — Jc estimated from 2.4 % of the batch  ·  **SEVERITY: MEDIUM · FIXED**

The dual update reacts to `jc = mean(self._cost_buffer)`, where `_cost_buffer` was
`deque(maxlen=100)`. That length is inherited from rsl_rl's reward buffer, which is fed a
handful of episodes per iteration. Here the horizon is a fixed 250 steps with no early
termination in practice, so **all 4096 environments terminate on the same step** and the
deque discards all but the last 100 of 4096 episodes.

Consequences: Jc is noisier than it needs to be, and it is biased toward whichever
environments happen to sit last in the tensor ordering. With λ pinned near a boundary
(0), noise in Jc translates directly into spurious λ excursions — visible as the isolated
0.706 spike in `cppo_s1`.

**Fix (applied):** `cost_buffer_size` is now a config field, default 4096 (= `num_envs`,
one full wave). The number of episodes behind each estimate is logged as
`Loss/cost_episodes_in_estimate` so the thesis can state the estimator's sample size rather
than assume it.

### A4 — Seeds are not paired across arms  ·  **SEVERITY: LOW · NOT FIXABLE IN CODE**

Constructing the cost critic draws from the global RNG. Because `ActorCriticCost` calls
`super().__init__()` first, the **actor and reward critic still initialise identically** to
the PPO baseline at the same seed (confirmed: iteration-0 reward matches to 4 dp). But every
subsequent random draw — action sampling, minibatch permutation — is offset, so the two arms
follow different trajectories from step 1 even before any algorithmic difference applies.

This is ordinary seed noise, not a bug, and it cannot be removed without a separate RNG
stream per component. It is handled by **seed count** (5 rather than 3) and by the `ctrl`
arm, which carries the same offset as cPPO and so absorbs it as a matched control.

### A5 — SAC would have been evaluated with random actions  ·  **SEVERITY: HIGH · FIXED**

Not part of the PPO/cPPO question, but found while preparing the SAC arm, and it would have
silently destroyed that arm's result.

skrl's off-policy agents open `act()` with:

```python
if timestep < self._random_timesteps:
    return self.policy.random_act(...)
```

`eval_policy.py` calls `runner.agent.act(obs, timestep=0, timesteps=0)`, and a training SAC
config sets `random_timesteps` to a positive number for exploration. `0 < 1000`, so **every
evaluation action would have been drawn uniformly from the action space.** `random_act` also
returns an empty outputs dict, so the existing `outputs[-1].get("mean_actions", outputs[0])`
fallback would have quietly returned the random sample. The failure mode is not a crash —
it is SAC scoring near zero and appearing to confirm that off-policy methods fail on this
task.

**Fix (applied):** `eval_policy.py` now zeroes `random_timesteps`, pushes `learning_starts`
out of reach, and shrinks the replay buffer whenever it loads an off-policy skrl config.

### A6 — Metric ceiling on goal-reach  ·  **SEVERITY: MEDIUM · REPORTING ISSUE**

Already partly identified on Day 23 in `09_comparison_test.md`, restated here because it
bears on the "how can cPPO be 100 % every time" question directly.

Once the proximity weld latches, the cube's pose **is** the reach frame's pose —
`_apply_weld` writes `pose[:, 0:3] = tcp[ids]` every control step. So "cube within 1 cm of
the goal" reduces to "TCP within 1 cm of the goal", i.e. a pure reaching problem with no
contact physics in the loop. A converged policy solves that on essentially every episode,
and a non-converged one fails on essentially every episode. The metric is close to binary
**by construction of the environment**, not because of anything the algorithms did.

So cPPO's 100.00 % ± 0.00 is not evidence of suspicious behaviour, and PPO's 0.00 % is not
evidence of sabotage. Both are the same ceiling seen from opposite sides. What the metric
genuinely cannot do is rank two policies that both converge.

**Reporting rule:** lead with the goal-distance *distribution* (mean / median / p90 / max —
`eval_policy.py` already records it per episode) and with success at 1 / 2 / 5 cm. Treat any
single-threshold success rate as a coarse summary, and never present 100 % vs 0 % as the
headline of a three-seed comparison.

---

## 2. What was checked and found CORRECT

Recorded so the audit is falsifiable and so nobody re-derives it later.

| Component | Checked against | Result |
|---|---|---|
| Lagrangian surrogate `(A_r − λA_c)/(1+λ)` | standard PPO-Lagrangian formulation | correct; reduces to PPO at λ=0 |
| Dual ascent `λ ← clip(λ + η(Jc − d), 0, λmax)` | projected dual ascent | correct, including the projection onto λ ≥ 0 |
| Cost GAE recursion | `RolloutStorage.compute_returns` v3.0.1 | identical recursion, own γ/λ, correct `dones` masking |
| Minibatch generator | `RolloutStorage.mini_batch_generator` v3.0.1 | identical, including `randperm` outside the epoch loop |
| Timeout bootstrapping of cost | stock reward bootstrap | mirrors it correctly (`γ_cost · V_cost · time_outs`) |
| Adaptive-KL LR schedule | stock PPO | copied verbatim, including the multi-GPU reduction |
| Value-loss clipping (both critics) | stock PPO | identical scheme |
| Actor / reward-critic init | `ActorCritic.__init__` | identical weights at equal seed (cost critic built after `super().__init__()`) |
| Cost-critic parameter sharing | `ActorCriticCost` | none — separate MLP, Identity normalizer, no shared trunk. Only the clip coupled them (A1) |
| `obs_groups: {}` in the PPO cfg vs explicit in the cPPO cfg | `resolve_obs_groups` v3.0.1 | **not** an asymmetry: the empty dict resolves to `{"policy": ["policy"], "critic": ["policy"]}`, identical to the explicit form. Worth recording because it looks alarming in a `diff` of the two `agent.yaml` files |
| Env config used by both arms | `diff` of dumped `params/env.yaml` | identical apart from the two log-path strings |
| Cost computed for both arms | `ur5e_lift_env.py` | yes — `COST_ENABLED` is unconditional, PPO simply ignores `extras["cost"]` |

---

## 3. Two environment-level notes (not defects, but they belong in Methods)

**The weld's one-step lag.** `step()` calls `super().step(action)` and only then
`_apply_weld()`. The observation and reward returned for step *t* therefore reflect the cube
where physics left it, before that step's weld correction is written. It is a 20 ms lag at
50 Hz, identical for every arm, and not a fairness problem — but it should be stated rather
than discovered by a reader.

**The gripper convention flip (`b8f0727`).** `GRIPPER_OPEN`/`GRIPPER_CLOSE` were swapped
from `0.0/0.8` to `0.8/0.0` on Day 18, described in the commit as "cosmetic for the RL (the
weld latches on action sign, not joint value)". The claim is correct about the *latch* —
`_apply_weld` reads `action[:, -1] < 0.0`, which is unaffected. It is **not** correct that
nothing changed physically: after the flip, a CLOSE command drives the pads to a 0 mm gap
around a ~63 mm cube that the weld is simultaneously pinning to the TCP, so the pads are
commanded into the cube rather than around it. Whatever contact impulses result are new
relative to the pre-Day-18 runs.

This is a plausible partial answer to "PPO used to do better than it does now" — those early
runs predate the flip — but it is a **hypothesis that has not been tested**, it affects both
arms equally, and it should not be asserted. The clean test is a single PPO run with the
pre-flip constants; it is not in the v2 matrix because it would not change any
cPPO-vs-PPO conclusion. Record it as an open question.

---

## 4. The v2 matrix, and what each comparison is licensed to claim

5 arms × 5 seeds. Arms differ from one another by exactly one variable each.

| arm | agent entry point | differs from | by |
|---|---|---|---|
| `ppo` | `rsl_rl_cfg_entry_point` | — | baseline |
| `ctrl` | `rsl_rl_ctrl_cfg_entry_point` | `cppo` | `lambda_max = 0` |
| `cppo` | `rsl_rl_cppo_cfg_entry_point` | `ctrl` | `lambda_max = 100` |
| `cppo10` | `rsl_rl_cppo10_cfg_entry_point` | `cppo` | `cost_limit = 10` |
| `sac` | `skrl_sac_cfg_entry_point` | — | different algorithm family |

Licensed readings:

- **`ctrl` vs `ppo`** — the cost of merely attaching a cost critic. Expected null after the
  A1 fix. **If it is not null, no cPPO-vs-PPO number may be reported at all**, because the
  arms still differ by something nobody has named.
- **`cppo10` vs `ctrl`** — the effect of an active safety constraint, with everything else
  held fixed. **This, and only this, is the safe-RL claim.**
- **`cppo` vs `ctrl`** — the effect of a slack constraint. Expected null. Reporting this
  null is what makes the `cppo10` result credible.
- **`cppo` vs `ppo`** — the Day-22 comparison. Now reportable only as a *decomposition*:
  whatever gap appears here should equal (ctrl−ppo) + (cppo−ctrl), and the first term is the
  artifact.
- **`sac` vs the rest** — matched on gradient steps (~30–35 k), **not** on environment
  samples (147.5 M vs 4.6 M). State the matching axis in the table caption.

### If the results come out flat

There is a real possibility that after the fix, `cppo` ≈ `ctrl` ≈ `ppo`, and only `cppo10`
separates — or that nothing separates at all. That is not a failed thesis. "A published-style
safe-RL comparison reproduced a large apparent effect that turned out to be a
gradient-clipping artifact, and the corrected comparison shows X" is a stronger and more
defensible contribution than the original headline, and it is directly in line with the
diagnostic-discipline thread already running through this project (`03c`, the 2f-85 close,
the five instrument failures). Write it that way from the start rather than trying to rescue
the old claim.

---

## 5. Addendum — Day 23 (cont.): goal-pose box widened, A2/A3 calibrations now provisional

Touhid's call: the goal-pose sampling box (`self.commands.object_pose.ranges` in
`ur5e_lift_env_cfg.py`, inherited unchanged from Isaac Lab's Franka lift defaults and never
previously overridden here) felt too narrow. Widened same day, twice, before any run against
either version — kept inside the UR5e's ~0.85 m reach envelope on purpose (a rejected draft put
the far corner at 1.02 m, unreachable):

| | pos_x | pos_y | pos_z | far-corner distance from base |
|---|---|---|---|---|
| Isaac Lab default | (0.4, 0.6) | (-0.25, 0.25) | (0.25, 0.5) | 0.82 m |
| round 1 | (0.30, 0.60) | (-0.28, 0.28) | (0.15, 0.50) | 0.83 m |
| round 2 (current) | (0.22, 0.60) | (-0.30, 0.30) | (0.10, 0.50) | 0.84 m |

Round 2 widens mostly by extending the MIN bounds toward the base (x, z), which doesn't cost any
reach margin since only the MAX bounds set the far corner; `y` has no such free direction (both
signs feed the same squared term) so it only moved by 2 cm each way, and `x_max`/`z_max` were
left untouched to protect the now-13 mm margin to the 0.85 m spec.

This is an env-level change, applied identically to all 5 arms — it does **not** reopen the
arm-isolation question in §4 (each arm still differs from its neighbor by exactly one agent-side
variable). What it does affect: **A2** and the manipulability side of **A3** both describe
threshold calibrations (`cost_limit`, `MANIP_FLOOR`) measured against the *old* box's task
difficulty. A different goal region changes how often the arm nears joint limits or low
manipulability while reaching, which changes the natural cost distribution those numbers were
set against. Both are marked STALE inline (`ur5e_lift_env.py`, `agents/rsl_rl_cppo_cfg.py`) and
must be re-evidenced — Step 4 in `RUN_CHECKLIST_v2.md` (moved before the freeze, Step 5, so
recalibration lands in the tagged commit) — before Step 7's "did `cost_limit` actually bind?"
check can be trusted. Full change record: `run_log.md`, Day 23 (cont.).

## 6. Addendum — Day 23 (cont.): lift reward re-weighted and its "lifted" gate made goal-relative

Touhid's call. Two changes to `self.rewards` in `ur5e_lift_env_cfg.py`, applied identically to
all 5 arms (env-level, does not reopen §4's arm-isolation question):

| term | weight before | weight after | "lifted" gate before | "lifted" gate after |
|---|---|---|---|---|
| `lifting_object` | 15.0 | 10.0 | `object.z > 0.04` (fixed) | `object.z >` 50% of the climb from table to this episode's goal height |
| `object_goal_tracking` | 16.0 | 15.0 | `object.z > 0.04` (fixed) | same goal-relative gate |
| `object_goal_tracking_fine_grained` | 5.0 | 5.0 (unchanged) | `object.z > 0.04` (fixed) | same goal-relative gate |

The fixed 0.04 m gate made sense when goals sat in a narrow, fairly low band; it doesn't scale
now that `pos_z` spans 0.10-0.50 m (§5). New functions `object_lifted_toward_goal` /
`object_goal_distance_relative_lift` in new project-owned `tasks/lift/rewards.py` (drop-in
replacements for Isaac Lab's `object_is_lifted` / `object_goal_distance`; vendored source
untouched, same rule as §5). All three terms switch together so "lifted" means one consistent
thing across the reward function — `lifting_object` alone using the old fixed gate while the two
tracking terms used the new one would have been an internal inconsistency.

**Combined with §5, this is now two task-defining changes stacked before the v2 matrix has run
once.** `RUN_CHECKLIST_v2.md` Step 4 covers both — recalibrate `MANIP_FLOOR` / `cost_limit`
against the config as it stands after both changes, not against either one alone.

## 7. Addendum — Day 23 (cont.): collision and joint-limit margins widened

Touhid's call, two more constants in `ur5e_lift_env.py` (`UR5eCubeLiftEnv`), applied identically
to all 5 arms:

| constant | before | after | Day-9 finding at the old value |
|---|---|---|---|
| `COLLISION_Z_FLOOR` | 0.0 m (bare table plane; only literal penetration costs) | 0.05 m (5 cm standoff above table/floor) | min link height 0.125 m -> INACTIVE by construction |
| `JOINT_LIMIT_MARGIN` | 0.10 rad (~5.7°) | 0.175 rad (~10.0°) | min joint clearance 1.39 rad -> INACTIVE by construction |

Both constraints were reported "monitored but satisfied" in the Day-9 calibration (§2 of this
document; also `run_log.md` Day 18) precisely because the old margins sat far inside the arm's
observed operating range. Widening the margins alone doesn't necessarily make either term active
— but §5's goal-pose box now reaches goals as low as `pos_z=0.10` m and as close as 0.24 m from
the base, which was never true when these were calibrated. `calibrate_manipulability.py` already
reports joint-limit-clearance and min-link-height distributions alongside `w` (built Day 9 for
exactly this purpose) — `RUN_CHECKLIST_v2.md` Step 4 now checks all three, not just
manipulability, before the freeze.

**Combined with §5 and §6, this is now three task-defining/threshold changes stacked before the
v2 matrix has run once.** None reopen §4's arm-isolation question (all env-level). If Step 4
finds collision or joint-limit have gone from ~0 cost to something non-trivial, that is itself
worth reporting — it would mean `cost_limit` (10/25) is being spent across more than the one
constraint the Day-9 Methods narrative describes, and the write-up should say so rather than
silently keep calling singularity "the" active constraint.
