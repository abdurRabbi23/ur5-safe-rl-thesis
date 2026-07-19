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

## Current status (updated 2026-07-16, Day 9)
Roadmap week ~5–9 zone. Module 02 done (PPO retrained on the weld env, play-verified). Module 03
(**Layer 1**) is coded, smoke-tested, and calibrated: cPPO = PPO-Lagrangian on rsl_rl 3.0.1 with a
separate cost critic; the active safety constraint is **manipulability/singularity** (`MANIP_FLOOR=0.045`,
`cost_limit=25`). The full Lagrangian mechanism is verified working on a 50-iter probe.
**IMMEDIATE NEXT: run the 2 full trainings (cPPO + matched PPO baseline at floor 0.045) → overlay
→ results table.** Commands + what-to-watch: `logbook/03b_cppo_runbook.md` (Steps 6–7);
deep state + locked settings: `logbook/03_cppo_benchmark.md`.

## Modules
| File | Work-stream | Status |
|---|---|---|
| `01_env_setup.md` | Stack install, Isaac validation, reaching tasks | ✅ done |
| `02_grasp_env.md` | UR5e lift env, weld grasp, PPO baseline | ▶ weld done; PPO retrain pending |
| `03_cppo_benchmark.md` | Safety constraints + cPPO vs PPO (**Layer 1 deliverable**) | ▶ coded+calibrated; run 2 full trainings |
| `04_layer2_ibvs.md` | IBVS visual loop, RL-tuned image Jacobian (Layer 2) | ⏳ later |
| `05_layer3_sim2real.md` | ROS 2 transfer to physical UR5e + RH-P12-RN (Layer 3) | ⏳ later |
| `06_writing.md` | Thesis chapters, figures, defense prep | ◻ ongoing |

## Key pointers
- Code package: `ur5_grasp/` (git-tracked; separate from the `IsaacLab/` clone).
- Deep technical state (asset paths, joint names, gripper decisions): `ur5_grasp/CONTEXT.md`.
- Trained PPO checkpoint: `IsaacLab/logs/rsl_rl/ur5e_lift/2026-07-12_18-54-03/model_1499.pt`.
