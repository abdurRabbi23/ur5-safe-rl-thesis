# Module 09 — Comparison Test (4-algorithm benchmark, redone clean)

Status: ▶ ACTIVE — this is now where the Layer 1 comparative benchmark actually happens.
Chat type: safe-RL / benchmarking
Opened: 2026-07-29 (Day 19, evening)

## ⚡ Pick-up-here (for a new session)
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
4. Author the skrl configs (`configs/skrl_ppo_cfg.yaml`, `skrl_sac_cfg.yaml`, `skrl_td3_cfg.yaml`)
   and register the entry points in `Comparison_test/ur5_grasp/tasks/lift/__init__.py` — mirrors
   03c "Next steps" item 2, just pointed at this copy.
5. Smoke-test each new algorithm at 50 iters before committing to a full run.
6. Remaining runs in cut order (skrl-PPO bridge ×3, SAC ×3, TD3 ×3).
7. Extend `results/scripts/make_layer1_figs.py` from 2 series to 4 + seed bands and **repoint its
   hardcoded `DATA` path** (currently a dead sandbox path) at `results/tb_csv/`, which
   `summarize_runs.py` now populates automatically; regenerate the results table.

## Refs
Daily timeline scoped to this folder: `Comparison_test/run_log_new.md` (dual-tracked — every entry there also appears in the project-wide `run_log.md`). Read it first if picking up work only inside `Comparison_test/`.

Decision record / rationale: `logbook/03c_multialgo_benchmark.md` (unchanged, still the source of
truth for *why*). This file is the *where*. Import note + folder creation: `run_log.md`, Day 19.
