# Module 04 — IBVS Visual Loop (Layer 2, stretch)

Status: 🟡 IN PROGRESS — Phase 1 (camera) DONE; Phase 2 (classical IBVS baseline) BUILT, ~50% error
reduction demonstrated, full convergence blocked by a controller limitation (below). Layer 1 signed
off and untouched.
Chat type: vision / IBVS
Last updated: 2026-07-25 (Day 14)

## Goal
Replace privileged pose with an eye-in-hand camera and close the loop in the image. Phase 2 is the
CLASSICAL IBVS baseline; Phase 3 will add the RL-tuned image Jacobian (fuzzy state coding + mixture β)
that the baseline is compared against.

## Hardware decision (Day 13)
Monocular RGB webcam only — no depth. The unmeasured Z is the job of the RL-tuned Jacobian (cleaner
contribution; matches Khan 2026's monocular baseline). Sim camera configured RGB-only to match.

## Phase status
1. ✅ Camera → cube pixel (eye-in-hand RGB, verified).
2. 🟡 Classical IBVS baseline — camera + detection + self-measured Jacobian + servo all WORK; servo
   halves the centroid error (~43→~20 px) reproducibly, then destabilises (see limitation).
3. ⏳ RL-tuned image Jacobian (cPPO correction + FOV cost term).
4. ⏳ Benchmark RL-tuned vs classical + figures.

## What works (`ur5_grasp/scripts/ibvs_servo.py`)
- **Mount (recovered via mount_finder):** `pos=(0.06, 0.0, 0.0)` wrist frame (beside gripper),
  `rot=(0.9894, 0.0, -0.1452, 0.0)` (w,x,y,z), aimed along wrist **+z** at the grasp region.
- **Detection:** largest highly-saturated blob = the multi-colour DexCube. Robust to stray pixels /
  a second coloured object. No colour hard-coded.
- **Image Jacobian:** self-measured by finite differences (two probe moves), using the ACTUAL camera
  displacement from the wrist articulation state (not `cam.data.pos_w`, which lags). `ds = J·dc`,
  2×2, well-conditioned (det ≈ 2.2e6). Re-measured periodically during servo.
- **Servo:** proportional `dc = −λ J⁻¹ (s−s*)`, mapped to joints via damped least squares on the full
  6×6 arm Jacobian with orientation + height held; per-step error logged; edge/approach guards.
- **Deterministic setup:** reset randomisation frozen; cube spawned at `(0.56, 0.16, 0.055)` so every
  run starts identically, centrally framed.

## Result (verified, repeatable)
- Camera sees the cube; detection reliable.
- Image Jacobian measured, det ≈ 2.2e6; arm-Jacobian cond ≈ 9 at the servo pose (NOT singular).
- Servo reduces centroid error **~43 px → ~20 px (≈50%) every run**, then loses the cube after
  ~10–30 steps. debug_start/end.png saved each run.

## Limitation + diagnosis (Day 14)
- Not a singularity (arm cond ≈ 9). The servo leaks ORIENTATION: the optical axis tilts during the
  run (optz world-z −0.949 → −0.808), i.e. the camera pitches toward the table, apparent size grows,
  target lost. Same failure under pinv, DLS, and Jacobian-transpose → it's the arm-motion layer, not
  the image controller. Holding wrist orientation strictly through incremental joint-position targets
  (mixed linear/angular least-squares) is not orientation-tight.
- **Fix (future work):** resolved-rate / operational-space velocity controller with a HARD orientation
  constraint (or explicit re-levelling each step); or pick the servo pose by an image-motion
  manipulability scan. This is a controller sub-project, not gain tuning — and it's exactly what the
  Phase 3 RL-tuned Jacobian is meant to absorb, so it motivates rather than blocks the contribution.

## Bugs solved this session (the long road to a working camera)
1. **Mount aimed backwards.** 0.30 m standoff aimed back at the grasp point → saw only the gripper (+ a
   wrist webcam model), never the cube. `geometry.txt` from `mount_finder.py` showed the cube sits
   along wrist **+z** (the old "approach = wrist −z" note was backwards). Fixed with the side-mount.
2. **Wrong cube colour.** Assumed violet `[112,83,190]`; the DexCube is multi-colour, so the colour
   mask never matched. Fixed with the saturation + largest-blob detector.
3. **Lagging camera pose.** `cam.data.pos_w` read ~0 displacement during probes → garbage Jacobian.
   Fixed by deriving the camera pose from `body_pos_w`/`body_quat_w` + the fixed mount offset.
4. **Debug gizmos in view.** The command goal-pose / ee_frame markers rendered into the camera and
   fooled the colour mask. Fixed with `debug_vis=False` on `commands.object_pose` and `scene.ee_frame`.
5. **Phantom second cube.** Placing the cube with `write_root_pose_to_sim` produced a duplicate cube in
   view → detector averaged both. Fixed by freezing randomisation + spawning at a fixed pose (no
   `write_root_pose`); largest-blob detector as the safety net.

## Gotchas (carry forward)
- Camera sensors REQUIRE `--enable_cameras`; headless training never exercised rendering.
- `CUDA error 804` / "Failed to query CUDA device count" on first camera run = apt driver auto-update
  (→580.173) with the old kernel module loaded. Fix = reboot; consider `apt-mark hold` on the driver.
- Use `Camera`, not `TiledCamera` (hangs on Blackwell).

## Tools written
- `ibvs_servo.py` — Phase 2 baseline (camera + detection + Jacobian + servo).
- `ibvs_camera_test.py` — Phase 1 camera smoke test.
- `mount_finder.py` — camera-mount × arm-pose sweep + wrist-frame geometry reporter (`geometry.txt`).
- `pose_finder.py` — arm-pose sweep to visualise the wrist-camera view.

## Key references
Shi 2020 (IBVS + Q-learning), Zhang (fuzzy IBVS), Khan 2026 (classical monocular baseline).

## run_log.md refs
- 2026-07-24 (Day 13) — Layer 2 kickoff + Phase 1 camera verified.
- 2026-07-25 (Day 14) — Phase 2 baseline built; mount + detection + Jacobian fixed; ~50% error
  reduction; servo-convergence limitation diagnosed (orientation leak) and documented.
