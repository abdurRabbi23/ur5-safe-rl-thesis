# UR5 Safe RL Grasping — Working Context & Decisions

Living memory for the thesis code under `ur5_grasp/`. Update as decisions change.

## Environment / access
- Claude desktop (Cowork) now runs **on the lab PC** (i9, 64 GB, RTX 5090, Ubuntu, NoMachine).
- The thesis repo `~/Abdur_Rabbi_THESIS` is mounted with full read/write in Cowork,
  alongside the THESIS 4200 project instructions.
- Sandbox note: Claude's bash sandbox CANNOT run Isaac Sim or reach Nucleus. All Isaac
  runs (inspection, training) happen in Touhid's terminal on the lab PC; Claude writes
  code + gives commands, Touhid runs and pastes results.

## Simulation asset facts (verified on this machine, Isaac assets 5.1)
- **UR5e USD (arm):** `{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd`
  - `ISAAC_NUCLEUS_DIR = https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac`
- **Variant sets on ur5e.usd:** `Physics=[None, PhysX]`, `Sensor=[None, Sensors]`,
  `Gripper=[None, Robotiq_2f_85]`.
- **Arm joints (6):** shoulder_pan_joint, shoulder_lift_joint, elbow_joint,
  wrist_1_joint, wrist_2_joint, wrist_3_joint.
- **Arm bodies (7):** base_link, shoulder_link, upper_arm_link, forearm_link,
  wrist_1_link, wrist_2_link, wrist_3_link.
- **Merged single-articulation USD:** `ur5_grasp/assets/ur5e_robotiq_2f85.usd` (built by
  `tools/make_ur5e_robotiq_usd.py`; disables the gripper's nested articulation root).
  Loads as ONE articulation, 12 joints / 16 bodies.
- **Gripper joints (6):** `finger_joint` (drive, 0=open ~0.8=closed) + coupled
  `right_outer_knuckle_joint`, `left_inner_finger_joint`, `right_inner_finger_joint`,
  `left_inner_finger_knuckle_joint`, `right_inner_finger_knuckle_joint`.
- **Gripper bodies:** `base_link_0` (arm's duplicate base auto-renamed), left/right
  outer_knuckle, outer_finger, inner_finger, inner_knuckle.
- EE frame: root `base_link`, target `wrist_3_link` + ~0.16 m offset to TCP (approx, tune).

## Env scaffold status (Day 7)
- `ur5_grasp/` package registers gym tasks `Isaac-Lift-Cube-UR5e-v0` (+ `-Play-v0`),
  retargeting Isaac Lab's Franka lift env. Train via `ur5_grasp/scripts/train.py`.
- KNOWN follow-ups after the loop runs: (1) gripper finger coupling (PhysX mimic) so all
  fingers close with `finger_joint`; (2) tune ready pose + EE offset; (3) verify
  FrameTransformer prim paths (`Robot/base_link`, `Robot/wrist_3_link`).

## Key decision — gripper (2026-07-12)
- **Sim (Layer 1): use the built-in Robotiq 2f-85 variant.** The cPPO-vs-PPO safe-RL
  result is gripper-agnostic (control is a single normalized open/close), so use the
  free built-in gripper to protect the Layer 1 timeline.
- **Real robot gripper = ROBOTIS RH-P12-RN.** Import into sim during the **Layer 3**
  sim-to-real window, not before. Logged as the known sim-to-real gap.

## RH-P12-RN reference (for the Layer 3 import — do not build yet)
- 1-DOF two-finger adaptive hand, DYNAMIXEL 2.0 protocol.
- ROS pkgs: https://github.com/ROBOTIS-GIT/RH-P12-RN (description pkg `rh_p12_rn_description`).
  URDF xacro: `rh_p12_rn_description/urdf/rh_p12_rn.xacro`; meshes STL scaled 0.001.
- Links: `rh_p12_rn_base` (mount point), `rh_p12_rn_r1`, `rh_p12_rn_r2`,
  `rh_p12_rn_l1`, `rh_p12_rn_l2` (+ a `world` link joined by fixed `world_fixed` — drop
  the `world` link when mounting to the UR5e flange).
- Joints (all revolute): `rh_p12_rn` (base->r1, axis +x, limit 0..1.1) is the **driven**
  joint; `rh_l1` (base->l1, 0..1.1) mirrors it; `rh_r2`/`rh_l2` (0..1.0) are the passive
  coupling. Effort interface. In sim: actuate `rh_p12_rn` (+ mirror `rh_l1`), close ~1.1,
  open 0.0.
- Import path when the time comes: URDF->USD via Isaac Lab UrdfConverter, then mount
  `rh_p12_rn_base` to UR5e `tool0`/`wrist_3_link` with a fixed joint.

## Plan for Layer 1 grasp env
- Template: Isaac Lab Franka **lift** env
  (`source/isaaclab_tasks/.../manipulation/lift/`). It is the canonical grasp-and-lift
  task with privileged object-pose observations + reach/grasp/lift reward shaping.
- Retarget to UR5e + Robotiq 2f-85: swap robot cfg, arm joint action, gripper binary
  action, EE FrameTransformer (root=base_link, target=tool link), and
  `commands.object_pose.body_name`.
- Register gym ids under a git-tracked `ur5_grasp/` package (separate from the gitignored
  IsaacLab clone). Validate headless with rsl_rl PPO like Reach was.

## `ur5_grasp/` layout
- `tools/inspect_ur5e_asset.py` — asset inspector (USD path, variants, joint/body names).
  Writes `tools/ur5e_asset_report.txt`.
