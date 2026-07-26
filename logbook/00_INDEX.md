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

## Current status (updated 2026-07-26, Day 16)
**Layer 1 (Module 03) COMPLETE** — cPPO vs PPO benchmark done and written up: cPPO matches PPO on
task (both 100% lift; reward 166.3 vs 167.2) while spending ~60% less time near singularities
(viol 6.65% vs 16.86%). Results: `results/03_cppo_vs_ppo_results.docx`; figures in
`Thesis_Documentation/assets/`.
**Layer 2 (Module 04) CLOSED** — IBVS pipeline built (mount, detection, self-measured image
Jacobian, ~50% centroid-error reduction); servo-convergence limitation documented as future work.
**Module 05 now ACTIVE** — the real hardware gripper (ROBOTIS RH-P12-RN) is imported into sim and
**grasps with real contact forces, no weld** (`TCP_OFFSET = 0.130`, pad faces close to within
0.1 mm of the cube width). This closes the largest sim-to-real gap on the simulation side.
**IMMEDIATE NEXT: `logbook/HANDOFF_next.md`** — run the geometry check, then train PPO on
`Isaac-Lift-Cube-UR5e-RHP12-v0` and compare against the Layer 1 weld baseline. That comparison
turns the weld from an unexamined shortcut into a measured, justified abstraction.
Deep state: `logbook/05_layer3_sim2real.md`.

## Modules
| File | Work-stream | Status |
|---|---|---|
| `01_env_setup.md` | Stack install, Isaac validation, reaching tasks | ✅ done |
| `02_grasp_env.md` | UR5e lift env, weld grasp, PPO baseline | ✅ done (weld + PPO baseline retrained, play-verified) |
| `03_cppo_benchmark.md` | Safety constraints + cPPO vs PPO (**Layer 1 deliverable**) | ✅ DONE — Layer 1 PASS (benchmark + figures) |
| `04_layer2_ibvs.md` | IBVS visual loop, RL-tuned image Jacobian (Layer 2) | ✅ built + documented |
| `05_layer3_sim2real.md` | RH-P12-RN gripper (DONE, contact grasp) + ROS 2 transfer (Layer 3) | ▶ ACTIVE |
| `06_writing.md` | Thesis chapters, figures, defense prep | ◻ ongoing |
| `07_documentation.md` | Beginner replicate-from-scratch guide (`Thesis_Documentation/`) | ▶ ongoing, parallel |

## Key pointers
- Beginner docs: `Thesis_Documentation/` (start at `00_START_HERE.md`) — the cleaned-up,
  replicate-from-scratch version of these notes; kept in sync via `logbook/07_documentation.md`.
- Code package: `ur5_grasp/` (git-tracked; separate from the `IsaacLab/` clone).
- Deep technical state (asset paths, joint names, gripper decisions): `ur5_grasp/CONTEXT.md`.
- Two robots now exist: `ur5e_robotiq_2f85.usd` (Layer 1, weld grasp, FROZEN) and
  `ur5e_rhp12.usd` (RH-P12-RN, real contact grasp). Task ids `Isaac-Lift-Cube-UR5e-v0` vs
  `Isaac-Lift-Cube-UR5e-RHP12-v0`.
- Trained PPO checkpoint: `IsaacLab/logs/rsl_rl/ur5e_lift/2026-07-12_18-54-03/model_1499.pt`.
