# Module 02 — UR5e Grasp Env + PPO Baseline

Status: ✅ done — grasp reliable via proximity weld (hold-verified); PPO baseline retrained on the
weld env and play-verified (reused as the cPPO env and the Module 03 unconstrained baseline).
Chat type: sim env / RL engineering
Last updated: 2026-07-20 (Day 10)

## ⚠️ Day-8 correction (read first)
- The Day-7 checkpoint (`...18-54-03/model_1499.pt`) is **DEAD** — visual verify showed the
  robot **throwing** the cube. It reward-hacked the height-only lift term because the
  Robotiq 2f-85 closed loop transmits **no grip force** in sim (confirmed by
  `scripts/grasp_hold_test.py`; even 20x clamp force didn't hold).
- FIX (pre-agreed escape hatch): **proximity weld** grasp — `tasks/lift/ur5e_lift_env.py:
  UR5eCubeLiftEnv`. On CLOSE + cube within `GRASP_TOL=0.06 m` of the reach frame, the cube
  latches to the gripper (pose tracks frame, velocity zeroed); releases on open. Registered
  for `-v0` and `-Play-v0`. Weld makes throwing impossible → height reward no longer hackable.
- Hold test with weld → **GRIP HOLDS ✅**. Geometry is fine (do NOT zero the EE offset — the
  "offset=0" probe hint was an artifact of finger body origins sitting at the flange).
- IsaacLab pinned to the **v2.3.0 TAG** (`frozen/2.3.0`), not the branch (branch drifted to
  v2.3.1 and broke the URDF-importer version pin).
- DONE (Day 9): PPO retrained on the weld env → visual `play.py` check passed → Module 03 benchmark
  run. This weld env + baseline is the one used for the Layer 1 cPPO-vs-PPO comparison.

## Goal
A UR5e + Robotiq 2f-85 cube-lift env (privileged object pose) that trains a PPO grasping
policy — the foundation for the Layer 1 safety benchmark.

## Current state — done
- Env retargets Isaac Lab's Franka lift env to UR5e. Gym ids `Isaac-Lift-Cube-UR5e-v0`
  and `-Play-v0`.
- Full 1500-iter PPO run completed clean: mean_reward 0.72→8.5, lifting_object 0.12→2.16
  (UR5e grasps and lifts the cube). Gripper closes via the mechanical 4-bar loop.
- Checkpoint: `IsaacLab/logs/rsl_rl/ur5e_lift/2026-07-12_18-54-03/model_1499.pt`
  (JIT/ONNX exported alongside by play.py).

## Key facts / decisions
- Exact-arm fidelity chosen: real robot = **UR5e**; sim asset = Nucleus `ur5e.usd`.
- Sim gripper = built-in **Robotiq 2f-85** variant. Real gripper = **ROBOTIS RH-P12-RN**
  (import deferred to Layer 3). Full details + joint names: `ur5_grasp/CONTEXT.md`.
- Built a corrected single-articulation USD (`ur5_grasp/assets/ur5e_robotiq_2f85.usd`)
  by disabling the gripper's nested articulation root.
- 3 bugs fixed at scale: self-collision hang → self-collisions off; NaN divergence →
  drive only `finger_joint`, coupled joints passive + armature/damping/friction +
  observation clamp firewall.

## Files
- `ur5_grasp/robots/ur5e_robotiq.py` — robot cfg
- `ur5_grasp/tasks/lift/` — env cfg + gym registration + rsl_rl agent cfg
- `ur5_grasp/scripts/train.py`, `play.py` — launchers
- `ur5_grasp/tasks/lift/ur5e_lift_env.py` — **weld env class** (grasp escape hatch)
- `ur5_grasp/scripts/zero_agent.py` — geometry probe (prints reach-frame vs fingertips)
- `ur5_grasp/scripts/grasp_hold_test.py` — physics-only 30s hold test (HOLDS/TOO-WEAK verdict)
- `ur5_grasp/tools/` — asset inspector + USD builder (+ their reports)

## Commands
Train: `./isaaclab.sh -p ../ur5_grasp/scripts/train.py --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096`
Play:  `./isaaclab.sh -p ../ur5_grasp/scripts/play.py --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 16`
(run from `~/Abdur_Rabbi_THESIS/IsaacLab`)

## Next steps (optional polish)
- Play-verify grasp quality; tune ready pose / EE offset (0.16) / reward weights if the
  grasp looks off or episode length dips late in training.
- Proper PhysX mimic coupling if the mechanical-loop grip proves inconsistent.

## run_log.md refs
Day 7.
