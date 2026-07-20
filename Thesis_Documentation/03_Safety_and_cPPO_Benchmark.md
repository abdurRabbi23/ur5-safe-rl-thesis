# 03 — Safety Constraints & the cPPO vs PPO Benchmark

**Status:** ✅ COMPLETE (2026-07-19) · **Layer:** 1 (the must-pass deliverable — **PASS**) · **Roadmap:** Weeks 9–10

**Goal of this section:** add **safety constraints** to the grasp task and train **cPPO** (a *safe*
RL algorithm) so the arm learns to grasp *while keeping unsafe behaviour under a fixed budget*. The
headline result is a fair **cPPO vs plain-PPO** comparison on the identical environment. This is the
single most important result in the thesis.

**Where we are right now (as of 2026-07-19, Day 9–10):** DONE. Both full 1500-iter runs (cPPO +
matched PPO baseline, num_envs=4096) are complete and the benchmark is written up. **Headline: cPPO
matches PPO on the task (both 100% lift; final reward 166.3 vs 167.2) while cutting time spent near
singularities by ~60% (viol 6.65% vs 16.86%) — safety at no measurable task cost.** Results table:
`results/03_cppo_vs_ppo_results.docx`; the four figures are in `assets/` (see §6 / the Results page).
The Steps 6–7 sections below are kept as the reproducible procedure, now annotated with real numbers.

---

## 1. The idea in plain words

Plain RL (PPO) chases **reward** and nothing else. If throwing the arm into a risky pose earns more
reward, PPO will do it. That's unacceptable for a real robot.

**Constrained RL** adds a second signal: a **cost** for unsafe behaviour, plus a **budget** (the
`cost_limit`) the policy must stay under. The algorithm then answers a harder question: *"get as
much reward as possible **without** letting total cost exceed the budget."*

The specific method is **cPPO = PPO-Lagrangian**. A **Lagrange multiplier** (called `lambda`, λ)
acts like an automatically-tuned "safety tax": when the policy is over budget, λ rises and reward is
penalised more heavily for unsafe acts; when the policy is safely under budget, λ falls. λ tunes
*itself* during training — you don't hand-set it.

> **Beginner analogy.** PPO is a driver told only "get there fast". cPPO is a driver told "get there
> fast, but keep your speeding tickets under N per month" — and λ is how much each ticket *hurts*,
> automatically dialled up when you're collecting too many.

---

## 2. What counts as "unsafe" — the three cost terms

Defined in `ur5_grasp/safe_rl/costs.py` (`SafetyCostComputer`). Each term is **0 while safe** and
grows **smoothly** as the arm enters a danger zone (smoothness matters — it gives the cost critic a
usable gradient to learn from). The three are summed into one aggregate cost, so there is **one**
Lagrange multiplier.

1. **Collision keep-out** — penalises any monitored arm link dropping **below the table plane**
   (`z_floor`). Self-collisions are off in sim and there are no contact sensors, so this geometric
   proxy is the honest cheap choice.
2. **Joint-limit margin** — penalises any arm joint entering the last `joint_margin` radians before
   its soft limit, normalised to [0, 1] per joint.
3. **Singularity floor (the star)** — penalises the **Yoshikawa manipulability**
   `w = sqrt(det(J · Jᵀ))` of the 6-DOF arm Jacobian dropping below `manip_floor`.

> **Beginner note — what a singularity is.** At certain arm configurations the robot momentarily
> *loses the ability to move in some direction* (like your arm at full stretch — you can't reach
> further without repositioning your whole body). Mathematically the **Jacobian** becomes
> near-singular and `w` drops toward 0. Near-singular poses cause huge, jerky joint velocities and
> are genuinely dangerous. Keeping `w` above a floor keeps the arm in well-conditioned poses. This
> constraint is also the natural bridge to the **IBVS** theme in Layer 2, which is why we lead with
> it.

The computer also exposes each term's **mean** and a 0/1 **violation rate** for logging, so the
thesis can report each constraint separately even though they share one budget.

---

## 3. Why we built cPPO on rsl_rl (not OmniSafe/skrl)

**Decision (Day 9):** the PPO baseline already runs on **`rsl_rl` 3.0.1**. Building cPPO on the
*same trainer and hyperparameters* means the only difference between baseline and safe policy is the
safety machinery — the cleanest possible comparison. Using a different library (OmniSafe/skrl) would
introduce dozens of confounding differences and make the benchmark unconvincing.

