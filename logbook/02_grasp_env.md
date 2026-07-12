# Module 02 — UR5e Grasp Env + PPO Baseline

Status: ✅ baseline done (grasps + lifts); minor tuning optional
Chat type: sim env / RL engineering
Last updated: 2026-07-12 (Day 7)

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
