# Module 09 — Comparison Test (4-algorithm benchmark, redone clean)

Status: ▶ ACTIVE — this is now where the Layer 1 comparative benchmark actually happens.
Chat type: safe-RL / benchmarking
Opened: 2026-07-29 (Day 19, evening)

## ⚡ Pick-up-here (for a new session)

> ## ▶ EXECUTION STATUS (2026-08-01, Day 24) — Steps 4-6+8 done for a 3-of-5-arm subset; Step 9 partial
>
> **Full results:** `Comparison_test/results/MATRIX_V2_PARTIAL_3ARM.md` (+ same content as
> `MATRIX_V2_PARTIAL_3ARM_report.pdf`, English — no Bengali font available in the sandbox to
> render a Bangla PDF). This block is the short version.
>
> **Step 4 (recalibrate) — DONE.** First attempt accidentally calibrated against a 50-iteration
> smoke checkpoint (bogus — an almost-untrained policy); caught before acting on it, redone
> against a proper 1500-iter probe. `MANIP_FLOOR: 0.045 → 0.06`. `JOINT_LIMIT_MARGIN` held at
> 0.175 but **reclassified from inactive to ACTIVE** (33.7% baseline violation, now the
> *larger* of the two constraints) — the widened goal box did this. `COLLISION_Z_FLOOR` held at
> 0.05, confirmed still inactive. `cost_limit` held at 25 — later shown to be a highly
> seed-variable question, not a fixed slack/binding verdict (see below).
>
> **Step 5 (freeze) — DONE.** Commit `567e4c0`, tag `matrix-v2`.
>
> **Step 6 (matrix) — PARTIAL: 3 of 5 arms, but 10 seeds not 5.** `ppo` / `ctrl` / `cppo` only,
> seeds 1-5 **and** 50-54 (Touhid asked for the extra 5 mid-session). `cppo10` and `sac` are
> **NOT in this batch** — "does an actively-binding budget help" is still unanswered; only
> "does a budget that's borderline-to-binding depending on seed help" is in scope here. All 30
> checkpoints verified on disk.
>
> **Step 7 (the decisive check) — PASSED, unusually strongly.** ctrl vs ppo is not just
> statistically null, it is **bitwise identical** — checkpoint-hash-verified (all 68 of ppo_s1's
> actor+critic tensors found byte-identical inside ctrl_s1's checkpoint), reproduced
> independently across all 10 seeds, and reproduced again at evaluation time. The A1
> gradient-clip fix is confirmed as strongly as this kind of check can confirm anything.
>
> **Step 8 (eval) — DONE for this batch**, scoped script `run_eval_matrix_v2_3arm.sh` (not the
> shared `run_eval_policy_v2.sh` — that one still expects `cppo10`/`sac`). 3 arms x 10 seeds x
> eval-seeds 101/102/103, 1000 episodes each. Found and filtered 20 stale rows in the
> append-only `eval_policy_results.csv` left over from the old pre-freeze/pre-audit sweep —
> filter by checkpoint path date, not by label, if reading that file directly.
>
> **Headline results:** (1) ctrl≡ppo, see Step 7. (2) cPPO's main measured effect is collapsing
> **seed-to-seed safety variance**, not just the mean — `ctrl`'s natural episodic cost ranges
> 1.8-164.5 across seeds (~90x), `cppo` holds every seed to 9.5-24 (~2.5x), at ~0.7% reward cost.
> (3) Pooled over 30,000 eval episodes/arm: true singularity crossings (w<1e-4) 1.343%
> (ppo/ctrl) vs 0.250% (cppo); joint-limit touched at all 5.37% vs **0.00%, all 10 seeds**;
> goal-reach <1cm 94.28% vs 96.49% (no task cost). Honest counter-note: cppo's single
> worst-episode manipulability was *not* shallower than ppo/ctrl's — the constraint reduces
> frequency/consistency of near-singular excursions, not the rare worst-case depth.
>
> **Written up (2026-08-01, Day 24 cont., separate session):**
> `Thesis_Documentation/Results_Chapter_Layer1.md` — Chapter 4 prose from this batch. Two things
> that came out of drafting it and matter here:
> (a) **`MATRIX_V2_PARTIAL_3ARM.md` §4.1's λ sentence was wrong and is retracted in place.** That
> row is λ at the *final iteration*, not a trajectory; λ must have engaged hard on the high-cost
> seeds and relaxed to 0 (else, by §2's argument, those seeds would be bitwise identical to `ctrl`,
> which they are not). **Per-iteration λ curves were never extracted for this batch — do not quote
> a λ peak or engagement iteration for any seed** until `Loss/cost_lambda` is pulled from the event
> files.
> (b) **Number discrepancy, unresolved:** this block and the Day-24 `run_log` entry both say
> `ctrl`'s cost range tops at **164.5**; `MATRIX_V2_PARTIAL_3ARM.md` §4.1's per-seed table maxes at
> **162.3** (seed 3). The chapter uses 162.3 (source of truth, and the per-seed table is the more
> likely to be right). One of the two is a typo — reconcile.
>
> **NOT yet done:** `cppo10` + `sac` (this batch deliberately excludes them); archiving the 3
> superseded pre-audit `cppo_s1/s2/s3` run dirs still sitting in `logs/rsl_rl/ur5e_lift_cppo/`
> under the same labels as the new ones (checkpoint-selection logic resolves correctly via
> mtime, verified, but this is a standing risk, not a fix); `skrl_ppo_cfg.yaml` still unverified
> under skrl 2.1.0 (open since Day 22-23).
>
> **Correction 2026-08-01 (Day 24, cont. — separate session, cfg prep only, no runs).** The
> "NOT yet done" bullet above is wrong about where the stale runs live. Checked directly: the 3
> superseded pre-audit `cppo_s1/s2/s3` runs are in `logs/rsl_rl/ur5_lift_cppo_v0/` (note: no
> "e" in "ur5", plus a `_v0` suffix) — a **different directory** from `logs/rsl_rl/ur5e_lift_cppo/`,
> which holds only the 10 new matrix-v2 runs. They do not collide and never did; the "archive
> before training" concern in `logbook/NEXT_SESSION_cppo15.md` Rule 3 does not apply. Left in
> place (Touhid's call) rather than moved/deleted — corrected here so it isn't re-flagged as a
> live risk later.
>
> **`cppo15` arm created this session, replacing the registered `cppo10`, at
> `cost_limit = 15`.** New class `UR5eLiftCPPO15RunnerCfg` in `agents/rsl_rl_cppo_cfg.py`,
> entry point `rsl_rl_cppo15_cfg_entry_point` registered on `-v0` and `-Play-v0`. Differs from
> the parent `cppo` cfg by `cost_limit` only (25.0 → 15.0), verified by `git diff`. Deviation
> from `ALGORITHM_AUDIT.md` §4's registered `cppo10` design, justification re-verified against
> `MATRIX_V2_PARTIAL_3ARM.md` §4.1's actual per-seed table (not assumed): a budget of 15 binds
> on seeds 1/3/4/5/52/53 and is slack on 2/50/51/54; a budget of 10 binds on the identical
> partition (min natural cost across all 10 seeds is 1.8, seed 51 — only a budget below that
> binds everywhere). Full reasoning in the class docstring and `logbook/NEXT_SESSION_cppo15.md`.
>
> **Freeze:** commit `684c595` (Day-24 batch results/thesis/logbook — output only, no code) +
> a second commit adding the `cppo15` cfg, tag `matrix-v2-cppo15`. Both from this session
> directly (git operations don't need the lab PC's GPU, same as the Day-24 freeze).
>
> **NOT run — this sandbox has no GPU/Isaac Sim (`nvidia-smi`, `import torch` both fail here,
> confirmed this session).** Steps 3 (smoke) through 8 (eval) of `RUN_CHECKLIST_v2.md`, and the
> results file / thesis §4.3/§4.7 update, all remain for Touhid to run on the lab PC.
> `run_cppo15_seeds.sh` (smoke + full 10-seed training) and `run_eval_cppo15.sh` (eval, scoped
> to the new checkpoints — `ctrl` doesn't need re-running) are written and `bash -n` clean, not
> executed. If picking this up cold: Step 1 resolve-check still needs running first (substitute
> `rsl_rl_cppo15_cfg_entry_point`), then `./run_cppo15_seeds.sh smoke`, then the full run.
>
> **The retrospective λ half of item 5 is DONE, no GPU needed.** `summarize_runs.py` already
> wrote per-iteration `Loss/cost_lambda` for all 10 `cppo`(25) runs to `results/tb_csv/` last
> session; read directly this session. Every seed shows an early transient spike (λ 14–48 around
> iteration 50–60) that decays to 0 by ~iteration 70–115 for 8 of 10 seeds; only seeds 5 and 53
> stay engaged almost to the end. Full table and corrected framing:
> `MATRIX_V2_PARTIAL_3ARM.md` §4.1 (dated update, replaces the "not yet measured" note). The
> `cppo15` half of item 5 (log λ per iteration as part of that run) still needs the actual
> training to exist first.

> ## Historical — EXECUTION STATUS (2026-07-31, Day 23, cont.), superseded by the block above
>
> Working through `Comparison_test/RUN_CHECKLIST_v2.md` on the lab PC (9 steps, reordered —
> freeze is step 5, not step 1; see the reordering update further down).
>
> **Step 1 — PASSED.** Hit two lab-PC/environment bugs first (nothing to do with the config
> changes below), both fixed:
> 1. `isaaclab`/`isaaclab_rl`/`isaaclab_tasks` were stale-editable-installed against an
>    abandoned second folder `~/Abdur_Rabbi_Thesis_updated` (Touhid confirmed not in use).
>    Fixed: `cd ~/Abdur_Rabbi_THESIS/IsaacLab && ./isaaclab.sh -i`.
> 2. Step 1's one-liner imported `rsl_rl_cppo_cfg` directly, which needs `omni.*` modules —
>    only importable AFTER Isaac Sim's Kit runtime launches. Fixed by adding
>    `AppLauncher(headless=True)` to the top of the script (`RUN_CHECKLIST_v2.md` Step 1 has
>    the corrected version). Pattern confirmed against Isaac Lab's own test suite.
>
> **Step 2 — PASSED.** All 4 smoke trains (ppo/ctrl/cppo/cppo10, 50 iters, seed 1) finished
> clean, no traceback. Two findings (full detail: `run_log.md`, Day 23 cont.):
> - All 4 arms produced numerically IDENTICAL reward/safety metrics — expected since
>   `cost_lambda` is still 0.0 for cppo/ctrl/cppo10 this early (Lagrangian = stock PPO at
>   λ=0). Good early sign for the A1 gradient-clip fix, but NOT the decisive check — that's
>   Step 7, on the full 1500-iter/5-seed data.
> - `safety/cost_collision` is now nonzero (~0.0014-0.0019 violation rate) — every historical
>   run before today shows exactly `0.0000` for this term. Direct confirmation that
>   `COLLISION_Z_FLOOR: 0.0 -> 0.05` (§7 addendum) activated a previously-dormant constraint.
>   Small so far; Step 4 needs to characterize it properly. `cost_joint_limit` stayed `0.0`.
> - Today's smoke reward (~7-8) is far below the pre-Day-23 smoke baseline (65.47) — expected
>   given the widened goal box + goal-relative lift gate, not a regression.
>
> **Step 3 — PASSED, after fixing three real skrl-2.1.0 incompatibilities in `skrl_sac_cfg.yaml`**
> (the config had never been executed before today). Installed skrl is 2.1.0, not the 1.4.3 the
> file was written against. All three fixed and recorded inline in the yaml + `RUN_CHECKLIST_v2.md`
> + `run_log.md` (Day 23 cont.): (1) Hydra override path needed `agent.trainer.timesteps=200`, not
> `trainer.timesteps=200` — the composed config nests everything under `agent.`; (2) the 1.4.3
> compound token `OBSERVATIONS_ACTIONS` no longer exists in 2.x and silently mangled into an
> undefined `observations_taken_actions` — fixed to `concatenate([OBSERVATIONS, ACTIONS])`;
> (3) skrl 2.x's SAC agent config is now a typed dataclass, not an open dict — rewrote
> `actor_learning_rate`/`critic_learning_rate`/`entropy_learning_rate` into one `learning_rate`
> triple and renamed `state_preprocessor(_kwargs)` to `observation_preprocessor(_kwargs)`.
> Confirmed on the lab PC: 200/200 timesteps, ~64 it/s, no traceback. **Open item, not blocking:**
> `skrl_ppo_cfg.yaml` (PPO bridge arm) was authored against the same 1.4.3 API and has NOT been
> run under 2.1.0 yet — check it the same way before Step 6, don't assume it's fine by analogy.
>
> **NEXT: Step 4 (recalibration — the real test of whether
> `MANIP_FLOOR`/`cost_limit`/`COLLISION_Z_FLOOR`/`JOINT_LIMIT_MARGIN` need adjusting after
> today's four task-defining changes).**

> ## 🛑 Update 2026-07-31 (Day 23, LATE) — THE 2026-07-30 MATRIX IS WITHDRAWN
>
> **An algorithm audit found the cPPO-vs-PPO comparison confounded. Do not quote any number
> from `results/LAYER1_RESULTS_3seed.md` or `results/LAYER1_FINDINGS.md`, including the
> numbers in the Day-23 block immediately below this one.** Full working:
> `Comparison_test/results/ALGORITHM_AUDIT.md`. Short version:
>
> `Loss/cost_lambda` sat at 0.0 for essentially every iteration of all three cPPO runs
> (cppo_s2: 0.0 at *every* iteration). At lambda = 0 the Lagrangian update is algebraically
> stock PPO, so the constraint cannot explain the gap — but a single global
> `clip_grad_norm_` spanning the cost critic could, and did: it shrank the actor's step on
> every update in the cPPO arm only. cPPO was PPO with a quieter optimiser.
>
> Second problem: `cost_limit = 25` is *above* the converged natural cost (7-29), so the
> constraint never bound. Third: the 100 %/0 % goal-reach saturation is a ceiling created by
> the weld (the cube's pose *is* the TCP's pose), not a property of either algorithm.
>
> **The rerun is 5 arms x 5 seeds**, adding a control (`ctrl`, lambda pinned to 0) that
> isolates the artifact from the constraint, and a binding budget (`cppo10`).
> **Start here:** `Comparison_test/RUN_CHECKLIST_v2.md`, step 1. (Freeze moved to step 5 —
> see the Day-23-cont. reordering note below; don't freeze first anymore.)
> Launchers: `run_matrix_v2.sh`, `run_eval_policy_v2.sh`.
> `run_ppo_cppo_seeds.sh` and `run_eval_policy.sh` are superseded — do not run them.
>
> The licensed comparisons are `ctrl vs ppo` (the artifact; must come out null) and
> `cppo10 vs ctrl` (the constraint alone — **this is the thesis claim**).
>
> **Update 2026-07-31 (Day 23, cont.) — goal-pose box widened (twice), one new checklist step.**
> `ur5e_lift_env_cfg.py` now overrides the goal-pose sampling box (was inheriting Isaac Lab's
> Franka defaults unchanged), widened once and then further on request, before either version
> ever ran: current `pos_x=(0.22,0.60), pos_y=(-0.30,0.30), pos_z=(0.10,0.50)`, far corner
> 0.84 m — kept inside the UR5e's ~0.85 m reach on purpose (~13 mm margin; a rejected first
> draft put it at 1.02 m). Env-level, applies to all 5 arms — does not affect arm isolation.
> **Does** make `MANIP_FLOOR` and `cost_limit` provisional (both calibrated Day 9 against the
> old, narrower box) — **run `RUN_CHECKLIST_v2.md` Step 4 before Step 5 (freeze) and Step 6
> (the matrix)** to re-evidence them. Full record: `run_log.md`, Day 23 (cont.);
> `ALGORITHM_AUDIT.md` §5.
>
> **Update 2026-07-31 (Day 23, cont.) — reward terms re-weighted, "lifted" now goal-relative.**
> `lifting_object` 15.0 -> 10.0; `object_goal_tracking` 16.0 -> 15.0;
> `object_goal_tracking_fine_grained` stays 5.0. All three now gate on 50% of the climb from the
> table to *this episode's* goal height (new `tasks/lift/rewards.py`), replacing a fixed
> `object.z > 0.04 m` that didn't scale once the goal box's `pos_z` spans 0.10-0.50 m. Env-level,
> all 5 arms, arm isolation unaffected. Stacks with the goal-pose widening above as a second
> task-defining change before the matrix runs once — Step 4 now recalibrates against both
> together. Full record: `run_log.md`, Day 23 (cont.); `ALGORITHM_AUDIT.md` §6.
>
> **Update 2026-07-31 (Day 23, cont.) — checklist reordered: freeze is now step 5, not step 1.**
> Recalibration (step 4) can edit tracked files (`MANIP_FLOOR`, `cost_limit`); freezing before
> that would tag the wrong commit. New order: 1 arms-resolve, 2 smoke trains, 3 SAC smoke,
> 4 recalibrate, 5 freeze, 6 matrix, 7 decisive check, 8 eval, 9 report. Full record:
> `run_log.md`, Day 23 (cont.).
>
> **Update 2026-07-31 (Day 23, cont.) — collision/joint-limit margins widened, third change
> stacked.** `COLLISION_Z_FLOOR` 0.0 -> 0.05 m; `JOINT_LIMIT_MARGIN` 0.10 -> 0.175 rad
> (`ur5e_lift_env.py`). Both were "monitored but satisfied" at Day 9 (min link height 0.125 m,
> min joint clearance 1.39 rad), so may still land inactive — but the widened goal box (pos_z
> down to 0.10 m) changes the operating range enough that Step 4 now explicitly checks both
> distributions, not just `MANIP_FLOOR`. Env-level, all 5 arms, arm isolation unaffected. Full
> record: `run_log.md`, Day 23 (cont.); `ALGORITHM_AUDIT.md` §7 (also fixes a structural bug
> from the earlier §5/§6 edit today — content was misordered, now corrected).

> **Update 2026-07-31 (Day 23) — SUPERSEDED by the block above; kept as a dated record.**
> **TD3 is CUT.** The benchmark is three algorithms: PPO / cPPO / SAC. Run matrix 15 → 12.
> Decision record: `03c_multialgo_benchmark.md`, top of file.
>
> **The evaluation was rebuilt.** The Day-22 safety percentages (83.72% / 42.27% singularity,
> 30.27% / 0.85% joint-limit) are tail-means of *training* TensorBoard scalars — a stochastic,
> still-learning policy — and cannot support a claim about the frozen policy. New
> `Comparison_test/ur5_grasp/scripts/eval_policy.py` + `run_eval_policy.sh` count violations
> per episode during evaluation, report the goal-distance distribution instead of one hard
> 5 cm threshold, run 4 eval seeds × 1000 episodes, and load skrl checkpoints as well as
> rsl_rl (clearing the Day-22 blocker). Written and compiling; NOT yet run.
>
> **"PPO 0.00% vs cPPO 100.00%" is explained.** ppo_s2 genuinely converged badly (reward 90.7
> vs 166.4). The eval merely rendered it as a step function. Full working: `run_log.md` and
> `Comparison_test/run_log_new.md`, both dated 2026-07-31.
>
> **New trap:** `Metrics/object_pose/position_error` tracks `wrist_3_link`, not the cube. Its
> ~0.16 m floor is the `ee_frame` offset. Never quote it as task error.
>
> **Everything below predates this and lists TD3 — read those parts as historical.**

The 4-algorithm comparison (PPO/SAC/TD3/cPPO) planned in `03c_multialgo_benchmark.md` is being
**redone from scratch in a dedicated folder**, `Comparison_test/`, instead of continuing inside
the main `ur5_grasp/` + `IsaacLab/logs/` sprawl. Reasons (Touhid's call, Day 19): a clean,
self-contained record of the full run matrix, separate from the Day 18 restart / shelved
contact-env history in the main folder.

**All decisions, hypotheses, protocols and the run matrix from `03c_multialgo_benchmark.md` still
apply unchanged.** That file remains the decision record — read it for *why*. This file is the
*where and how* for the redo.

## What "redo from scratch" means here
- **Every run in the matrix is retrained inside `Comparison_test/`**, including PPO ×3 seeds —
  even though PPO ×3 already completed once in the main folder (`IsaacLab/logs/rsl_rl/ur5e_lift/
  ..._ppo_s1/s2/s3`). Those are **not** reused. This folder's results must all come from runs
  launched inside it, on its own copy of the code, so the whole 15-run matrix has one consistent
  provenance.
- The env itself does **not** change — it's the frozen `layer1-env-freeze` state (tag `b8f0727`
  in the main repo). Nothing in `costs.py`, `ur5e_lift_env_cfg.py`, or `ur5e_robotiq.py` gets
  re-opened for edits as part of this move. If a bug is found, fix it here AND port the fix back
  to the main `ur5_grasp/` (see "Two copies" below).

## Folder layout
```
Abdur_Rabbi_THESIS/
├── IsaacLab/              ← main folder, used AS-IS (the Isaac Sim install + isaaclab.sh).
│                            Not duplicated — too large, no need to.
├── ur5_grasp/             ← main folder's frozen code (layer1-env-freeze). Reference only,
│                            do not train against this copy for the comparison test.
└── Comparison_test/       ← NEW. All comparison-test work happens here.
    ├── ur5_grasp/         ← working COPY of the frozen code (copied 2026-07-29, matches
    │                         b8f0727 exactly at copy time). Train against THIS copy.
    ├── configs/            ← skrl YAML configs (sac, td3, ppo-bridge) go here once written —
    │                         see 03c "Next steps" item 2 for the entry-point names needed.
    ├── results/            ← results tables + figures. `results/scripts/make_layer1_figs.py`
    │                         copied in as a starting point — needs extending from 2 series to
    │                         4 + seed bands (03c "Next steps" item 5).
    ├── docs/               ← empty, for a Methods/results write-up specific to this run, if kept
    │                         separate from `Thesis_Documentation/`.
    ├── runs/               ← placeholder, NOT where logs actually land — see the gotcha below.
    │                         Ignore/remove; kept only so the intent is visible in git history.
    └── logs/               ← created AUTOMATICALLY by rsl_rl / skrl the first time you train.
                               This is where the real run data lives (see below).
```

## ⚠️ Technical gotcha: log location is cwd-relative, not script-location-relative
Checked directly in the code (2026-07-29): `train.py` / `eval_success.py` /
`calibrate_manipulability.py` all compute
```python
log_root_path = os.path.abspath(os.path.join("logs", "rsl_rl", agent_cfg.experiment_name))
```
— a **relative** path resolved against the process's **current working directory**, not against
where `train.py` itself lives. `isaaclab.sh` does not `cd` anywhere before launching Python
(confirmed: it just runs `${python_exe} "$@"` from wherever it was invoked). So:

- The old workflow (`cd IsaacLab/ && ./isaaclab.sh -p ../ur5_grasp/scripts/train.py`) writes logs
  to `IsaacLab/logs/rsl_rl/...` because cwd = `IsaacLab/`.
- **To get logs inside `Comparison_test/`, run from `Comparison_test/` as cwd and call
  `isaaclab.sh` by relative path the other way:**

```bash
cd "$HOME/Abdur_Rabbi_THESIS/Comparison_test"

../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096 --seed 1 --run_name ppo_s1

../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096 --seed 1 --run_name cppo_s1 \
    --agent rsl_rl_cppo_cfg_entry_point
```

This lands runs at `Comparison_test/logs/rsl_rl/ur5e_lift/<timestamp>_ppo_s1/` and
`Comparison_test/logs/rsl_rl/ur5e_lift_cppo/<timestamp>_cppo_s1/` — self-contained, no cross-talk
with the main folder's `IsaacLab/logs/`. skrl runs (SAC/TD3/bridge, once configs exist) will
follow the equivalent `logs/skrl/<experiment_name>/...` pattern — confirm the exact skrl log-path
line the same way before the first SAC run, don't assume it matches rsl_rl's.

**Folder renamed 2026-07-30 (Day 22): `Comparison test` → `Comparison_test`.** The space is
gone, so shell quoting is no longer required and the whole class of "stray unquoted path
silently `cd`s to the wrong place" bugs is retired. Note that `run_log.md` and
`run_log_new.md` entries dated before Day 22 still show the old spaced name — those are a
dated record and were deliberately NOT rewritten. Every instructional file and all code
were updated.

## ⚠️ Second log-path gotcha: `experiment_name` comes from the AGENT cfg, not the task
Found Day 22 when `smoke_sg` (SimpleGripper, `ur5e_simple_gripper.usd`) landed in
`logs/rsl_rl/ur5e_lift/` — **the same directory as the weld-env PPO runs**, because both use
`UR5eLiftPPORunnerCfg`, whose `experiment_name = "ur5e_lift"`. The task ID does not appear in
the log path at all. So two runs on physically different robots become indistinguishable by
directory, and anything that globs `logs/rsl_rl/ur5e_lift/*` — `make_layer1_figs.py`, the
cross-run table in `summarize_runs.py`, a future reader — will silently average two different
environments into one comparison.

Mitigated (not fixed) by moving the two SimpleGripper runs to
`logs/rsl_rl/ur5e_lift_simplegripper/`. **The real fix, if the SimpleGripper is ever trained
beyond a smoke test, is a separate agent cfg with its own `experiment_name`.** Until then:
`--run_name` is the only thing distinguishing envs in `ur5e_lift/`, so never reuse a run name
across tasks. Verify which env a run actually used by reading
`<run_dir>/params/env.yaml` — rsl_rl dumps the resolved cfg there, and grepping it for the
USD filename is definitive.

## Two copies of `ur5_grasp/` now exist — keep them straight
- `Abdur_Rabbi_THESIS/ur5_grasp/` — the main folder's copy. Git-tracked, tagged
  `layer1-env-freeze`. This is the **source of truth** for the env/cost-function definition.
- `Abdur_Rabbi_THESIS/Comparison_test/ur5_grasp/` — a working copy. Train against this one. If a real
  bug in the frozen env is found here, the fix must be ported back to the main copy — do not let
  the two silently diverge on anything that affects the comparison (env, costs, reward). New
  files that are specific to this run (skrl configs, new scripts) can live only in the
  `Comparison_test/` copy.

> **Correction (Day 22).** This section used to say the `Comparison_test/` copy is "**not**
> git-tracked as part of the main repo (a plain filesystem copy)". That is FALSE — checked
> directly: `git ls-files Comparison_test` returns tracked files and `git status` lists five
> *modified* tracked files under it. The folder is in the repo. It matters because the
> fairness protocol's "env frozen and tagged before run 1" is achievable here with an ordinary
> commit + tag, rather than needing a separate provenance mechanism.

## Run matrix (unchanged from 03c, restated for convenience)
| Algorithm | Framework | Envs | Seeds | Status |
|---|---|---|---|---|
| PPO | rsl_rl 3.0.1 | 4096 | 3 | not started here (main-folder run exists but is NOT reused) |
| cPPO (PPO-Lagrangian) | rsl_rl 3.0.1 | 4096 | 3 | not started |
| PPO (skrl bridge) | skrl | 4096 | 3 | not started — needs `skrl_ppo_cfg.yaml` |
| SAC | skrl | 128–256 | 3 | not started — needs `skrl_sac_cfg.yaml` + entry-point registration |
| TD3 | skrl | 128–256 | 3 | not started — needs `skrl_td3_cfg.yaml` + entry-point registration |

Cut order, fairness protocol, registered hypothesis, and the schedule (writing due 2026-08-11,
TD3 hard cut 2026-08-06 EOD) are all unchanged — see `03c_multialgo_benchmark.md`.

## ⚠️ Day 20–21: the run matrix is BLOCKED on a gripper rebuild
The Robotiq 2f-85 asset was abandoned on Day 20 (closed 4-bar linkage folded into a foreign
articulation → degenerate body positions ~~+ missing finger colliders~~) and replaced with a
hand-built simple two-finger prismatic gripper, which gave this project its first real
contact grasp.

> **Correction (Day 22).** The "missing finger colliders" half of that is **FALSE** and was
> already retracted on Day 18 (`run_log.md` lines 186–188): the pads DO have 10 enabled
> convexHull colliders; "no collider" was a false alarm from a traversal that omitted
> `TraverseInstanceProxies` on an instanceable asset. The Day-20 entry reinstated the false
> alarm as fact and Day 21 + `docs/HANDOFF_robotiq_2f85.md` inherited it. Only the degenerate
> body positions survive as an objection — and that finding contradicts itself (all nine
> gripper bodies at `[0,0,0]`, yet an 84.4 mm pad gap measured between two of them in the same
> session) and has never been diagnosed. See Day 22 in `Comparison_test/run_log_new.md`.
> **This does not change the Day-21 scope call:** the SimpleGripper remains the Layer-1
> deliverable and the matrix does not wait for the 2f-85.

Day 21 then fixed two faults in the SimpleGripper build: it was mounted along
`wrist_3_link`'s **+Z** and came out sideways (the +Z figure was inherited from the frozen
weld env and had never been validated — a weld env teleports the cube to whatever point the
TCP names, so it could not have caught this), and the grasp point sat at the finger midpoint
rather than between the tips.

All gripper geometry now lives in **one** file, `Comparison_test/ur5_grasp/robots/
gripper_geometry.py`, imported by the USD builder, the training env cfg, the grasp test and
the live demo. The tool axis is measured by `tools/check_wrist_frame.py`, not assumed.

**Steps 1–2 below cannot start until the gripper clears its checks** — see `HANDOFF.md` for
the three lab-PC runs, in order, and `run_log_new.md` (2026-07-30, Day 21) for the full
reasoning. The matrix will then target `-SimpleGripper-v0`, not the old weld `-v0`.

## ✅ Day 22: the gripper gate is CLEARED. The matrix is unblocked.
`make_ur5e_simple_gripper_usd.py` re-run on the lab PC — section 3 reads **`error 0.00 mm`,
"OK. The mount transform PhysX resolved matches what was authored"**, with `left_finger_joint`
parked at exactly 0.0 (the Day-21 fix to the check working as intended). Together with the
Day-21 close (mount + TCP confirmed by eye in the GUI), the SimpleGripper is DONE.

**Remaining before the matrix launches** — mechanical, no open questions:
1. `simple_gripper_grasp_test.py` on `-SimpleGripper-Play-v0`, `--num_envs 1`
2. ~50-iter smoke train on `-SimpleGripper-v0`
3. re-freeze + re-tag the Layer-1 env; repoint the matrix at `-SimpleGripper-v0`
4. PPO ×3, then cPPO ×3

## ❌ Day 22: the Robotiq 2f-85 is CLOSED — permanently, on schedule grounds
Reopened this session under `docs/HANDOFF_robotiq_2f85.md` and closed the same day. **Not
because the asset was shown to be broken** — that was never established, and the evidence
leans the other way:
- the pads have **10 enabled `convexHull` colliders** (fresh run) — reason #2 for the Day-20
  abandonment is definitively FALSE, confirming the Day-18 retraction;
- at `finger_joint = 0.8` the pads separated by **84.9 mm** against an 85 mm spec stroke — the
  4-bar linkage WORKS and PhysX resolved distinct pad transforms.

The diagnostic written for it (`tools/check_robotiq_pads.py`) printed a confident STOP verdict
from **three unvalidated premises** — the project's fifth instrument failure, documented in
full at the top of that script and in `run_log_new.md` Day 22. Its verdict line must not be
trusted; its collider audit can be.

**Open hypothesis, recorded and never tested:** nothing may be wrong with the 2f-85 at all, and
every `[0,0,0]` in this thread — Day 18's included — may be the same class of instrument bug.
Closed anyway: three sessions consumed, two more rounds needed for a validated TCP, deliverable
already working, TD3 hard cut Aug 6, writing due Aug 11, and Layer-3 hardware is an RH-P12-RN.

**Thesis value:** the honest negative result is stronger than the old one — *one stated reason
was a retracted false alarm reinstated as fact three sessions later, the other was never
diagnosed, and the workstream closed because the deliverable succeeded without it.* Methods
paragraph on diagnostic discipline, not on a broken asset.

## ✅ Day 22 (cont.): grasp test PASSED, and the matrix is repointed at the WELD env `-v0`

`ur5_grasp/tools/simple_gripper_grasp_report.txt` (01:19, found unread on disk):
fingers stalled at a **62.8 mm pad gap** against a 30 mm closed target — obstructed by the
cube, not passing through — and the cube held at z = +0.268 for 140 steps after the pin
released. Every authored segment resolved to its designed value to 4 dp. **The SimpleGripper
is a working contact grasp.** (Cube is therefore ~63 mm across.)

**Decision (Touhid, Day 22): the 15-run matrix runs on `Isaac-Lift-Cube-UR5e-v0`**, the frozen
weld env — reversing the Day-20/21 repoint to `-SimpleGripper-v0`. `-v0` is frozen, tagged, and
already produced the Day-10 headline; the 2f-85 is genuinely present and driven in it, with only
the *grasp* abstracted as a weld (declared in Methods §2). `03c`'s locked schedule had these six
runs finishing today and the count is zero of fifteen, so the deciding factor is schedule, not
fidelity. The SimpleGripper is reduced to a ~50-iter smoke train and stands as a separately
demonstrated real-contact result.

⚠️ **Fragility on the launch path — fix before run 1.** `tasks/lift/__init__.py` registers the
SimpleGripper cfg alongside `-v0`, so importing the task package imports `gripper_geometry.py`,
which raises `FileNotFoundError` at import time if `assets/wrist_frame.json` is missing — and
that file is currently **untracked**. The frozen weld env's importability therefore depends on an
uncommitted JSON. Commit it as part of the freeze.

**Instruments added Day 22** (both verified as far as a GPU-free sandbox allows; see
`run_log_new.md` for what was and was not verified):
- `run_ppo_cppo_seeds.sh` — rewritten. No longer aborts the batch on one failed run; captures
  per-run exit codes and wall-clock, verifies each run by its checkpoint on disk rather than by
  stdout, writes a flushed `logs/batch_report.txt`.
- `ur5_grasp/tools/summarize_runs.py` — new. TensorBoard event files → flushed text report +
  per-tag CSVs in `results/tb_csv/`. Replaces the manual, unreproducible export that
  `make_layer1_figs.py` still expects from a dead sandbox path.

## Next steps
0. **Freeze:** commit `assets/wrist_frame.json` + Day-21/22 changes, then re-tag. Fairness
   protocol requires the env frozen and stamped before run 1.
1. **Smoke trains, 50 iters each, in this order** — `-v0` PPO, `-v0` cPPO, then
   `-SimpleGripper-v0`. Do not skip the `-v0` pair: it has never been trained inside this folder,
   and both `train.py` and `tasks/lift/__init__.py` have changed since the freeze.
2. `./run_ppo_cppo_seeds.sh` — PPO ×3 then cPPO ×3 on `-v0`, seeds 1/2/3, naming
   `ppo_s1`/`s2`/`s3` and `cppo_s1`/`s2`/`s3` to match the main folder.
3. `../IsaacLab/isaaclab.sh -p ur5_grasp/tools/summarize_runs.py` — read the reports.
4. ~~Author the skrl configs~~ **PPO bridge DONE (Day 22 evening, code only).** Corrections to
   what this item originally said: the configs do **not** go in `configs/` — skrl yaml entry
   points resolve package-relative (`"<module>:<file>.yaml"`), so they live in
   `ur5_grasp/tasks/lift/agents/`. And the stock `IsaacLab/scripts/reinforcement_learning/skrl/
   train.py` cannot be used directly: it never imports `ur5_grasp.tasks`, so our task is
   unregistered. Use `ur5_grasp/scripts/train_skrl.py` (stock + four marked TOUHID edits).
   Entry points registered on `-v0` and `-Play-v0`. `skrl_sac_cfg.yaml` / `skrl_td3_cfg.yaml`
   are registered but **not authored** — that is the remaining schedule risk.
5. Smoke-test each new algorithm at 50 iters before committing to a full run. For the bridge:
   `--algorithm PPO --num_envs 128 --max_iterations 50`. **First** confirm `skrl.__version__`
   ≥ 1.4.3 under `isaaclab.sh`; nothing below it has been executed anywhere yet.
6. Remaining runs in cut order (skrl-PPO bridge ×3, SAC ×3, TD3 ×3).
7. Extend `results/scripts/make_layer1_figs.py` from 2 series to 4 + seed bands and **repoint its
   hardcoded `DATA` path** (currently a dead sandbox path) at `results/tb_csv/`, which
   `summarize_runs.py` now populates automatically; regenerate the results table.

## Refs
Daily timeline scoped to this folder: `Comparison_test/run_log_new.md` (dual-tracked — every entry there also appears in the project-wide `run_log.md`). Read it first if picking up work only inside `Comparison_test/`.

Decision record / rationale: `logbook/03c_multialgo_benchmark.md` (unchanged, still the source of
truth for *why*). This file is the *where*. Import note + folder creation: `run_log.md`, Day 19.
