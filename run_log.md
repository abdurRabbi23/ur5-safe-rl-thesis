# UR5 Safe RL Grasping — Run Log

## Session-start checklist (every NoMachine session)
- `conda activate isaaclab`  (fresh terminals open in base)
- `sudo cpupower frequency-set -g performance`  (governor resets on reboot)
- Launch training/TensorBoard inside tmux so a dropped connection doesn't kill runs

## Day 1 — Machine prep + compatibility check
- Lab PC: i9, 64 GB, RTX 5090 (Blackwell sm_120), driver 580.159.03.

## Day 2 — Stack install + validation
- Frozen stack: Isaac Sim 5.0.0 · Isaac Lab release/2.3.0 · Python 3.11 conda env `isaaclab` · PyTorch 2.7.0+cu128 (torchvision 0.22.0, torchaudio 2.7.0) · numpy 1.26.0.
- Validated: torch sees RTX 5090 (no sm_120 warning); Isaac Sim GUI launches over NoMachine; headless smoke test create_empty.py --headless printed "Setup complete", no traceback.
- Gotcha: TiledCamera hangs on Blackwell — use Camera instead.
- NOTE: git/run_log claimed done on Day 2 but were NOT actually created; set up for real on Day 3.

## Day 3 — Cartpole pipeline validation
- Isaac-Cartpole-v0, rsl_rl, headless. Converged 150 iters / ~17s on 5090.
- Mean episode length 300 (cap), time_out 0.999 / cart_out_of_bounds 0.001 — learned.
- TensorBoard served with --bind_all, reached laptop over Tailscale (100.109.10.66:6006). Curves render.
- Debug lesson: "connection refused" = process down; hang = network/firewall.
- Git initialised, .gitignore added (excludes IsaacLab clone + logs/checkpoints), first real commit.
## Day 4: Isaac-Reach-Franka-v0 headless trained, reward climbs sharply then plateaus ~400 iters, ep length stable, TB verified from laptop

## Day 5 — num_envs scale test (Reach-Franka, 100 iters each)

| num_envs         | wall time | it/s | throughput (env·it/s) | peak VRAM |
|------------------|-----------|------|-----------------------|-----------|
| 4096 (default)   | 40.9s     | 2.44 | ~10.0k                | 4600 MiB  |
| 8192             | 50.5s     | 1.98 | ~16.2k                | 5059 MiB  |
| 16384            | 74.1s     | 1.35 | ~22.1k                | 7554 MiB  |

Sweet spot: 8192 (best throughput/time balance, trivial VRAM). Note: UR5 grasping env is heavier per-env — re-time before setting real training budgets.

## Day 6: Spinning Up Parts 1-2 + PPO page read. Notes committed. Khan §3-4 deferred to pre-cPPO week.