Variant chosen: **separate cost critic** (textbook PPO-Lagrangian), not the single-critic penalty
shortcut. A "critic" is the network that predicts future return; we add a **second** critic that
predicts future *cost*, so reward and cost are estimated independently.

**The new package `ur5_grasp/safe_rl/`:**

| File | Role |
|------|------|
| `costs.py` | the three safety cost terms (above) |
| `actor_critic_cost.py` | adds the second (cost) critic network |
| `rollout_storage_cost.py` | stores costs and computes cost-GAE (advantage for cost) |
| `ppo_lagrangian.py` | combined advantage `(A_r − λ·A_c)/(1+λ)` + dual-ascent update of λ |
| `lagrangian_runner.py` | the training loop that ties it together |

The env now emits a per-step `extras["cost"]` (read by the trainer) and logs `safety/*`
diagnostics. The cPPO config is `UR5eLiftCPPORunnerCfg` (experiment name `ur5e_lift_cppo`),
registered under `rsl_rl_cppo_cfg_entry_point`. **The PPO baseline path is untouched** — you opt
into cPPO with `--agent rsl_rl_cppo_cfg_entry_point`.

---

## 4. Calibration — making the constraints actually "bite"

**Why this step exists.** A safety benchmark is meaningless if unconstrained PPO never breaks the
rules — then cPPO has nothing to prove. So the thresholds must be set from the *real trained
baseline* such that plain PPO **does** violate them a meaningful fraction of the time. This is the
subtle, essential step.

**4a. Manipulability floor.** Run the calibration script on the trained baseline:

```bash
cd ~/Abdur_Rabbi_THESIS/IsaacLab
./isaaclab.sh -p ../ur5_grasp/scripts/calibrate_manipulability.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 64 --steps 400
```

**What it reports:** the distribution (percentiles) of manipulability `w`, joint-limit clearance,
and minimum link height across a baseline rollout, plus baseline violation rates.

**Calibrated results (25.6k samples, Day 9):**

| Quantity | Distribution | Decision |
|----------|--------------|----------|
| Manipulability `w` | min .021 / mean .055 / max .114 | **`MANIP_FLOOR = 0.045`** (~p10–p25 ⇒ ~20% baseline violation) → **the ACTIVE constraint** |
| Joint-limit clearance | min 1.39 rad (never near a limit) | INACTIVE by construction; keep margin 0.10 as *monitored-but-satisfied* |
| Min link height | min 0.125 m above table | INACTIVE; keep floor 0.0 as *monitored-but-satisfied* |

**Sanity check:** `w` should be a smooth spread of small positive numbers (≈0.01–0.1), **not**
all-zero and **not** 1e6. A degenerate value means the Jacobian index is wrong. (This was the
biggest untested risk; the smoke test confirmed `manipulability_mean = 0.11`, so the Jacobian
extraction in `costs.py` is correct.)

> **Thesis framing (honest and still valid).** Lead with **manipulability/singularity as the active
> constraint**. Report joint-limit and collision as **monitored constraints that stayed satisfied**.
> This is a truthful result — a cPPO benchmark on one biting constraint plus two satisfied ones is
> perfectly defensible.

**4b. Collision floor.** Confirm the table-top height. In the play GUI, or by probing
`robot.data.body_pos_w[..., 2]` at rest, check the table top is z ≈ 0; if not, set
`COLLISION_Z_FLOOR` in `ur5_grasp/tasks/lift/ur5e_lift_env.py` accordingly.

---

## 5. Setting the cost budget (`cost_limit`)

**Why:** the budget is the target the arm must get *under*. Too loose and cPPO looks identical to
PPO; too tight and the arm gives up on grasping. We set it from a short unconstrained probe.

**Probe (50 iters, 4096 envs) result (Day 9):** clean, no NaN, ~200k steps/s. The Lagrangian
mechanism is confirmed fully working:

- `cost_singularity` rises 0.1 → 0.4 (the constraint **bites** at floor 0.045).
- `mean_episode_cost` climbs 6.7 → 74 as the policy learns to grasp near singular poses.
- `cost_lambda` self-engages 0 → 6.85 (controlled, **not** railed at its max).
- reward 58 → 48 — the safety-vs-reward trade-off is visibly present.

**Decision: `cost_limit = 25`** (set in `rsl_rl_cppo_cfg.py`) — roughly a 65% cut versus the natural
~70+ cost, costing ~17% reward. Tighten later only if needed.

> **Important benchmark note.** The Day-7 PPO checkpoint (`model_1499`) was trained at the *old*
> `MANIP_FLOOR = 0.02`, where its cost curve is ~0 and **not comparable**. The unconstrained PPO
> baseline must be **re-run at floor 0.045** so PPO and cPPO share the exact same cost definition.

