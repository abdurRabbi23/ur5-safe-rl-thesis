HANDOFF — UR5e Safe-RL Thesis · Layer 2 (IBVS), resume at Phase 2 control (Day 13, 2026-07-24)

READ FIRST: logbook/00_INDEX.md, logbook/04_layer2_ibvs.md, then the two scripts
ur5_grasp/scripts/ibvs_camera_test.py and ur5_grasp/scripts/ibvs_servo.py. Then continue below.

STATE
- Layer 1 (must-pass, cPPO vs PPO) = COMPLETE and written up. UNTOUCHED this session.
- Layer 2 decision: eye-in-hand, MONOCULAR RGB (no RGB-D / no depth sensor). Classical IBVS
  with approximate depth; the unmeasured Z is what the RL-tuned image Jacobian (Phase 3)
  compensates for. Matches Khan 2026's monocular baseline. Sim camera is RGB-only.
- Phase 1 (camera -> cube pixel) = DONE. Eye-in-hand RGB camera renders; projection verified.
- Phase 2 detection = DONE. Cube found reliably by colour.
- Phase 2 control (ibvs_servo.py) = WRITTEN but BLOCKED on camera framing (see BLOCKER).

KEY VALUES (verified)
- Camera mount on wrist_3_link, ROS convention (in ibvs_camera_test.py / ibvs_servo.py):
    pos=(0.0002, -0.0276, 0.2987)   rot=(-0.03285, 0.70643, 0.70629, 0.03228)  (w,x,y,z)
  Aim points camera +z at the fingertip grasp point; APPROACH AXIS = wrist -z (not +z).
- DexCube colour (violet) ≈ RGB [112, 83, 190]  -> lock this for the colour detector.
- Run cmd (lab PC, tmux, env `isaaclab`; cameras REQUIRE --enable_cameras):
    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/ibvs_servo.py \
        --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1 --headless --enable_cameras

BLOCKER (where to resume)
At the RL ready pose the eye-in-hand view frames the cube too large / at the image edge, so
small servo/probe moves push it out of view (`[abort] cube left view during probe`). This is a
visual-geometry problem, NOT a code bug. ibvs_servo.py is already hardened (probe-measured 2x2
image Jacobian, joint-step cap, lost-detection guard).

NEXT — recommended path
Start IBVS from a POLICY-DRIVEN PRE-GRASP pose, not the raw ready pose:
  1. Load the trained cPPO/PPO checkpoint (reuse the ur5_grasp/scripts/play.py pattern) and
     step the policy until the arm hovers above the cube looking down (a few dozen steps).
  2. THEN hand control to the IBVS centroid servo (the probe + servo loop already in
     ibvs_servo.py). At the pre-grasp pose the camera frames the cube naturally.
  3. Verify: logged `err_px` shrinks toward ~0 (cube centred). That = the classical baseline.
Alternative if preferred: a short Isaac GUI session (run without --headless, switch the
viewport to the wrist_cam prim) to place/aim the mount visually, then lock the numbers.
After the classical baseline works -> Phase 3 (RL-tuned image Jacobian: cPPO correction with
fuzzy state coding + mixture β; add ONE field-of-view soft cost term to SafetyCostComputer).

GOTCHAS (new this session)
- Camera sensors need `--enable_cameras`; headless training never exercised rendering.
- CUDA error 804 / "Failed to query CUDA device count" on first camera run = NVIDIA driver was
  auto-updated (userspace 580.173) with the OLD kernel module still loaded -> REBOOT fixes it.
  Driver moved off the frozen 580.159.03; consider `apt-mark hold` on the nvidia driver.
- Base lift env ALREADY has a dome light (/World/light, 3000). Lighting is fine.
- A wrist camera at a tiny (~4 cm) mount sits INSIDE the gripper mesh -> black frames. Needs a
  standoff along the view axis (current 0.3 m).
- env `ee_frame` offset [0,0,0.16] is approximate/sign-flipped vs the true fingertip TCP.
- ibvs_camera_test.py world->pixel projection is ~50 px off (camera convention). NOT needed for
  IBVS (servo on the DETECTED centroid) — don't rely on it.
- tmux mandatory; tee/log paths absolute; clear `.git/index.lock` before commits.

UNCOMMITTED on lab PC (push when back):
  cd ~/Abdur_Rabbi_THESIS && rm -f .git/index.lock
  git add -A && git commit -m "Layer 2 Phase 1 (camera+detection) + Phase 2 IBVS servo WIP" && git push
  (new: ibvs_camera_test.py, ibvs_servo.py; updated: logbook/04_layer2_ibvs.md, run_log.md)