## Day 7 — Cowork on lab PC + start UR5e grasp env (Layer 1)
- Claude desktop (Cowork) now runs on the lab PC with full read/write access to this repo.
- Chose grasp env template: Franka **lift** env (privileged object pose + reach/grasp/lift reward) → retarget to UR5e.
- Verified UR5e asset on Nucleus (Isaac assets 5.1): `.../UniversalRobots/ur5e/ur5e.usd`, with a built-in `Robotiq_2f_85` gripper variant. Arm joints + base_link confirmed. Details in `ur5_grasp/CONTEXT.md`.
- Gripper decision: build **Layer 1 on Robotiq 2f-85** (safe-RL result is gripper-agnostic); real gripper is **ROBOTIS RH-P12-RN**, import in the Layer 3 sim-to-real window. RH-P12-RN URDF facts saved in CONTEXT.md.
- Started `ur5_grasp/` package (git-tracked, separate from IsaacLab clone) with an asset-inspection tool.
- Housekeeping: removed a duplicated Day 6 line in this log.
- Built merged single-articulation USD `ur5_grasp/assets/ur5e_robotiq_2f85.usd` (disabled gripper's nested articulation root). Loads clean: 12 joints / 16 bodies.
- Scaffolded `ur5_grasp` package: UR5e+2f85 robot cfg, lift env retargeted from Franka, gym id `Isaac-Lift-Cube-UR5e-v0`, own train.py.
- SMOKE TEST PASSED (64 envs, 10 iters): env loads as one articulation, all reward terms compute, reach reward rising, ep length 20→127, no crash. Layer 1 infra works.
- Follow-ups: (1) gripper finger coupling (only finger_joint driven now — can't grasp yet); (2) tune ready pose + EE offset via Play; (3) then full training run + start cPPO vs PPO benchmark.
- Full-run bug #1: hung at "Starting the simulation" at 4096 envs → cause: enabled_self_collisions=True on the multi-body gripper overflowing GPU contact-pair buffers. Fix: set enabled_self_collisions=False (matches Isaac Lab convention).
- Full-run bug #2: NaN crash at iter ~35 (`normal expects std >= 0.0`) → cause: all 2f-85 joints actively driven, fighting the closed-loop 4-bar linkage → physics blow-up. Fix: drive only finger_joint, coupled joints PASSIVE (stiffness/damping 0), mirroring Isaac Lab UR10e Robotiq split. Bonus: mechanical loop should make fingers close.
- Full-run bug #2b: passive-but-undamped linkage still NaN'd at iter ~92 (energy build-up in loop constraint). Fix: add armature=0.01 + friction=0.1 to gripper joints, damping 0.5 on passive joints, armature 0.01 on arm, plus observation clamp (-100,100) as a NaN firewall.
- ✅ PPO BASELINE TRAINED (Layer 1): full 1500-iter run completed clean, no NaN. mean_reward 0.72→8.5 (max 10.6), lifting_object 0.12→2.16 — the UR5e is grasping AND lifting the cube. Gripper closes via the mechanical loop (task #6 resolved). Checkpoint: logs/rsl_rl/ur5e_lift/2026-07-12_18-54-03/model_1499.pt.
- Added play.py launcher (loads checkpoint, opens GUI, exports jit/onnx for later ROS2 deploy).
- NEXT: (1) Play to visually verify the grasp + tune ready pose/EE offset if needed; (2) THE Layer 1 deliverable — add safety constraints (collision/joint-limit/singularity/FOV) + cPPO (OmniSafe Lagrangian), benchmark cPPO vs PPO.

## Day 8 — Grasp verification gate + escape-hatch weld
- Pushed Day 7 commit to GitHub (SSH key set up; reconciled a divergent `release/2.3.0` history via rebase).
- BUG: play/train crashed at AppLauncher — `isaacsim.asset.importer.urdf` wanted 2.4.31 but installed Isaac Sim ships 2.4.19. Cause: the IsaacLab clone sat on the **`release/2.3.0` branch tip**, which had advanced to **v2.3.1** (URDF importer bumped, exact-pinned). Fix: `git checkout -b frozen/2.3.0 v2.3.0` (the TAG, which pins urdf importer `{}` = any). LESSON: pin IsaacLab to the **v2.3.0 tag**, never the branch.
- VISUAL VERIFY of the Day-7 PPO baseline FAILED: robot flings the cube instead of holding it. Diagnosis: base lift reward pays for cube height > 4cm with no requirement it be held → the policy reward-hacks by throwing. Same reward works for Franka because its gripper HOLDS; ours does not.
- Built `scripts/zero_agent.py` (geometry probe) + `scripts/grasp_hold_test.py` (physics-only hold test). Geometry OK (reach frame ~at finger level; the automated "offset=0" hint was an artifact of inner-finger body origins sitting at the flange — do NOT zero the offset).
- HOLD TEST: cube placed between pads + gripper closed → falls straight through. Bumping finger drive stiffness 20→400 / effort 50→200 did NOT help (no NaN, just no force). Confirmed the known 2f-85 closed-loop force-transmission problem — passive pads (stiffness 0) transmit no normal force.
- DECISION (pre-agreed tripwire): took the **escape hatch**. New env class `tasks/lift/ur5e_lift_env.py:UR5eCubeLiftEnv` — a proximity weld: when gripper commands CLOSE and cube is within GRASP_TOL=0.06 m of the reach frame, the cube latches to the gripper (pose tracks reach frame, velocity zeroed); releases on open. Registered for both `-v0` and `-Play-v0`. Bonus: welding makes throwing impossible, so the height reward is no longer hackable.
- HOLD TEST re-run with weld → GRIP HOLDS ✅ (cube stays at pad level 210 steps, no NaN). Grasp is now reliable in the RL sense.
- NEXT: retrain PPO baseline on the weld env (old checkpoint is reward-hacked, dead) → visual `play.py` check (expect real reach→close-near→lift-to-goal) → then Module 03 (safety constraints + cPPO vs PPO).

## Day 9 — cPPO (PPO-Lagrangian) implemented on rsl_rl 3.0.1 (Module 03 start)
- Decided the constrained-RL library: **rsl_rl-Lagrangian** (not OmniSafe/skrl) — baseline is
  rsl_rl 3.0.1, so cPPO on the same trainer/hyperparams keeps the comparison clean. Variant:
  **separate cost critic** (textbook PPO-Lagrangian), not the single-critic penalty shortcut.
- Pulled rsl_rl 3.0.1 source (ppo/storage/runner/actor_critic/utils) and built against the real
  API: obs is a TensorDict with obs-groups; cost rides the `extras` channel of process_env_step.
- New package `ur5_grasp/safe_rl/`: costs.py (collision/joint-limit/manipulability), actor_critic_cost.py
  (2nd cost critic), rollout_storage_cost.py (cost-GAE), ppo_lagrangian.py (combined advantage
  (A_r−λA_c)/(1+λ) + dual-ascent λ), lagrangian_runner.py.
- Env now emits per-step `extras["cost"]` (both agents) + logs safety/* diagnostics. cPPO cfg
  `UR5eLiftCPPORunnerCfg` (experiment ur5e_lift_cppo); registered `rsl_rl_cppo_cfg_entry_point`;
  train.py/play.py gained a LagrangianRunner branch. PPO baseline path untouched.
- All 12 touched files pass py_compile. NOT yet run on hardware (sandbox has no GPU/Isaac).
- Placeholders to calibrate on the lab PC: MANIP_FLOOR (via new calibrate_manipulability.py),
  COLLISION_Z_FLOOR (table height), cost_limit (from PPO baseline mean episodic cost).
- NEXT: finish Module 02 (retrain PPO on weld env + play-verify) → cPPO smoke test (5 iters) →
  calibrate floors → full cPPO run → overlay cPPO-vs-PPO in TB.
- Re-ran zero_agent.py (Day 9): probe again reports "offset=0" but "true grasp point" == wrist_3
  position exactly -> the SAME finger-origin-at-flange artifact from Day 8. ee_frame z=0.180 sits
  0.16 m below the flange (=fingertip level). CONFIRMED: keep offset=0.16, do NOT zero it. Gripper
  visual mesh roll is cosmetic -> deferred to Layer 3 (real-hardware mounting). Weld is unaffected.
- cPPO SMOKE TEST PASSED (Day 9, 64 envs x 5 iters, logbook/smoke_cppo.log): Cost Critic MLP built,
  ran clean no traceback, cost_value_function loss decreasing (critic learning), cost_lambda/
  mean_episode_cost/safety/* all logged, reward finite. Logs -> logs/rsl_rl/ur5e_lift_cppo/.
  KEY: safety/manipulability_mean=0.11 min=0.091 -> Jacobian extraction in costs.py is CORRECT
  (biggest untested risk cleared). Also confirmed PPO baseline retrain done (model_1499, 11:13 run).
- OBSERVATION: all cost terms read 0 at the placeholder thresholds -> constraints currently inert.
  For a meaningful benchmark the thresholds must make UNCONSTRAINED PPO violate. Extended
  calibrate_manipulability.py to report w + joint-limit clearance + min link-height distributions
  and baseline violation rates, so thresholds can be set to bite (~few-30% violation).
- Calibrated safety thresholds from trained baseline (logbook/calib.log, 25.6k samples):
  * Manipulability w: min .021 / mean .055 / max .114. Set MANIP_FLOOR=0.045 (~p10-p25 => ~20%
    baseline violation). THIS is the active constraint (near-singular Jacobian; ties to IBVS theme).
  * Joint-limit clearance: min 1.39 rad -> arm never nears limits in tabletop grasp. INACTIVE by
    construction. Keep margin 0.10 as monitored-but-satisfied.
  * Min link height: min 0.125 m above table -> arm links never near table. INACTIVE. Keep floor 0.0
    as monitored-but-satisfied.
  THESIS FRAMING: lead with manipulability/singularity as the active constraint; report joint-limit
  & collision as monitored constraints that stayed satisfied (honest, still a valid cPPO result).
  * cost_limit still to set from a 50-iter unconstrained episodic-cost probe.
- cost_limit probe (50 iters, 4096 envs, logbook/cost_probe.log): CLEAN, no NaN, ~200k steps/s
  (keep num_envs=4096). Lagrangian mechanism fully working: cost_singularity 0.1->0.4 (constraint
  bites at floor 0.045); mean_episode_cost climbs 6.7->74 as policy learns to grasp near singular
  poses; cost_lambda self-engages 0->6.85 (controlled, not railed); reward 58->48 = safety-vs-reward
  tradeoff visible. DECISION: keep cost_limit=25 (~65% cut vs natural ~70+ cost; ~17% reward dip).
- BENCHMARK NOTE: PPO baseline model_1499 was trained at old MANIP_FLOOR=0.02 (cost curve ~0, not
  comparable). Re-run unconstrained PPO at floor 0.045 so PPO vs cPPO use the same cost definition.
- NEXT: full cPPO run (ur5e_lift_cppo) + full PPO baseline at floor 0.045 (ur5e_lift), then overlay.

## 2026-07-19 (Day 9 cont.)
- Runbook Step 0: mandated tmux session `thesis_abrabbi` for all training (start tmux first,
  then activate/run inside it; detach Ctrl-b d).
- Doc-debt reconcile: 03_cppo_benchmark.md thresholds/next-steps/open-Qs updated to calibrated
  state (MANIP_FLOOR=0.045, cost_limit=25 validated, Jacobian index resolved); rsl_rl_cppo_cfg.py
  cost_limit comment un-placeholdered; runbook intro marks Steps 1-5 done, only 6-7 remain.
- Built results-table scaffold: results/03_cppo_vs_ppo_results.docx (TNR 14, centered caption,
  PPO vs cPPO, empty cells to fill after the two full runs).
- Started `Thesis_Documentation/` — the beginner-facing replicate-from-scratch guide (Module 07),
  written parallel to the thesis. 10 pages built from logbook + run_log + ur5_grasp source:
  01 env-setup and 02 grasp-env fully written (done work); 03 cppo-benchmark documented to the
  calibrated state with Steps 6-7 marked PENDING; 04/05 planned outlines; 06 results,
  07 troubleshooting (all bugs+fixes), 08 glossary, 09 changelog. All referenced paths verified.
  Convention going forward: fold each session's work into the matching Thesis_Documentation page
  + append to its 09_Changelog.md.

## 2026-07-19 (Day 9 cont.) — Module 03 COMPLETE (Layer 1 PASS)
- Ran both full 1500-iter trainings, num_envs=4096: cPPO (ur5e_lift_cppo) + matched PPO baseline
  (ur5e_lift) at MANIP_FLOOR=0.045. NOTE: my tee path `logbook/03_cppo_full.log` was wrong (cwd is
  IsaacLab, logbook is ../logbook) so nothing saved — rsl_rl TB event files hold the real data. Use
  absolute path next time.
- Results pulled from TB CSVs. cPPO: reward 166.3, viol_singularity 6.65% (peak 51.7%),
  cost_total 0.0149, mean_episode_cost 2.24 (peak 80.2, budget 25), cost_lambda peak 16.7 -> 0.
  PPO: reward 167.2, viol_singularity 16.86% (peak 74.8%), cost_total 0.0201 (no lambda/episode_cost
  logged — Lagrangian-only metrics, expected).
- Wrote eval_success.py (new): replays a checkpoint, scores lift + goal-reach over N episodes using
  the env's own object_is_lifted / object_goal_distance math. Over 512 episodes (lift>0.1 m,
  goal<1 cm): cPPO 100% lift / 99.6% goal; PPO 100% / 100%. Task success is a tie.
- HEADLINE: cPPO = same grasping success + reward as PPO, ~60% fewer singularity violations. Safety
  at no task cost. Layer 1 must-pass = DONE.
- Deliverable: results/03_cppo_vs_ppo_results.docx (TNR 14, centered caption). Module 03 updated.
- TODO: commit on lab PC (eval_success.py + logs); optional fill of joint-limit/collision monitored
  rows (both ~0) from TB.

## 2026-07-20 (Day 10) — Layer 1 figures + tracking sync
- Archived both runs' TB scalars to `results/tb_csv/` (cppo/ + ppo/, 9 CSVs + README).
- Generated the four Layer 1 figures from those CSVs (script `results/scripts/make_layer1_figs.py`,
  reproducible): reward overlay, cost-vs-budget (cost_limit=25 line), cost_lambda dynamics,
  singularity-violation bars (MANIP_FLOOR=0.045 annotated). Saved PNG (300 dpi) + vector PDF to
  `Thesis_Documentation/assets/`. Times-New-Roman style (Liberation Serif substitute in sandbox;
  real TNR picks up automatically when compiled on a machine that has it), centered captions,
  two-colour palette. Verified each figure visually; numbers match the CSVs and the results doc.
- Filled the four PENDING figure links in `06_Results_and_Experiments.md` to embed the assets.
- Swept every lagging tracking file to reflect Layer 1 = DONE (data pulled from run_log Day-9 entry +
  the TB CSVs; cross-checked against the <10> benchmark session — no new/changed numbers):
  `logbook/00_INDEX.md` (status line + module table 02/03), `logbook/02_grasp_env.md` (PPO retrain
  done), `logbook/03_cppo_benchmark.md` (next-steps 4–5 → done), `logbook/03b_cppo_runbook.md`
  (all steps done), `logbook/07_documentation.md`, and `Thesis_Documentation/` pages 00/03/06/09.
- Still open: commit on the lab PC. NOTE: `.project-cache/.../memory.md` is read-only in this
  session — it still describes "Day 8 next / run 2 full trainings" and should be refreshed from the
  claude.ai project side so future chats start with Layer 1 marked complete.

## 2026-07-19 (Day 9 cont.) — Consolidation: Methods chapter
- Drafted Thesis_Documentation/Methods_Chapter_Layer1.md (formal Methods prose for Layer 1), pulled
  from source (env cfg, costs.py, ppo_lagrangian.py, rsl_rl cfgs). Next consolidation items: figures
  (separate session, CSVs in results/tb_csv/) and typesetting into the KUET thesis book.
## 2026-07-22 (Day 11) — Caught & fixed isaaclab.sh path bug in doc commands 
- missing ../ prefix for ur5_grasp/ scripts, since IsaacLab is a sibling dir not a subdir
- commited the bug fixed in the github

## 2026-07-24 (Day 13) — Layer 2 kickoff (IBVS), Phase 1 camera test
- Decision: eye-in-hand, RGB webcam only (no RGB-D). Monocular IBVS with approximate depth;
  the unmeasured Z becomes the job of the RL-tuned image Jacobian.
- Added ur5_grasp/scripts/ibvs_camera_test.py — wrist-mounted RGB CameraCfg injected into the
  PLAY env (Layer 1 files untouched); saves crosshair-overlay frames to results/ibvs_phase1/.
- PENDING first run on lab PC: ./isaaclab.sh -p ../ur5_grasp/scripts/ibvs_camera_test.py
  --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1 --headless --enable_cameras
- Phase 1 VERIFIED: eye-in-hand RGB camera renders + world->pixel projection correct
  (on-axis point -> image centre; cube pixel tracks cube). Mount recovered empirically:
  approach axis = wrist -z; pos=(-3e-05,0.00368,-0.03983) rot=(-0.03285,0.70643,0.70629,0.03228).
  Gotchas: needs --enable_cameras; CUDA 804 was a driver-update/reboot issue (now fine).
  Next: Phase 2 — colour-centroid detection + classical IBVS control law.
- Phase 2 (detection) working: colour-blob detector finds the DexCube (violet ~[112,83,190]).
  Black frames were the camera buried INSIDE the gripper mesh (4cm mount) -> fixed with a 0.3m
  standoff along the view axis (base env already had a dome light). Mount framing still needs
  tuning (cube too large/edge, flange occludes). GT world->pixel projection ~50px off but not
  needed for IBVS (servo on detected centroid). Next: tune mount, then IBVS control law.
- Phase 2b: wrote ibvs_servo.py (probe-measured image Jacobian + proportional centroid servo).
  Runs, but BLOCKED on eye-in-hand framing at the RL ready pose (cube too large/at edge ->
  probe pushes it out of view). Not a code bug. Next: either GUI mount tuning, or start IBVS
  from a policy-driven pre-grasp pose (recommended) so the camera frames the cube naturally.

## Day 14 — Layer 2 Phase 2 unblocked (IBVS framing)
- Diagnosed the `[abort] cube left view` blocker: root cause was `ibvs_servo.py`'s cube PIN, not the arm pose. It forced a 0.30 m depth + a world-frame `[0.03,0,0]` offset → cube too large / at the frame edge, so probe/servo moves ejected it.
- Fix (surgical; probe+servo loop untouched): pin now projects the camera's optical axis onto the cube's resting plane (the geometry `ibvs_camera_test.py` already verified), then applies a controlled image-horizontal off-centre with a margin guard (`SAFE_U/V`, `START_OFFSETS_M`) that shrinks/re-pins so the cube always starts safely in view. Emits `[start] … err_px=…`.
- Dropped the policy-driven start for the classical baseline (stochastic + couples the baseline to the RL policy); kept an optional `HOVER_Q` look-down hook (default off) for flange occlusion only.
- Confirmed both scripts use the 0.30 m standoff mount; logbook's "verified 4 cm mount" flagged STALE.
- NEXT (lab PC): run `ibvs_servo.py` with `--enable_cameras`, confirm `err_px` shrinks toward ~0 = classical baseline; save curve to `results/ibvs_phase2/`.
- Day 14 follow-up: first run showed the ready-pose camera looks SIDEWAYS (`fwd_z > -0.05`), so table-projection can't work from there. Reworked the pin to be orientation-agnostic: pin the cube STATIC on the optical axis (`cpos + 0.30*fwd`, dead-centre by construction), controlled image-horizontal off-centre, and re-pin every physics step (`step_cam_move`) so it doesn't free-fall. Valid classical centering baseline (cube floats; fine for the image-Jacobian comparison). `HOVER_Q` kept for an optional look-down/table-realistic view.
- Day 14 probe fix: start framing now works (err_px≈66 at depth 0.30). Probe aborted on the vertical axis — the ~11 cm DexCube fills ~14% of frame AND the arm Jacobian is ill-conditioned for one camera axis (pinv amplifies a fixed nudge → view swings). Fix: (1) `START_DEPTH_M` 0.30→0.45 so the cube sits ~65 px with room; (2) adaptive probe — on lost detection, undo and retry with a smaller nudge AND a tighter joint-step `cap` (added `cap` arg to `step_cam_move`; servo keeps the full 0.08 cap). Informative aborts point to the exact knob to tune next.
- Day 14 root cause (frames): with debug gizmos disabled, the wrist cam shows the GRIPPER + empty background and NO cube (`settled global-violet=None`). The earlier "detections" were a debug axis-arrow, not the DexCube. The mount is aimed at the grasp point between the fingers (via `recommend_aim`), so from the sideways ready pose it never sees a cube out on the table. Conclusion: camera/pose problem, not a code bug. Also disabled `commands.object_pose.debug_vis` + `ee_frame.debug_vis` in ibvs_servo (gizmos polluted the colour mask), and added saved debug frames.
- Decision: get a LOOK-DOWN pose via a short GUI session. New helper `ur5_grasp/scripts/pose_finder.py` holds the arm at a passed `--q`, opens the GUI, and prints/saves the wrist-cam view + a copy-paste HOVER_Q line. Iterate `--q` until the cube is centred, then set HOVER_Q in ibvs_servo.py.
- Day 14 pose sweep (8 configs, frames read): DEFINITIVE — the wrist camera sees a grey webcam model + the black gripper at ~0.30 m in EVERY pose; the cube is never in view (2 poses black = lens buried). Root cause is the MOUNT, not the arm pose: the camera is 0.30 m out along wrist +z aimed BACK at the grasp point, so the wrist/gripper are always between the lens and the workspace. Fix must re-place the camera beside the gripper looking OUTWARD along the approach axis (wrist -z). Arm-pose sweeping was the wrong variable. Decision pending: bounded mount-fix vs timebox/document Layer 2 (stretch; Layer 1 done+written) vs switch to a fixed external camera.
- Day 14 BREAKTHROUGH (mount_finder + geometry.txt): geometry.txt showed the cube sits along wrist +z (z=+0.18..+0.33), so the "approach = wrist -z" note was BACKWARDS. Re-aimed candidate cameras along +z from small side offsets; at the READY pose the +x-side mount (pos (0.06,0,0), rot (0.9894,0,-0.1452,0)) sees the cube cleanly on the table (scan_p1_c0/c1/c3). Also found the cube is the MULTI-COLOUR DexCube (cyan/yellow/red faces), not violet — the [112,83,190] colour mask never matched it. Rewrote ibvs_servo.py: new mount, saturation-based detector (most-colourful blob), and dropped all the floating-cube pinning — it now detects and servos the REAL cube at the ready pose. Ready to test the classical baseline.
- Day 14 IBVS servo status: end-to-end loop WORKS partially. Camera (fixed mount) sees the cube; saturation+largest-blob detector is reliable; wrist-derived camera pose fixed the dc=0 bug; image Jacobian is well-conditioned (det ~2.2e6). Servo consistently reduces centroid error 42.6 -> ~20 px (~50%), then the arm arcs the camera INTO the cube (npx explodes 2k->20k) and it diverges — same result across DLS-vs-pinv, orientation-lock (full 6x6 J, zero angular), height-lock (zero world-z), depth-hold, gentle gain/cap, and periodic re-probing. Root cause = poor arm conditioning for camera translation at the ready servo pose; needs a better-conditioned HOVER_Q (a conditioning scan), not more gain tuning. Deterministic setup: randomisation frozen, cube spawned at (0.56,0.16,0.055) to frame centrally. debug_start/end.png saved each run.
- Day 14 IBVS servo — final diagnosis: arm-Jacobian cond=9 (NOT singular), so translation is physically fine, but the optical axis tilts during servo (optz -0.949 -> -0.808) even with angular rows weighted 25x. Root cause of the persistent ~50%-then-diverge: the incremental joint-target + linear/angular least-squares scheme leaks orientation (camera pitches -> dives at the cube). Fixing it properly needs a resolved-rate/operational-space velocity controller with a hard orientation constraint (or a servo pose chosen by an image-motion manipulability scan) — a control sub-project, not a tuning tweak. RECOMMENDATION: lock in the working pipeline (mount, detection, self-measured image Jacobian, ~50% centroid-error reduction) and document the servo-convergence limitation as future work. Layer 1 remains the defensible thesis.
- Day 14 write-up: documented Layer 2 Phase 2 properly. Rewrote logbook/04_layer2_ibvs.md (clean final status); replaced Thesis_Documentation/04_Layer2_IBVS.md outline with the built pipeline + ~50% result + honest limitation; added Methods_Chapter_Layer2.md (formal thesis prose, parallels Layer 1); added the 5 Layer 2 bugs to 07_Troubleshooting; added 3 evidence figures (assets/fig_l2_*.png); updated 00_START_HERE + 09_Changelog. Scripts finalised: ibvs_servo.py, mount_finder.py, pose_finder.py.

## 2026-07-26 (Day 16) — RH-P12-RN gripper import started (real contact grasp, replaces the weld)
- Decision: build the REAL gripper (ROBOTIS RH-P12-RN) as a SEPARATE additive env rather than
  fixing the Robotiq 2f-85 contact physics. Rationale: the 2f-85 is not the hardware gripper, so
  perfecting its contact buys no sim-to-real; and swapping the weld inside the Layer 1 env would
  invalidate both trained policies + all Layer 1 figures. Layer 1 files stay FROZEN.
- KEY FINDING: the RH-P12-RN URDF is a pure TREE (5 links / 4 revolute joints, no closed loop),
  unlike the 2f-85 4-bar. Every joint is directly drivable -> there IS a force path to the pads.
  This is why the 2f-85 could never hold (passive joints, stiffness=0, loop never closed in PhysX).
- Joint coupling: opposed axis signs (rh_p12_rn +x / rh_r2 -x / rh_l1 -x / rh_l2 +x) mean all four
  joints take the SAME scalar target q to keep the pads parallel. q=0 open, q=1.0 closed.
  No PhysX mimic joints and no loop-closure joint needed.
- Vendored `ur5_grasp/assets/rh_p12_rn/` (flat URDF + 5 STLs + ROBOTIS licence). Three edits vs the
  upstream xacro: xacro removed / relative mesh paths; `world` link + `world_fixed` joint dropped so
  rh_p12_rn_base is the root; and INERTIAS FIXED — upstream ships placeholder ixx=iyy=izz=1.0 with
  the real values commented out (a 22 g fingertip with 1.0 kg*m^2 would behave like a flywheel).
  rh_*_2 ixx/izz round to 0.0 upstream -> 1e-5 floor applied.
- Geometry measured from the STLs (sandbox): pad inner faces sit at y=+/-0.0535 in base frame ->
  ~107 mm max opening (matches the 106 mm spec); fingertip reaches z~0.1165 above the mount face,
  so TCP is ~0.095-0.10 (vs the Robotiq's 0.16). DexCube is ~4.1 cm (0.0515 * 0.8) -> ample room.
- Added `ur5_grasp/tools/make_ur5e_rhp12_usd.py`: UrdfConverter (convex_decomposition colliders so
  the pad faces survive) -> merged single-articulation USD (ur5e.usd with Gripper=None + fixed joint
  wrist_3_link -> rh_p12_rn_base, nested articulation root disabled) -> validate + STROKE SWEEP that
  prints pad separation vs q. The sweep is the acceptance test.
- PENDING on lab PC:
    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/tools/make_ur5e_rhp12_usd.py --headless
  Then paste tools/make_rhp12_report.txt. Next after that: robots/ur5e_rhp12.py + a no-weld
  task id Isaac-Lift-Cube-UR5e-RHP12-v0, then grasp_hold_test.py for the real contact verdict.
- BUILD SUCCEEDED first try (tools/make_rhp12_report.txt). Single articulation, 10 joints /
  12 bodies. Joint order is INTERLEAVED — ['...arm x6', 'rh_l1', 'rh_p12_rn', 'rh_l2', 'rh_r2'] —
  so always resolve gripper joints by NAME, never by index.
- Stroke sweep PASSED and is monotonic: pad gap 0.1145 (q=0) -> 0.0216 (q=1.0). Confirms a real
  force path to the pads, i.e. the thing the Robotiq never had. Default flange mount (pos 0,0,0,
  identity rot on wrist_3_link) was correct — no --mount_pos/--mount_rpy tuning needed.
- IMPORTANT FINDING — the TCP is NOT a fixed point. The fingers curl FORWARD as they close, so
  the pad midpoint travels 0.0767 m (open) -> 0.1049 m (closed) from wrist_3_link. A single
  guessed ee_frame offset can therefore fail for a purely geometric reason that looks identical
  to "grip too weak". Calibration must be empirical.
- Added (Layer 1 untouched, all additive):
    ur5_grasp/robots/ur5e_rhp12.py            — ArticulationCfg; drives ALL FOUR finger joints
                                                 (legal here: tree, no loop to fight). Grip force
                                                 set by effort_limit_sim=5.0 Nm (~100 N at the pad),
                                                 NOT by stiffness. TCP_OFFSET=0.085 provisional.
    ur5_grasp/tasks/lift/ur5e_rhp12_env.py    — subclass of UR5eCubeLiftEnv with _apply_weld() as
                                                 a no-op. Safety-cost channel kept, so a cPPO run
                                                 here stays comparable with Layer 1.
    ur5_grasp/tasks/lift/ur5e_rhp12_env_cfg.py— env cfg; gripper action = one binary command over
                                                 all 4 joints, so the ACTION SPACE is unchanged
                                                 from Layer 1 (policies stay comparable).
    ur5_grasp/scripts/rhp12_grasp_sweep.py    — contact-only hold test that sweeps the TCP offset.
  Registered ids: Isaac-Lift-Cube-UR5e-RHP12-v0 and -RHP12-Play-v0.
- PENDING on lab PC (the real verdict — does it grip without a weld?):
    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/rhp12_grasp_sweep.py \
        --task Isaac-Lift-Cube-UR5e-RHP12-Play-v0 --num_envs 1 --headless
  Writes results/rhp12_grasp_sweep.txt. If nothing holds, tune in order: pad friction material,
  then effort_limit_sim, then solver iterations — NOT stiffness (that was the Robotiq failure mode).
- Bug on first sweep run: `RuntimeError: Inplace update to inference tensor outside InferenceMode`.
  Cause: the env publishes safety-cost tensors into `self.extras` inside step() (so they are inference
  tensors), and the sweep called `env.reset()` OUTSIDE inference mode on each iteration. grasp_hold_test.py
  never hit it because it resets only once. Fix: the whole sweep loop, every reset included, now sits in one
  `torch.inference_mode()` block with act/scratch tensors allocated inside. Logged in 07_Troubleshooting.md.
- Sweep run 1: NO offset held, but the data was diagnostic, not just negative. In every row
  `cube->grasp` ~= `z_drop`, i.e. the cube's displacement was almost purely VERTICAL — it fell
  straight down rather than being squeezed out sideways or launched. That rules out friction.
  ROOT CAUSE = test protocol, not the gripper: the cube was released as a free rigid body at the
  same instant the CLOSE command was issued. The fingers need ~0.2 s to travel; a free body falls
  ~0.2 m in that time, and the grasp point sits only ~0.065-0.078 m above the table, so the cube
  always reached the table before the pads met. The middle band (0.070-0.095) shows the cube simply
  dropping to the table; the outer offsets (0.060 / 0.100 / 0.110) show it batted off the table
  (drop 0.21-0.26) because the cube was placed inside the palm or beyond the fingertips.
- FIX: added a SEAT PHASE to rhp12_grasp_sweep.py — the cube is held still (pose re-written, velocity
  zeroed) for `--seat_steps` (45) while the fingers close around it, then the help stops and the HOLD
  PHASE runs on contact forces alone. This is a test fixture only; it is switched off before the
  measurement, so the verdict is still a genuine contact-grasp result.
- Also added two diagnostic columns that identify WHICH failure any future run has:
    q_final ~ 1.00 -> fingers closed with nothing in the way => never touched the cube
                      (geometry / collider problem; friction irrelevant)
    q_final ~ 0.78 -> fingers stalled on the cube => real contact, residual position error is
                      being converted to clamp force; a drop then means friction/effort.
  pad_gap at end of seating is logged alongside it.
- PENDING re-run on lab PC (same command as before).
- ✅ SWEEP RUN 2 — **GRIP HOLDS WITH CONTACT FORCES ALONE (no weld).** 4/9 offsets held:
  0.090 / 0.095 / 0.100 / 0.110. Full table in logbook/05_layer3_sim2real.md.
  Reading: `q_final` stalled short of 1.0 in EVERY row (0.64-0.78), so the fingers made contact
  everywhere — no row was a geometry miss. The failures at 0.060-0.085 stall EARLIER with a WIDER
  pad gap: the cube sits too deep and is caught on the curved proximal r1/l1 links instead of the
  flat pads, which cannot hold it. From 0.090 the cube sits in the pad region, the fingers close
  further, and it holds. The holding band brackets the closed-pose TCP of 0.1049 as expected.
- CAVEAT: the sweep stopped at 0.110, so the band's UPPER edge is unknown and the reported
  "centre 0.099" is biased low. TCP_OFFSET deliberately NOT changed yet.
- Module 05 promoted to ACTIVE and rewritten with the full result. NEXT: extend the sweep upward
  (--offsets "0.100 0.110 0.120 0.130 0.140"), set TCP_OFFSET to the true centre, confirm, then
  train PPO on Isaac-Lift-Cube-UR5e-RHP12-v0 and compare against the Layer 1 weld baseline.
- Extended sweep (0.100-0.140): held at ALL FIVE, so "held" alone could not pick a value. Resolved it
  on physics instead: converted pad_gap (body origins) to the clear opening between pad FACES
  (face_gap = pad_gap - 0.0078) and compared against the 0.0412 m DexCube.
    0.100 -> +21.6 mm   0.110 -> +17.1 mm   0.120 -> +14.3 mm   0.130 -> +0.3 mm   0.140 -> -1.6 mm
  0.100-0.120 are FALSE POSITIVES: they pass a static hold with the pads stopped 14-22 mm wider than
  the cube, i.e. the cube is WEDGED on the curved proximal r1/l1 links, not held by the flat pads.
  That survives a static test and fails under real lift accelerations. 0.140 interpenetrates by 1.6 mm.
- **TCP_OFFSET LOCKED = 0.130** in robots/ur5e_rhp12.py (true flat-pad grip, q stalls 0.875,
  z_drop 2.9 mm). rhp12_grasp_sweep.py rewritten to report face_gap and select on it rather than on
  an arithmetic centre-of-band, which was a misleading statistic on a truncated band.
- NEXT: confirm with --offsets "0.125 0.130 0.135" (env ee_frame now actually uses 0.130), then
  train PPO on Isaac-Lift-Cube-UR5e-RHP12-v0 vs the Layer 1 weld baseline.
- ✅ CONFIRMATION RUN — calibration closed. 0.125/0.130/0.135 all HELD; 0.130 gives face_gap 0.0413
  vs cube 0.0412 (delta +0.1 mm), reproducing the previous run's 0.0415 to within 0.2 mm.
  q_final 0.876 = fingers stall on the cube and convert the residual 0.124 rad of commanded travel
  into clamp force. TCP_OFFSET = 0.130 is final.
- NEXT: smoke-test training (256 envs / 20 iters) before spending GPU hours, then the full PPO run on
  Isaac-Lift-Cube-UR5e-RHP12-v0 vs the Layer 1 weld baseline. Reward shaping was tuned for the weld
  (where grasping is free), so a slower curve under real contact is a FINDING about the weld's cost,
  not a failure — record it either way.
- Ran the 20-iteration smoke test with the GUI; robot does not grasp. EXPECTED — 20 iterations of PPO
  is a random policy (the Layer 1 weld env needed 1500 iters; lifting_object went 0.12 -> 2.16 over
  that run). A smoke test checks the loop runs and geometry is sane, NOT that grasping works.
- BUT one real risk to rule out first: TCP_OFFSET moved 0.085 -> 0.130, pushing the RL reach target
  4.5 cm further along wrist +z. The grasp sweep only ever proved the gripper holds a cube TELEPORTED
  between its pads; it never checked that the reach target the reward chases is somewhere useful. If
  the frame now sits below the table or off the pads, the reach reward is unlearnable and PPO will
  never find a grasp — which looks exactly like "the robot can't grasp".
- Added ur5_grasp/scripts/rhp12_geometry_check.py (zero_agent.py hardcodes Robotiq body names and
  crashes on this env). Reports at the ready pose: ee_frame vs TRUE pad midpoint, ee_frame height
  above the table, ee_frame -> cube distance, and the exact OffsetCfg that would land on the pads.
  Writes results/rhp12_geometry_check.txt.
- Wrote logbook/HANDOFF_next.md for a fresh training session (overwrote the stale Layer 2 handoff —
  that work's final state lives in logbook/04_layer2_ibvs.md, nothing lost). Handoff covers: the
  mandatory geometry check first, smoke test + full train commands, how to read the curve (do NOT
  judge before ~500 iters; watch Episode_Reward/lifting_object; Layer 1 went 0.12 -> 2.16), the
  Layer 1 comparison target, what would keep the weld defensible, and the session's gotchas.
- Refreshed logbook/00_INDEX.md status block + module table (04 closed, 05 ACTIVE).
- Geometry check PASSED, cleared for training. Closed-pad numbers: ee_frame vs pad origins
  0.0251 m, height above table +0.2123 m, ee_frame -> cube 0.2731 m. The feared failure (reach
  target inside the table) did not happen — it sits at +0.212 m, not the guessed ~0.07 m.
- FIXED rhp12_geometry_check.py before running it. It stepped with a zero action, but
  BinaryJointPositionAction masks on `action < 0`, so that leaves the gripper OPEN — it was
  comparing a CLOSING TCP against the open-pose pad origins and gating at < 0.02 m. It would
  have failed a correct config (0.0535 m) and recommended TCP_OFFSET ~0.077, outside the
  0.125-0.135 band the contact sweep proved HELD. Now probes open AND closed, gates on closed
  only, splits BLOCKING (table height, cube distance) from the advisory frame error, and names
  the contact sweep as the authority. Also fixed the stale '0.085' TCP_OFFSET comments in
  tasks/lift/ur5e_rhp12_env_cfg.py (actual value is 0.130).
- Cosmetic: gripper is now rendered near-black so it is distinguishable from the grey UR5e in the GUI
  (both imported light grey, so the hand blended into the wrist and you could not see open vs closed).
  Added `colour_gripper()` to tools/make_ur5e_rhp12_usd.py — binds a UsdPreviewSurface to every
  renderable prim under /Robot/RHP12, authored on the MERGED stage so it overrides the importer's
  material. New `--gripper_color "r g b"` flag (default "0.02 0.02 0.02"). Mass, inertia, colliders
  and joints untouched; TCP_OFFSET and all calibration remain valid.
  Rebuild:  ./isaaclab.sh -p ../ur5_grasp/tools/make_ur5e_rhp12_usd.py --headless --skip_convert
- Gripper colour attempt 1 FAILED (still white). Cause: binding a material on each MESH is not
  enough — USD resolves bindings by strength, and a binding authored on an ANCESTOR prim with
  `strongerThanDescendants` beats every binding below it, which is what the URDF importer does.
  Fix in tools/make_ur5e_rhp12_usd.py: (1) strip every existing binding in the /Robot/RHP12 subtree,
  (2) bind our material ONCE at the subtree root with strongerThanDescendants, (3) also write
  `displayColor` on each Gprim to cover meshes that had no material at all. The rebuild now logs how
  many prims it touched and which bindings it displaced, so a repeat failure is diagnosable.
- DECIDED to shape the reward up front rather than wait for a stall. Added
  ur5_grasp/tasks/lift/rhp12_rewards.py::object_lift_progress and wired it into the RH-P12-RN
  cfg, replacing the 0.04 m step in `lifting_object`. Strict superset: 1.0 at/above 0.04 m
  (identical to object_is_lifted, so object_goal_distance still switches on at the same point
  and weight 15.0 keeps its meaning), gated linear ramp below it from the MEASURED resting
  cube height 0.021 m. Rejected the obvious 'closed gripper near cube' bonus — that predicate
  IS _apply_weld's latch condition, so it would reinstate the weld in reward-space.
  near_tol=0.05 blocks farming height by batting the cube. COST: raw episode reward is no
  longer comparable with Layer 1 (166.3/167.2); the cross-run comparison moves to lift-success
  % (eval_success.py) and violation % (_apply_cost), neither of which depends on the reward.
- Smoke test PASSED (20 iters, 256 envs, shaped env): lifting_object 0.1584 nonzero as required,
  and object_goal_tracking 0.0227 is nonzero too — that term is gated on z > 0.04 m, so the cube
  already clears the lift threshold by chance. Safety channel live (manip 0.0970/0.0637, costs 0
  because MANIP_FLOOR 0.045 not breached). object_dropping 4.23% vs Layer 1's ~0% — expected
  without the weld, but watch it climb.
- Checked the Layer 1 log: the full 1500-iter run took 11 min 19 s, not 'hours' as the handoff
  claimed. That kills the shaped-vs-unshaped tradeoff — at 11 min a run you can have both.
  Added UR5eRHP12LiftEnvCfg_STOCK (+_PLAY) and registered Isaac-Lift-Cube-UR5e-RHP12-Stock-v0 /
  -Stock-Play-v0: identical contact env, Layer 1's ORIGINAL sparse lift reward. Registered as a
  task id rather than reverting the shaping by hand so both conditions stay reproducible and the
  logs self-document which ran. Plan: run Stock then shaped, same --seed 42; the gap between them
  IS the exploration cost of removing the weld, and Stock's reward stays comparable with Layer 1.
- BOTH contact runs done, 1500 iters / 4096 envs / seed 42, ~15 min each.
  FINDING 1: the task is learnable WITHOUT the weld and without reward help — stock-reward run
  reached lifting_object 13.84/15.0 (94% of the weld run's 14.80). Layer 3's minimum bar cleared.
  FINDING 2: cost of the weld = -37.6% episode reward (167.18 -> 104.28, identical reward fns so
  this is a valid comparison). It concentrates in PRECISION, not grasping: lifting_object -6% but
  object_goal_tracking -35% and fine-grained -90%. A real grip lets the cube shift; the weld pinned
  it to the TCP.
  FINDING 3: baseline singularity violation reproduces under contact — weld PPO 16.86% vs contact
  stock 13.98%. The Layer 1 safety result is NOT an artifact of the weld.
  FINDING 4 (the big one): the dense lift shaping BACKFIRED. It bought +31% reward over stock and
  paid 6.5x the singularity violations (91.57% vs 13.98%), cost_total 16x, manipulability_min
  0.0002 — parked on a singularity. Not transient: flat at ~91% for the last 400 iterations, while
  stock on the same env and seed learned AWAY from singularities (42% peak -> 14%). Plain PPO has
  no reason to resist since the cost channel is not in its objective. An innocuous shaping term
  silently traded safety for reward and only the cost channel caught it — a stronger motivation for
  cPPO than the Layer 1 numbers themselves.
  DECISION: stock is the PRIMARY contact result; shaped becomes a separate safe-RL finding.
  Checkpoints: 2026-07-26_21-36-58 (stock), 2026-07-26_22-30-27 (shaped).
