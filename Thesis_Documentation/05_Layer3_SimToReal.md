# 05 — Layer 3: Sim-to-Real Transfer to the Physical UR5e

**Status:** ⏳ PLANNED (not started) · **Layer:** 3 (optional) · **Roadmap:** Weeks 11–13 if time

> Placeholder outline. Filled in with real commands and outputs when Layer 3 begins, and only if the
> timeline allows. Layer 3 must never endanger Layers 1–2.

---

## What Layer 3 is (plain words)

Take the policy that learned to grasp in simulation and run it on the **real UR5e robot** — ideally
**zero-shot** (no real-world retraining). The gap between sim and reality (friction, timing, camera
noise, a *different gripper*) is what makes this hard; **domain randomization** during training is
what makes it possible.

---

## Known sim-to-real gaps to close

- **Gripper mismatch.** Sim (Layers 1–2) uses the Robotiq 2f-85; the **real gripper is a ROBOTIS
  RH-P12-RN**. It must be imported into sim during this window (details below), and the "weld"
  grasp abstraction from section 02 must be reconciled with real contact.
- **Perception.** The real camera replaces privileged pose info — Layer 2's IBVS is the bridge.

---

## RH-P12-RN import reference (do not build until Layer 3)

- 1-DOF two-finger adaptive hand, DYNAMIXEL 2.0 protocol.
- ROS package: `https://github.com/ROBOTIS-GIT/RH-P12-RN` (description pkg `rh_p12_rn_description`);
  URDF xacro at `rh_p12_rn_description/urdf/rh_p12_rn.xacro`; meshes STL scaled 0.001.
- Links: `rh_p12_rn_base` (mount point), `rh_p12_rn_r1/r2`, `rh_p12_rn_l1/l2` (drop the `world`
  link when mounting to the UR5e flange).
- Joints (revolute): `rh_p12_rn` (base→r1, axis +x, limit 0..1.1) is the **driven** joint; `rh_l1`
  mirrors it; `rh_r2`/`rh_l2` (0..1.0) are passive coupling. Actuate `rh_p12_rn` (+ mirror `rh_l1`);
  close ≈ 1.1, open 0.0.
- Import path: URDF → USD via Isaac Lab's `UrdfConverter`, then mount `rh_p12_rn_base` to the UR5e
  `tool0` / `wrist_3_link` with a fixed joint.

---

## Planned sub-steps

1. **ROS 2 bring-up** — ROS 2 Humble + `Universal_Robots_ROS2_Driver`; confirm control of the real
   arm.
2. **Deploy the policy** — load the JIT/ONNX export from `play.py` (section 02) into a ROS 2 node.
3. **Import & mount RH-P12-RN** — as above; retrain/adapt the grasp with the real gripper.
4. **Zero-shot test** — run the sim-trained policy on hardware; measure real grasp success and
   safety-constraint behaviour.

## Success criterion (to confirm later)

The sim-trained safe policy performs a real grasp on the physical UR5e while respecting the safety
constraints, demonstrating the sim-to-real transfer end-to-end.

## Key references

Shahid 2022 (sim-to-real PPO/SAC); Xia 2024 (UR5e safe DRL); Khan (cPPO grasping).
