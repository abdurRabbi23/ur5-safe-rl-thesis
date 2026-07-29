# Module 03c — Layer 1 Expanded: 4-Algorithm Comparative Benchmark

Status: ◻ decision record — still the source of truth for the WHY (hypothesis, fairness
protocol, cut order, schedule). The WHERE moved 2026-07-29 to a dedicated folder,
`Comparison test/`, redone from scratch there. **Read `logbook/09_comparison_test.md` for
current work; everything below is unchanged and still binding.**
Chat type: safe-RL / benchmarking
Opened: 2026-07-28 (Day 18)

## ⚡ Pick-up-here (for a new session)
Scope changed on Day 18. Layer 1 is no longer "cPPO vs PPO" — it is a **4-algorithm
comparative analysis** on the frozen weld env: **PPO, SAC, TD3, cPPO**. Contact-grasp
work (`-Contact-v0`) is SHELVED, not deleted.

**Step 0 is CLOSED (Day 18, evening) — see "Step 0 resolution" below.** Outcome: the EE
offset stays at `[0, 0, 0.16]` (verified correct); the "1.3 cm" figure was an artefact.
Only the gripper open/close inversion gets applied. Next action = apply that one constant
swap, sanity-check with `play.py`, freeze + git-tag, then launch PPO ×3 seeds.

## Goal / success criterion
A defensible four-way comparison on a single frozen environment, 3 seeds per algorithm,
showing that (a) all four solve the task, and (b) they differ materially in **safety cost**,
with only cPPO controlling it by construction.

Done = a results table + Pareto figure covering 4 algorithms × 3 seeds, with the
framework-equivalence bridge run reported, and the write-up updated.

## Decisions locked (Day 18 — don't re-litigate)
1. **Grasp stays a WELD.** Contact grasping abandoned for time. The Day-18 diagnosis
   (inverted open/close, EE frame offset) is written up as a thesis subsection justifying
   the abstraction — a negative result, not wasted work.
2. **Cost function unchanged** — the frozen 3 terms (collision keep-out, joint-limit
   margin, singularity floor), `MANIP_FLOOR=0.045`, `cost_limit=25`. **No FOV term.**
   FOV has no camera in Layer 1; it belongs to Layer 2. Adding it would invalidate the
   calibration, the results doc, all four figures and the Methods chapter.
3. **Honest constraint reporting.** Only the singularity constraint is ACTIVE. Joint-limit
   and collision are inactive by construction in this workspace. Report as
   "one binding + two monitored-and-satisfied". Never claim three active constraints.
4. **Framework split with a bridge run.** PPO + cPPO stay on rsl_rl 3.0.1 (preserves the
   Module-03 argument that the comparison differs by the constraint alone). SAC + TD3 come
   from skrl. A **skrl-PPO bridge run** anchors the two stacks against each other.
5. **3 seeds minimum, all algorithms.** The current Layer 1 is single-seed. Acceptable for a
   two-way must-pass; fatal for a four-way comparative claim.

## Registered hypothesis (state this BEFORE running — it is the actual contribution)
All four algorithms are expected to reach ~100% task success, so task success is not the
result. The result is on the safety axis:

> SAC maximises policy entropy and should therefore explore into near-singular
> configurations **more** than PPO. TD3's deterministic target policy should do the
> **opposite**. If this holds, unconstrained algorithms differ in safety as a function of
> their exploration mechanism, and only the Lagrangian formulation controls it directly.

Registering the prediction in advance is worth substantially more at defense than a
post-hoc explanation of the same bars.

## Environment changes before freeze
**APPLIED Day 19 — three changes, all in, env ready to freeze:**
- ✅ `GRIPPER_OPEN` / `GRIPPER_CLOSE` swapped in `robots/ur5e_robotiq.py`
  (0.0 = pads touching = CLOSED; 0.8 = ~85 mm = OPEN). Confirmed by measurement:
  `finger_joint = 0.796` gives an 84.4 mm pad gap against an 85 mm spec stroke.
  Cosmetic for the RL (weld latches on action sign) but visibly wrong in play videos.
  `play.py` gate PASSED — weld still latches. The stale checkpoint places sloppily
  because `joint_pos_rel` on `finger_joint` flipped sign with `default_joint_pos`;
  OOD for a checkpoint being discarded anyway. Not a blocker.
- ❌ REVERTED: arm speed cap 1.0 rad/s. **Erased the safety signal — see below.** Back to 3.14.
- ❌ REVERTED: episode length 7.0 s. Back to the base 5.0 s.
- ❌ REJECTED: EE / FrameTransformer offset change. `[0, 0, 0.16]` is verified correct.

