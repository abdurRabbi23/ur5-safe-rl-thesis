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

## Current status (updated 2026-07-15, Day 8)
Roadmap week ~1–5 zone. Day-7 PPO baseline was **reward-hacked** (robot threw the cube — the
2f-85 closed loop can't grip in sim). Fixed with a **proximity-weld grasp** (escape hatch;
hold-verified). IsaacLab pinned to the **v2.3.0 tag**. **IMMEDIATE NEXT: retrain PPO on the
weld env → visual play.py check → then start Module 03** (cPPO-vs-PPO safety benchmark).
See `logbook/02_grasp_env.md` Day-8 correction + `run_log.md` Day 8 for the full story.

## Modules
| File | Work-stream | Status |
|---|---|---|
| `01_env_setup.md` | Stack install, Isaac validation, reaching tasks | ✅ done |
| `02_grasp_env.md` | UR5e lift env, weld grasp, PPO baseline | ▶ weld done; PPO retrain pending |
| `03_cppo_benchmark.md` | Safety constraints + cPPO vs PPO (**Layer 1 deliverable**) | ▶ next |
| `04_layer2_ibvs.md` | IBVS visual loop, RL-tuned image Jacobian (Layer 2) | ⏳ later |
| `05_layer3_sim2real.md` | ROS 2 transfer to physical UR5e + RH-P12-RN (Layer 3) | ⏳ later |
| `06_writing.md` | Thesis chapters, figures, defense prep | ◻ ongoing |

## Key pointers
- Code package: `ur5_grasp/` (git-tracked; separate from the `IsaacLab/` clone).
- Deep technical state (asset paths, joint names, gripper decisions): `ur5_grasp/CONTEXT.md`.
- Trained PPO checkpoint: `IsaacLab/logs/rsl_rl/ur5e_lift/2026-07-12_18-54-03/model_1499.pt`.
