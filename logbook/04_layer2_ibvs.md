# Module 04 — IBVS Visual Loop (Layer 2, stretch)

Status: 🟢 STARTED — Phase 1 (camera) DONE. Phase 2 framing UNBLOCKED via pin fix (Day 14) — pending lab-PC run. Layer 1 signed off.
Chat type: vision / IBVS
Last updated: 2026-07-25 (Day 14)

## Goal
Add the image-based visual servoing loop with an RL-tuned image Jacobian (fuzzy state
coding, mixture parameter β), replacing privileged pose with an eye-in-hand camera.

## Hardware decision (Day 13)
RGB **webcam only** — no RGB-D available. Monocular IBVS with approximate depth; the
unmeasured Z becomes the job of the RL-tuned image Jacobian (a cleaner contribution, and
it matches Khan 2026's monocular CSRT baseline). Sim camera configured RGB-only to match.

## Phase plan
1. ✅ Camera → cube pixel (eye-in-hand RGB, verified).
2. 🔶 Classical IBVS baseline — detection WORKING; mount framing + control law to do.
3. ⏳ RL-tuned image Jacobian (cPPO correction + FOV cost term).
4. ⏳ Benchmark RL-tuned vs classical + figures.

## Phase 2 progress (Day 13)
- **Detection works.** Saturated-colour blob detector finds the cube robustly.
  **DexCube colour ≈ RGB [112, 83, 190]** (violet) — lock this for the live detector.
- **Lighting:** base lift env already has a dome light (`/World/light`, 3000). Black
  frames were NOT a lighting problem.
- **Camera-in-mesh was the black-frame cause.** A 4 cm wrist mount sits *inside* the
  gripper body → renders the black interior. Fix = STANDOFF along the view axis. Current
  test mount: `pos=(0.0002, -0.0276, 0.2987)` (0.3 m back). Renders fine but frames the
  cube too large/at the edge with the flange occluding — MOUNT STILL NEEDS TUNING
  (side-offset or a quick GUI look) for a clean object view.
- **Ground-truth world→pixel projection in `ibvs_camera_test.py` is ~50 px off** (camera
  convention). NOT needed for IBVS (we servo on the detected centroid) — treat as a
  Phase-1 crutch, don't rely on it.
- Detector is currently seeded near the (slightly-wrong) GT; for the live loop switch to
  a GLOBAL colour mask on the locked violet, largest blob = cube centroid.
- **Phase 2b control script written** (`ur5_grasp/scripts/ibvs_servo.py`): probe-measured
  2x2 image Jacobian + proportional centroid servo, joint-step capped, lost-detection
  guarded. BLOCKED on framing — at the RL ready pose the eye-in-hand view frames the cube
  too large / at the edge, so small probe moves push it out of view (`[abort] cube left
  view`). Root cause: ready-pose gripper points sideways + camera-convention wobble.
- **Two ways to unblock (next session):** (a) short Isaac GUI session to place the mount
  visually; or (b) START IBVS from a policy-driven pre-grasp pose (run the trained
  checkpoint until the arm hovers above the cube looking down, THEN servo) so framing is
  natural. (b) reuses the trained policy + play.py and is the recommended path.

## Phase 2 resolution (Day 14) — the PIN was broken; the ready pose also looks sideways
- **Real cause:** `ibvs_servo.py` pinned the cube at a *forced 0.30 m depth* plus a
  *world-frame* `[0.03,0,0]` nudge. Forcing 0.30 m floats the cube nearer than the table
  (→ "too large"); a world-frame nudge maps to an unpredictable image direction with the
  gripper turned (→ "at the edge"). The ready pose itself is fine — `ibvs_camera_test.py`
  already frames the cube cleanly from it by **projecting the optical axis onto the table**.
- **First run revealed more:** at the ready pose the camera looks **sideways**, not down
  (`fwd_z > -0.05`), so projecting onto the table can't work from there — a downward-view
  assumption aborts. (Confirmed live: `[abort] camera isn't looking down…`.)
- **Fix that works with the sideways camera — optical-axis STATIC pin:** `cpos + D·fwd`
  (`D = START_DEPTH_M = 0.30`, the aim point) is dead-centre in the image *for any camera
  orientation*. Hold the cube STATIC at that fixed world point and let the arm servo the
  camera onto it. A controlled image-horizontal off-centre (`START_OFFSETS_M`, largest that
  fits `SAFE_U/V`) gives the servo a real error. `step_cam_move` re-pins the cube every
  physics step (else it free-falls out of frame). Prints `[start] … err_px=…`.
- Valid classical *centering* baseline; the cube floats (not on the table), which is fine
  for the image-Jacobian comparison. For a table-realistic view, set `HOVER_Q` (below).
- **Policy-driven start dropped** for the baseline: stochastic (noisy err_px curves) and
  couples a *classical* baseline to the RL policy. If a look-down view is wanted, use the
  policy ONCE to discover a good hover config, freeze those 6 joints into `HOVER_Q`.
- **Optional `HOVER_Q`** hook added (default `None`): 6 arm joint angles applied via
  `write_joint_state_to_sim` before servoing — use only for a table-realistic look-down view.
- **Mount note:** both scripts fly the **0.30 m standoff** `pos=(0.0002,-0.0276,0.2987)`.
  The "verified 4 cm mount" below is STALE (that one renders black inside the gripper).
- **Still to do on the lab PC:** run it, confirm `err_px` shrinks toward ~0 (that = the
  classical baseline), save the curve to `results/ibvs_phase2/`.

## Phase 1 result (verified)
- `ur5_grasp/scripts/ibvs_camera_test.py` — wrist-mounted `CameraCfg` injected into the
  PLAY env (Layer 1 files untouched). Renders RGB; world→pixel projection confirmed
  (on-axis point projects to image centre; cube pixel tracks the cube).
- **Verified camera mount** (eye-in-hand on `wrist_3_link`, ROS convention):
  `pos=(-3e-05, 0.00368, -0.03983)`, `rot=(-0.03285, 0.70643, 0.70629, 0.03228)`.
  ⚠️ STALE: this 4 cm `pos` renders black (lens inside the gripper). Live mount in BOTH
  scripts is the 0.30 m standoff `pos=(0.0002, -0.0276, 0.2987)` (same `rot`).
- **Approach axis is wrist −z** (not +z). The env `ee_frame` offset `[0,0,0.16]` is
  approximate/sign-flipped vs the true fingertip TCP — camera aim was recovered
  empirically via `recommend_aim()`.

## Guardrail
Never let Layer 2 endanger Layer 1. (Layer 1 = pass bar, signed off.)

## Gotchas (Day 13)
- Camera sensors REQUIRE `--enable_cameras`; headless training never exercised this path.
- `CUDA error 804` / "Failed to query CUDA device count" on first camera run = an apt
  driver update (→580.173) with the old kernel module still loaded. Fix = reboot.
  Consider `apt-mark hold` on the nvidia driver to freeze the stack.

## Key references
Shi 2020 (IBVS + Q-learning), Zhang (fuzzy IBVS), Khan 2026 (classical monocular baseline).

## run_log.md refs
- 2026-07-24 (Day 13) — Layer 2 kickoff + Phase 1 camera verified.
- 2026-07-25 (Day 14) — Phase 2 framing fix (pin geometry), servo loop untouched.