---

## 6. The runbook — step by step to the result

Run everything on the lab PC, from `~/Abdur_Rabbi_THESIS/IsaacLab`, **inside tmux**
(`tmux new -s thesis_abrabbi`; detach Ctrl-b then d). Steps 1–5 are ✅ done; **Steps 6–7 are the
only remaining work.**

**Step 3 — cPPO smoke test (5 iters, the cheap bug-catcher):**

```bash
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --agent rsl_rl_cppo_cfg_entry_point \
    --headless --num_envs 64 --max_iterations 5
```

*Pass checklist (all must hold):*
- Startup prints `Cost Critic MLP: Sequential(...)` once (the 2nd critic built).
- `Resolved observation sets:` shows `policy: ['policy']` and `critic: ['policy']`.
- All 5 iterations run with **no traceback**.
- The log block shows `cost_value_function`, `cost_lambda`, `mean_episode_cost`.
- `safety/cost_total`, `safety/viol_joint_limit`, `safety/manipulability_mean` appear.
- `mean_reward` is finite (no NaN).

*Expected-but-fine at 5 iters:* `cost_lambda = 0` and `mean_episode_cost = 0` — episodes rarely
finish in 5×24 steps, so λ hasn't moved yet. Plumbing is what's under test, not learning.
✅ This smoke test **passed** (Day 9, `logbook/smoke_cppo.log`).

**Step 6 — Full cPPO run** ✅ DONE (2026-07-19; 1500 iters, num_envs=4096):

```bash
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --agent rsl_rl_cppo_cfg_entry_point \
    --headless --num_envs 4096
```

Watch the **Lagrangian dynamics** — this *is* the story of the thesis:

| Scalar | Healthy behaviour |
|--------|-------------------|
| `Loss/mean_episode_cost` | starts high, **trends down toward `cost_limit` (25)** |
| `Loss/cost_lambda` | rises while over budget, **settles** as cost approaches budget (must NOT pin at `lambda_max = 100`) |
| `Train/mean_reward` | still learns to grasp — lower than PPO is OK; collapse to ~0 is not |
| `safety/viol_*` | violation rates drop versus the PPO baseline |

*Red flags & fixes:* λ railed at 100 (budget too tight / `lambda_lr` too high) → loosen
`cost_limit` or drop `lambda_lr`. Reward collapses to 0 while cost → 0 (over-constrained) → same
fix.

*Observed (healthy):* `mean_episode_cost` peaked ≈ 80.2 → driven to 2.24 (well under the budget of
25); `cost_lambda` rose to a 16.7 peak (never near the 100 cap) → relaxed to 0; `viol_singularity`
fell from a 51.7% peak to 6.65%; final reward 166.3. No railing, no collapse.

**Step 6b — Matched PPO baseline at floor 0.045** ✅ DONE (so both use the same cost definition):

```bash
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096
```

**Step 7 — The benchmark deliverable** ✅ DONE:

```bash
tensorboard --logdir logs/rsl_rl --port 6006 --bind_all
```

`logs/rsl_rl/ur5e_lift` (PPO) and `logs/rsl_rl/ur5e_lift_cppo` (cPPO) overlay automatically. Report,
per run: **success rate**, **sample efficiency** (reward vs steps), and **constraint-violation
rate / cost** (`safety/viol_*`). Fill the numbers into `results/03_cppo_vs_ppo_results.docx` and
`06_Results_and_Experiments.md`. Success measured by `eval_success.py` over 512 episodes.

**The headline (CONFIRMED):** cPPO keeps constraint violations under budget while grasping just as
well as PPO — both lift on 100% of episodes at essentially identical reward (166.3 vs 167.2), while
cPPO spends ~60% less time near singularities (6.65% vs 16.86%). PPO grasps but violates freely.

---

## 7. What "done" looks like for this section

- [x] Safety costs implemented and Jacobian extraction verified.
- [x] cPPO (separate cost critic) implemented on rsl_rl 3.0.1.
- [x] Thresholds calibrated so the constraint bites (~20% baseline violation).
- [x] `cost_limit = 25` validated by a 50-iter probe.
- [x] Full cPPO run complete (Step 6).
- [x] Matched PPO baseline at floor 0.045 complete (Step 6b).
- [x] Overlay + results table filled (Step 7); four figures generated to `assets/`.

✅ Steps 6–7 finished (2026-07-19), real numbers and the final table are in — **Layer 1 is complete.**
