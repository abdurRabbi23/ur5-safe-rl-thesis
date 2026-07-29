# Module 09 — Comparison Test (4-algorithm benchmark, redone clean)

Status: ▶ ACTIVE — this is now where the Layer 1 comparative benchmark actually happens.
Chat type: safe-RL / benchmarking
Opened: 2026-07-29 (Day 19, evening)

## ⚡ Pick-up-here (for a new session)
The 4-algorithm comparison (PPO/SAC/TD3/cPPO) planned in `03c_multialgo_benchmark.md` is being
**redone from scratch in a dedicated folder**, `Comparison test/`, instead of continuing inside
the main `ur5_grasp/` + `IsaacLab/logs/` sprawl. Reasons (Touhid's call, Day 19): a clean,
self-contained record of the full run matrix, separate from the Day 18 restart / shelved
contact-env history in the main folder.

**All decisions, hypotheses, protocols and the run matrix from `03c_multialgo_benchmark.md` still
apply unchanged.** That file remains the decision record — read it for *why*. This file is the
*where and how* for the redo.

## What "redo from scratch" means here
- **Every run in the matrix is retrained inside `Comparison test/`**, including PPO ×3 seeds —
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
└── Comparison test/       ← NEW. All comparison-test work happens here.
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
- **To get logs inside `Comparison test/`, run from `Comparison test/` as cwd and call
  `isaaclab.sh` by relative path the other way:**

```bash
cd "$HOME/Abdur_Rabbi_THESIS/Comparison test"

../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096 --seed 1 --run_name ppo_s1

../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096 --seed 1 --run_name cppo_s1 \
    --agent rsl_rl_cppo_cfg_entry_point
```

This lands runs at `Comparison test/logs/rsl_rl/ur5e_lift/<timestamp>_ppo_s1/` and
`Comparison test/logs/rsl_rl/ur5e_lift_cppo/<timestamp>_cppo_s1/` — self-contained, no cross-talk
with the main folder's `IsaacLab/logs/`. skrl runs (SAC/TD3/bridge, once configs exist) will
follow the equivalent `logs/skrl/<experiment_name>/...` pattern — confirm the exact skrl log-path
line the same way before the first SAC run, don't assume it matches rsl_rl's.

**The folder name has a space in it.** Always quote it (`"Comparison test"` or
`"$HOME/Abdur_Rabbi_THESIS/Comparison test"`) in every shell command, including inside tmux and
any `cd` in scripts. This is the single easiest thing to get bitten by here — a stray unquoted
path will silently `cd` to the wrong place or fail with a confusing "no such file" from `cd`
splitting on the space.

## Two copies of `ur5_grasp/` now exist — keep them straight
- `Abdur_Rabbi_THESIS/ur5_grasp/` — the main folder's copy. Git-tracked, tagged
  `layer1-env-freeze`. This is the **source of truth** for the env/cost-function definition.
- `Abdur_Rabbi_THESIS/Comparison test/ur5_grasp/` — a working copy, **not** git-tracked as part of
  the main repo (it's a plain filesystem copy, made 2026-07-29). Train against this one. If a real
  bug in the frozen env is found here, the fix must be ported back to the main copy — do not let
  the two silently diverge on anything that affects the comparison (env, costs, reward). New
  files that are specific to this run (skrl configs, new scripts) can live only in the
  `Comparison test/` copy.

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

## Next steps
1. Launch PPO ×3 seeds from inside `Comparison test/` (commands above), seeds 1/2/3, matching the
   main folder's naming convention (`ppo_s1`/`s2`/`s3`) so results are easy to cross-reference.
2. Launch cPPO ×3 seeds the same way.
3. Author the skrl configs (`configs/skrl_ppo_cfg.yaml`, `skrl_sac_cfg.yaml`, `skrl_td3_cfg.yaml`)
   and register the entry points in `Comparison test/ur5_grasp/tasks/lift/__init__.py` — mirrors
   03c "Next steps" item 2, just pointed at this copy.
4. Smoke-test each new algorithm at 50 iters before committing to a full run.
5. Full run matrix in cut order.
6. Extend `results/scripts/make_layer1_figs.py` (copied in already) from 2 series to 4 + seed
   bands; regenerate the results table.

## Refs
Decision record / rationale: `logbook/03c_multialgo_benchmark.md` (unchanged, still the source of
truth for *why*). This file is the *where*. Import note + folder creation: `run_log.md`, Day 19.
