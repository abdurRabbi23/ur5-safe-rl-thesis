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

##Day 6: Spinning Up Parts 1-2 + PPO page read. Notes committed. Khan §3-4 deferred to pre-cPPO week.

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