**Net: the env is identical to `2026-07-19_16-29-57` except the gripper OPEN/CLOSE swap.**
Exactly one change from the proven pass-bar environment. `cost_limit = 25` and
`MANIP_FLOOR = 0.045` both keep their Day-9 calibrations, valid again at 250 steps.

### ⛔ DO NOT LOWER `velocity_limit_sim` — it deletes the Layer-1 result
Day 19 tried 1.0 rad/s (from 3.14) plus a 7 s episode. A full 1500-iter PPO run
(`ur5e_lift/2026-07-28_23-24-42_ppo_s1_vel1_ep7`) gave:

| | PPO 7 s / 1.0 | PPO 5 s / 3.14 |
|---|---|---|
| `viol_singularity`, iters 1400–1499 | **0.0000%** | **15.24%** |
| iters with any violation | 4.5% (all before iter 400) | 96.8% |
| converged `manipulability_min` | 0.0547 (**above** the 0.045 floor) | 0.0170 |
| `cost_total` | 0.0000 | 0.0179 |
| `lifting_object` / `position_error` | 14.44 / 0.1625 | 14.79 / 0.1582 |

Task performance is unchanged; the policy simply never approaches a singularity. **With no
violations, lambda never activates, the Lagrangian term is identically zero, and cPPO's gradient
equals PPO's.** The four-algorithm benchmark would return a cost column of zeros and no safety
axis — the registered hypothesis would have nothing to be measured against.

Cause isolated by the 5 s / 1.0 rad/s probe acting as an accidental ablation: 43.2% → 7.1% from
the speed cap alone at matched iterations, then 7.1% → 0.19% from the extra 2 s. **The speed cap
is what did it.** At π rad/s the policy can whip the wrist through ill-conditioned configurations
because recovery is cheap; at 1 rad/s it physically cannot leave a well-conditioned region.

**KEEP the run — it is a thesis result.** "Constraint violations under this cost function are a
function of commanded joint velocity; at 1 rad/s an unconstrained policy satisfies the constraint
by construction, with no task-performance penalty." A genuine sensitivity analysis that pre-empts
the obvious examiner question *"why not just slow the robot down?"* and feeds the Layer-3
hardware discussion. Goes in Discussion/Limitations, not the headline benchmark.

### ⚠️ `cost_limit` and episode length are coupled
The budget is an undiscounted **episodic** sum of a **per-step** cost, so changing
`episode_length_s` silently rescales the constraint (250 → 350 steps would have moved the
per-step allowance from 25/250 = 0.100 to 25/350 = 0.071, ~30% tighter) and voids the Day-9
calibration. Change both together or neither. This is the Lagrangian silent-failure mode from
the project notes: training looks perfectly healthy while the constraint does something other
than what Methods claims. `MANIP_FLOOR` is a per-step configuration threshold and is unaffected
by timing.

### Confirmed — no work needed
The Layer-1 task is *already* "grasp a randomly spawned cube, carry it to a randomised target".
`reset_object_position` samples uniformly over x ∈ (−0.1, 0.1), y ∈ (−0.25, 0.25) around
[0.5, 0, 0.055]; the `object_pose` command drives `object_goal_tracking`. Nothing to build.

Also: 7 s episodes do **not** cost more compute. The rsl_rl budget is
`max_iterations × num_steps_per_env × num_envs`, independent of episode length. Longer episodes
just complete fewer episodes inside the same step budget → marginally noisier episodic stats.
SAC/TD3 schedule risk unchanged.

## Step 0 resolution (Day 18 evening) — EE offset verified, change REJECTED
Ran `scripts/grasp_lift_test.py` and a new `tools/check_gripper_mount.py` on the weld env,
plus GUI inspection and paired `play.py` runs. Findings, in order of what they settle:

1. **The arm is exact.** Local-frame body positions match UR5e DH parameters to four
   decimals (`wrist_2` at −0.0996 m, `wrist_1` at [0, +0.0997, −0.0996]). The articulation
   view reads arm transforms correctly.
2. **Gripper body positions are degenerate.** All nine gripper bodies (indices 7–15,
   `base_link_0` through `right_inner_knuckle`) report *exactly* `[0, 0, 0]` in the
   `wrist_3` local frame. Nine distinct rigid bodies cannot be coincident. Yet the contact-env
   run measured an 84.4 mm pad gap — so the bodies are not statically collapsed, they are
   unreliable. **Gripper `body_pos_w` must not be trusted in this asset.**
3. **The `[0,0,0.16]` offset is correct.** `wrist_2_link` sits at local −Z, so **+Z is the
   forward tool axis**; 0.16 m is the right axis and a plausible magnitude for a 2F-85 pad
   midpoint (flange d6 ≈ 0.0996 m + gripper body ≈ 0.13 m). GUI confirms the marker lands at
   a sensible grasp height along the approach direction.
