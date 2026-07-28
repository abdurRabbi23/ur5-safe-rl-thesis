# Thesis Logbook — INDEX (read this first)

Front door for the UR5 Safe RL Grasping thesis. Any new chat should start here.

## How I work across chats
Each Cowork chat is a separate session, but they all share **this folder** as memory.
To start a new chat with full context:
1. Open the chat inside the **THESIS 4200** project.
2. Connect this folder (`Abdur_Rabbi_THESIS`).
3. Paste the block from **`logbook/HANDOFF.md`** — it carries the current next action and the
   list of settled questions. Keep it overwritten whenever the next action changes.

Two layers of memory:
- **`run_log.md`** — the daily timeline (what happened each day, chronological).
- **`logbook/NN_*.md`** — one file per work-stream (deep context: goals, decisions,
  files, next steps). Use these for "how / why did I do X".

Rule of thumb: work happens in a module → update that module file + add a dated line to
`run_log.md`.

## Project one-liner
Safe Adaptive IBVS with constrained RL (cPPO) for precision grasping on a UR5e, sim →
real. Three layers: L1 safe-RL grasping in sim (must-pass), L2 IBVS visual loop
(stretch), L3 sim-to-real on the physical UR5e (optional). See project instructions.

## Current status (updated 2026-07-28, Day 18)
**SCOPE CHANGE — Layer 1 expanded to a 4-algorithm comparative benchmark (PPO, SAC, TD3, cPPO).**
Active module is now `logbook/03c_multialgo_benchmark.md` — read that, not the section below, for
current work. Contact-grasp (`-Contact-v0`) is SHELVED; the grasp stays a WELD and the Day-18
gripper diagnosis becomes a thesis subsection justifying the abstraction. Cost function is
unchanged and frozen (3 terms, one binding: `MANIP_FLOOR=0.045`, `cost_limit=25`; **no FOV term**).
Framework: PPO+cPPO stay on rsl_rl, SAC+TD3 come from skrl, with a skrl-PPO bridge run for
framework equivalence. 3 seeds per algorithm.
**Step 0 CLOSED (Day 18 evening):** EE offset verified — `[0,0,0.16]` is correct, the "1.3 cm"
figure was an artefact of collapsed gripper bodies, and the gripper USD is NOT being rebuilt
(visual defect only; no frozen consumer reads gripper bodies). Only ONE env change goes into the
freeze: the `GRIPPER_OPEN`/`GRIPPER_CLOSE` swap.
**Day 19 (Jul 29) — env settled, ONE change from the proven env.** Gripper OPEN/CLOSE convention
corrected (`play.py` weld gate passed). A 1.0 rad/s arm speed cap and a 7 s episode were tried and
**REVERTED**: a full 1500-iter PPO run gave `viol_singularity` = **0.0000%** converged (vs 15.24%)
with `manipulability_min` above the floor — a slow arm satisfies the constraint by construction,
lambda never activates, and cPPO degenerates to PPO. ⛔ **Do not lower `velocity_limit_sim`.**
That run is KEPT as a sensitivity analysis for Discussion. `cost_limit=25` and `MANIP_FLOOR=0.045`
retain their Day-9 calibrations. Details in `03c`.
**IMMEDIATE NEXT: commit shelved contact files → freeze + git-tag → launch PPO ×3 seeds.**

### Historical status (2026-07-20, Day 10) — the 2-algorithm result
Roadmap week ~9–10 zone. **Module 03 (Layer 1) is COMPLETE — the must-pass deliverable is DONE.**
Both full 1500-iter trainings (num_envs=4096) are run: cPPO = PPO-Lagrangian on rsl_rl 3.0.1 with a
separate cost critic, plus a matched unconstrained PPO baseline, both at `MANIP_FLOOR=0.045`,
`cost_limit=25`. **Headline (2026-07-19): cPPO matches PPO on task (both 100% lift; reward 166.3 vs
167.2) while spending ~60% less time near singularities (viol 6.65% vs 16.86%) — safety at no task
cost.** Results table: `results/03_cppo_vs_ppo_results.docx`. The four Layer 1 figures are generated
(2026-07-20) into `Thesis_Documentation/assets/` (PNG+PDF), script `results/scripts/make_layer1_figs.py`.
**IMMEDIATE NEXT: commit on the lab PC (eval_success.py + TB logs + tb_csv/), then start Layer 2 (IBVS)
or push thesis writing.** Deep state + locked settings: `logbook/03_cppo_benchmark.md`;
reproduce commands: `Thesis_Documentation/06_Results_and_Experiments.md`.

## Modules
| File | Work-stream | Status |
|---|---|---|
| `01_env_setup.md` | Stack install, Isaac validation, reaching tasks | ✅ done |
| `02_grasp_env.md` | UR5e lift env, weld grasp, PPO baseline | ✅ done (weld + PPO baseline retrained, play-verified) |
| `03_cppo_benchmark.md` | Safety constraints + cPPO vs PPO (2-algorithm Layer 1) | ✅ done — superseded by 03c, kept as historical record |
| `03c_multialgo_benchmark.md` | 4-algorithm comparative benchmark: PPO/SAC/TD3/cPPO (**Layer 1 deliverable**) | ▶ ACTIVE — start here |
| `04_layer2_ibvs.md` | IBVS visual loop, RL-tuned image Jacobian (Layer 2) | ⏳ later |
| `05_layer3_sim2real.md` | ROS 2 transfer to physical UR5e + RH-P12-RN (Layer 3) | ⏳ later |
| `06_writing.md` | Thesis chapters, figures, defense prep | ◻ ongoing |
| `07_documentation.md` | Beginner replicate-from-scratch guide (`Thesis_Documentation/`) | ▶ ongoing, parallel |

## Key pointers
- Beginner docs: `Thesis_Documentation/` (start at `00_START_HERE.md`) — the cleaned-up,
  replicate-from-scratch version of these notes; kept in sync via `logbook/07_documentation.md`.
- Code package: `ur5_grasp/` (git-tracked; separate from the `IsaacLab/` clone).
- Deep technical state (asset paths, joint names, gripper decisions): `ur5_grasp/CONTEXT.md`.
- Trained checkpoints (weld env, pre-freeze — superseded once the 3-seed runs land):
  - PPO:  `IsaacLab/logs/rsl_rl/ur5e_lift/2026-07-19_16-29-57/model_1499.pt`
  - cPPO: `IsaacLab/logs/rsl_rl/ur5e_lift_cppo/2026-07-19_12-05-49/model_1499.pt`
  `play.py` defaults to `--agent rsl_rl_cfg_entry_point` → PPO. For cPPO pass
  `--agent rsl_rl_cppo_cfg_entry_point` (this also selects `LagrangianRunner`).
