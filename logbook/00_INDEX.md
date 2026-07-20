# Thesis Logbook — INDEX (read this first)

Front door for the UR5 Safe RL Grasping thesis. Any new chat should start here.

## How I work across chats
Each Cowork chat is a separate session, but they all share **this folder** as memory.
To start a new chat with full context:
1. Open the chat inside the **THESIS 4200** project.
2. Connect this folder (`Abdur_Rabbi_THESIS`).
3. Say: *"Read `logbook/00_INDEX.md` and `logbook/<module>.md`, then continue with X."*

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

## Current status (updated 2026-07-20, Day 10)
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
| `03_cppo_benchmark.md` | Safety constraints + cPPO vs PPO (**Layer 1 deliverable**) | ✅ DONE — Layer 1 PASS (benchmark + figures) |
| `04_layer2_ibvs.md` | IBVS visual loop, RL-tuned image Jacobian (Layer 2) | ⏳ later |
| `05_layer3_sim2real.md` | ROS 2 transfer to physical UR5e + RH-P12-RN (Layer 3) | ⏳ later |
| `06_writing.md` | Thesis chapters, figures, defense prep | ◻ ongoing |
| `07_documentation.md` | Beginner replicate-from-scratch guide (`Thesis_Documentation/`) | ▶ ongoing, parallel |

## Key pointers
- Beginner docs: `Thesis_Documentation/` (start at `00_START_HERE.md`) — the cleaned-up,
  replicate-from-scratch version of these notes; kept in sync via `logbook/07_documentation.md`.
- Code package: `ur5_grasp/` (git-tracked; separate from the `IsaacLab/` clone).
- Deep technical state (asset paths, joint names, gripper decisions): `ur5_grasp/CONTEXT.md`.
- Trained PPO checkpoint: `IsaacLab/logs/rsl_rl/ur5e_lift/2026-07-12_18-54-03/model_1499.pt`.