4. **The "~1.3 cm" figure is dead.** It was `[0, +0.0135, 0]` measured off collapsed gripper
   bodies — an artefact, not a TCP. `_TCP_OFFSET = (-0.013, 0, 0)` in `ur5e_contact_env_cfg.py`
   is invalid and stays in the shelved branch.
5. **The `base_link` name-collision theory is dead.** Isaac auto-disambiguates the gripper
   base to `base_link_0`. No duplicate names; both fixed joints resolve cleanly.
6. **Visual defect confirmed (case B), impact is renders only.** GUI shows the gripper drawn
   at the wrist joint with the welded cube floating 16 cm out at the TCP. Nothing in the
   deliverable figure set renders the scene — all four Layer-1 figures are matplotlib plots
   from TensorBoard scalars (`make_layer1_figs.py`).

**Why no fix:** every frozen consumer reads arm bodies only —
`MONITORED_BODIES = [forearm_link, wrist_1_link, wrist_3_link]` (indices 3, 4, 6),
`EE_BODY = wrist_3_link` (6), Jacobian over `ARM_JOINTS` only, and the weld latches to the
synthetic `ee_frame`. **No frozen consumer touches indices 7–15.** Rebuilding
`make_ur5e_robotiq_usd.py` would cost days of shelved-branch work to fix something that
appears in no deliverable. Characterise, document, freeze — do not fix.

**Thesis value:** this replaces "the gripper didn't grasp" with a stated mechanism. Written
into `Thesis_Documentation/Methods_Chapter_Layer1.md` §2 as a declared lumped-mass +
kinematic-TCP abstraction, with two consequences stated (altered wrist inertia — identical
across all runs, so not a confound; self-collision disabled — a Layer 3 caveat).

## Qualitative figure — parked to Aug 7–11 (do NOT do this before the freeze)
Paired `play.py` runs (PPO `ur5e_lift/2026-07-19_16-29-57` vs cPPO
`ur5e_lift_cppo/2026-07-19_12-05-49`, both `model_1499.pt`) show PPO in a folded,
tucked-wrist configuration and cPPO extended and open — directionally consistent with the
measured `viol_singularity` gap (16.86% vs 6.65%). Worth a figure; the results chapter is
currently 100% scalar plots.

**Not yet valid as evidence.** Three fixes required, all cheap, all belonging to the figures
block because these checkpoints are superseded by the post-freeze 3-seed runs:
- Matched `--seed` on both runs (otherwise the cube spawns differently and the pair is void).
- Matched camera pose and episode step.
- **Annotate each panel with the measured Yoshikawa `w`.** "Folded" ≠ "singular" for a 6-DOF
  arm — an examiner who knows kinematics will ask, and "it looks awkward" loses the point.
  `SafetyCostComputer.manipulability()` already computes it.
- Pick a frame where the gripper geometry does not overlap the arm links (the collapsed mount
  makes folded poses look self-intersecting; invites a question with no clean answer).

Command for the cPPO side: `play.py --agent rsl_rl_cppo_cfg_entry_point` (this also switches
the runner to `LagrangianRunner` automatically via `agent_cfg.class_name`).

Consequence: fixing these makes the existing Layer 1 numbers stale. Acceptable because every
run is being repeated for seeds anyway, and on-policy runs are cheap (~12–15 min estimated at
200k steps/s, 1500 iters × 4096 envs — confirm against TB wall-clock).

After the fixes: **freeze and git-tag the env.** Nothing in `ur5e_lift_env*.py` or `costs.py`
changes again until all 15 runs are done.

## Run matrix (15 runs)
| Algorithm | Framework | Envs | Seeds | Role |
|---|---|---|---|---|
| PPO | rsl_rl 3.0.1 | 4096 | 3 | unconstrained on-policy baseline |
| cPPO (PPO-Lagrangian) | rsl_rl 3.0.1 | 4096 | 3 | constrained — the contribution |
| SAC | skrl | 128–256 | 3 | unconstrained off-policy, max-entropy |
| TD3 | skrl | 128–256 | 3 | unconstrained off-policy, deterministic |
| PPO (bridge) | skrl | 4096 | 3 | framework-equivalence check, not a headline row |

Rough budget: 9 on-policy runs ≈ 2–3 h total; SAC/TD3 are the real cost (hours per run).
**SAC and TD3 are the entire schedule risk.**

## Fairness protocol (write this into the Methods chapter)
- Identical env, reward, obs and action spaces. Env frozen and tagged before run 1.
- **Equal budget in environment steps, not wall-clock.** Report wall-clock separately as a
  practical note, never as the comparison axis.
