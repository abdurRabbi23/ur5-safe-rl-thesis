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

## Current status (updated 2026-07-29, Day 19 evening)
**Layer 1 env is FROZEN and TAGGED** (`layer1-env-freeze`, commit `b8f0727`). Contact-grasp
(`-Contact-v0`) is SHELVED; the grasp stays a WELD, the Day-18 gripper diagnosis is a thesis
subsection justifying the abstraction. Cost function frozen (3 terms, one binding:
`MANIP_FLOOR=0.045`, `cost_limit=25`; no FOV term). Arm speed 3.14 rad/s / 5.0 s episodes — do
NOT lower `velocity_limit_sim` (kills the safety signal, see `03c`).

**The 4-algorithm comparative benchmark (PPO/SAC/TD3/cPPO) is being redone from scratch in a
dedicated folder, `Comparison test/`, as of Day 19 evening — read `logbook/09_comparison_test.md`
for current work.** `03c_multialgo_benchmark.md` is now the decision record only (hypothesis,
fairness protocol, cut order, schedule — all still binding); `09` is where the runs actually
happen now. Nothing is reused from the main folder's earlier PPO ×3 seeds — this folder's matrix
is trained fresh, start to finish, on its own copy of `ur5_grasp/`.

**IMMEDIATE NEXT (inside `Comparison test/`): launch PPO ×3 seeds, then cPPO ×3 seeds.**

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
| `03c_multialgo_benchmark.md` | 4-algorithm comparative benchmark — decisions/hypothesis/protocol | ◻ decision record — still binding, see `09` for current work |
| `09_comparison_test.md` | Same benchmark, redone from scratch in `Comparison test/` (**Layer 1 deliverable, current work**) | ▶ ACTIVE — start here |
| `04_layer2_ibvs.md` | IBVS visual loop, RL-tuned image Jacobian (Layer 2) | ⏳ later |
| `05_layer3_sim2real.md` | ROS 2 transfer to physical UR5e + RH-P12-RN (Layer 3) | ⏳ later |
| `06_writing.md` | Thesis chapters, figures, defense prep | ◻ ongoing |
| `07_documentation.md` | Beginner replicate-from-scratch guide (`Thesis_Documentation/`) | ▶ ongoing, parallel |
| `08_project_context.md` | KUET admin details, supervisor, references, role/working-principles (imported from the old Claude Project) | ◻ reference — read once, revisit if a row changes |

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
