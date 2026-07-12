# Module 05 — Sim-to-Real Transfer (Layer 3, optional)

Status: ⏳ later
Chat type: hardware / ROS 2
Last updated: 2026-07-12 (Day 7)

## Goal
Zero-shot transfer of the trained policy to the physical UR5e via ROS 2 Humble +
Universal_Robots_ROS2_Driver.

## Known sim-to-real gaps to close here
- **Gripper:** sim uses Robotiq 2f-85; real robot has a **ROBOTIS RH-P12-RN**. Import the
  RH-P12-RN into sim in this window. URDF facts + import plan already saved in
  `ur5_grasp/CONTEXT.md` (repo: github.com/ROBOTIS-GIT/RH-P12-RN).
- Domain randomization coverage; camera calibration; controller/rate matching.

## Assets ready
- Policy exported to JIT + ONNX by `play.py` (in the checkpoint's `exported/` dir).

## Next steps
- TBD after Layers 1–2.

## run_log.md refs
(none yet)