- skrl defaults per algorithm + a documented 3-value LR sweep each. Publish the sweep table —
  an untuned SAC baseline is the easiest possible line of attack.
- Eval: `eval_success.py`, 512 episodes, frozen policies, mean ± std over seeds.
- Headline figure: success rate vs. cost-return scatter, 4 algorithms, seeds as points.
- Secondary table: per-constraint violation breakdown (this is where cPPO should separate).

## Schedule (locked Day 18 — writing must be finished 2026-08-11)
Training wall-clock is NOT the constraint (confirmed by Touhid). The constraint is that SAC/TD3
are untested on this env and off-policy tuning is unpredictable. ~2 days of slack total.

| Date | Work | Gate |
|---|---|---|
| Jul 29 (Wed) | Step 0 offset verification → apply both cfg fixes → freeze + git-tag env | env frozen |
| Jul 30 (Thu) | PPO ×3 seeds, cPPO ×3 seeds (rsl_rl, cheap) | **pass bar restored — Layer 1 safe from here** |
| Jul 31–Aug 2 | Author skrl cfgs, 50-iter smoke tests, skrl-PPO bridge ×3 | framework equivalence shown |
| Aug 3–4 | SAC ×3 seeds | |
| Aug 5–6 | TD3 ×3 seeds | **HARD CUT: Aug 6 EOD** |
| Aug 7–11 | Figures (2→4 series + seed bands), results doc, Methods chapter | writing done |

**Cut rule:** if TD3 is not tuned and running by Aug 6 EOD, it is dropped and the thesis reports
three algorithms with the omission stated in Limitations. Do not negotiate with this on Aug 6.
The same rule applies to SAC on Aug 4 if skrl off-policy turns out to be a fight — PPO + cPPO +
one off-policy baseline is still a complete comparative result.

## Cut order (deadline valve — decide the cut date in advance and honour it)
1. Env fixes + freeze + tag
2. PPO × 3 seeds
3. **cPPO × 3 seeds ← pass bar restored here.** Everything after this is upside.
4. skrl-PPO bridge × 3
5. SAC × 3
6. TD3 × 3 ← **first thing cut**

If TD3 is not tuned by the cut date, report three algorithms and state the omission in
Limitations. That is an unremarkable sentence in a thesis. A rushed, untuned TD3 row is not —
it is a hole an examiner walks straight through.

## Next steps
0. ✅ **DONE — Step 0, EE offset verified.** Change rejected; `[0, 0, 0.16]` is correct.
   See "Step 0 resolution" above for the evidence chain.
1. ✅ **DONE (Day 19) — gripper OPEN/CLOSE swap applied**, `play.py` weld gate passed.
   Speed cap and 7 s episode were tried and reverted (see above). The env is now one change
   away from `2026-07-19_16-29-57`. **No re-probe needed** — this is the proven env.
1b. **Freeze + git-tag.** Commit the shelved contact-env files separately FIRST so the tag
   points at a clean tree. Nothing in `ur5e_robotiq.py`, `ur5e_lift_env*.py` or `costs.py`
   changes after this.
2. Author `agents/skrl_ppo_cfg.yaml`, `skrl_sac_cfg.yaml`, `skrl_td3_cfg.yaml`; register
   `skrl_cfg_entry_point` / `skrl_sac_cfg_entry_point` / `skrl_td3_cfg_entry_point` on both
   gym ids in `tasks/lift/__init__.py`.
3. Short smoke run per new algorithm (50 iters) before committing to full runs — especially
   off-policy replay-memory sizing at high `num_envs`.
4. Full run matrix, in cut order.
5. Regenerate figures (`results/scripts/make_layer1_figs.py` needs extending from 2 to 4
   series + seed bands) and rewrite `results/03_*` and the Methods chapter.

## Open questions
- Off-policy `num_envs` and `RandomMemory` sizing in skrl on this env — untested. Biggest
  unknown in the matrix; resolve it in Step 3, not during a full run.
- ~~Whether the existing single-seed Layer 1 runs can be reused as seed 1~~ — the EE offset
  does NOT move (Step 0), so the only env change is the gripper constant swap, which the weld
  latch ignores (it triggers on action sign, not joint value). Reuse is now *technically*
  defensible. **Still recommended: re-run.** The runs are cheap, and "all 15 runs came from
  one tagged commit" is a cleaner sentence at defense than an explained exception.

## Refs
Supersedes `03_cppo_benchmark.md` (kept as the historical 2-algorithm record).
Day 18 diagnosis + restart: `run_log.md`.
