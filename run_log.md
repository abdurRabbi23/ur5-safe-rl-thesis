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
[Day 11] Caught & fixed isaaclab.sh path bug in doc commands (missing ../ prefix for ur5_grasp/ scripts, since IsaacLab is a sibling dir not a subdir)

## 2026-07-28 (Day 18) — Restart after Layer 1 + gripper diagnosis
- **Restart decision:** reset the whole repo to the Layer-1 commit (8d4cb41); deleted all
  Layer 2 (IBVS) and Layer 3 (RH-P12-RN gripper) work + the Module 08/09 experiments and
  their checkpoints. Layer 1 is untouched and is the frozen baseline. Old history preserved
  in tag `backup/pre-layer1-reset` and on origin/main (remote left as-is; local only).
- **New direction:** fix the real gripper. Layer 1's grasp is a proximity WELD (cube teleported
  to the gripper frame) — the 2f-85 never physically grips. Goal: make it grip with contact
  forces. No new gripper, no new algorithm.
- **Diagnosis (physics-only, scripts/grasp_hold_test.py with new probes):**
  - Bug 1 — open/close INVERTED. Measured pad gap vs finger_joint: 0.0 = pads touching (CLOSED),
    0.8 = ~85 mm (OPEN). Layer-1 cfg had GRIPPER_OPEN=0.0/CLOSE=0.8 swapped, so 'close' opened
    the hand fully. The weld hid this (it latches on action sign, not finger motion).
  - Bug 2 — reach frame 16 cm off. FrameTransformer used wrist_3 + [0,0,0.16]; real pad midpoint
    is ~1.3 cm from wrist_3. Exact local offset printed by grasp_lift_test.py.
  - CLEARED — fingers DO have enabled convexHull colliders (10, incl. both inner_finger pads);
    checked with tools/check_gripper_colliders.py (needs TraverseInstanceProxies — Isaac assets
    are instanceable). "No collider" was a false alarm from the first, buggy traversal.
  - Note: the mid-air freeze test is confounded (post-step teleport lets fingers ratchet through);
    a proper hold test needs the cube supported without teleport.
- **Built (Layer 1 untouched):** `-Contact-v0` / `-Contact-Play-v0` variant —
  `tasks/lift/ur5e_contact_env.py` (UR5eCubeContactEnv: weld no-op, keeps safety cost) +
  `ur5e_contact_env_cfg.py` (open/close swapped, EE offset corrected) + registration.
  Smoke test `scripts/grasp_lift_test.py` floats the cube (anti-gravity force) while the fingers
  close, then releases it to test if friction holds. NEXT: run it, read the [local offset] +
  HELD/DROPPED verdict; if it slips, tune pad friction / clamp effort; then re-run cPPO vs PPO on
  -Contact-v0.

## 2026-07-28 (Day 18, cont.) — SCOPE CHANGE: Layer 1 → 4-algorithm comparative benchmark
- **Contact grasping abandoned.** The 2f-85 will not grip reliably and pad-friction / clamp-effort
  tuning is a bottomless pit at this deadline. Reverted to the frozen WELD env; `-Contact-v0` is
  SHELVED (kept registered, not deleted). The Day-18 diagnosis (inverted open/close, EE frame
  offset, collider false alarm) is repurposed as a thesis subsection justifying the weld
  abstraction — negative result, not wasted work.
- **New Layer 1 scope:** comparative analysis over 4 algorithms — PPO, SAC, TD3, cPPO — on one
  frozen env, 3 seeds each. Supersedes the 2-algorithm cPPO-vs-PPO result.
- **Decisions locked:**
  - Cost function UNCHANGED and frozen: 3 terms, `MANIP_FLOOR=0.045`, `cost_limit=25`.
    **FOV term rejected** for Layer 1 — no camera exists there; it would invalidate the
    calibration, results doc, all 4 figures and the Methods chapter. FOV moves to Layer 2.
  - Constraint reporting corrected to "one binding (singularity) + two monitored-and-satisfied
    (joint-limit, collision)". Do not claim three active constraints.
  - Framework: PPO+cPPO stay on rsl_rl 3.0.1 (preserves the Module-03 "differs by the constraint
    alone" argument); SAC+TD3 from skrl; plus a **skrl-PPO bridge run** so the two stacks are
    anchored and no gap can be attributed to differing implementations.
  - 3 seeds minimum per algorithm (current Layer 1 is single-seed — fatal for a comparative claim).
- **Registered hypothesis (recorded before running):** all four will hit ~100% success, so the
  result lives on the safety axis — SAC (max-entropy) should violate the singularity floor MORE
  than PPO, TD3 (deterministic) LESS, and only cPPO controls it by construction.
- Checked the tree: Isaac Lab ships only `skrl_ppo_cfg.yaml` (no SAC/TD3 cfgs anywhere, incl. the
  Franka lift task). skrl's Runner does support both and IsaacLab's skrl train.py already resolves
  `--algorithm sac` → `skrl_sac_cfg_entry_point`, so this is YAML + registration, not trainer code.
- **FLAGGED for verification before any cfg edit:** the Day-18 note records the pad midpoint as
  ~1.3 cm from `wrist_3`. A 2f-85 is ~150 mm long, so that number looks like it was measured from
  the gripper base link, or is an instanceable-proxy transform artefact (same class as the earlier
  false "no colliders" alarm). Re-read the `[local offset]` print from grasp_lift_test.py and
  sanity-check against physical gripper length BEFORE editing `ur5e_lift_env_cfg.py`.
- Wrote `logbook/03c_multialgo_benchmark.md` (goal, locked decisions, run matrix, fairness
  protocol, cut order with TD3 as first-cut). Updated `logbook/00_INDEX.md` status + module table.
- Schedule locked: writing must be finished 2026-08-11. Training wall-clock is not the constraint;
  untested skrl off-policy is. Gates: env frozen Jul 29 → PPO+cPPO seeds Jul 30 (pass bar restored)
  → skrl cfgs + bridge Jul 31–Aug 2 → SAC Aug 3–4 → TD3 Aug 5–6 (**HARD CUT Aug 6 EOD**) →
  figures + writing Aug 7–11. Full table in `logbook/03c_multialgo_benchmark.md`.

## 2026-07-28 (Day 18, evening) — Step 0 CLOSED: EE offset verified, change REJECTED
- **Outcome: only ONE env change goes into the freeze** — the gripper open/close swap. The EE
  offset stays at `[0, 0, 0.16]`. Applying the flagged "fix" would have been wrong.
- Built `tools/check_gripper_mount.py` (prints every body in the `wrist_3` local frame, pad gap,
  reach frame, and a plausibility check; `--hold` keeps the GUI alive for inspection).
- **Gripper inversion CONFIRMED — apply it.** `finger_joint = 0.796` → 84.4 mm pad gap vs an
  85 mm spec stroke. So 0.8 = OPEN, 0.0 = pads touching = CLOSED. `robots/ur5e_robotiq.py` has
  these backwards.
- **EE offset `[0,0,0.16]` VERIFIED CORRECT — do not change.** `wrist_2_link` sits at local −Z,
  so +Z is the forward tool axis; 0.16 m matches flange d6 (0.0996) + 2F-85 body (~0.13). GUI
  confirms the marker lands at a sensible grasp height along the approach direction.
- **The "~1.3 cm" figure is an artefact.** Measured `[0, +0.0135, 0]` off collapsed gripper
  bodies. `_TCP_OFFSET = (-0.013, 0, 0)` in the contact cfg is invalid; stays shelved.
- **`base_link` name-collision theory is DEAD.** Isaac auto-renames the gripper base to
  `base_link_0`. No duplicates; both fixed joints resolve cleanly.
- **Root cause found:** all nine gripper bodies (idx 7–15) report *exactly* `[0,0,0]` in the
  `wrist_3` frame — degenerate. But the contact run measured an 84.4 mm pad gap, so they are not
  statically collapsed, they are *unreliable*. Gripper `body_pos_w` cannot be trusted in this
  asset. This fully explains the Day-18 finger pass-through: contact cannot resolve where the
  geometry renders. Arm transforms are exact (UR5e DH to 4 decimals) — the defect is gripper-only.
- **Confirmed case (B), impact = renders only.** GUI shows the gripper drawn at the wrist with the
  welded cube floating 16 cm out at the TCP. All four Layer-1 figures are matplotlib plots off TB
  scalars — zero renders in the deliverable set.
- **Decided NOT to rebuild the gripper USD.** Every frozen consumer reads arm bodies only
  (`MONITORED_BODIES` = idx 3/4/6, `EE_BODY` = 6, Jacobian = arm joints, weld → synthetic
  `ee_frame`). Nothing touches idx 7–15. Rebuilding `make_ur5e_robotiq_usd.py` = days of
  shelved-branch work fixing something that appears in no deliverable.
- **Written into `Thesis_Documentation/Methods_Chapter_Layer1.md` §2** as a declared abstraction
  (lumped-mass gripper + kinematic 160 mm TCP + proximity weld) with the mechanism stated, plus
  two consequences: altered wrist inertia (identical across runs → not a confound) and disabled
  self-collision (Layer 3 caveat). Turns a negative result into a defensible methods paragraph.
- **Qualitative figure identified and PARKED to Aug 7–11.** Paired play runs show PPO folded /
  tucked-wrist vs cPPO extended — matches the measured viol_singularity gap (16.86% vs 6.65%).
  Not yet valid: camera and seed unmatched, and "folded" ≠ "singular" for a 6-DOF arm, so each
  panel needs its measured Yoshikawa `w` in the caption. These checkpoints are superseded by the
  post-freeze 3-seed runs anyway — doing it now is throwaway work.
- Fixed stale PPO checkpoint pointer in `00_INDEX.md` (`2026-07-12_18-54-03` does not exist; the
  real weld-retrained run is `2026-07-19_16-29-57`).
- **NEXT (Jul 29):** swap the gripper constants → `play.py` sanity-check → freeze + git-tag →
  launch PPO ×3 seeds. Jul 30 gate is intact.

## 2026-07-29 (Day 19) — Env changes applied: gripper convention, 1 rad/s speed cap, 7 s episode
Pre-freeze env work. Three changes went in; the env is now ready to freeze + tag.

**1. Gripper open/close convention corrected** (`robots/ur5e_robotiq.py`).
`GRIPPER_OPEN` 0.0 → 0.8, `GRIPPER_CLOSE` 0.8 → 0.0, and the misleading comment above them
rewritten. Confirmed by Day-18 measurement (`finger_joint = 0.796` → 84.4 mm pad gap vs 85 mm
spec stroke). Three consumers, all resolved: the init pose (now genuinely open) and the two
`BinaryJointPositionActionCfg` command exprs in `ur5e_lift_env_cfg.py`. The shelved
`ur5e_contact_env_cfg.py` was left alone — it has its own `_TRUE` constants and is off the
Layer-1 path.

**`play.py` sanity check: weld latches — GATE PASSED.** The stale 2026-07-19 PPO checkpoint
places the cube sloppily and misses the target pose. This is EXPECTED and is not a blocker:
the policy obs is `joint_pos_rel` over all 12 joints, and `default_joint_pos["finger_joint"]`
moved 0.0 → 0.8, so a close command now reads as −0.8 where the policy was trained on +0.8.
One obs dimension flipped sign (plus the coupled knuckle joints) → out-of-distribution input
for a checkpoint that is being discarded anyway. The weld itself is kinematic
(`write_root_pose_to_sim`), so finger contact cannot break it. Retraining resolves it.

**2. Arm joint speed capped at 1.0 rad/s** (`robots/ur5e_robotiq.py`, `velocity_limit_sim`
3.14 → 1.0 on the `"arm"` actuator). Previous speed was π rad/s ≈ 180°/s. Rationale: a
plausible real-UR5e operating speed, which strengthens the Layer-3 sim-to-real argument, and
a *safety* thesis should not be running the arm at 180°/s. PhysX enforces it hard, so it
applies to train and play alike with no extra flags. Gripper actuators left at 2.0 rad/s
(finger travel, not arm motion). Verified by a 150-iter probe at `num_envs=4096`: reward
curve is near-identical in shape and trajectory to `ur5e_lift/2026-07-19_16-29-57` at matched
iteration count. Task remains feasible.

**3. Episode length 5.0 s → 7.0 s** (`ur5e_lift_env_cfg.py`). 250 → 350 control steps at
50 Hz. Pairs with the slower arm.

**4. `cost_limit` HELD at 25 — deliberate, and NOT the Day-9 number.** The budget is an
undiscounted *episodic* sum of a *per-step* cost. Lengthening the episode by 40% therefore
changes what the number means: the per-step allowance falls from 25/250 = 0.100 to
25/350 = 0.071, i.e. **~30% tighter**. Rescaling to 35 would have preserved the Day-9
calibration; holding at 25 is a deliberate choice to run a stricter safety budget.
**Consequence for the write-up: the Day-9 calibration can no longer be cited as the
justification for 25.** It must be re-evidenced by the Day-19 cPPO probe. This is exactly the
Lagrangian silent-failure mode flagged in the project notes — training would have looked
fine while the constraint quietly did something other than what the Methods chapter claimed.

**Correction to an earlier estimate:** 7 s episodes do NOT cost ~40% more compute. The rsl_rl
budget is `max_iterations × num_steps_per_env × num_envs` (1500 × 24 × 4096), independent of
episode length. Longer episodes mean fewer *completed* episodes inside the same step budget →
marginally noisier episodic statistics and fewer distinct cube spawns seen. `eval_success.py`
at 512 episodes takes ~40% longer wall-clock; irrelevant. SAC/TD3 schedule risk unchanged.

**Confirmed, no work needed:** the Layer-1 task is *already* "grasp a randomly spawned cube,
carry it to a randomised target". `reset_object_position` samples uniformly over
x ∈ (−0.1, 0.1), y ∈ (−0.25, 0.25) around [0.5, 0, 0.055], and the `object_pose` command
drives `object_goal_tracking`. `MANIP_FLOOR = 0.045` also needs no change — it is a per-step
threshold on joint configuration, untouched by timing.

**NEXT:** re-run the 150-iter PPO probe (env moved again) + a 50-iter cPPO probe to
re-evidence `cost_limit=25` at 350 steps. On the cPPO probe watch **lambda**: it must rise
from 0 and settle — saturating at `lambda_max=100` means 25 is unreachably tight, sitting at
0 means it is not binding and cPPO has nothing to do. Then freeze + git-tag and launch
PPO ×3 seeds. Jul 30 gate still reachable.

## 2026-07-29 (Day 19, cont.) — Speed cap and 7 s episode REVERTED: they erased the safety signal
The 1.0 rad/s cap and 7.0 s episode from earlier today are both **reverted**. A full 1500-iter
PPO run (`ur5e_lift/2026-07-28_23-24-42_ppo_s1_vel1_ep7`) showed they destroy the phenomenon
Layer 1 measures.

**`safety/viol_singularity`, 100-iter blocks:**

| iters | PPO 7 s / 1.0 rad/s | PPO 5 s / 3.14 (old) | cPPO 5 s / 3.14 (old) |
|---|---|---|---|
| 0–99 | 7.45% | 18.25% | 7.55% |
| 100–199 | 0.00% | 49.37% | 3.00% |
| 200–299 | 1.72% | 66.83% | 6.31% |
| 300–399 | 0.66% | 29.23% | 7.90% |
| 400–499 | 0.06% | 56.26% | 5.10% |
| 500–1399 | 0.00% | 7–19% | 4–6% |
| **1400–1499** | **0.0000%** | **15.24%** | **6.38%** |

Exactly zero from iteration 400 to 1500. Only 4.5% of iterations register any violation at all
(all before iter 400) against 96.8% for the old run. Converged `manipulability_min = 0.0547`,
**above** `MANIP_FLOOR = 0.045` — the arm never approaches a singularity. `cost_total = 0.0000`.

**Task performance was unaffected:** `lifting_object` 14.44 vs 14.79, `position_error` 0.1625 vs
0.1582, zero drops, `mean_episode_length` 350/350. Not a broken policy — a policy that solves the
task and is safe *by construction*.

**Why this is fatal to the benchmark:** with no violations, lambda never activates, the Lagrangian
term is identically zero, and cPPO's gradient becomes the same gradient as PPO's. Four algorithms
× three seeds would produce a cost column of zeros and no safety axis. The registered hypothesis
(SAC's entropy drives it into singularities, TD3's determinism does not) would have nothing to be
measured against.

**Cause isolated.** The 5 s / 1.0 rad/s probe run acted as an accidental ablation:
43.2% → 7.1% from the speed cap alone (matched iters 100–149), then 7.1% → 0.19% from the extra
2 s. **The speed cap did it.** At π rad/s the policy can whip the wrist through low-manipulability
configurations because recovery is cheap; at 1 rad/s it physically cannot leave a well-conditioned
region near the ready pose.

**Reverted:**
- `velocity_limit_sim` 1.0 → **3.14** (`"arm"` actuator) — with a DO-NOT-LOWER note in the file.
- `episode_length_s` back to the base **5.0 s**; the override is removed, with a note that
  `cost_limit` is an episodic budget and the two must move together or not at all.
- `cost_limit` = 25 with the **Day-9 calibration restored** as its justification (valid again at
  250 steps).

**The env is now identical to `2026-07-19_16-29-57` except for the gripper OPEN/CLOSE swap** —
exactly one change from the proven pass-bar environment. Ready to freeze.

**KEEP THIS RUN — it is a thesis result, not a failure.** "Constraint violations under this cost
function are a function of commanded joint velocity; at 1 rad/s an unconstrained policy satisfies
the constraint by construction with no task-performance penalty." It pre-empts the obvious examiner
question *"why not just slow the robot down?"*, it is a genuine sensitivity analysis on
`velocity_limit_sim`, and it feeds the Layer-3 hardware discussion. Log dir retained.

**NEXT:** commit shelved contact files separately → freeze + git-tag → PPO ×3 seeds.

## 2026-07-29 (Day 19, cont.) — Freeze landed; PPO ×3 seeds already done; new Cowork session picked up
Status check from a new Cowork session (folder freshly connected) found the above "NEXT" already
executed, just not logged: shelved contact files committed (`a9acc1a`), freeze committed
(`b8f0727`, "gripper OPEN/CLOSE convention corrected; velocity/episode experiment reverted"),
tagged `layer1-env-freeze`. **PPO ×3 seeds ran to completion** — `ur5e_lift/2026-07-28_23-53-22_ppo_s1`,
`…00-05-10_ppo_s2`, `…00-17-05_ppo_s3`, all to `model_1499.pt`. Jul 30 gate (pass bar restored) is
effectively already hit a day early. **cPPO ×3 seeds have NOT started** — only the superseded
100-iter probe (`probe_cppo_ep7_cl25`) exists. That is the actual next action, not "launch PPO".

**Git divergence found:** local `main` has 2 commits origin doesn't (`a9acc1a`, `b8f0727` above);
`origin/main` has 6 commits local doesn't (`0596d8b`…`0c320cf`, all Layer 2 IBVS + RH-P12 gripper
work — evidently pushed from the lab-PC session while this laptop-side clone worked the Layer-1
restart). No conflicts yet (clean split), but needs a pull/merge before either side pushes further,
or the freeze tag ends up on a history the lab PC doesn't have. Open task, not yet resolved.

**Project-memory import:** pulled a full handoff dump from the original "THESIS 4200" Claude
Project (custom instructions + its `memory.md` + uploaded-knowledge list — that project has no
raw transcripts, so this is its distilled summary, not literal recovery). Written into
`logbook/08_project_context.md` (new module) + a role/working-principles section added to
`CLAUDE.md`. Key findings, reconciled against this repo:
- **Scope-pivot memory was stale.** The old project's memory records the PPO/SAC/TD3/cPPO pivot
  as an open, unresolved debate with no title agreed. It's actually resolved — Day 18 here, with
  a registered hypothesis, fairness protocol, and cut order already written in `03c`. No action;
  just don't reopen it as if live.
- **KUET admin details captured for the first time in this repo:** BSc Mechatronics, supervisor
  Dr. Md. Helal-An-Nahiyan, IEEE citation style, the 6-chapter KUET structure incl. the easy-to-miss
  Ch.5 SDG-mapping requirement. Full table in `08_project_context.md`.
- **Font size conflict is real and still open** (12 pt per project instructions vs 14 pt per a
  separate note) — already flagged in `06_writing.md` since Day 7, still unconfirmed.
- **Genuinely missing, not just undocumented:** defense date, submission deadline, page limit —
  need to come from the supervisor directly. Also the Xia 2024 (UR5e safe DRL) reference has no
  PDF anywhere, old project or this repo.
- **Reference papers (Fawad Khan cPPO paper, Shahid, Shi, Zhang, the thesis proposal doc, and Md
  Masrul Khan's predecessor thesis book) exist only in the old Project's uploads — none are in
  this working folder.** Needed before lit-review/Chapter 2 writing happens in this session.
- **Robotiq 2F-85 rejection note is superseded by what actually shipped** — old memory says
  "rejected, use simple prismatic gripper"; the frozen env instead keeps the real 2F-85 asset and
  sidesteps the same mimic-joint problem via the kinematic weld. Already the accepted framing in
  `Methods_Chapter_Layer1.md` §2; no change needed, just noted for consistency.

**NEXT:** launch cPPO ×3 seeds (rsl_rl, on the frozen env). Resolve the git divergence before any
further pushes. Get defense date / deadline / page limit / font size from the supervisor.

## 2026-07-29 (Day 19, evening) — New folder: `Comparison test/`, benchmark redone from scratch
Decision: the 4-algorithm comparative benchmark moves out of the main `ur5_grasp/`/
`IsaacLab/logs/` sprawl into a dedicated folder, `Comparison test/`, and is retrained **completely
fresh there — including PPO, even though PPO ×3 seeds already finished in the main folder.**
Rationale (Touhid's call): one self-contained, clean provenance for the whole 15-run matrix,
separate from the Day 18 restart / shelved contact-env history.

Confirmed with the user before building: (1) redo everything, including PPO — not reusing the
main folder's `ppo_s1/s2/s3`; (2) the env/algorithm code (`ur5_grasp/`) gets copied into the new
folder as a working copy, rather than the new folder just holding configs/results while code
stays only in the main `ur5_grasp/`.

**Built:**
- `Comparison test/ur5_grasp/` — full copy of the main folder's `ur5_grasp/` (matches the
  `layer1-env-freeze` / `b8f0727` state exactly at copy time; `__pycache__` excluded).
- `Comparison test/configs/`, `results/` (with `make_layer1_figs.py` pre-copied), `docs/`.
- `Comparison test/runs/{ppo,cppo,sac,td3,skrl_ppo_bridge}/` — created as placeholders, then
  found to be the WRONG structure (see gotcha below). Left in place, empty, harmless; not where
  real output lands. Delete permission for these five empty dirs was denied by the mount (minor,
  not worth chasing).

**Technical gotcha found before any training ran (would have wasted a full session otherwise):**
read `train.py` / `eval_success.py` / `calibrate_manipulability.py` directly — `log_root_path` is
computed as `os.path.abspath(os.path.join("logs", "rsl_rl", experiment_name))`, i.e. relative to
the **process's cwd**, not to where the script file lives. Also confirmed `isaaclab.sh` never
`cd`s internally (`extract_python_exe` + `${python_exe} "$@"` only). So the *old* workflow
(`cd IsaacLab/ && ./isaaclab.sh -p ../ur5_grasp/scripts/train.py`) writes logs to
`IsaacLab/logs/...` purely because cwd = `IsaacLab/` at call time — **the log location has never
been tied to script location.** To land logs inside `Comparison test/`, the new session must `cd`
there FIRST and call IsaacLab by relative path the other way: `../IsaacLab/isaaclab.sh -p
ur5_grasp/scripts/train.py ...`. Written up with exact commands in the new module file. Also
flagged: the folder name has a space (`Comparison test`) — every shell command referencing it
needs quoting, otherwise `cd` silently splits on the space.

**Docs written:** `logbook/09_comparison_test.md` (new, active module — folder layout, the log-path
gotcha, the two-copies-of-ur5_grasp bookkeeping note, restated run matrix, next steps).
`logbook/03c_multialgo_benchmark.md` re-scoped to "decision record only" (hypothesis, fairness
protocol, cut order, schedule all still binding) with a pointer to `09` for current work.
`00_INDEX.md` and `HANDOFF.md` updated to point new sessions at `09` first.

**Not yet decided, flagged for the new session:** whether `Comparison test/` becomes part of the
main git repo (currently a plain filesystem copy, untracked) or gets its own — decide before the
first commit inside it, don't let it accumulate uncommitted history either way.

**NEXT:** from inside `Comparison test/`, launch PPO ×3 seeds, then cPPO ×3 seeds (commands in
`logbook/09_comparison_test.md` / `HANDOFF.md`).

**Committed** (`ed12dd0`): `Comparison test/` joins the main repo, per Touhid's call — not a
separate repo. Hit a real blocker first: `.git/index.lock` was a stale 0-byte file left behind by
an earlier `git status` in this sandboxed session (the mount's file-delete restriction meant `git`
itself couldn't clean up its own lock file, so every git command failed with "Another git process
seems to be running"). Fixed via `allow_cowork_file_delete` on the VM-mapped path (the
`/home/...` path form was rejected — needed the `/sessions/.../mnt/...` form) then `rm`. Also had
to set local git identity (`user.name`/`user.email`, matching the existing commit history —
Abdur Rabbi <abrabbi9999@gmail.com>) since this sandbox had none configured. `.gitignore`'s
`logs/` and `__pycache__/` rules apply repo-wide (no leading slash), so `Comparison test/logs/`
will be excluded automatically once training starts — confirmed before committing, nothing extra
needed in `.gitignore`.

## 2026-07-29 (Day 20) — Robotiq 2f-85 dropped; new simple two-finger gripper, real contact grasp validated
Decision (Touhid's call, before the PPO/cPPO launch): stop trying to make the Robotiq 2f-85 asset
work. Root cause finally pinned down, not just worked around: the stock `ur5e.usd`'s 2f-85 variant
is a closed 4-bar linkage authored as its OWN articulation; `make_ur5e_robotiq_usd.py`'s surgery to
fold it into the arm's articulation is what produced the Day 18 degenerate body positions, and
`check_gripper_colliders.py` separately found the finger pads had no working collider at all
(mesh-only, no `UsdPhysics.CollisionAPI`) — two independent bugs, same root cause. Also relevant:
the real Layer-3 hardware gripper is a ROBOTIS RH-P12-RN, not a 2f-85 (`CONTEXT.md`), so 2f-85
fidelity was never buying real sim-to-real value.

**Built (`Comparison test/ur5_grasp/`, additive only — nothing in the frozen Layer-1 files touched):**
- `tools/make_ur5e_simple_gripper_usd.py` — builds the UR5e arm alone (`Gripper=None` variant,
  confirmed available in `CONTEXT.md` — sidesteps the nested-articulation problem entirely) plus
  two independent prismatic finger joints authored from primitives (boxes), no linkage, no mimic
  joint — same "two independent prismatic joints" pattern as Isaac Lab's own Franka gripper.
- `robots/ur5e_simple_gripper.py` — `UR5E_SIMPLE_GRIPPER_CFG`, both fingers driven directly
  (symmetric, opposite sign, no passive/coupled joints).
- `tasks/lift/ur5e_simple_gripper_env_cfg.py` + two new gym ids (`Isaac-Lift-Cube-UR5e-
  SimpleGripper-v0` / `-Play-v0`) — reuses the existing `UR5eCubeContactEnv` class unchanged
  (its only job, `_apply_weld` -> no-op, is gripper-agnostic).
- `scripts/simple_gripper_grasp_test.py` — pin/close/release contact-hold test, adapted from
  `grasp_lift_test.py`.
- `tools/check_simple_gripper_joint_attrs.py` — raw-USD attribute dump (no sim), written mid-debug
  to separate "wrong value authored" from "PhysX interprets it unexpectedly".

**Two real bugs hit and fixed, in order:**
1. Fingers never moved under either open or close command, from step 0. Cause: the two hand-built
   `PrismaticJoint`s had kinematics (axis/limits) but no `UsdPhysics.DriveAPI` — nothing for
   `ImplicitActuatorCfg` to drive. The stock arm joints work because NVIDIA's asset already carries
   that schema. Fixed: explicit `UsdPhysics.DriveAPI.Apply(joint_prim, "linear")` on both finger
   joints.
2. After the drive fix, fingers moved and genuinely stalled against a cube (real contact confirmed)
   but the measured wrist_3->pad offset was ~0.031 m against a designed ~0.075 m. Raw-USD check
   confirmed `localPos0` was authored correctly (`(0.015, 0, 0.045)`) — so PhysX was resolving a
   `PrismaticJoint`'s off-axis (Y/Z) anchor offset differently than a `FixedJoint`'s identical-shape
   offset (which measured correctly at 0.03 m). Rather than chase the exact PhysX mechanism further,
   routed around it: moved the entire 0.075 m reach into the (proven-correct) `FixedJoint` mount,
   zeroed the finger joints' own Z offset. Re-measured exactly on target (0.0750 m). Known cosmetic
   side effect not yet fixed: fingers now visually overlap the mount plate by about half their
   length (self-collision between them is disabled, so not a stability risk) — deferred to a later
   visual pass, same as every other geometry number in this build (finger size/travel/friction are
   all first-pass, untuned beyond "does it grasp").

**Validated (standalone, `simple_gripper_grasp_test.py`, not yet inside the RL loop):** cube pinned
at the pad midpoint, gripper commanded closed, fingers stall at ~0.030 m (well short of their 0 m
closed target — genuinely obstructed, not passing through), pin released, cube holds (z steady,
even rises slightly) through 140 further steps. This is the first working real-contact grasp in
this project — no weld, no proximity latch.

**Schedule impact:** the Jul 30 gate ("launch PPO ×3 seeds, then cPPO ×3 seeds" on the frozen weld
env) is superseded — the whole 15-run matrix now needs to target the new SimpleGripper task instead
of the old weld env, once it clears the remaining checks below. Touhid's call on the rebuild cutoff
was "no fixed date — reassess after the first standalone grasp test," which is the checkpoint just
reached.

**NEXT (not yet done):**
1. ~~`play.py` visual gate~~ — superseded by the live grasp+lift demo script (see Day 20 cont.
   entry below). Waiting on Touhid to run it on the lab PC and report what he actually sees.
2. Short smoke-train (~50 iters) on the new task to confirm the full RL reward/obs loop behaves
   with the new gripper before committing to a full run.
3. Once both pass: re-freeze/tag this as the new Layer-1 env, update `09_comparison_test.md` /
   `03c_multialgo_benchmark.md` to point the run matrix at `-SimpleGripper-v0` instead of `-v0`,
   THEN launch PPO ×3 / cPPO ×3.

## 2026-07-29 (Day 20, cont.) — Live GUI grasp+lift demo: black gripper, TCP axis markers

Requested: a real (not pinned/teleported) visual validation of the simple gripper — reach down,
close on an actual cube, lift it into the air, hold it, with the gripper painted black and the TCP
marked with axis arrows, running in the GUI until manually stopped. This is a stronger version of
NEXT item 1 above (`play.py` visual gate), not a separate task — writing it that way instead.

**Why not the registered gym task:** `Isaac-Lift-Cube-UR5e-SimpleGripper-Play-v0`
(`ur5e_simple_gripper_env_cfg.py` -> `LiftEnvCfg`) carries `episode_length_s = 5.0` plus
`time_out` / `object_dropping` terminations — stepping it with `env.step()` the way
`simple_gripper_grasp_test.py` does would auto-reset mid-demo, the opposite of "hold it in the air
until I decide to quit." Built a standalone `InteractiveScene` script instead (same robot/table/
object/`ee_frame` config, no gym wrapper, so nothing times out) — same pattern IsaacLab's own
`scripts/tutorials/05_controllers/run_diff_ik.py` uses.

**Built:** `Comparison test/ur5_grasp/scripts/simple_gripper_live_grasp_demo.py`
- Real IK-driven approach: `DifferentialIKController` (`dls`, absolute pose) drives `wrist_3_link`;
  target TCP poses are converted to wrist targets by subtracting the fixed 0.075 m pad-plane tool
  offset (rotated into world frame via `quat_apply`) — same `_EE_OFFSET_Z` constant used in
  `ur5e_simple_gripper_env_cfg.py`, read once at runtime rather than re-guessed.
- State machine, loops forever (`while simulation_app.is_running()`): SETTLE -> DESCEND (down onto
  the cube's actual live position, read from `object.data.root_pos_w` each cycle, not hardcoded)
  -> CLOSE (real PD finger drive, no pinning) -> LIFT (+0.25 m, configurable via `--lift_height`)
  -> HOLD (3 s, the actual validation moment) -> LOWER -> OPEN -> RETRACT -> PAUSE -> repeat. Prints
  finger joint positions and cube height every cycle so the console output corroborates whatever's
  seen in the viewport (same "stalled short of closed = real contact" signature
  `simple_gripper_grasp_test.py` established).
- Gripper painted black: `UsdPreviewSurface` material bound to the default/visual material purpose
  on `base_link` + `left_finger` + `right_finger` (found by name under `.../SimpleGripper/`, so it
  covers every env if `--num_envs` > 1). Left the existing "physics"-purpose friction material
  binding untouched — this is cosmetic only, doesn't touch grip behavior.
- TCP marked live: `VisualizationMarkers(FRAME_MARKER_CFG)` (the same RGB axis-arrow marker
  IsaacLab's own diff-IK tutorial uses) updated every step from `ee_frame.data.target_pos_w` /
  `target_quat_w` — i.e. it tracks the REAL, currently-computed pad-midpoint frame, not a static
  guess.

**Not yet run — no GPU/Isaac Sim in this sandbox, same limitation as every other script here.**
Checked line-by-line against the actual API in this repo's `IsaacLab/source/isaaclab` (not
recalled from training data): `SceneEntityCfg.resolve`, `Articulation.set_joint_position_target`,
`DifferentialIKController.action_dim`, `VisualizationMarkers.visualize`,
`isaacsim.core.utils.stage.get_current_stage` — all confirmed to exist with the signatures used.
`python -m py_compile` passes. That's the ceiling of verification possible from here.

Run on the lab PC, GUI (no `--headless`):
```
cd ~/Abdur_Rabbi_THESIS/"Comparison test"
../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/simple_gripper_live_grasp_demo.py
```

**NEXT:** Touhid runs it and reports back — specifically whether the fingers visibly stall on the
cube (not pass through), whether the cube visibly leaves the table and stays up during HOLD, and
whether the black paint / TCP arrows actually render as expected. Any traceback goes back here
verbatim, same as every other first run in this project.

## 2026-07-29 (Day 20, cont.) — New gotcha: cli_args import path breaks one level deeper in `Comparison test/`
Ran the first smoke-train command from `Comparison test/` and hit
`ModuleNotFoundError: No module named 'cli_args'` in `train.py`. Root cause: `train.py` /
`play.py` / `eval_success.py` / `calibrate_manipulability.py` all compute Isaac Lab's rsl_rl
`cli_args` dir as `_CLI_ARGS_DIR = os.path.join(_REPO_ROOT, "IsaacLab", "scripts",
"reinforcement_learning", "rsl_rl")`, where `_REPO_ROOT` is "two directories up from this
script". In the main folder (`Abdur_Rabbi_THESIS/ur5_grasp/scripts/train.py`), two levels up
correctly lands at `Abdur_Rabbi_THESIS/`, right next to `IsaacLab/`. In `Comparison test/`
(`Abdur_Rabbi_THESIS/Comparison test/ur5_grasp/scripts/train.py`), two levels up only reaches
`Comparison test/` — one level short of `Abdur_Rabbi_THESIS/` where `IsaacLab/` actually lives.
This is a different bug from the Day 19 log-path gotcha (that one was about cwd; this one is
about `__file__`-relative path depth) — the extra directory nesting `Comparison test/` adds
broke an assumption baked into these four scripts that happened to be invisible in the main
folder's shallower layout.

**Fixed** (all four files, `Comparison test/ur5_grasp/scripts/` only — main folder's originals
untouched, they're correct for their own location): replaced the hardcoded 2-levels-up
`_CLI_ARGS_DIR` computation with `_find_isaaclab_root()`, which walks up from the script's own
directory looking for whichever ancestor actually contains `IsaacLab/isaaclab.sh`, capped at 8
levels. Verified the resolved path against the real filesystem before re-running:
`_find_isaaclab_root` correctly returns `Abdur_Rabbi_THESIS/IsaacLab`, and `cli_args.py` exists
there. Immune to however many directories deep this package ever gets copied again.

Not yet ported to the main folder's copy (same fix would be a no-op improvement there, not a
bug fix, since 2-levels-up already happens to be correct there) — flagged, not done, per
"mention rather than silently fix elsewhere."

## 2026-07-30 (Day 21) — Gripper orientation MEASURED not assumed; grasp point moved to the finger tips

Two problems reported from the GUI after the Day-20 live demo run: (1) the gripper sticks out
**sideways**, ~90 degrees off the arm's tool axis, and (2) the cube is not grasped between the
finger tips. Different causes, both now fixed — but **nothing has been run yet**, no GPU in the
sandbox as always. Everything below is written and cross-checked, not validated.

**Cause of (1): the mount axis was inherited, never measured.** The gripper was fixed onto
`wrist_3_link`'s local **+Z**. That number traces back to the frozen weld env's
`OffsetCfg(pos=[0, 0, 0.16])`, which is commented "approx, tune" in `ur5e_lift_env_cfg.py` and
was never validated — and, importantly, **could not have been**: a weld env teleports the cube
to whatever point the TCP names, so a TCP pointing out of the side of the wrist welds the cube
to a spot in mid-air and trains to 100% success exactly like a correct one. The Layer-1 result
is unaffected (the weld is an admitted abstraction), but the frozen env is **not evidence** for
the tool axis, and the HANDOFF "settled" table asserting "+Z is forward tool axis" was resting
on it. That row is corrected, not deleted — see below.

**Cause of (2): the Day-20 "round 2" workaround, mislabelled cosmetic.** Round 2 dodged a PhysX
quirk (an off-axis anchor offset on a `PrismaticJoint` resolving to 0.031 m where 0.075 m was
authored, while the identical offset on a `FixedJoint` measured correctly) by pushing the entire
forward reach into the fixed mount and setting `FINGER_Z_OFFSET = 0.0`. Consequence, flagged at
the time as a visual nit: the plate spanned 0.060–0.090 m from the flange while the finger boxes
spanned 0.045–0.105 m — the fingers were buried in their own mounting plate, half of each
sticking out *backwards* toward the wrist, and the TCP sat at 0.075 m = the finger MIDPOINT.
So the cube was being pinched at the middle of the fingers, level with the plate. Not cosmetic.

**Built:**
- `tools/check_wrist_frame.py` (new) — MEASURES which local axis of `wrist_3_link` is the tool
  axis, two independent ways, and refuses to write a result if they disagree. (a) *Which axis*:
  the tool axis is by definition the one `wrist_3_joint` rotates about, so it is the single local
  axis of `wrist_3_link` whose world direction is unchanged between wrist_3 = 0 and wrist_3 = 0.7
  rad — the other two read cos(0.7) = 0.76. (b) *Which sign*: on a UR arm the last link extends
  along its own rotation axis (d6 = 99.6 mm), so the wrist_2 -> wrist_3 origin offset, rotated
  into wrist_3's frame, gives the outward direction. Gravity is disabled for the run so the arm
  holds the written joint state exactly. Writes `assets/wrist_frame.json`.
- `robots/gripper_geometry.py` (new) — **single source of truth** for the gripper. Reads that
  JSON (and raises with the exact command to run if it is missing — no silent fallback to a
  guess) and derives everything else: `MOUNT_QUAT` (rotates the gripper's own +Z onto the
  measured tool axis, plus a tunable `MOUNT_ROLL_DEG` about it), `MOUNT_POS`, `TCP_OFFSET_POS`,
  `TCP_OFFSET_ROT`, and the open/close joint targets. This kills a real hazard: `0.075` was
  previously hand-copied into three files, each carrying a comment asking whoever changed one to
  remember the other two — and Day 21 is exactly the change that breaks that arrangement.

**New geometry** (metres from the flange, along the measured tool axis): plate 0.000–0.030
(flush on the flange, no floating gap), fingers 0.030–0.100, **TCP 0.075 = TIP_Z − GRASP_INSET
(0.025)**. The TCP lands on 0.075 again — the same number as before, but now *derived* rather
than coincidental: change `FINGER_LEN` or `BASE_THICK` and it follows automatically.

**How (2) is fixed without reopening the round-2 PhysX bug:** each finger is now a rigid-body
Xform whose ORIGIN sits exactly at its prismatic joint anchor — so the joint still carries zero
off-axis offset and the buggy code path is never taken — with its collision box as a CHILD prim
translated forward by `FINGER_GEOM_OFFSET_Z = 0.05`. A collider offset inside a rigid body is
ordinary USD (it is how nearly every robot link is authored) and never reaches the joint solver.
This is the "joint-anchor + offset-visual-child split" the round-2 note itself deferred.

**Changed:**
- `tools/make_ur5e_simple_gripper_usd.py` — imports all geometry from the new module; authors
  `localRot0` on the mount joint (the orientation fix); finger bodies via the new Xform +
  child-collider `add_body()`; guarded import that shuts Isaac down cleanly if the measurement
  JSON is missing. **New: a post-spawn geometry check** that measures where `left_finger`
  actually ended up relative to `wrist_3_link` and compares it against what was authored, in mm.
  Rounds 2 and 3 were both "the USD says X, PhysX resolved Y" bugs, and neither was visible in
  the joint/body name dump the report used to print. This check catches both immediately.
- `tasks/lift/ur5e_simple_gripper_env_cfg.py` — `ee_frame` offset now carries a **rotation** as
  well as a translation, so the TCP frame's own +Z is the true approach direction. Matters for
  anything reasoning about approach direction rather than just position (the demo's IK now, IBVS
  in Layer 2 later).
- `scripts/simple_gripper_live_grasp_demo.py` — **real bug found while making this change**:
  `wrist_target_for_tcp()` fed the TCP quaternion straight to the IK. That was correct while the
  offset was pure translation (TCP quat == wrist quat) but is wrong now that the offset rotates:
  FrameTransformer composes `tcp_quat = wrist_quat (x) MOUNT_QUAT`, so passing it through would
  command the WRIST to take the GRIPPER's orientation. Now undone explicitly. Also: the black
  paint pass had to change, since the gripper links are no longer Gprims (geometry moved to a
  child) — material binding inherits, `displayColor` is set on the descendants that are geometry.
- `scripts/simple_gripper_grasp_test.py` — pins the cube at the env's **`ee_frame` TCP**, not at
  the mean of the two finger BODY origins. Those used to coincide; they no longer do (finger body
  origins now sit at the joint anchors, level with the plate), so the old code would have dropped
  the cube inside the mounting plate. Taking it from `ee_frame` also means this test can't drift
  away from the frame the reward function actually uses.
- `robots/ur5e_simple_gripper.py` — open/close constants re-exported from the geometry module
  instead of redefined with a "must match the builder" comment. Same names, no import breaks.

**Verified from here (the ceiling without a GPU):** `py_compile` passes on all seven touched
files; every non-trivial IsaacLab API used was checked against this repo's actual
`source/isaaclab` (`quat_apply`, `quat_apply_inverse`, `quat_inv`, `quat_mul`,
`write_joint_state_to_sim`, `UsdFileCfg.variants`, `OffsetCfg.rot`, `SimulationCfg.gravity`,
`InteractiveScene.keys`), and `combine_frame_transforms` was read directly to confirm the
`tcp_quat = wrist_quat (x) offset_quat` composition order the demo fix depends on. The
`MOUNT_QUAT` math was unit-tested standalone against all six axis-aligned tool axes including
the antiparallel (-Z) branch: in every case `R(MOUNT_QUAT) @ [0,0,1]` equals the tool axis to
1e-16, the finger opening axis stays perpendicular to it, and `MOUNT_ROLL_DEG` rotates the
fingers about the approach axis while leaving the approach axis itself invariant.

**Not done / flagged, not silently fixed:**
- The gripper plate is still authored as `base_link`, which collides with the arm's own
  `base_link` and gets auto-renamed to `base_link_0` by Isaac Lab. Renaming it to `gripper_base`
  would be clearer but is out of scope for this pass and would touch the grasp test's body
  lookups. Noted in the builder's report output.
- `MOUNT_ROLL_DEG = 0.0` is a placeholder. The measured axis fixes the APPROACH direction; the
  roll about it (which way round the fingers open) is still arbitrary and has to be set by eye.
- Finger size / travel / friction / `GRASP_INSET` remain first-pass, untuned beyond "does it
  grasp" — unchanged from Day 20.
- The main folder's `ur5_grasp/` is untouched, per the two-copies rule. If the measurement comes
  back non-+Z, the frozen env's `OffsetCfg(pos=[0, 0, 0.16])` is pointing the wrong way too. That
  does NOT invalidate the Layer-1 weld results (a weld teleports the cube regardless), but it
  does need saying in the thesis text, and it matters for Layer 2. Decide separately.

**NEXT (lab PC, in this order — each gates the next):**
1. `../IsaacLab/isaaclab.sh -p ur5_grasp/tools/check_wrist_frame.py --headless`
   -> paste the report back. This is the measurement everything else depends on.
2. `../IsaacLab/isaaclab.sh -p ur5_grasp/tools/make_ur5e_simple_gripper_usd.py --headless`
   -> check section 3 of the report reads "OK", error under 2 mm.
3. `../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/simple_gripper_live_grasp_demo.py` (GUI)
   -> gripper should now point along the wrist with the plate flush on the flange, and the TCP
   arrows should sit between the finger tips. If the fingers close diagonally across the cube
   instead of squarely onto two faces, that's the roll — set `MOUNT_ROLL_DEG` (90 is the usual
   answer) and re-run step 2 only.
4. Then, unchanged from Day 20: `simple_gripper_grasp_test.py`, ~50-iter smoke train, re-freeze
   and re-tag the Layer-1 env, repoint the run matrix at `-SimpleGripper-v0`, launch PPO x3 /
   cPPO x3.

## 2026-07-30 (Day 21, cont.) — Measurement says the mount axis was RIGHT all along; the "26 mm mismatch" was my check, not the asset

Steps 1 and 2 run on the lab PC. Both reports read back directly from the folder
(`tools/check_wrist_frame_report.txt`, `tools/make_simple_gripper_report.txt`).

**Result 1 — the tool axis is +Z. The hypothesis was wrong.** Two independent methods, no
disagreement: local Z is the ONLY axis of `wrist_3_link` invariant under `wrist_3_joint`
rotation (dot = 1.000000, versus 0.764842 = cos(0.7) for both X and Y), and the wrist_2 ->
wrist_3 origin offset expressed in wrist_3's own frame is `[0, 0, +0.0996]` — exactly a
UR5e's d6, positive sign. So `MOUNT_QUAT` came out identity and **the Day-21 rebuild changed
the gripper's orientation not at all.** The pre-existing +Z mount was correct.

Worth being explicit that this was the point of measuring rather than reasoning: the standard
UR URDF convention made -Y look like the likely answer, and it is not. `HANDOFF.md`'s
"settled" row for `[0,0,0.16]` was reopened that morning and is now restored — but on
evidence this time, not on the weld env, which never could have tested it. (The magnitude
0.16 is a separate question and is still only "approx, tune".)

**Result 2 — the build's new geometry check fired a false alarm, and I fixed the check.**
It reported `expected [0.015, 0, 0.015]` vs `measured [0.04143, -0.0, 0.015]`, 26.43 mm, and
told Touhid not to proceed. That verdict was wrong. The error was entirely in **X** — the
finger joints' own free axis — while **Z, the mount offset actually under test, was exact to
five decimals**. Cause: the finger joints' `UsdPhysics.DriveAPI` carries an OPEN target
(authored on purpose so the asset spawns open) and the validation spawns with
`ImplicitActuatorCfg(stiffness=None, damping=None)`, which INHERITS the USD gains instead of
overriding them. So across the 5 settle steps the drives were hauling the fingers out toward
+TRAVEL and the read caught them mid-stroke at 0.0264 m of 0.035 m. 0.015 + 0.0264 = 0.04143.

Fixed three ways, so this cannot recur or be misread if something like it does:
  - park every joint at zero and settle 60 steps before reading, instead of 5;
  - compute the expected X from the finger joint's ACTUAL position read back from sim, so
    the check tests "given the joint is here, is the body where the geometry says" rather
    than silently also assuming the drive has not moved;
  - on failure, print the PER-AXIS error with the rule for reading it — error in X means the
    finger joints, error in Z means the mount.

Lesson recorded because it nearly cost a day: a diagnostic that cries wolf is worse than no
diagnostic. The numbers contained their own refutation (Z exact, error all in X) and the
verdict line ignored them.

**So where does that leave the original complaint?** The mount axis is confirmed correct and
was never the problem, which means "sticks out sideways" has to be either (a) the ROLL about
the tool axis — `MOUNT_ROLL_DEG` is still 0.0 and the finger opening direction is whatever
wrist_3_link's X happens to be, which at the ready pose may well sit diagonally across the
cube's faces — or (b) the old floating-plate geometry being read as "sideways": before the
rebuild the plate hung 7.5 cm off the flange with the finger boxes buried inside it and half
of each sticking out BACKWARDS toward the wrist, which is a strange enough shape to be
described that way. (b) is now fixed regardless — plate flush on the flange, fingers
projecting forward, TCP between the tips — so the GUI is the discriminator.

**NEXT:** step 3 was run but not yet reported. Waiting on what the viewport actually shows
now. If the fingers close diagonally across the cube rather than squarely onto two opposite
faces, it is the roll: set `MOUNT_ROLL_DEG` in `robots/gripper_geometry.py` (90 the usual
answer) and re-run step 2 only. Step 2 should also be re-run once regardless, to get a clean
section-3 "OK" from the corrected check before the grasp test.

## 2026-07-30 (Day 21, cont.) — Demo produced no diagnosable output; the capture command was the bug

Step 3 (the GUI demo) was reported as "errored / didn't run properly", so it was re-run piped
through `tee` into `tools/demo_run.log`. That log is 162 KB, 672 lines, and contains **not one
line from the script** — the full Isaac Sim extension startup, `Simulation App Startup
Complete` at 10.0 s, `Simulation App Shutting Down` at 13.3 s, and nothing in between. No
traceback either.

**The capture command was mine and it was wrong.** Piping stdout makes Python switch from
line-buffered to block-buffered; Isaac's `simulation_app.close()` tears the process down
without flushing, so every `print()` in the script died in the buffer. Isaac's own startup
logs survived because they are written from the C++ side, which is exactly what made the log
look like a normal startup followed by a silent death. One useful negative remains: Python
keeps stderr line-buffered even when redirected, so the absence of a traceback in a merged
`2>&1` capture is real evidence — **the script did not raise.** Which leaves "died during
scene construction" versus "ran fine and the window was closed three seconds in", and the log
cannot distinguish them. That ambiguity is the actual cost of the mistake.

**Fixed by following the pattern every other tool in this folder already used and this script
did not:** `simple_gripper_live_grasp_demo.py` now writes a flushed report to
`tools/demo_run_report.txt` (`log()` = print + write + flush, same helper as the builders),
wraps `main()` in a try/except that logs the traceback into that file, and logs PROGRESS at
every stage — context created, scene built, sim reset, body/joint names, paint count, setup
complete — plus the resolved geometry summary at the top. A run that dies now says where. No
pipe needed, and nothing to lose to buffering.

Note for the re-run: one full demo cycle is SETTLE 100 + DESCEND 200 + CLOSE 150 + LIFT 200 +
HOLD 300 steps at dt = 0.01, so with rendering it is on the order of a minute of wall clock
before the cube is in the air. Three seconds is not long enough to judge it — the arm will
still be settling.

**NEXT:** re-run step 3 (no `tee`), let it run at least a minute, then `tools/demo_run_report.txt`
gets read from here. Also worth re-running step 2 once for a clean section-3 "OK" from the
corrected geometry check.

## 2026-07-30 (Day 21, cont.) — Root cause: the demo has never run, since Day 20. `_marker_cfg` was a scene entity.

With the flushed report in place the re-run gave a clean traceback immediately:

```
File ".../simple_gripper_live_grasp_demo.py", line 454, in main
    scene = InteractiveScene(scene_cfg)
File ".../isaaclab/scene/interactive_scene.py", line 786, in _add_entities_from_cfg
    raise ValueError(f"Unknown asset config type for {asset_name}: {asset_cfg}")
ValueError: Unknown asset config type for _marker_cfg: VisualizationMarkersCfg(...)
```

**Cause.** `GraspDemoSceneCfg` declared its TCP marker in the configclass BODY:
```python
_marker_cfg = FRAME_MARKER_CFG.copy()
_marker_cfg.markers["frame"].scale = (0.12, 0.12, 0.12)
_marker_cfg.prim_path = "/Visuals/TCPFrame"
```
Read the actual source rather than assuming: `InteractiveScene._add_entities_from_cfg()`
iterates `self.cfg.__dict__.items()` and skips **only** names that appear in
`InteractiveSceneCfg.__dataclass_fields__` (`num_envs`, `env_spacing`, `lazy_sensor_update`,
...). A leading underscore means nothing to it. So `_marker_cfg` was not a private helper —
it was a scene entity, and `VisualizationMarkersCfg` is not a spawnable asset type, so the
chain falls through every `isinstance` branch to the final `else: raise ValueError`. It even
passed the `hasattr(asset_cfg, "prim_path")` regex-resolution step on the way, which is why
the error message shows a fully-formed marker cfg.

The frozen training env cfg does the identical three lines and is fine, because it builds its
marker inside `__post_init__` where it is an ordinary local, not a class field.

**Fixed:** marker cfg moved to module level as `_TCP_MARKER_CFG`, referenced by `ee_frame`.
Comment left at both sites explaining why it cannot move back.

**The significant part is the date.** This bug is from Day 20, when the script was written —
the failure is in scene construction, before a single frame renders, so **this demo has never
once run.** It was written Day 20 and "NEXT: Touhid runs it and reports back" was never
closed out; today's first attempt was reported as "errored" and the second was destroyed by
the `tee` buffering problem. Three sessions of it being the pending visual gate, and it had
never produced an image.

**Consequence worth carrying forward: where did "the gripper sticks out sideways" come from?**
It cannot have come from this script. The tool axis has since been measured as +Z, twice over,
so the mount was never wrong — meaning the original observation was made against some other
view (`play.py`, the grasp test, or the pre-rebuild floating-plate geometry, which really did
look wrong: plate hanging 7.5 cm off the flange with the finger boxes buried inside it and
half of each pointing BACKWARDS toward the wrist). That last one is the most likely candidate
and it is fixed regardless. Do not spend more effort on the mount axis without new evidence —
the measurement is decisive and the geometry that plausibly produced the complaint is gone.

**Three self-inflicted diagnostic failures in one day, all the same shape:** a check that
reported 26 mm of "PhysX mismatch" that was really finger travel; a capture command that
silently discarded every line the script printed; and a visual gate that had been the pending
next action for three sessions without ever having executed. Each cost more than the bug it
was meant to find. The pattern to watch: the instrument was trusted without being tested.

**NEXT:** re-run step 3 (no `tee`), let it run a full minute, then read
`tools/demo_run_report.txt` — it now logs progress at every stage and the geometry summary at
the top. Then re-run step 2 for a clean section-3 "OK" from the corrected geometry check.

## 2026-07-30 (Day 21, cont.) — Demo RUNS. Marker clutter fixed; first actual image of the gripper.

The `_marker_cfg` fix worked — the demo reached the viewport for the first time since it was
written. Screenshot shows the arm in its ready pose over the table, the black gripper plate
mounted at the flange, and the cube on the table.

**Problem in the image: the RGB axis marker was enormous**, dwarfing the whole robot. Cause
confirmed against `IsaacLab/source/isaaclab/markers/config/__init__.py`: `FRAME_MARKER_CFG`'s
default frame scale is **(0.5, 0.5, 0.5)** — half-metre axes — and `run_demo()` built its live
marker from a bare `FRAME_MARKER_CFG.copy()`, ignoring the 0.12 scale that was carefully set
for the `ee_frame` marker three lines away. Half-metre arrows on a 0.10 m gripper.

There were also **two** frame markers plus a beam, not one. `FrameTransformer`'s `debug_vis`
draws a marker at the SOURCE frame (the arm's `base_link`) as well as at every target, joined
by a `connecting_line` marker — a 1 m cylinder of radius 0.002 in yellow, which is the beam
crossing the screenshot. Three separate visual artefacts, none of them the grasp point.

**Fixed:**
- one marker cfg for the whole script, scale from a new `--marker_scale` flag, default **0.05
  m** — deliberately shorter than the gripper's own 0.10 m reach, so it reads as a frame ON
  the gripper instead of scenery;
- `run_demo()`'s live `tcp_marker` now uses that cfg instead of the 0.5 default;
- `ee_frame.debug_vis = False`, removing the source-frame marker and the yellow line, so the
  live TCP marker is the ONLY frame drawn;
- `connecting_line` radius thinned anyway, so turning `debug_vis` back on later is not a trap.

**Unresolved, deliberately left for the next image rather than guessed at:** in the screenshot
the large marker and the small one appear at DIFFERENT positions, when both should sit at the
TCP. Candidate explanations exist (the large one being the live marker at the TCP and the
small one the FrameTransformer target, or vice versa with one of them at `base_link`) but a
single screenshot cannot separate them, and this is the third instrument-not-tested trap
today. With exactly one frame now drawn, the next image answers it with no inference required:
if a stray triad still appears away from the gripper, that is a real finding worth chasing.

**NEXT:** re-run step 3 and look at where the single remaining marker sits relative to the
finger tips. That is the original Day-21 question — "is the grasp point between the tips" —
finally in a form that can actually be answered by looking.

## 2026-07-30 (Day 21, close) — CONFIRMED BY EYE: gripper orientation and TCP are correct

Touhid re-ran the demo with the single 0.05 m marker and confirmed visually: **the gripper is
aligned with the wrist and the TCP sits between the finger tips.** That closes the Day-21
question and, with it, the visual gate that had been the pending next action since Day 20.

Final state of the gripper geometry, all of it derived in `robots/gripper_geometry.py` from
one measured input:
- `TOOL_AXIS = (0, 0, 1)` — MEASURED (`tools/check_wrist_frame.py`), not inherited. Two
  independent methods agreeing. `MOUNT_QUAT` is identity as a result.
- plate 0.000–0.030 m from the flange (flush, no floating gap); fingers 0.030–0.100 m;
  **TCP 0.075 m = TIP_Z − GRASP_INSET(0.025)**, between the tips.
- The finger forward reach lives in the fixed mount plus a child-geometry offset inside each
  finger body, never in a prismatic joint's off-axis anchor — the round-2 PhysX trap stays
  avoided by construction.

**Decision (Touhid, Day 21 close): the 2f-85 comes back as a PARALLEL, OPTIONAL workstream.**
The SimpleGripper remains the Layer-1 deliverable and the benchmark launches on
`-SimpleGripper-v0` without waiting for the 2f-85. Rationale: the 2f-85 has already failed
twice (nested closed-loop articulation → degenerate body positions; finger pads with no
`UsdPhysics.CollisionAPI`), the 15-run matrix is still unlaunched, and writing is due Aug 11.
Putting the must-pass deliverable behind a twice-failed asset is not a trade worth making. A
separate chat picks up the 2f-85 with the Day-21 method (measure the mount, derive the TCP
from tip geometry, one geometry module) — handoff prompt written to
`Comparison test/docs/HANDOFF_robotiq_2f85.md`.

**NEXT on the main line (unchanged, now unblocked):** re-run the builder once for a clean
section-3 "OK" from the corrected geometry check, then `simple_gripper_grasp_test.py`, then a
~50-iter smoke train, then re-freeze/re-tag the Layer-1 env, repoint the matrix at
`-SimpleGripper-v0`, then PPO ×3 / cPPO ×3.

## 2026-07-30 (Day 22) — 2f-85 reopened: one of the two condemning reasons was RETRACTED before it was made

Parallel/optional 2f-85 workstream picked up from `docs/HANDOFF_robotiq_2f85.md`. Read the
Day 18/20/21 record before touching anything, per the handoff. **Three things in the record
do not hold up, and one of them shrinks this task substantially.** No code has been run —
no GPU in the sandbox, as always.

**1. Reason #2 for abandoning the 2f-85 ("the finger pads have no collider") IS FALSE, and
the retraction predates the accusation.** `run_log.md`, Day 18, lines 186–188:

> CLEARED — fingers DO have enabled convexHull colliders (10, incl. both inner_finger pads);
> checked with `tools/check_gripper_colliders.py` (needs `TraverseInstanceProxies` — Isaac
> assets are instanceable). "No collider" was a false alarm from the first, buggy traversal.

The Day-20 abandonment entry (line 497) reinstates the false alarm as settled fact; Day 21's
close, `logbook/09`, and the 2f-85 handoff all inherit it from there. The script on disk is
already the FIXED version — it uses `Usd.TraverseInstanceProxies()` — so the retraction is
what the current code produces. So "the 2f-85 failed twice, for two independent and
separately confirmed reasons" is, on this project's own record, **one reason plus a bug that
had already been found and corrected.**

This is the fourth instrument failure of the shape Day 21 named ("the instrument was trusted
without being tested"), and the only one of the four that propagated into a scoping decision.
Not re-verified from here: `check_gripper_colliders.py` only `print()`s and never writes a
file, so its output cannot be read from this sandbox at all. That gap is why the collider
audit is folded into the new script below rather than re-run separately.

**2. The surviving reason contradicts itself and was never diagnosed.** Day 18 found all nine
gripper bodies reporting *exactly* `[0,0,0]` in `wrist_3_link`'s frame — while the same
session measured an 84.4 mm pad-to-pad gap between two of those same bodies. Both cannot be
true of one array. Day 18 called them "unreliable, not statically collapsed" and moved on,
which was right at the time: nothing frozen reads bodies 7–15 (`MONITORED_BODIES` = 3/4/6,
`EE_BODY` = 6, Jacobian = arm joints, weld → synthetic `ee_frame`). But Day-21 ideas 3 and 4
(derive the TCP from tip geometry; make the builder measure itself after spawn) **both** need
trustworthy pad positions. So the single surviving objection sits exactly on this task's
critical path, unexplained rather than diagnosed.

**3. Half the success criterion is plausibly already met, and the other half is a number
nobody has measured.** The tool axis is +Z (measured, Day 21). The frozen weld env already
mounts the stock 2f-85 variant along +Z with no rotation, via the variant's own
`robot_gripper_joint` — there is no mount joint to author, and `MOUNT_QUAT` would come out
identity exactly as it did for the simple gripper. Day-18's GUI check confirmed the gripper
renders at the end of the wrist. So "aligned with the wrist" may need no work.
The open half is the TCP. Day 18 defended `OffsetCfg(pos=[0,0,0.16])` as "d6 (0.0996) +
2F-85 body (~0.13)" — that arithmetic gives **0.23, not 0.16**, and 0.16 only just enters
`check_gripper_mount.py`'s own 0.15–0.30 plausibility window. Measure it; don't defend it.

**Consequence: the real job is much smaller than the handoff assumes.** No rebuild, no
collider authoring, no mount joint. One measurement — where are the pads, in `wrist_3_link`'s
frame — plus a small geometry module that consumes it.

**Built (diagnostic only — deliberately no geometry module yet):**
- `tools/check_robotiq_pads.py` (new). Mirrors `check_wrist_frame.py`'s discipline: two
  independent methods, cross-checked, **refuses to write a result if the measurement is not
  conclusive.** Writes a FLUSHED report (`tools/check_robotiq_pads_report.txt`) plus
  `assets/robotiq_pads.json` only on success.
  - **Method A — pure USD, no PhysX.** Traverses the built USD *with* instance proxies,
    computes each pad prim's local-to-world off the stage and expresses it in `wrist_3_link`'s
    frame. Nothing is simulated, so the articulation surgery cannot affect it. This is the
    ground truth, not the tie-breaker.
  - **Method B — PhysX `body_pos_w` after spawn.** The array Day 18 called degenerate.
    Gravity off, all joints parked, 60 settle steps (not 5 — 5 is what read the simple
    gripper's fingers mid-stroke and produced the false 26.43 mm alarm).
  - Adds an **exact degeneracy test** (max separation between any two of the nine gripper
    bodies) rather than a tolerance judgement, and a second read at `finger_joint = 0.8` to
    cross-check Day-18's own 84.4 mm figure against the same array it was attributed to.
  - Folds the collider audit in, so the retracted claim is settled in a file that can be read.

**Stop rule, fixed BEFORE the run and written into the script's docstring:**
| Outcome | Action |
|---|---|
| A and B agree, midpoint in 0.15–0.30 m | Day-18's `[0,0,0]` was itself an artefact; last objection falls. Proceed — small job. |
| A sane, B degenerate | Geometry from A; post-spawn self-check becomes USD-based. ~1 extra day, contained. |
| A also degenerate | Assembly really is broken. **STOP**, drop permanently, write the negative result. |

A fourth state (they disagree and B is not degenerate) is explicitly *not* covered by the
rule; the script says so and refuses to pick a winner, because picking one from a single
ambiguous report is the exact move that cost Day 21 three sessions.

**Verified from here (the ceiling without a GPU):** `py_compile` passes. Every non-obvious API
checked against this repo's actual `IsaacLab/source` — `quat_apply_inverse` signature,
`SimulationCfg.gravity`, and in particular the Gf matrix composition order for "prim expressed
in root's frame", which is confirmed against
`isaaclab_tasks/.../dexsuite/mdp/utils.py:137` (`M_prim * M_root.GetInverse()`, applied as
`pts_h @ mat_t` — row-vector, same order used here). Noted in the script: line 64 of that same
file uses the opposite order under an identical comment, but it only feeds a hash, so it is
not a counter-example. `Usd.TraverseInstanceProxies()` is already proven in this repo by
`check_gripper_colliders.py`.

**Not done / flagged, not silently fixed:**
- `check_gripper_colliders.py` and `check_gripper_mount.py` both only `print()`. Per the Day-21
  rule an Isaac script's stdout can die in `simulation_app.close()`, and neither is readable
  from the sandbox regardless. Left untouched (the new script subsumes what was needed);
  flagged rather than fixed, per Touhid's "diagnostic only" scope call.
- `assets/ur5e_robotiq_2f85.usd` here is a Jul-13 copy and `make_usd_report.txt` still shows
  main-folder paths, so this folder has no local build record for the asset. Step 0 below
  fixes that. The USD itself is a thin variant wrapper and is path-independent, so this is
  provenance hygiene, not a correctness issue.
- No `robots/robotiq_geometry.py` written. Deliberate: writing geometry against a measurement
  that might say "stop" is how a one-run question becomes a three-session one.

**Scope call (Touhid, this session):** SimpleGripper first — it is the deliverable and the
matrix gate — then the 2f-85 measurement in the same sitting. The 2f-85 never blocks the matrix.

**NEXT (lab PC, in this order):**
1. **Main line first.** `../IsaacLab/isaaclab.sh -p ur5_grasp/tools/make_ur5e_simple_gripper_usd.py --headless`
   → section 3 should now read "OK", error under 2 mm (the report on disk is the pre-fix run
   showing the 26.43 mm false alarm). Then `simple_gripper_grasp_test.py`, then the ~50-iter
   smoke train, then re-freeze/re-tag and launch PPO ×3 / cPPO ×3.
2. `../IsaacLab/isaaclab.sh -p ur5_grasp/tools/make_ur5e_robotiq_usd.py --headless`
   → rebuilds the 2f-85 USD inside this folder, for local provenance.
3. `../IsaacLab/isaaclab.sh -p ur5_grasp/tools/check_robotiq_pads.py --headless`
   → **no `tee`.** `tools/check_robotiq_pads_report.txt` gets read from here.

## 2026-07-30 (Day 22, cont.) — Reports read. SimpleGripper gate CLEARED. 2f-85 CLOSED — and my own diagnostic was the fifth instrument failure.

All three commands run on the lab PC. Both reports read directly from the folder.

### Result 1 — SimpleGripper: CLEAN. The matrix gate is open.
`tools/make_simple_gripper_report.txt`, section 3:
```
left_finger_joint at read time : +0.00000 m (parked target 0.0; open would be +0.035)
expected : [0.015, 0.0, 0.015]
measured : [0.015, -0.0, 0.015]
error    : 0.00 mm
-> OK. The mount transform PhysX resolved matches what was authored.
```
The Day-21 fix to the check works: the joint is parked at exactly 0.0 (the false 26.43 mm alarm
was the drives hauling the fingers open mid-read), and the mount resolves exactly as authored.
Combined with the Day-21 close (mount + TCP confirmed by eye in the GUI), **the SimpleGripper
is done and the run matrix is unblocked.**

### Result 2 — 2f-85: reason #2 is definitively dead, on a fresh run.
10 finger/knuckle prims with `UsdPhysics.CollisionAPI`, `enabled=True`, `approx=convexHull`,
including both `inner_finger` pads. The handoff's "the pads have no collider" is FALSE, exactly
as Day 18 said before Day 20 reinstated it. Record corrected in `logbook/09`.

### Result 3 — my script printed a STOP verdict it was not entitled to.
It concluded "the USD's authored geometry is wrong." **It cannot support that.** Read line 64
of its own report:
```
[read 2] finger_joint commanded 0.8, actual +0.8000
pad-to-pad gap at open : 84.9 mm   (Day 18 measured 84.4 mm; spec stroke is 85 mm)
```
**The linkage works.** At `finger_joint = 0.8` PhysX resolved two distinct pad positions 84.9 mm
apart against an 85 mm spec — in the *same run* whose read 1, sixty steps earlier, was called
"degenerate". "PhysX is not resolving distinct transforms" is false as a blanket claim.

Three flaws, all mine, all the project's signature shape — trusting an instrument without
testing it — and all written into a file whose docstring warns about exactly that:

1. **Read 2 prints the pad GAP but not the pad POSITIONS.** So it cannot distinguish "pads
   correctly placed ~0.2 m out from the wrist" from "pads correctly separated but the whole
   assembly collapsed onto the wrist origin." It measured the one number that cannot separate
   the two cases it exists to separate.
2. **The read-1 table lists only the nine GRIPPER bodies.** If the ARM bodies also read
   `[0,0,0]` relative to `wrist_3_link` at read 1, then the articulation simply had not resolved
   at that read and read 1 is a bad read — not a gripper defect at all. Never printed, so
   unknowable from this report.
3. **Method A read the wrong prims.** The collider audit shows where the geometry actually
   lives: `/Robot/Gripper/Robotiq_2F_85/left_inner_finger/visuals/Defeatured_..._finger4step_01/...`.
   The LINK prims are almost certainly identity xforms — normal for a PhysX-authored robot,
   where kinematics live in the joints' `localPos0/localPos1` and geometry lives in child mesh
   prims. Method A computed the local-to-world of the body prim, got identity, and reported
   "the asset is wrong."

**Honest state of the 2f-85, recorded as an OPEN HYPOTHESIS and not a verdict:** there is a
strong, simple explanation in which **nothing is wrong with the 2f-85 at all** — both zeros are
two ordinary instrument bugs, and Day 18's original `[0,0,0]` was the same class of bug a fourth
time. The 84.9 mm pad gap and the 10 enabled convexHull colliders both point that way. This is
NOT established; it is the most likely reading of the evidence available and it was not tested.

### Decision (Touhid, Day 22): the 2f-85 is CLOSED. Permanently.
Not because the asset is broken — that was never shown, and the evidence now leans the other
way. Because:
- it has consumed Day 18, Day 20 and Day 22, each ending at "one more measurement would settle it";
- reaching a *validated* TCP needs two more rounds minimum (fix both instruments, re-run, GUI gate);
- the SimpleGripper cleared its check this session at 0.00 mm, so the deliverable is unblocked NOW;
- the 15-run matrix is still unlaunched, TD3 hard-cuts Aug 6, writing is due Aug 11;
- Layer-3 hardware is a ROBOTIS RH-P12-RN, so 2f-85 fidelity buys no sim-to-real value.

The handoff's own bar was "if the collider or articulation problems resist, say so early and
recommend stopping rather than grinding." They resisted — just not the way it predicted.

### What this is worth for the thesis
The negative result gets STRONGER, not weaker. "We abandoned it because the asset was broken" is
weak and, as it turns out, unsupported. The defensible version is: *the 2f-85 was abandoned on
two stated grounds; one was a retracted false alarm that had been reinstated as fact three
sessions later, the other was never diagnosed; and the workstream was finally closed not because
the asset failed but because the deliverable had already succeeded without it.* That is a real
methods paragraph on diagnostic discipline, which is the actual through-line of Days 18–22.

**Running count of instrument failures in this project — all the same shape:**
1. Day 18 — collider traversal omitting `TraverseInstanceProxies` on an instanceable asset.
2. Day 21 — geometry check reporting 26.43 mm of "PhysX mismatch" that was entirely drive travel.
3. Day 21 — `| tee` block-buffering every line the script printed into oblivion.
4. Day 21 — a "visual gate" pending for three sessions that had never once executed.
5. Day 22 — this script: a confident STOP verdict from three unvalidated premises.
Failure 1 is the expensive one: it propagated into the Day-20 scoping decision and was still
being cited as fact in the Day-22 handoff, two days after being retracted.

**Files:** `tools/check_robotiq_pads.py` + `tools/check_robotiq_pads_report.txt` are KEPT, not
deleted — the collider audit in them is the evidence that settles reason #2, and the flawed
verdict is itself the material for the methods paragraph. Flaws documented at the top of the
script so nobody re-runs it believing the verdict line. No `robots/robotiq_geometry.py` was ever
written; nothing to unwind.

### NEXT — main line only, nothing else is open
From inside `Comparison test/`:
1. `../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/simple_gripper_grasp_test.py --task Isaac-Lift-Cube-UR5e-SimpleGripper-Play-v0 --num_envs 1`
2. ~50-iter smoke train on `-SimpleGripper-v0`.
3. Re-freeze + re-tag the Layer-1 env; repoint the matrix at `-SimpleGripper-v0`.
4. Launch PPO ×3 then cPPO ×3.

## 2026-07-30 (Day 22, cont.) — Grasp test produced no readable result: it writes no file. Instrument fixed BEFORE the run this time.

Touhid ran `simple_gripper_grasp_test.py`. **Nothing to read.** Not a failed run — the script
had 17 `print()` calls and wrote no file at all, so its result could not reach disk under any
circumstance. Checked the whole folder: no file modified since 01:07 (the two Day-22 tool runs)
except this session's own edits.

This is the Day-21 trap for the **fourth** time in this project, and the first time it was
called in advance: it was flagged one message before the run, and the fix was interrupted
mid-edit. The failure mode is nastier than it looks — piping to capture output is what CAUSES
the block-buffering that `simulation_app.close()` then discards, so both "run it plain" and
"run it through tee" lose the output, and from outside the result is indistinguishable from
the run having crashed.

**Fixed — `scripts/simple_gripper_grasp_test.py` now follows the same pattern as every tool in
`tools/`:**
- writes a FLUSHED report to `tools/simple_gripper_grasp_report.txt` (`log()` = print + write
  + flush); all 17 `print()` calls converted, none left outside the helper;
- logs the resolved geometry summary at the top, so every run records which numbers it used;
- **PROGRESS lines at every stage** — cfg parsed, `gym.make` (scene construction), `env.reset`,
  scene up, body/joint names — so a run that dies says WHERE. This is the exact instrumentation
  that finally caught the live demo's `_marker_cfg` bug after three sessions of it looking like
  "ran fine and got closed early";
- `main()` wrapped in try/except that logs the traceback INTO the report file rather than
  relying on which stream the reader happened to capture.

`py_compile` passes. Nothing else in the script was touched — the test logic, the pin/release
methodology and the Day-21 `ee_frame` TCP change are all unchanged.

**Standing rule, now demonstrated four times: a script in this project that does not write a
flushed report file cannot be run for a result.** Check for `_FH`/`log()` before running
anything, not after. Remaining scripts that still only `print()`: `check_gripper_colliders.py`,
`check_gripper_mount.py` (both 2f-85-only, now closed, so left alone deliberately).

**NEXT:** re-run, no `tee`, then `tools/simple_gripper_grasp_report.txt` gets read from here.
```
cd ~/Abdur_Rabbi_THESIS/"Comparison test"
../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/simple_gripper_grasp_test.py \
    --task Isaac-Lift-Cube-UR5e-SimpleGripper-Play-v0 --num_envs 1
```
Pass bar (Day 20): finger joints stall ~0.030 m short of their 0 m closed target — genuinely
obstructed, not passing through — then the cube's z holds steady after the pin releases.

## 2026-07-30 (Day 22, cont.) — Grasp test PASSED (result found unread on disk). Matrix repointed to the WELD env `-v0`.

Dual-tracked: full entry in `Comparison test/run_log_new.md`. Summary:

- **`simple_gripper_grasp_report.txt` (01:19) was written and never read.** It **PASSES**:
  fingers stalled at a **62.8 mm pad gap** against a 30 mm closed target — obstructed by the
  cube, not passing through — and the cube held at z = +0.268 for 140 steps after the pin
  released. Every authored segment resolved to its designed value to 4 dp. The SimpleGripper
  is a working contact grasp. (Cube is ~63 mm across; the 2f-85's 85 mm stroke would clear it.)
- **Decision (Touhid): the 15-run matrix runs on `Isaac-Lift-Cube-UR5e-v0`**, the frozen weld
  env — reversing the Day-20/21 repoint to `-SimpleGripper-v0`. `-v0` is frozen, tagged and
  already produced the Day-10 headline; the 2f-85 is present and driven in it, with only the
  *grasp* abstracted as a weld. Decided on schedule: `03c` had these six runs finishing today,
  and the count is zero of fifteen. SimpleGripper drops to a ~50-iter smoke train and stands as
  a separately demonstrated real-contact result.
- **Correction:** `logbook/09` claimed `Comparison test/` is not git-tracked. False — checked
  with `git ls-files`; it is tracked, with five modified files. Fixed in `09`.
- **Fragility found:** `tasks/lift/__init__.py` imports `gripper_geometry.py` at package-import
  time, which raises `FileNotFoundError` if `assets/wrist_frame.json` is missing — and that file
  is untracked. So the frozen weld env's importability depends on an uncommitted JSON. Fix by
  committing it during the freeze.
- **Instruments:** `run_ppo_cppo_seeds.sh` rewritten (no longer aborts the batch on one failed
  run; per-run exit codes, wall-clock, checkpoint verification, flushed `logs/batch_report.txt`)
  and `ur5_grasp/tools/summarize_runs.py` added (TB event files → flushed report + CSVs,
  replacing the manual export `make_layer1_figs.py` expects from a dead sandbox path). Both
  verified against stubs; neither has met real Isaac/TensorBoard yet — see `run_log_new.md` for
  exactly what was and was not verified.

**NEXT:** commit + re-tag → three 50-iter smoke trains (`-v0` PPO, `-v0` cPPO,
`-SimpleGripper-v0`) → `./run_ppo_cppo_seeds.sh` → `summarize_runs.py`.

## 2026-07-30 (Day 22, close) — All three smoke trains PASS. Layer-1 mechanism visible at 50 iters.

Dual-tracked; full entry in `Comparison_test/run_log_new.md`. Also: folder renamed
`Comparison test` → `Comparison_test` (space removed); freeze commit `2b19e90`, tag
`comparison-matrix-v0`.

All three gates pass. `-v0` PPO and cPPO both train on `ur5e_robotiq_2f85.usd`;
`-SimpleGripper-v0` trains on `ur5e_simple_gripper.usd` (each confirmed by grepping the run's
own `params/env.yaml`, not assumed). cPPO wiring is live — `Loss/cost_lambda` 19.40 plus a cost
critic and episode-cost channel.

**The headline separation is already there at 50 iters:** cPPO holds `manipulability_mean`
0.0972 vs PPO's 0.0330, `manipulability_min` 0.0472 (above the 0.045 floor) vs 5.7e-06, and
`viol_singularity` 0.35% vs 71.9%. Collision and joint-limit costs ~0 in both — singularity is
confirmed as the single binding constraint.

Three predictions recorded for the 1500-iter runs: (1) the separation is far wider than Day 10's
6.65% vs 16.86%, expected because lambda=19.4 is still climbing and cPPO is over-constraining —
viol should rise toward ~6-7%; (2) cPPO's reward currently *exceeds* PPO's (73.61 vs 65.47),
which should not persist — if it does across 3 seeds, suspect cost leaking into reward;
(3) PPO's manipulability_min of 5.7e-06 is a true rank-deficient Jacobian — if it persists,
report the mean rather than the min.

**Bug found:** `experiment_name` comes from the agent cfg, not the task, so the SimpleGripper
run landed in the same log directory as the weld-env PPO runs and any glob would have averaged
two different robots. Mitigated by moving the SimpleGripper runs to `ur5e_lift_simplegripper/`.

**NEXT:** `./run_ppo_cppo_seeds.sh` → `summarize_runs.py`.


---

## Day 22 (2026-07-30), evening — skrl bridge wired (code only, no runs)

Handoff steps 1-2 of the 4-algorithm comparison. Two blockers caught before any GPU time:
(1) IsaacLab's stock skrl `train.py` never imports `ur5_grasp.tasks`, so our task is not
registered — added `Comparison_test/ur5_grasp/scripts/train_skrl.py`, the stock file plus four
marked edits, diff-verified. (2) skrl yaml entry points resolve package-relative
(`"<module>:<file>.yaml"`), so the config lives in `tasks/lift/agents/`, not in `configs/` as
the handoff assumed. Bridge config hyperparameters are matched to `UR5eLiftPPORunnerCfg`, not to
the franka template — nine deliberate divergences, listed in the config header, so the run
actually tests framework equivalence. skrl install still UNVERIFIED (no Isaac env in sandbox).

Detail: `Comparison_test/run_log_new.md`, same date.

## Day 22 (2026-07-30), late — skrl bridge smoke PASSED; eval_success blocker found

50-iter smoke ran (128 envs, seed 1), checkpoint on disk, 32 TB tags. Env diff-verified
identical to the Layer-1 rsl_rl PPO runs (only difference is env.yaml dump timing relative to
`gym.make`). Value-loss and adaptive-LR trajectories track rsl_rl closely, so the null-
preprocessor / unscaled-reward choice is largely vindicated. Return gap (4.48 vs rsl_rl's
64.85) is confounded by 128 vs 4096 envs — re-smoke at 4096 before drawing any conclusion.

**New blocker:** `eval_success.py` is hard-wired to rsl_rl runners and cannot load a skrl
checkpoint, so goal-reach success is uncomputable for skrl-PPO, SAC and TD3 alike. Needs a
skrl loader path before any skrl run can enter the results table.

Detail: `Comparison_test/run_log_new.md`, same date.

## Day 23 (2026-07-31) — bridge smoke at 4096 envs misses criterion; proceeding to the full x3

skrl-PPO reached 33.82 mean return at 50 iters vs rsl_rl's 64.85 — outside the +-30% band I set
in advance, recorded as a fail. But the criterion tested a 1500-iter question with a 50-iter
proxy. No sign of breakage: identical env, stable entropy and std, returns and episode length
both climbing, value loss the same shape. skrl-PPO looks like a slower, gentler PPO (drives into
singularity 65x less at this point). Decision: stop smoking, run the bridge x3 at 1500 iters,
which costs ~30 min and produces the number that actually goes in the thesis.

Added `Comparison_test/run_skrl_seeds.sh`, the skrl analogue of run_ppo_cppo_seeds.sh; it also
serves SAC and TD3. Duplicate-run trap found: the same smoke was launched twice and produced two
bit-identical run dirs that a later glob would average as independent seeds.

Detail: `Comparison_test/run_log_new.md`, same date.

## Day 23 (2026-07-31, later) — TD3 CUT. Evaluation rebuilt: safety now measured on the frozen policy.

**TD3 dropped**, Touhid's call, six days ahead of the agreed Aug 6 hard-cut date. The benchmark
is now three algorithms: PPO / cPPO / SAC. Entry point and `--algorithm` choice removed so an
accidental `--algorithm TD3` fails at argparse rather than 40 s later inside Isaac.

**Diagnosed "how can PPO score 0 and cPPO 100 on the same seed".** Answer: the training failure
is REAL, the eval merely rendered it as a step function. PPO seed 2 finished at reward 90.7 vs
cPPO's 166.4, `object_goal_tracking` 4.42 vs 14.78, and wrist-to-goal error 0.566 m vs 0.161 m.
The checkpoint paths in the CSV are correct, so this is not the log-dir trap. What the eval got
wrong is that a single hard 5 cm threshold on a quantity with near-zero within-policy spread
saturates at exactly 0 or exactly 100 — ppo_s1's 58.59% is the one policy sitting on the knife
edge. Also found: `Metrics/object_pose/position_error` in TensorBoard tracks **wrist_3_link**,
not the cube (`body_name = "wrist_3_link"`), so it reads ~0.16 m for a policy whose cube is
exactly on target — that 0.16 is the wrist-to-TCP offset, not error. Do not quote it as task error.

**The bigger flaw, and the reason the evaluation had to be rebuilt:** the singularity and
joint-limit violation percentages in `LAYER1_RESULTS_3seed.md` came from TRAINING TensorBoard
scalars, tail-averaged over the last 10% of iterations — a still-learning policy with exploration
noise on. They cannot support a claim about the final policy. New `eval_policy.py` counts
violations during evaluation, per episode, on the deterministic frozen policy, using the same
`SafetyCostComputer` thresholds the training constrained.

**Retracted:** I first suspected the 0.04 m lift threshold was trivially satisfied because the
cube spawns at z = 0.055. It is not. `Episode_Reward/lifting_object` is 0.117 at iteration 0
(≈2 of 250 steps above the line — the cube settling after spawn) and 14.61 at iteration 1499
(≈243 of 250), so the resting height is below the threshold and the metric is real. Reward
function left untouched.

New: `ur5_grasp/scripts/eval_policy.py` + `run_eval_policy.sh` (4 eval seeds × 1000 episodes ×
6 checkpoints, rsl_rl and skrl loaders, per-episode CSV). Not yet run — needs the lab PC.

Detail: `Comparison_test/run_log_new.md`, same date.

## Day 23 (2026-07-31) — bridge x3 done, and it undercuts a Layer-1 claim

skrl-PPO x3 finished (10-11 min each, all OK). Training metrics: reward 158.04 +- 2.02,
viol_sing 34.52%, viol_jlim 0.00%. That is cPPO's profile (163.35 +- 3.71 / 44.30% / 0.61%),
not rsl_rl-PPO's (132.45 +- 37.25 / 81.85% / 35.50%). An UNCONSTRAINED PPO reproduced nearly
every property Layer 1 credits to the Lagrangian constraint, which threatens the "PPO is
inconsistent across seeds" finding — that may be an rsl_rl implementation property.

Not yet conclusive: these are training metrics, and Layer 1's own discriminating metric is
goal-reach success, still unmeasured for skrl. Built `eval_success_skrl.py` and
`run_eval_skrl.sh` to measure it (both unverified, never executed). That eval is now the top
priority, ahead of SAC. TD3 cut on schedule grounds.

Detail: `Comparison_test/run_log_new.md`, same date.

## Day 23 (2026-07-31, close) — evaluation sweep complete: 18 runs, 18 000 episodes, safety measured on the frozen policy

Frame sanity check passed (mean commanded goal height 0.3741 m vs the expected 0.375), so the new
50 %-of-goal-height lift rule is valid.

cPPO vs PPO, mean ± sd over three training seeds: goal-reach @1 cm **96.52 ± 3.45** vs
34.72 ± 56.54; episodic safety cost **17.75 ± 7.41** vs 261.31 ± 163.49 against a budget of 25;
joint-limit violations **0.00 %** vs 35.34 %. PPO per-seed goal-reach is 4.2 / 0.0 / 100.0 — three
qualitatively different policies, not one noisy one.

Four framing changes: (1) the episodic cost is the strongest number, being the exact quantity the
Lagrangian constrains; (2) report singularity CROSSINGS (w < 1e-4: PPO 7.9–100 % of episodes,
cPPO 0.0–0.1 %) rather than the step fraction, which is a binary test on a soft margin and
undersells the gap ~50×; (3) `ppo_s3` matches cPPO on task while being the least safe run in the
matrix — the claim is "the constraint buys reliability", not "PPO cannot do the task";
(4) `ppo_s2` lifts and then puts the cube back down (100 % lifted at some point, 9.8 % at the end).

Eval-seed spread is 1.05 points against 56.5 across training seeds, so the Day-22 worry that
"0.00 %" might have been a bad exam is settled — it was the policy.

New: `results/LAYER1_RESULTS_eval.md` (generated), `results/LAYER1_FINDINGS.md` (interpretation +
limitations), `results/scripts/summarize_eval.py`. Detail: `Comparison_test/run_log_new.md`.

## Day 23 (2026-07-31, late) — ALGORITHM AUDIT: the cPPO-vs-PPO result is confounded and is withdrawn

Touhid's challenge, verbatim in spirit: PPO used to beat cPPO, now it loses badly, and cPPO scores
100 % goal-reach every time — "something fishy in the algorithms code". He was right to push.

**The finding.** `Loss/cost_lambda` is 0.0 for essentially every iteration of all three cPPO runs
in the 2026-07-30 matrix. `cppo_s2` never leaves 0.0 at any iteration. At lambda = 0 the Lagrangian
surrogate `(A_r - lambda*A_c)/(1+lambda)` is algebraically `A_r`, i.e. the update **is stock PPO**.
So the constraint cannot be what separated the arms — yet cppo_s2 scored reward 166.4 against
ppo_s2's 90.8 from an identical seed, identical env cfg (verified by `diff` of the dumped
`params/env.yaml`) and an identical iteration-0 reward of 0.7152.

**The mechanism.** `ppo_lagrangian.py` inherited stock PPO's single
`clip_grad_norm_(self.policy.parameters(), max_grad_norm)`. In cPPO that parameter list also holds
the cost critic, and `clip_grad_norm_` rescales *every* gradient by one global factor — so the cost
critic's gradients were shrinking the actor's step on every update, including all the updates where
lambda was 0. cPPO was PPO with a smaller, cost-loss-dependent learning rate. A quieter optimiser
converging on 3/3 seeds while the baseline converges on 1/3 is exactly the pattern Day 22 read as
"the constraint buys reliability".

**Second finding.** `cost_limit = 25` was calibrated on Day 9 from a 50-iter probe against a natural
cost of ~70. Converged runs sit at 7–29, so the budget is slack and the dual update correctly holds
lambda at 0. A constraint that never binds measures nothing. The Day-9 calibration is not wrong — it
described a policy that had barely started learning.

**Also found, before it cost anything:** SAC would have been evaluated with uniform random actions.
skrl's off-policy `act()` returns `random_act` while `timestep < random_timesteps`, and
`eval_policy.py` calls it with `timestep=0`. It would have looked like SAC failing the task, not like
a bug. Guarded in `eval_policy.py`.

**The 100 % goal-reach is a metric ceiling, not a cheat.** `_apply_weld` writes the cube's position
to the reach frame every step, so "cube within 1 cm of goal" reduces to "TCP within 1 cm of goal" —
a reaching problem a converged policy solves every episode and an unconverged one fails every
episode. Report the distance distribution, never a single threshold as the headline.

**Withdrawn:** `results/LAYER1_RESULTS_3seed.md` and `results/LAYER1_FINDINGS.md`. Not deleted — that
a large apparent effect turned out to be an artifact belongs in the Methods narrative on diagnostic
discipline, alongside the 2f-85 close and the five instrument failures.

**Fixed / added** (Comparison_test/, ported to the main `ur5_grasp/` for `safe_rl/` and the agent cfg):
`ppo_lagrangian.py` two-group gradient clip + Jc buffer sized to a full 4096-env wave + two new
diagnostics (`cost_episodes_in_estimate`, `cost_budget_used`); `UR5eLiftCtrlRunnerCfg`
(lambda_max = 0 — the missing CONTROL); `UR5eLiftCPPO10RunnerCfg` (cost_limit = 10, a budget that
binds); `skrl_sac_cfg.yaml` authored from skrl 1.4.3 source; `run_matrix_v2.sh` (5 arms x 5 seeds);
`run_eval_policy_v2.sh` (75 launches); `ur5_grasp/tools/test_grad_clip_fix.py` (2-second regression
test, no Isaac); `results/ALGORITHM_AUDIT.md`; `RUN_CHECKLIST_v2.md`.

**What the new matrix licenses.** ctrl vs ppo = the implementation artifact (must be null, else the
audit is incomplete and nothing may be reported). cppo10 vs ctrl = the constraint alone, and that
difference is the only safe-RL claim. Decomposition: (cppo - ppo) = (ctrl - ppo) + (cppo - ctrl).

Detail: `Comparison_test/results/ALGORITHM_AUDIT.md`, `Comparison_test/RUN_CHECKLIST_v2.md`.

## Day 23 (2026-07-31, cont.) — Goal-pose box widened; MANIP_FLOOR/cost_limit marked stale

Touhid's call: the goal-pose sampling box felt too narrow. It was never actually set in this
project's own files — `ur5e_lift_env_cfg.py` inherits `self.commands.object_pose.ranges`
unchanged from Isaac Lab's Franka lift defaults (`pos_x=(0.4,0.6), pos_y=(-0.25,0.25),
pos_z=(0.25,0.5)`) and had never overridden it.

**Reach check before widening.** UR5e base sits at the env origin; rated reach ~0.85 m. The old
box's far corner (0.6, 0.25, 0.5) is already 0.82 m out — near full extension, i.e. the current
task already occasionally asks for a near-singular reach. A first wider draft
(pos_x=(0.3,0.7), pos_y=(-0.4,0.4), pos_z=(0.13,0.62)) put the far corner at 1.02 m —
unreachable, would have injected goals the arm physically cannot reach into the training
distribution. Scaled back to keep the far corner at 0.83 m (same margin as today), widening
mostly toward the base and downward instead: `pos_x=(0.30,0.60), pos_y=(-0.28,0.28),
pos_z=(0.15,0.50)`.

**Applied:** `Comparison_test/ur5_grasp/tasks/lift/ur5e_lift_env_cfg.py`,
`UR5eCubeLiftEnvCfg.__post_init__` — new `ranges=` override next to the existing `body_name`
override. Env-level, applies identically to all 5 arms; does not reopen the arm-isolation
question in `ALGORITHM_AUDIT.md` §4. `py_compile` clean.

**Consequence, flagged inline and in the tracking docs:** `MANIP_FLOOR` (`ur5e_lift_env.py`) and
`cost_limit` (`agents/rsl_rl_cppo_cfg.py`, both 25 and 10) were calibrated Day 9 against the OLD
box's task difficulty. A different goal region changes how often the arm nears joint limits or
low manipulability while reaching, so both are now provisional until re-evidenced. Marked STALE
inline in both files; new `RUN_CHECKLIST_v2.md` Step 4 (recalibration probe, ~15-20 min) added,
positioned before the freeze (Step 5) and the 5-hour matrix (Step 6) — see the reordering note
below; `ALGORITHM_AUDIT.md` §5 (addendum) records the before/after numbers and why.

**NEXT:** run Step 4 on the lab PC (`calibrate_manipulability.py` + a 50-iter cost probe against
the new box) before launching the v2 matrix. If either threshold has drifted off its Day-9
percentile/range, treat it as a normal one-line-diff calibration update, recorded the same way.

**Widened again, same session, still before any run.** Touhid asked for "a bit wider." Round 1
above (0.83 m far corner) had ~20 mm of margin left to the 0.85 m reach spec, so the second pass
took width mostly from the "free" direction — extending the MIN bounds toward the base, which
doesn't touch the far-corner distance at all — rather than pushing the MAX bounds further out.
`pos_x=(0.30,0.60)->(0.22,0.60)`, `pos_y=(-0.28,0.28)->(-0.30,0.30)`, `pos_z=(0.15,0.50)->(0.10,0.50)`.
New far corner 0.84 m (~13 mm margin). `py_compile` clean. `ur5e_lift_env_cfg.py`,
`RUN_CHECKLIST_v2.md`, `ALGORITHM_AUDIT.md` §5 all updated to the round-2 numbers in place
(round 1 never ran, so nothing is being retroactively rewritten). The recalibration probe (now
Step 4) still applies unchanged — it'll pick up round 2's numbers automatically since it reads
whatever the env is currently configured with.

## Day 23 (2026-07-31, cont.) — Reward terms re-weighted; "lifted" made goal-relative

Two edits to `self.rewards` in `ur5e_lift_env_cfg.py`, Touhid's call, both asked with clarifying
questions answered first (formula for "50% crossed", whether both tracking terms move, whether
the lift gate stays consistent across all three terms):

1. **`lifting_object` weight 15.0 -> 10.0.**
2. **"Lifted" redefined, all three terms together.** Was a fixed `object.z > 0.04 m` (Isaac Lab's
   Franka default, inherited unchanged, same number reused by `lifting_object`,
   `object_goal_tracking`, `object_goal_tracking_fine_grained`). Now: `object.z >` `spawn_height
   + 0.5*(goal_z - spawn_height)` — 50% of the vertical climb from the table (0.055 m, read from
   the cube's own `init_state` rather than duplicated) to THIS EPISODE's commanded goal height.
   Chosen over "50% of the goal's absolute height" because goal_z now spans 0.10-0.50 m (today's
   other change) and the absolute-height version would demand climbing to 0.25 m for the highest
   goals while barely requiring anything for the lowest — the relative version scales sensibly
   either way. New functions `object_lifted_toward_goal` / `object_goal_distance_relative_lift`
   in new `Comparison_test/ur5_grasp/tasks/lift/rewards.py` (Isaac Lab's stock
   `object_is_lifted`/`object_goal_distance` only take a fixed scalar height — no way to make
   them goal-relative without new code; vendored source untouched).
3. **`object_goal_tracking` weight 16.0 -> 15.0.** `object_goal_tracking_fine_grained` weight
   unchanged at 5.0 — only its lift gate changed, to stay consistent with the other two terms
   (explicitly scoped this way, not "both tracking terms to 15").

Env-level, applies to all 5 arms — doesn't reopen the arm-isolation question. Combined with the
same-day goal-pose widening, this is a second task-defining change before the matrix has run once;
`RUN_CHECKLIST_v2.md` Step 4 now covers recalibrating `MANIP_FLOOR`/`cost_limit` against both
changes together. `ALGORITHM_AUDIT.md` §6 has the before/after table. `py_compile` clean on both
new/edited files; no torch or isaaclab in this sandbox, so — same as every other change made from
here — the ceiling of verification is static (signatures cross-checked against the actual Isaac
Lab source, arithmetic hand-checked), not a real run. First real test happens on the lab PC.

**Checklist reordering, same session.** Freeze (was Step 0, first) moved to Step 5, after the
sanity checks and recalibration (Step 4). Caught while re-reading the checklist for this
response: recalibration can edit tracked files (`MANIP_FLOOR`, `cost_limit`), and the freeze's
whole purpose is to tag the exact commit run 1 trains against. Freezing before a step that might
still change tracked files would tag the wrong commit. Full renumber: 1 arms-resolve, 2 smoke
trains, 3 SAC smoke, 4 recalibrate (was 3.5), 5 freeze (was 0), 6 matrix (was 4), 7 decisive
check (was 5), 8 eval (was 6), 9 report (was 7). All cross-references in `ALGORITHM_AUDIT.md`
and `logbook/09_comparison_test.md` updated to match.

## Day 23 (2026-07-31, cont.) — Collision and joint-limit margins widened

Two more constants in `ur5e_lift_env.py` (`UR5eCubeLiftEnv`), Touhid's call, straightforward
field edits (no new functions, no arm-isolation questions — same env-level pattern as today's
other two changes):

1. **`COLLISION_Z_FLOOR` 0.0 -> 0.05 m.** Was the bare table-plane height — `costs.py`'s
   `penetration = clamp(z_floor - link_z, 0)` only went positive on literal table penetration.
   Now a 5 cm standoff above the table/floor counts.
2. **`JOINT_LIMIT_MARGIN` 0.10 -> 0.175 rad (~10.0°, was ~5.7°).** Wider buffer before a soft
   joint limit starts costing.

Both were "monitored but satisfied" at Day 9 (min link height 0.125 m, min joint clearance
1.39 rad — both comfortably outside even the new, wider margins) — so on their own these edits
might still land as inactive. But today's goal-pose widening (pos_z down to 0.10 m, near corner
0.24 m from the base) changes the arm's operating range in a direction that could make either
term active for the first time. Flagged, not assumed — `calibrate_manipulability.py` already
reports joint-limit-clearance and min-link-height distributions (built Day 9 for exactly this),
so `RUN_CHECKLIST_v2.md` Step 4 now explicitly checks both, not just `MANIP_FLOOR`.

**Also fixed while writing this up:** `ALGORITHM_AUDIT.md` had a structural bug from the earlier
two edits today — the second addendum (§6, reward re-weighting) got inserted in the middle of
the first (§5, goal-pose box), splitting §5's closing paragraph off after §6 instead of before
it. Content was all present, just misordered under the wrong headers. Reconstructed correctly:
§5 complete, §6 complete, new §7 (this change) appended after.

`py_compile` clean. Third task-defining/threshold change stacked before the matrix has run once
— `RUN_CHECKLIST_v2.md` Step 4, `ALGORITHM_AUDIT.md` §7, and the module logbook all updated.

## Day 23 (2026-07-31, cont.) — Step 1 blocked: stale IsaacLab editable install

First lab-PC run of the v2 checklist. Step 1 crashed: `import ur5_grasp.tasks` and the gym
entry-point printout worked, but `from ...rsl_rl_cppo_cfg import (...)` traced into
`/home/mte/Abdur_Rabbi_Thesis_updated/IsaacLab/source/...` (a second, abandoned IsaacLab
checkout — confirmed by Touhid, not used anymore) instead of `~/Abdur_Rabbi_THESIS/IsaacLab`,
and died on `ModuleNotFoundError: No module named 'omni.log'` inside `isaaclab.utils.math`.

Diagnosis: `import ur5_grasp.tasks` only registers gym entry-point strings (no real import), so
it doesn't touch the RL library; the direct `rsl_rl_cppo_cfg` import does, pulling in
`isaaclab_rl` -> `isaaclab.envs` -> ... Confirmed no `_isaac_sim` symlink in
`Abdur_Rabbi_THESIS/IsaacLab` (checked directly) and the earlier `[INFO] Using python from:
.../envs/isaaclab/bin/python` line, both consistent with Isaac Sim installed via pip packages
into the `isaaclab` conda env rather than a binary+symlink install — so `omni` itself isn't
missing, the stale `_updated` checkout's Isaac Lab version is just mismatched against whatever
Isaac Sim pip packages are currently installed. Root cause: `isaaclab`/`isaaclab_rl`/
`isaaclab_tasks` are still editable-installed (pip) against the abandoned `_updated` folder.

**Fix given, not yet confirmed:** `cd ~/Abdur_Rabbi_THESIS/IsaacLab && ./isaaclab.sh -i` — the
official Isaac Lab command (verified against the actual script, not memory) that editable-
installs every `source/*` extension plus `isaaclab_rl[all]`/`isaaclab_mimic[all]` from whichever
IsaacLab folder it's run in, superseding the stale pointer. Idempotent (skips cmake/torch if
already satisfied). Next: confirm via `pip show isaaclab isaaclab_rl isaaclab_tasks | grep
Location`, then rerun Step 1.

## Day 23 (2026-07-31, cont.) — `./isaaclab.sh -i` fixed the folder bug; second, separate bug found

Touhid confirmed `Abdur_Rabbi_Thesis_updated` was an abandoned second folder, not in use. Ran
`./isaaclab.sh -i`, reran Step 1 — traceback now traces entirely through
`/home/mte/Abdur_Rabbi_THESIS/IsaacLab/source/...` (folder bug fixed) but still dies on
`ModuleNotFoundError: No module named 'omni.log'`, same as before.

**Root cause #2, different from #1:** `omni.*` modules (Kit-provided, not a normal pip package)
are only importable AFTER Isaac Sim's Kit runtime has been launched via `AppLauncher`/
`SimulationApp` — they don't exist as static importable files regardless of which folder or
site-packages entry is used. Step 1's one-liner imported `rsl_rl_cppo_cfg` directly (which
cascades into `isaaclab.controllers.differential_ik` -> `import omni.log` at module level)
without ever launching Kit first. `import ur5_grasp.tasks` alone worked earlier because gym
registration is just strings — no real import of the deep chain happens there. `train.py`
avoids this because it calls `AppLauncher(args_cli)` and gets `simulation_app` BEFORE any of
the deeper imports (confirmed by reading `train.py` lines 24-118 directly).

**Fix:** added `from isaaclab.app import AppLauncher; simulation_app = AppLauncher(headless=True).app`
to the top of Step 1's snippet, `simulation_app.close()` at the end. Pattern lifted directly from
Isaac Lab's own test suite (`isaaclab/test/controllers/test_differential_ik.py` and ~9 others all
open with the identical one-liner), not guessed. `RUN_CHECKLIST_v2.md` Step 1 updated with the
corrected script + explanation; time estimate bumped (~3-5 min, Kit headless boot adds ~20-60 s).

**Confirmed on the lab PC:** Step 1 now prints exactly the expected output — all 5 entry points
resolve, and `cost_limit`/`lambda_max` match spec (`cppo` 25.0/100.0, `cppo10` 10.0/100.0, `ctrl`
25.0/0.0). Both the stale-editable-install bug and the missing-AppLauncher bug are closed.
**Step 1 done.** Next: Step 2 (smoke trains, 50 iters each).

## Day 23 (2026-07-31, cont.) — Step 2 done: all 4 smoke trains clean; two findings from summarize_runs.py

Read `ur5_grasp/tools/summarize_runs_report.txt` directly (shared filesystem with the lab PC —
this session's connected folder IS `~/Abdur_Rabbi_THESIS`) rather than waiting for pasted
terminal output. All four Step-2 smoke runs (`ur5e_lift`, `ur5e_lift_ctrl`, `ur5e_lift_cppo`,
`ur5e_lift_cppo10`, all `2026-07-31_20-2x`, seed 1, 512 envs, 49 iters logged, `model_49.pt`
present) finished with no traceback — the gradient-clip fix and the new `rewards.py` code both
hold under real execution.

**Finding 1 (expected, still worth flagging):** `Train/mean_reward` and every `safety/*` metric
are numerically IDENTICAL across all four arms at 50 iters (7.0269 tail / 8.3210 final, every
run). This is consistent with the audit's own math — `Loss/cost_lambda` is 0.0 for cppo/ctrl/
cppo10 this early, so the Lagrangian surrogate is algebraically `A_reward` for all three, same as
stock PPO. `ctrl` matching `ppo` exactly (not just closely) is a genuinely positive early signal
for the A1 gradient-clip fix, but it is NOT the decisive check — that's Step 7, on the full
1500-iter/5-seed data, where lambda will actually move for `cppo10` and the arms can diverge.

**Finding 2 (a real effect of today's changes, not a bug):** `safety/cost_collision` is nonzero
today (~1.99e-05 tail / ~3.1e-05 final, `viol_collision` ~0.14%-0.19%) across all four arms —
every single historical run before today (Day 9 through Day 22) shows exactly `0.0000` for this
term. This is the `COLLISION_Z_FLOOR: 0.0 -> 0.05` change (§7 addendum) doing exactly what was
flagged as the most likely of the four Day-23 threshold changes to actually move a number.
Still tiny at 50 iterations — Step 4 needs to characterize it properly, not this smoke test.
`safety/cost_joint_limit` stayed exactly `0.0` for all four — that constraint (margin 0.175 rad)
is still inactive, consistent with the Day-9 baseline's 1.39 rad clearance.

**Also worth noting for future comparisons:** today's smoke reward (~7-8 at 49 iters) is far
below the pre-Day-23 smoke baseline (`2026-07-30_01-49-46_smoke_ppo`: 65.47 at 49 iters, same
seed/envs). Expected — the widened goal box and the goal-relative lift gate both make early
reward harder to earn than the old fixed narrow-box/low-bar setup — but a real difference, not
noise, and worth remembering so nobody mistakes it for a regression later.

**Step 2 done, clean.** Next: Step 3 (SAC smoke).

## Day 23 (2026-07-31, cont.) — Step 3 done: SAC smoke passed after three real skrl-2.1.0 bugs, all fixed

`skrl_sac_cfg.yaml` had genuinely never been executed. It failed three times in a row on the lab
PC, each a different symptom, all traceable to the same root cause: the config was authored
against skrl 1.4.3's API and the installed lab-PC skrl is **2.1.0**. Confirmed the version
directly (`python -c "import skrl; print(skrl.__version__)"` -> `2.1.0`), not assumed.

**Bug 1 — wrong Hydra override path.** `RUN_CHECKLIST_v2.md`'s smoke command used
`trainer.timesteps=200`, which failed (`Key 'trainer' is not in struct`). Root cause, checked
against `isaaclab_tasks/utils/hydra.py::register_task_to_hydra`: the composed Hydra config is
`{"env": ..., "agent": ...}`, so everything inside the SAC yaml — including its own top-level
`trainer:` block — lives under `agent.` for override purposes. Fixed to
`agent.trainer.timesteps=200`. Also recorded: `--max_iterations` is not usable for SAC at all —
`train_skrl.py` computes `agent_cfg["agent"]["rollouts"]`, a PPO-only key SAC's yaml doesn't
define, so that flag would raise `KeyError('rollouts')` for this arm specifically.

**Bug 2 — `OBSERVATIONS_ACTIONS` token removed in skrl 2.x.** Next failure:
`NameError: name 'observations_taken_actions' is not defined` inside a dynamically-compiled
`compute()`. The 1.4.3 compound token `OBSERVATIONS_ACTIONS` (meant
`torch.cat([states, taken_actions], dim=1)`) doesn't exist in 2.1.0's model instantiator at all —
confirmed against `common.py` on GitHub tag `2.1.0`. `_parse_input` does two blind, unguarded
substring replaces (`OBSERVATIONS`->`observations`, then `ACTIONS`->`taken_actions`), so the old
token silently became the undefined name `observations_taken_actions` instead of failing at
parse time. Fixed all four critic/target blocks to skrl 2.x's documented replacement,
`concatenate([OBSERVATIONS, ACTIONS])`.

**Bug 3 — SAC config schema itself changed.** Third failure, past model instantiation into agent
construction: `TypeError: SAC_CFG.__init__() got an unexpected keyword argument
'actor_learning_rate'`. skrl 2.x replaced the old dict-based `SAC_DEFAULT_CONFIG` (any key
allowed) with a typed `@dataclass(kw_only=True) SAC_CFG` — unknown keys now raise `TypeError`
instead of being silently ignored. Confirmed field-by-field against
`skrl/agents/torch/sac/sac_cfg.py` on GitHub tag `2.1.0` and rewrote the `agent:` block:
`actor_learning_rate`/`critic_learning_rate`/`entropy_learning_rate` collapsed into one
`learning_rate: [policy, critic, entropy]` triple; `learning_rate_scheduler(_kwargs)` removed
(let the dataclass default apply rather than pass `null` against a typed field); `state_preprocessor
(_kwargs)` renamed to `observation_preprocessor(_kwargs)` (2.1.0 keeps `state_preprocessor` as a
separate, unrelated field for Isaac Lab's asymmetric-obs case — left unset, not applicable here).
Everything else (`rewards_shaper_scale`, `gradient_steps`, `batch_size`, `discount_factor`,
`polyak`, `random_timesteps`, `learning_starts`, `grad_norm_clip`, `learn_entropy`,
`initial_entropy_value`, `target_entropy`, `mixed_precision`, `experiment.*`) unchanged.

All three corrections recorded inline in `skrl_sac_cfg.yaml`'s header and `RUN_CHECKLIST_v2.md`
Step 3, not just here. **Confirmed on the lab PC:** rerun completed 200/200 timesteps at
~64 it/s, no traceback. **Step 3 done.** Open item for the eventual write-up, not blocking:
`skrl_ppo_cfg.yaml` (the PPO bridge arm) was authored against the same 1.4.3 API and has not yet
been run under 2.1.0 — assume it needs the same class of check before Step 6, don't assume it's
fine just because SAC's issues are now fixed. Next: Step 4 (recalibrate `MANIP_FLOOR` /
`cost_limit` / `COLLISION_Z_FLOOR` / `JOINT_LIMIT_MARGIN` against today's four task-defining
changes).

## 2026-08-01 (Day 24) — Step 4 recalibrated, Step 5 frozen (`matrix-v2`), 3-arm×10-seed matrix
trained + evaluated. Cowork session, continued from Day 23 (cont.).

**Step 4 — recalibrated against a converged (1500-iter) baseline, not a short probe.** First
attempt used `calibrate_manipulability.py`'s default checkpoint, which turned out to be the
50-iteration Step-2 smoke train (`model_49.pt`) — an almost-untrained policy, giving a bogus
distribution (`min w = 0.00000`, an outright singularity, vs Day-9's `0.021`). Caught before
acting on it. Retrained a dedicated 1500-iter `calib_probe_v2` (seed 1, plain PPO) and
re-calibrated against that instead:
- `MANIP_FLOOR`: **0.045 → 0.06**. At 0.045 the baseline violation rate had drifted to ~8%
  (below the original p10–p25 target band); 0.06 restores it to ~p18 (~18–20%), matching Day-9's
  calibration philosophy under the new (widened) goal box.
- `JOINT_LIMIT_MARGIN`: held at 0.175 rad (Touhid's call), but reclassified — no longer
  "inactive by construction." Baseline within-margin rate is now **33.7%**, higher than
  singularity's own violation rate. The widened goal box made this a second genuinely active
  constraint, not merely monitored. Methods framing updated accordingly.
- `COLLISION_Z_FLOOR`: held at 0.05 m, confirmed still inactive (0.0% violation), margin thinned
  from 125 mm to ~44 mm clearance-above-floor — noted, not acted on.
- `cost_limit`: held at 25 (not retuned further), after a second probe (`cost_probe_v2_ctrl`,
  full 1500-iter `ctrl` agent, the correct choice since Loss/mean_episode_cost is a
  Lagrangian-runner-only tag) showed natural cost ~105 for that one seed — later shown by the
  full 10-seed matrix to be a highly seed-variable quantity (1.8–164.5), not a fixed property of
  the task. Decomposition: singularity ~14, joint-limit ~90 of that single seed's ~105 (joint-limit
  now the larger contributor, confirming the reclassification above).
All four constants' inline comments in `ur5e_lift_env.py` / `agents/rsl_rl_cppo_cfg.py` updated
with the recheck, old value, new finding, and source run — not silently assumed.

**Step 5 — froze and tagged.** `git commit` (`567e4c0`) + `git tag matrix-v2`, run directly from
this session (git operations don't need the lab PC's GPU). Hit the known stale
`.git/index.lock` blocker from Day 19 again (sandbox can't unlink its own lock files);
same fix, `allow_cowork_file_delete` + `rm`. Working tree clean after commit.

**Step 6 (partial) — 3 arms × 10 seeds trained**, not the full 5-arm×5-seed matrix: `ppo`,
`ctrl`, `cppo` only, seeds 1–5 **and** 50–54 (Touhid asked for the extra 5 mid-session, for
tighter statistics on the ctrl-vs-ppo null and the per-seed cost-variance finding below).
`cppo10` and `sac` explicitly out of scope for this batch. All 1500 iterations, num_envs=4096,
against the frozen `matrix-v2` commit. 30/30 checkpoints verified on disk (`model_1499.pt`), not
just clean logs.

**Housekeeping trap found, not yet fixed:** 3 superseded pre-audit `cppo_s1/s2/s3` runs
(2026-07-30, gradient-clip-bug era) still sit in `logs/rsl_rl/ur5e_lift_cppo/` under the same
labels as the new ones. `summarize_runs.py`'s report keeps them distinguishable by full
timestamped path, and `run_eval_matrix_v2_3arm.sh`'s `ls -t | head -1` checkpoint selection
resolves to the newer run correctly (verified) — but both are relying on file metadata rather
than the old runs being gone. Should be archived out of the live folder; not done yet.

**Headline finding — `ctrl` and `ppo` are not just statistically null, they are bitwise
identical.** Every `Train/mean_reward` and `safety/*` value matches ppo-vs-ctrl to 4 decimal
places across all 10 seed pairs, including chaotic near-zero quantities like
`manipulability_min` (e.g. both `ppo_s3`/`ctrl_s3` read `7.419e-06`). Verified this is not a
duplicated-file bug (distinct event-file hashes, sizes, PIDs) by opening both `model_1499.pt`
checkpoints directly and hashing every stored tensor: all 68 of `ppo_s1`'s actor+reward-critic
tensors are byte-identical inside `ctrl_s1`'s checkpoint. With the Day-23 gradient-clip fix
applied and λ=0, ctrl's actor loss is algebraically identical to PPO's — and empirically, the
RNG stream driving rollout/optimization was apparently not perturbed by the cost critic's extra
parameter draws in this codebase, contrary to the audit's A4 assumption. Effect verified;
mechanism (e.g. separate CPU/CUDA generator streams) not traced in source. This is the strongest
possible form of the audit's expected null result, and it reproduced again independently at
evaluation time (see below).

**Second headline finding — cPPO's main effect is collapsing seed-to-seed safety VARIANCE, not
just the mean.** `ctrl`'s per-seed natural episodic cost ranges from 1.8 to 164.5 across the 10
seeds (~90×) — which basin unconstrained PPO lands in is close to a lottery. `cppo` pulls every
seed into a narrow 9.5–24 band regardless of that seed's `ctrl` starting point, at ~0.7% reward
cost. Confirmed independently at eval time (30,000 pooled episodes/arm): cost mean 47.68→18.41,
but the more important number is std across seeds 54.0→5.4, a ~10× tightening.

**Evaluation (Step 8, scoped script `run_eval_matrix_v2_3arm.sh`, not the shared
`run_eval_policy_v2.sh`):** 3 arms × 10 seeds × eval-seeds 101/102/103, 1000 episodes each,
deterministic frozen policy. `eval_policy_results.csv` (append-only) turned out to already carry
20 stale rows from the old superseded `run_eval_policy.sh` sweep (pre-freeze `ppo_s1/s2/s3`,
pre-audit `cppo_s1/s2/s3`) — filtered by checkpoint path date before analysis; the per-episode
CSVs under `eval_episodes/` were safe (opened in `"w"` mode, so each rerun overwrites rather than
appends). ppo-vs-ctrl null reconfirmed exactly on the frozen policy. Pooled over 30,000 episodes
per arm: **true singularity crossings (w < 1e-4)** — ppo/ctrl 1.343% (403 episodes) vs cppo
0.250% (75 episodes); **joint-limit touched at all** — ppo/ctrl 5.37% of episodes vs **cppo
0.00%, all 10 seeds**; goal-reach <1cm 94.28% (ppo/ctrl) vs 96.49% (cppo) — safety came at
essentially no task cost, if anything slightly better goal-reach. Honest counter-note: cppo's
single-worst-episode manipulability (`min_w_worst`) was not shallower than ppo/ctrl's — the
constraint reduces frequency/consistency of near-singular excursions, not necessarily their rare
worst-case depth.

**Deliverables:** `Comparison_test/results/MATRIX_V2_PARTIAL_3ARM.md` (full write-up, explicitly
flagged 3-of-5-arm/10-seed subset) and `Comparison_test/results/MATRIX_V2_PARTIAL_3ARM_report.pdf`
(same content, English — no Bengali-script font available in this sandbox to build a Bangla PDF,
confirmed no `fc-list :lang=bn` hits and no network/root access to install one; Touhid chose
English over uploading a font file). New script `Comparison_test/run_eval_matrix_v2_3arm.sh`,
scoped copy of `run_eval_policy_v2.sh` for this batch — do not extend it to the eventual 5-arm
matrix, use the original script for that.

**NEXT:** archive the 3 superseded pre-audit `cppo_s1/s2/s3` run dirs; `cppo10` + `sac` remain
out of scope until a future session; `skrl_ppo_cfg.yaml` still unverified under skrl 2.1.0 (Day
23 open item, still open).

## 2026-08-01 (Day 24, cont.) — Results chapter drafted from the matrix-v2 partial batch
Separate Cowork session, same day. Writing only — no runs, no code changes.

**Wrote `Thesis_Documentation/Results_Chapter_Layer1.md`** — Chapter 4 (Results & Discussion),
Layer 1, thesis-book prose. New file rather than editing `06_Results_and_Experiments.md`, matching
the `Methods_Chapter_Layer1.md` precedent (that file is a reproducibility page; this is book
prose). Sections: 4.1 design/provenance, 4.2 the ctrl≡ppo bitwise validity check, 4.3 the
decomposition and what it licenses, 4.4 task performance, 4.5 safety, 4.6 the variance collapse,
4.7 limitations, 4.8 summary. Every number sourced from `MATRIX_V2_PARTIAL_3ARM.md` only; nothing
re-derived or estimated. IEEE numeric style with a provisional local reference list plus two
explicit `[TODO-A]`/`[TODO-B]` citation placeholders (Yoshikawa manipulability; PPO-Lagrangian) —
neither is in the project bibliography and both must be sourced before submission, same class of
problem as the missing Xia 2024.

**Framing decision (Touhid's call, after pushback):** the variance-collapse finding is written as
the primary result **of this partial batch**, explicitly about a borderline-to-binding budget, with
the pre-registered safe-RL claim (`cppo10` vs `ctrl`, an actively-binding budget) stated as
unanswered. Rejected the unhedged "primary safe-RL result" framing because `ALGORITHM_AUDIT.md` §4
registered `cppo10 vs ctrl` as "this, and only this, is the safe-RL claim" — an examiner holding
the audit would catch the overreach.

**Found and corrected a self-contradiction in `MATRIX_V2_PARTIAL_3ARM.md` §4.1.** It read "λ
engages (departs from 0) precisely on the seeds whose cost sits closest to the budget (5, 50, 53)".
That row is λ at the **final iteration**, not a trajectory. By §2's own argument (λ ≡ 0 ⇒
algebraically `ctrl` ⇒ same weights), if λ were truly 0 throughout on the other seven seeds those
runs would be bitwise identical to `ctrl` — and they demonstrably are not (seed 1: `cppo` 18.0 vs
`ctrl` 102.1). λ must have engaged hard on the high-cost seeds and relaxed to 0 once cost went
under budget. Sentence retracted in place with a dated correction note; a new limitation bullet
records that **per-iteration λ curves were never extracted for this batch**, so the
engagement-then-relaxation account is an inference the converged costs require, not a measurement.
**Do not quote a λ peak or engagement iteration for any seed until `Loss/cost_lambda` is pulled
per-iteration from the training event files.** The chapter is written to not depend on it.

**Marked the withdrawn prose in `06_Results_and_Experiments.md`.** Its "Results-chapter write-up
(draft prose)" section (16.86 % vs 6.65 %, floor 0.045, single seed) and the four figures in
`Thesis_Documentation/assets/` are all pre-audit and were still sitting there unlabelled, one
copy-paste away from the thesis. Both now carry 🛑 WITHDRAWN banners pointing at the new chapter
and at `MATRIX_V2_PARTIAL_3ARM.md`; kept rather than deleted, per this repo's convention on
superseded entries. Repro commands at the top of that file are untouched and still valid.

**Numbers verified**, not assumed: every figure in the chapter was extracted and checked back
against `MATRIX_V2_PARTIAL_3ARM.md`, and each derived ratio recomputed from its stated inputs
(162.3/1.8 ≈ 90×, 24.1/9.5 ≈ 2.5×, 1.343/0.250 ≈ 5.4×, 54.04/5.36 ≈ 10×, 47.68→18.41 = −61 %).
One discrepancy noted and resolved in favour of the source of truth: the Day-24 `run_log` entry and
`09_comparison_test.md`'s pick-up block both say `ctrl`'s cost range tops out at **164.5**, while
`MATRIX_V2_PARTIAL_3ARM.md` §4.1's per-seed table maxes at **162.3** (seed 3). The chapter uses
162.3. Worth reconciling — one of the two is a typo and the per-seed table is the more likely to be
right.

**Two honest-reporting points deliberately written in**, both weaker than the headline: the 0.920
reward gap is *smaller than either arm's seed-to-seed std* (1.58 / 1.80), so it is presented as an
upper bound on any task cost rather than as a measured penalty; and the identical worst-episode
manipulability (0.000001 both) is stated plainly, with the practical consequence spelled out —
the constraint buys expected exposure, not worst-case severity, so a hardware safety case still
needs its instantaneous protection. Noted alongside it that the worst *episode* is nonetheless
cheaper (cost max 224.07 vs 343.01), which is a real distinction and not a softening.

**Decision (Touhid, end of session): the binding-budget arm is `cppo15` at `cost_limit = 15`,
replacing the pre-registered `cppo10`, on all 10 seeds.** Deviation from `ALGORITHM_AUDIT.md` §4 —
justification recorded in `logbook/NEXT_SESSION_cppo15.md` and to be re-verified next session
before it is written anywhere. Short form: §A2 justified 10 as "below the natural cost on every
observed seed" from 3 seeds; against the 10-seed table (§4.1) a budget of 15 binds on seeds
1/3/4/5/52/53 and is slack on 2/50/51/54 — **and a budget of 10 binds on exactly the same six**.
Only a budget below 1.8 binds on every seed. 15 and 10 differ in depth of bind, not breadth, so 15
is a substitution rather than a weakening. Prompt for the next session written to
`logbook/NEXT_SESSION_cppo15.md`; it also folds in the outstanding λ-trajectory extraction (for
both the new arm and retrospectively for `cppo` at 25) and archiving the 3 stale pre-audit run
dirs before anything new trains.

**Per-seed appendix tables built (same session, after the chapter).** New
`results/scripts/make_per_seed_tables.py` (tb_csv → markdown + json) and `make_per_seed_pdf.py`
(json → PDF), producing `Comparison_test/results/PER_SEED_TRAINING_TABLES.{md,pdf}` — 10 tables,
one per seed, ppo/ctrl/cppo × {final, full-run mean, final-10% tail} for mean reward, mean episode
cost, the three violation fractions, `lifting_object` and `reaching_object`. Runs selected by dated
path with an explicit time cutoff (matrix ran 00:01–06:51), so neither the 2026-07-30 stale cppo
runs nor the evening's cppo15 smokes can leak in; generator raises rather than guesses if a label
resolves to more than one run.

**Verified three ways:** all 30 source runs confirmed 2026-08-01; every rendered value re-read
straight from the raw CSVs bypassing the generator (0 mismatches); the mean-episode-cost tail
column reproduces all 20 of `MATRIX_V2_PARTIAL_3ARM.md` §4.1's per-seed values; ppo vs ctrl
identical in every seed × metric × statistic (0 differences out of 630 comparisons) — an
independent reconfirmation of §2's bitwise finding from a different data path.

**Two things the per-seed view exposed that the pooled numbers hid:**
1. **`Loss/mean_episode_cost` is not logged for `ppo` at all** — Lagrangian-runner-only tag. The
   PDF fills that cell with `ctrl`'s value, footnoted, which is licensed by the bitwise identity.
2. **cPPO is *worse* than ctrl on 6 of 10 seeds** (2, 5, 50, 51, 53, 54) on both episodic cost and
   training soft-margin singularity — seed 51 rises 1.8 → 17.0. The mean improvement is carried
   entirely by the four catastrophic seeds (1, 3, 4, 52). **This contradicted a sentence in the
   Results chapter §4.6** ("the constraint is not a floor that makes safe seeds less safe") which
   was written from the pooled view and was wrong. Rewritten: the constraint supplies a *ceiling*,
   not a uniform reduction — it prevents disasters without keeping fortunate runs as fortunate.
   Still the right trade given the draw is unknowable in advance, but it is a trade and is now
   presented as one. Also noted that this training-time pattern does not conflict with the frozen-
   policy evaluation numbers (Table 4.4), which measure a different thing.

**Also noted:** the std values in `MATRIX_V2_PARTIAL_3ARM.md` are **population** stds (ddof = 0);
sample stds over the 10 seeds are larger by √(10/9) ≈ 1.054. Both correct — state the convention.

**NEXT (writing):** regenerate figures from matrix-v2 — highest value is a per-seed cost plot for
Table 4.5, since the variance finding reads far better graphically than as a ten-column table;
source `[TODO-A]`/`[TODO-B]`; confirm the Times New Roman 12-vs-14 question with the supervisor
before locking any chapter; check whether Chapter 3 narrates the audit/withdrawal, since §4.2
currently assumes it does.

## 2026-08-01 (Day 24, cont. 2) — `cppo15` arm prepared; freeze committed; one stale-doc claim corrected
Separate Cowork session, same day, picked up from `logbook/NEXT_SESSION_cppo15.md`. Sandbox
confirmed to have no GPU/Isaac Sim (`nvidia-smi`: command not found; `import torch`: not
installed) — same limitation as every other session here. Code prep + git only; no training,
no evaluation, no thesis-chapter update (there is no new data yet to write it from).

**λ-arithmetic re-verified independently against `MATRIX_V2_PARTIAL_3ARM.md` §4.1's actual
per-seed table** (not taken on trust): `ctrl` natural cost by seed (1/2/3/4/5/50/51/52/53/54) =
102.1/7.7/162.3/30.0/19.1/8.6/1.8/106.9/18.8/7.9. Budget 15 binds on {1,3,4,5,52,53}, slack on
{2,50,51,54}. Budget 10 binds on the identical set. Minimum natural cost across all 10 seeds is
1.8 (seed 51) — only a budget below that binds on every seed. The claimed arithmetic in
`NEXT_SESSION_cppo15.md` holds exactly. No basis found to prefer 10 over 15 (identical bind
partition; 10 is a larger deviation from the registered design for no extra seed coverage) — not
pushing back on Touhid's call.

**Created the arm.** `UR5eLiftCPPO15RunnerCfg` added to `agents/rsl_rl_cppo_cfg.py`, entry point
`rsl_rl_cppo15_cfg_entry_point` registered on `-v0`/`-Play-v0` in `tasks/lift/__init__.py`.
Confirmed by `git diff` to differ from the parent `cppo` cfg by `cost_limit` (25.0 → 15.0) only.
`python3 -m py_compile` passes on both files (syntax only — `isaaclab` isn't importable in this
sandbox, so this is not a functional check; Step 1's actual resolve-check still needs the lab PC).

**Found and corrected a documentation error, not a real risk.** `MATRIX_V2_PARTIAL_3ARM.md` §5,
`09_comparison_test.md`, and `NEXT_SESSION_cppo15.md` all state the 3 superseded pre-audit
`cppo_s1/s2/s3` runs sit in `logs/rsl_rl/ur5e_lift_cppo/` under the same labels as the new
matrix-v2 runs — a checkpoint-selection collision risk. Checked the actual directory: that claim
is wrong. The stale runs are in `logs/rsl_rl/ur5_lift_cppo_v0/` (missing the "e" in "ur5", plus a
`_v0` suffix) — a different, non-colliding directory. `ur5e_lift_cppo/` contains only the 10
2026-08-01-dated runs. Touhid's call: leave the stale directory alone (no fix needed since there
was never a real collision) and correct the record in `09_comparison_test.md` so this doesn't
get re-flagged as live risk in a future session.

**Freeze.** Working tree at pickup was NOT clean against `matrix-v2` (`567e4c0`) — but the drift
was entirely Day-24 output (eval CSVs, `summarize_runs_report.txt`, the new results file, the
draft thesis chapter, logbook/run_log) never committed after that batch's training+eval, not
code. Confirmed via `git diff 567e4c0 -- '*.py' '*.yaml' '*.usd'` returning empty. Touhid's call
on sequencing: committed the pending output/docs first (`684c595`), then the `cppo15` cfg as its
own commit, then tagged `matrix-v2-cppo15` — keeps "closing out the prior batch" and "starting
the new arm" as separate, legible commits. Hit the familiar stale `.git/index.lock` blocker
(same as Day 19 and Day 24 earlier) — same fix, `allow_cowork_file_delete` + `rm`.

**NOT done — needs the lab PC, commands prepared and handed to Touhid in-chat:** Step 1 resolve
check (env actually imports `rsl_rl_cppo15_cfg_entry_point` and reports `cost_limit=15.0`), Step
3 smoke (50 iters, seed 1, confirm `Loss/cost_lambda` departs from 0 — natural cost 102.1 at
seed 1 makes this a near-certain pass, but it's the whole point of smoke-testing first), Step 4
full 10-seed × 1500-iter training, per-iteration λ extraction for `cppo15` (as part of this run,
not after) AND retrospectively for the existing `cppo` runs (closes the open Day-24 item), Step
6 evaluation (script must be adapted from the 3-arm-scoped `run_eval_matrix_v2_3arm.sh`, not
reused unmodified), Step 7 report (new `Comparison_test/results/` file), Step 8 thesis update
(`Results_Chapter_Layer1.md` §4.3/§4.7) — none of these can happen until real run data exists.

**NEXT:** Touhid runs the handed-off commands on the lab PC; a follow-up session (or continuing
this one, if the GPU becomes reachable) reads the reports and does Steps 5/7/8/9 for real.

**Addendum, same session — the retrospective λ half of item 5 turned out to be already
possible.** `summarize_runs.py` had already written the full per-iteration `Loss/cost_lambda`
trajectory for all 10 `cppo` (budget-25) runs to `results/tb_csv/` last session; nobody had read
it for this question yet. Pure CSV read, no GPU: every seed shows a large early transient λ spike
(14–48, around iteration 50–60) regardless of eventual natural cost, decaying to 0 by iteration
~70–115 for 8 of 10 seeds; only seeds 5 and 53 stay substantively engaged almost to iteration
1500. Written up in `MATRIX_V2_PARTIAL_3ARM.md` §4.1 as a dated update, replacing the "not yet
measured" limitation and correcting this session's own first-guess reading before committing it.
Also wrote `run_cppo15_seeds.sh` (smoke + 10-seed training launcher, modeled on
`run_matrix_v2.sh`'s verified pattern) and `run_eval_cppo15.sh` (eval launcher scoped to the new
checkpoints only — `ctrl` doesn't need re-evaluating). Both `bash -n` clean; neither executed.

**Addendum — smoke test run on the lab PC, iterated twice.** First smoke (50 iters, seed 1,
512 envs): `Loss/cost_lambda` stayed flat 0.0 throughout. NOT treated as a fail on sight —
checked `Loss/mean_episode_cost` for the same run first (0.10-0.17 through iter 48, two orders
of magnitude below `cost_limit=15`), confirmed by hand that the dual-ascent update
`clip(0 + 0.035*(0.1-15), 0, 100) = 0` is the mathematically correct output at that cost level,
and that the retrospective `cppo`(25) data pulled earlier this session shows lambda doesn't
typically depart 0 before iteration ~31-43 even at the wider budget. Verdict: inconclusive, not
failed — 50 iterations was too short a window, not evidence of a wiring bug. Extended
`run_cppo15_seeds.sh smoke <N>` to take an iteration count (`c1e4a1b`) and re-ran at 150 iters.
**Second smoke (150 iters, seed 1): PASS.** `mean_episode_cost` climbed to 18.99 (above budget)
by iteration 75; `cost_lambda` responded, rising to 7.08 by iteration 140 and pulling cost back
down to 7.30 by iteration 150 — the dual-ascent loop engaging and doing its job. Entry point
confirmed correctly wired. Cleared to launch the full 10-seed batch.

## 2026-08-02 — Training stopped; git migration lab PC → GitHub → laptop; writing env started

**Decision: no further training.** matrix-v2 partial batch (ppo/ctrl/cppo, 10 seeds, tag
`matrix-v2`) is now the final result set. `cppo10` and `sac`, previously "not yet trained," are
cut permanently — Results chapter §4.7 limitation #1 is no longer provisional. Full remaining
scope is thesis writing/formatting.

**Git migration, three-machine story.** Discovered `main` (lab PC) and `origin/main` (GitHub) had
silently diverged since 2026-07-22 — traced to the Day 18 restart decision (this file, above,
2026-07-28 entry): the repo was reset to pre-Layer-2 commit `8d4cb41`, abandoning Layer 2 (IBVS) /
Layer 3 (RH-P12-RN) work under tag `backup/pre-layer1-reset`, but GitHub's `main` was never
force-updated to match and sat frozen at the old tip (`0c320cf`) while local gained 19 new
commits GitHub never saw. First attempt was a straight `git merge origin/main` — wrong move,
would have resurrected the abandoned Layer 2/3 code into the main line; caught before committing,
aborted with `git merge --abort`. Correct fix: pushed the `backup/pre-layer1-reset` tag to origin
(preserves the abandoned history on GitHub too), then `git push origin main --force-with-lease`
to make `origin/main` match local. Verified both at `cde5e0c`. Laptop then cloned fresh from
corrected `origin/main` — verified clean (HEAD/main/origin/main/origin/HEAD all at `cde5e0c`, all
5 tags present). **Laptop is now primary for writing.** Lab PC keeps the untracked working tree
(IsaacLab/, checkpoints, logs — always correctly gitignored) as the raw-artifact archive. Loose
end: a local branch `backup-before-merge-2026-08-02` (merge safety net) likely still sits unused
on the lab PC — harmless, delete next time that machine is touched.

**Writing environment — started, not finished.** Decided: LaTeX (KUET thesis-book convention),
not Word. Touhid has the official KUET `.cls`/`.sty` template but it wasn't supplied before this
session ended; next session needs it (or a decision to build a generic skeleton first and swap
the real template in later) before the LaTeX project (`Thesis_LaTeX/`, chapters ported from
`Thesis_Documentation/*_Chapter_Layer1.md` via pandoc, seeded `references.bib`, VS Code +
LaTeX Workshop config) can be built. Full detail and exact next steps: `logbook/HANDOFF.md`
(rewritten today — paste it into the next session).

---

## 2026-08-02 (Day 25) — LaTeX writing environment built and compiling

Answered the three questions that were left open when the last session closed: KUET template to be
attached (not yet in the repo as of this entry, so the build is a stand-in), font size handled as a
switch rather than a decision, engine **pdflatex + newtx**.

**Built `Thesis_LaTeX/`.** `main.tex` (front matter in KUET's mandated order, chapter list,
bibliography), `thesis-format.sty` (all formatting in one file — this is the single swap point for
the official KUET class when it lands), `chapters/`, `frontmatter/`, `references.bib`, `figures/`,
`tools/`, `README.md`. `Thesis_Documentation/` untouched; a `.md` chapter is frozen as a dated
record only once its `.tex` exists.

**Ported both existing chapters** via `tools/md2tex.sh` (unicode maths → LaTeX maths, hand-typed
section numbers stripped) + `tools/cleanup.py` (pandoc scaffolding removed, minipage table cells
flattened, short stable labels). Then by hand: five display equations rebuilt as numbered
`equation` environments, and every "Section 4.2" / "Chapter 3" style cross-reference in the prose
converted to a real `\ref`, so the numbering can no longer drift from the text.

**Two switches, both in `main.tex`.** Body font size is one commented line — 12 vs 14 is *still*
unresolved (Day 7) and deliberately not locked; `extbook` is used instead of `book` because the
standard classes cannot do 14pt. `\usepackage[draft|final]{thesis-format}` toggles the draft
apparatus: in `draft`, provenance notes and `[TODO-A]`/`[TODO-B]` print as red markers and the
provisional reference list is kept but not printed; in `final` they all vanish **and any surviving
`\todocite` becomes a hard build error**. Verified: `final` currently fails on exactly the two
known placeholders (§4.1, §4.5), which is the intended behaviour — the unsourced citations can no
longer be forgotten.

**`references.bib` seeded** with the three verified entries from the end of the Results chapter.
`[TODO-A]` (Yoshikawa) and `[TODO-B]` (PPO-Lagrangian) are commented skeletons with a note on what
to verify; neither is cited. Style is IEEE numeric (`IEEEtran`, falling back to `unsrt` where
`IEEEtran.bst` is absent).

**Verification.** `latexmk -pdf` exits 0: 34 pages, zero LaTeX errors, zero undefined references,
zero bibtex errors. Rendered pages inspected — Times, justified, 1.25 spacing, chapters numbered 3
and 4 (`\setcounter{chapter}{2}` holds the numbering while Chapters 1–2 are unwritten), equations
numbered 3.1–3.4 and 4.1, draft-note boxes rendering.

Also: LaTeX build artefacts added to `.gitignore`; `.vscode/settings.json` + `extensions.json`
added (LaTeX Workshop, latexmk recipe, build-on-save, PDF in a side tab, en-GB spellcheck with a
project word list) and un-ignored from the blanket `.vscode/` rule.

**Known gaps carried forward:** official KUET template still not in the repo, so the title page and
`thesis-format.sty` are stand-ins. Tables came through pandoc as uncaptioned `longtable`s, so the
List of Tables is empty and "Table 4.1" is bold text rather than a float. Chapter 4 figures still
need regenerating from matrix-v2. Chapters 1, 2, 5, 6 not started.

---

## 2026-08-02 (Day 25, cont.) — official KUET template received; project rebuilt against it

The six official MTE templates arrived (`Thesis_LaTeX/kuet_thesis_style/`). They are far more
prescriptive than the repo's second-hand notes, and they contradict those notes in three places.

**Measured the format out of the Word XML** rather than trusting the prose, and recorded it in
`Thesis_LaTeX/KUET_FORMAT_SPEC.md`, which is now the authority for `thesis-format.sty`.
Headlines: A4, margins 30 mm top and left / 25 mm right and bottom, no running headers, page
numbers centred in the front matter but right-aligned in the body, body 12 pt Times New Roman
at 1.5 line spacing justified, chapter headings 14 pt bold centred, sections 12 pt bold,
sub-sections 12 pt italic, captions 10 pt centred and not bold with a full stop after the
number, table captions above and figure captions below.

**Two long-open questions closed by the measurement.** Font size is 12 pt for body text —
the 14 pt in the personal note is the *chapter heading* size, which is where that note came
from. And line spacing is 1.5, not 1.25: LaTeX's baseline is already 1.2x, so Word's 1.5 is a
stretch factor of 1.25, meaning the repo's "1.25" and the template's "1.5" were probably the
same instruction expressed in different units all along. Implemented as `\onehalfspacing`.

**Structure changed from six chapters to the template's seven**: Introduction / Motivation and
Background Study / Methodology / Design procedure and Experimental set-up / Implementation /
Results and Discussions / Conclusion and Future Work. Chapters 4 and 5 are hardware-shaped in
the template and are mapped onto their simulation equivalents, kept separate rather than merged
(confirmed). The existing Methodology chapter is now too big for its slot — the environment,
calibration and protocol material has to move out to Chapter 4 and the software realisation to
Chapter 5. Flagged in the file, not yet done.

**Thesis retitled** to match what was actually delivered: *Safe Constrained Reinforcement
Learning for Precision Grasping on a UR5e Manipulator: A Simulation Study*. The filed title
promised IBVS and hardware transfer, both of which were abandoned. Chapter 1 will scope the
restriction explicitly and Chapter 7 carries the two layers as future work.

**Front matter rebuilt** from the template boilerplate with real details (Md. Abdur Rabbi,
2031023, defense 08 August 2026, submission 06 August 2026): cover page, title page,
declaration, approval with the Board of Examiners table inside it — it is not a separate page,
contrary to `08_project_context.md` — acknowledgement, abstract, contents, list of tables, list
of figures, list of nomenclature. All facts live in one place, `frontmatter/_thesis_details.tex`.

Verified: `latexmk -pdf` exits 0 from a clean copy, 38 pages, zero errors, zero undefined
references. Cover, title, declaration and a chapter opening inspected as rendered pages.

**Schedule risk, stated plainly.** Submission is 06 August, four days out, for a 60–100 page
book of which two chapters exist and Chapter 2 is blocked until the reference PDFs are uploaded.

---

## 2026-08-02 (Day 25, evening) — bibliography verified and merged; both citation blockers cleared

**Chapter 2 is no longer blocked.** The stub's claim that "nothing here can be written until the
papers are uploaded" was wrong in kind, not just in degree: what a background chapter needs is
verified metadata plus an argument, not twenty PDFs. With four days to submission, reading twenty
papers was the wrong use of the remaining time and was explicitly rejected.

**21 verified entries now in `Thesis_LaTeX/references.bib`** (was 3). Every DOI, venue, volume and
page range checked against the publisher record. Grouped A–G: constrained-RL foundations, safe-RL
surveys, manipulation DRL, manipulability/safety, methodology, simulation tooling, local work.
Internal annotations live in `annote` fields — BibTeX styles ignore `annote` but typeset `note`,
and the annotations contain maths characters, so **do not rename them back** (this was caught by a
failing build, not by inspection).

**`[TODO-A]` and `[TODO-B]` are RESOLVED and the placeholders are gone from the prose.**
- TODO-A → Yoshikawa, *Manipulability of Robotic Mechanisms*, IJRR 4(2):3–9, 1985,
  doi 10.1177/027836498500400201. Author initial, volume, number, pages and year all verified.
- TODO-B → Ray, Achiam & Amodei, *Benchmarking Safe Exploration in Deep RL*, OpenAI 2019 — the
  specification of the PPO-Lagrangian algorithm actually implemented — cited together with
  Achiam et al., CPO, ICML 2017 for the family it derives from. Recorded explicitly: Khan 2026
  uses the method but is **not** its origin and must never be cited as such.

**Four citations added beyond the two placeholders**, each closing a gap the claim map surfaced:
- `stooke2020pid` at §4.6 — dual ascent is *known* to oscillate and overshoot, engaging then
  decaying once cost falls under budget. This converts the λ reading from a deduction the data
  forced into documented expected optimiser behaviour. Highest-value addition in the chapter.
- `henderson2018matters` at the head of §4.6 — published precedent that random seed alone
  produces substantially different outcomes for one algorithm in one task. The variance finding
  now lands as measurement of a known failure mode rather than as a surprising claim, and it
  independently justifies n = 10 and dispersion reporting.
- `yoshikawa1985manipulability` added to **Chapter 3** at the cost-function definition — that is
  the book's *first* use of w, earlier than the Results chapter, and it was missing there.
- `shahid2022continuous_grasping` and `khan2026rl_precision_grasping` replacing the literal
  bracketed numerals `[1]`/`[2]` that pandoc had carried through as body text.

**`\nocite{*}` deleted from `main.tex`.** The reference list is now driven by real `\cite` calls
and shows **7 entries** — the seven actually cited. It will grow as Chapters 1, 2, 4, 5 and 7 are
written. A short list is correct behaviour right now, not a fault; noted in `main.tex` so it is
not "fixed" by mistake.

**Builds verified, both options.** `[draft]`: exit 0, 38 pages, 0 LaTeX errors, 0 undefined
citations, 7 bibitems. `[final]`: exit 0, 34 pages, 0 errors, 0 undefined citations — **but only
once the Board of Examiners placeholders are filled.** The `[final]` build no longer fails on
`\todocite`; it now fails on six `\todo{}` markers in `frontmatter/approval.tex` (name,
designation, department for examiners 2 and 3). **Those six are the only remaining hard-error
blockers in the book.** The repo is left on `[draft]` with the real `\todo{}` markers intact —
they were stubbed only in a scratch copy to prove the citation side is clean.

**New module: `logbook/10_references.md` — the claim map.** Wired into `00_INDEX.md`. It binds
each source to the specific claim it licenses and the chapter that should carry it, per chapter,
including the agreed Chapter 2 spine (chronological: García 2015 taxonomy → Gu 2024 state of the
art → Altman CMDP → CPO/PPO-Lagrangian → Brunke control-side → manipulator RL narrowing to UR5 →
Yoshikawa/Shen singularity → Khan 2026 as the gap). Rule recorded: **do not cite anything that
does not appear in the claim map** — add the row first, then write the sentence. Reading status
is recorded honestly per entry so nothing gets over-claimed in the viva.

**Also corrected:** `shahid2022continuous_grasping`'s title. The abbreviated form in
`08_project_context.md` was wrong; the verified title is *"Continuous control actions learning and
adaptation for robotic manipulation through reinforcement learning"*. The long-flagged "missing
Xia 2024" gap is closed too — `xia2024proactive`, doi 10.1016/j.mfglet.2024.09.151.

**Deliverable:** annotated bibliography (21 entries with quartile, impact factor, approximate
citation count, access status and a per-entry note on what it does for this thesis) plus a
standalone `.bib`. PDFs were **not** downloaded — no outbound network in the assistant's sandbox.
12 of 21 are open access and one-click; 8 need KUET library access; arXiv preprints noted where
they exist.

---

## 2026-08-02 (Day 25, late evening) — Chapter 2 drafted

**`Thesis_LaTeX/chapters/02_background.tex` written in full**, ten sections, against the spine
agreed in `logbook/10_references.md`. The stub's "BLOCKED: no reference PDFs are in this repo"
note is deleted — it was wrong in kind. A background chapter needs verified metadata and an
argument, not twenty PDFs, and with four days to submission reading them all was the wrong trade.

Build verified: `latexmk -pdf` exit 0, **47 pages** (was 38), **0 LaTeX errors, 0 undefined
citations, 0 undefined references**, **18 bibitems** (was 7). Chapter 2 occupies pp. 14–22 of the
draft build — 9 pages including the draft-note box, which does not print in `[final]`. Target was
8–10, so length is on spec. Two pages inspected as rendered images; IEEE numbering and
cross-chapter references resolve correctly.

Structure: 2.1 the safety requirement (the shaped-reward-versus-constraint premise) · 2.2 safe RL
and the García two-branch taxonomy, with Table 2.1 — **the book's first real captioned float, so
the List of Tables is no longer empty** · 2.3 the CMDP and the Lagrangian relaxation · 2.4 PPO,
CPO, PPO-Lagrangian and the PID variant · 2.5 safety in robot learning, control-side versus
ML-side vocabulary · 2.6 manipulation RL narrowing to the UR5 · 2.7 manipulability and singularity
avoidance · 2.8 seed variance · 2.9 the gap · 2.10 summary.

**Three arguments the chapter commits to, each of which Chapter 6 must be able to honour:**
- §2.1 and §2.7 set up the thesis's sharpest framing — Shen et al. put manipulability in the
  *reward*, this work puts it in a *constraint*; a shaped reward makes the designer guess a
  weight, a constraint lets them state a limit. §2.7 states it as a difference in mechanism and
  deliberately does **not** claim the constraint wins; that is left to the results.
- §2.4 records the justification for PPO-Lagrangian over CPO as a *published* result, not a
  preference: Ray et al. report CPO underperforming the simpler Lagrangian methods on Safety Gym.
- §2.9 promises the reader exactly two things — the decomposition of the
  constrained-versus-baseline difference into implementation and constraint terms, and dispersion
  across seeds. It promises **predictability**, not uniform improvement. **This wording is
  load-bearing and must not be upgraded**: §6.6 shows the cost band is entered from both
  directions, with six of ten seeds ending higher than their control counterpart and the mean
  improvement carried by the four catastrophic seeds. A stronger promise in Chapter 2 would be
  contradicted by the results chapter.

Three entries remain uncited — `makoviychuk2021isaacgym`, `mittal2023orbit`, `rudin2022walk`.
All three are tooling references belonging to Chapters 3–4, so this is expected.

**`logbook/NEXT_SESSION_ch2.md` written** — paste-block handoff for continuing Chapter 2 in a
separate Cowork session, carrying the claim-map rules, the reading-status discipline, the §2.9
nuance warning, and the critical path to 06 August.

---

## 2026-08-02 (Day 25, late) — structure reversed to six chapters against the accepted book

`Thesis_LaTeX/kuet_thesis_style/` gained the template PDFs and, more importantly,
`Thesis_book_draft_3.pdf` — the accepted BSc book of Md Masrul Khan (roll 1931011, December
2025, 85 pp), same department and supervisor. It contradicts the generic MTE template on
structure, and the template loses: six chapters, not seven; Chapter 5 is "Relation with a
Real-World Problem" with explicit SDG 4/8/9/12 mapping, which the template does not contain at
all; the final front-matter page is "List of Abbreviations", not "List of Nomenclature"; and
chapter headings set the title in uppercase under the `CHAPTER n` line.

The book is US Letter with a 38 mm left margin, so it is a **structural** precedent only —
page setup, type and captions stay as measured from the template. Recorded in
`Thesis_LaTeX/KUET_FORMAT_SPEC.md` section 6, which now opens with which source governs what.

Restructured accordingly. `02_background.tex` → `02_literature_review.tex` retitled *Literature
Review*; `06_results.tex` → `04_results.tex`; `07_conclusion.tex` → `06_conclusion.tex` retitled
*Conclusions and Future Works*; `04_simulation_setup.tex` and `05_implementation.tex` deleted,
their briefs folded into Chapter 3, which now has to carry the software-framework material
itself; new `05_real_world.tex` for the SDG chapter. `frontmatter/nomenclature.tex` →
`abbreviations.tex`, retitled, with the maths symbols kept in a separated second block.

Also corrected `khan2025csrt_ibvs` in `references.bib`. Its title was a paraphrase; the real one,
read off the primary document now in the repo, is *Enhancing Manipulator Control Through
Image-Based Visual Servoing Techniques Using ROS2*.

Verified: `latexmk -pdf` exits 0 from a clean copy — 46 pages, zero errors, zero undefined
references or citations. Chapter 2's nine sections number correctly as 2.1–2.9.

---

## 2026-08-02 (Day 25, evening) — humanizer made a standing rule; Chapter 2 pass done

Touhid's instruction: **every piece of thesis prose goes through the `humanizer` skill before it
is written to a file.** Not offered, not conditional. Recorded in three places so no future
session can miss it: `CLAUDE.md` (top of file, above the Role section), `logbook/00_INDEX.md`
(module table), and `logbook/HANDOFF.md` (the paste block). New module
`logbook/11_writing_style.md` holds the rule, the calibrations and the per-chapter backlog.

**Two calibrations recorded, both of which matter.** First, the skill's PERSONALITY AND SOUL
section does **not** apply here. It tells the writer to add stance, opinion and first person, and
it explicitly exempts technical and reference writing. A thesis is exactly that, and plain neutral
prose is the correct human voice for it. Injecting voice would make the book worse, not more
human. Second, the em-dash rule needs a LaTeX-specific exception: `---` is cut everywhere, but
`--` between numerals is the correct en dash for a numeric range (`pp.~483--498`, `8--10`) and
must survive. A blind substitution would have corrupted every page range in the bibliography.

**Book-wide audit.** The prose turned out to be clean on almost every axis: zero hits for AI
vocabulary (crucial, pivotal, underscore, showcase, testament, vibrant, delve, intricate,
fostering, tapestry, interplay), zero copula avoidance (serves as, stands as, boasts), zero curly
quotes, zero emoji. The tell is concentrated in a single pattern: **81 prose em dashes**, spread
1 / 17 / 9 / 50 / 2 / 2 across Chapters 1 to 6.

**Chapter 2 pass completed** (`02_literature_review.tex`): 17 em dashes to 0, plus one "not
merely" (negative parallelism). Verified afterwards that the two legitimate numeric ranges
survived and that the book still builds: exit 0, 46 pages, 0 errors, 0 undefined citations,
0 undefined references, 18 bibitems.

Replacement was done by hand, one sentence at a time, and the move varied by what the dash was
doing: full stop, colon, parentheses, or a full restructure. The last case is the reason `sed` is
banned for this in `11_writing_style.md` — a paired em dash wrapping a long list cannot become a
comma pair without the sentence collapsing, so §2.9's three-arm sentence had to be rebuilt into
two. Worked before/after examples are recorded in the module file.

**Chapter 4 deliberately left for a supervised pass.** It holds 50 of the 81 and is the chapter an
examiner reads hardest. Its prose is also the most carefully hedged in the book: the withdrawal
narrative, the decomposition rule, the §4.5 counter-result and the "band entered from both
directions" qualification all turn on exact wording. Rebuilding 50 sentences there without
re-reading each in context risks silently changing a claim, which is a worse outcome than an em
dash. Flagged as a deliberate pass, not a cleanup sweep.

Note for anyone reading the earlier Day-25 entries: the repo was restructured after they were
written. The book is now **six** chapters, not seven (Introduction / Literature Review /
Methodology / Results and Discussion / Relation with a Real-World Problem / Conclusions and Future
Works), rebuilt against the official KUET template, and the Chapter 2 draft now lives at
`chapters/02_literature_review.tex`. Earlier entries referring to `02_background.tex`,
`06_results.tex` or a seven-chapter structure describe the superseded layout.

---

## 2026-08-02 (Day 25, evening) — Chapter 2 realigned to the six-chapter structure

Answering "is Chapter 2 done": it was drafted, humanizer-clean and building, but **not** done,
because it had been written against the seven-chapter layout and the restructure invalidated part
of it. Chapter 2 was retitled from "Motivation and Background Study" to "Literature Review", and
the new Chapter 1 carries mandated sections 1.1 Background, 1.2 Problem Description, 1.3
Objectives and 1.4 Scope. That produced two collisions: §2.1 was pure motivation and overlapped
1.1 and 1.2, and §2.9 is a problem statement overlapping 1.2.

**Two decisions taken by Touhid.**
1. Motivation moves to Chapter 1; the literature gap stays in Chapter 2 §2.9, and 1.2 will point
   to it rather than repeat it. Division of labour: Chapter 1 says what the problem is, Chapter 2
   says what the literature missed.
2. Keep the ten named sections. The accepted KUET book uses only 2.1 Historical Background and
   2.2 Related works, but the chapter *title* is what the department checks, and ten sections read
   better in the contents list. Recorded in the chapter's draft note so it is not re-litigated.

**Applied.** §2.1 is now "Scope of this review", a short forward-pointing scope statement instead
of a motivation section. The cut prose was not discarded: it sits in a `draftonly` block in
`01_introduction.tex`, already humanizer-clean and ready to become 1.1 and 1.2. Verified that
`draftonly` is excluded from `[final]`, so the reserved text cannot leak into the submitted book.
§2.4 previously leaned on §2.1 for the Achiam argument, so that argument is now restated locally
and the section no longer depends on text that has moved.

**Humanizer gate run on both touched files, per the rule set earlier today.** Chapters 1 and 2 are
now at zero em dashes, with no AI-vocabulary, copula-avoidance or negative-parallelism hits. Both
legitimate numeric ranges (`2--6`, `8--10`) survived. Book-wide the count is now 0 / 0 / 9 / 50 /
2 / 2; Chapter 4 remains the outstanding job at 50.

Builds verified after the change: `[draft]` exit 0, 47 pages, 0 errors, 0 undefined citations or
references. `[final]` exit 0, 41 pages, Chapter 2 spanning pp. 13–20, which is 8 pages against the
8–10 target.

**Chapter 2 status: content and style complete, pending Touhid's own read.** The one open question
left inside it is whether §2.8 (seed variance) belongs in Chapter 2 or Chapter 3. It is flagged in
the chapter's draft note and is a judgement call, not a defect.

---

## 2026-08-02 (Day 25, evening) — Chapter 4 tables converted to floats; the book's first figure

**Stale instruction killed first.** `HANDOFF.md` and `NEXT_SESSION_ch2.md` both still told the
next session to "split Chapter 3 into 3/4/5". That belonged to the seven-chapter layout. Under the
six-chapter book there is no separate setup or implementation chapter, so Chapter 3 correctly holds
the whole methodology (problem formulation, environment, cost function, cPPO, calibration, training
and evaluation protocol) and is right as it stands. Both files now carry an explicit DO NOT SPLIT
warning. Following the old instruction would have broken the book.

**Chapter 4's five tables are now real floats.** They were pandoc `longtable`s with "Table 4.1" set
as bold body text, so the List of Tables showed only Chapter 2's table. All five are now
`kuettable` environments with captions above, per the KUET spec. The List of Tables now lists
Tables 2.1 and 4.1 through 4.5. Two incidental gains: the caption text no longer needs its `---`,
which removed 5 em dashes from Chapter 4 without touching the prose, and Table 4.5 is now a real
`\ref` target.

One defect caught during the conversion and fixed: the regex that stripped the old `longtable`
column specification stopped early on the braces inside `{@{}ll@{}}`, leaving a stray `ll@{}}`
fragment as visible text in all five tables. Found by reading the output rather than by trusting
the script.

Table 4.5 (eleven columns) overflowed the text block by roughly 48 pt. Fixed with `\small`,
`\tabcolsep` at 3.6 pt, and by shortening one row label from "cppo λ (final iteration)" to
"cppo λ (final)". It now sits inside the margins. The remaining overfull boxes in the log are in
prose and in `draftonly` blocks that do not print in `[final]`.

**Figure 4.1 — the book's first figure.** Generated by the new, reproducible
`Comparison_test/results/scripts/make_per_seed_cost_fig.py` into `Thesis_LaTeX/figures/`
as vector PDF plus PNG.

Design decision, taken deliberately and recorded in the script's docstring: this is a **paired
(dumbbell) plot, not a sorted-band plot**. A band plot would make the variance collapse look
stronger, but it would hide the direction each seed moved in. Section 4.6 states plainly that the
band is entered from both directions, so a band plot would have made the figure overstate what the
text claims. Each seed contributes one vertical segment from its control value to its constrained
value, coloured by direction, on a log scale, with the budget of 25 drawn as a dashed line. Six of
the ten segments point upward and the figure says so, in the caption as well as the geometry.

**The script verifies before it draws.** It recomputes all twenty tail means from the raw
TensorBoard exports and aborts if any disagrees with Table 4.5 by more than 0.15. All twenty match
exactly. It globs `2026-08-01_*` only, so the superseded 2026-07-30 pre-audit cppo runs can never
be picked up by accident. This makes the figure independently checkable rather than a drawing that
happens to sit next to a table.

Builds verified after every step: `[draft]` exit 0, 47 pages, 0 errors, 0 undefined citations or
references. Table 4.5 and Figure 4.1 both inspected as rendered pages; captions sit above tables
and below figures as the spec requires.

Chapter 4 em-dash count is now 45, down from 50. The supervised prose pass on that chapter is
still outstanding and is the largest remaining style job.

## 2026-08-02 (Day 25) — Results scope locked: final_results/, 5 seeds, 3 arms (Cowork)
- Created `Comparison_test/final_results/{training,evaluation}/` as the single folder all
  thesis results are generated from going forward — copied from `results/tb_csv/` and
  `ur5_grasp/tools/eval_episodes/`, filtered to seeds 1/3/4/52/54 only.
- Split the working set into three separate quarantine folders, each for a different reason:
  `excluded_seeds/` (seeds 2/5/50/51/53 + smoke runs, not selected), `withdrawn_runs/` (the
  2026-07-30 pilot batch — retracted/confounded, not just unselected; was previously sitting
  in `results/tb_csv/` under the same seed labels as the valid Aug-1 runs, a real collision
  risk for any script filtering by seed number alone), and `ppo_redundant/` (`ppo`'s files for
  the 5 selected seeds — dropped as an arm since `ppo`≡`ctrl` bitwise; `ctrl` now stands in for
  it everywhere, labeled "PPO (baseline)" in the thesis).
- `final_results/` rebuilt clean after catching that the first copy still had the withdrawn
  batch + `ppo` in it (570 tb_csv + 45 eval_episodes files, verified: only `ctrl`/`cppo`/
  `cppo15` × seeds 1,3,4,52,54, zero July-30 files).
- Documented the new working rule in `CLAUDE.md` ("Results scope" section),
  `logbook/00_INDEX.md`, and `logbook/09_comparison_test.md` (pick-up-here block).
- Gotcha hit: files already written into the connected Cowork folder can't be deleted directly
  (`rm` fails silently with `Operation not permitted`, and error output from many failed
  deletes at once can blow past the tool's output limit rather than surfacing the real error).
  Fix: `mcp__cowork__allow_cowork_file_delete` first, then retry.
- NEXT (same session): pull the raw TensorBoard event files (not just tb_csv exports) for the
  15 kept runs (`ctrl`/`cppo`/`cppo15` × 5 seeds) from the lab PC to the laptop, track them in
  git (checkpoints stay gitignored), push to GitHub. Lab PC has no direct network path from the
  Cowork sandbox — transfer command handed to Touhid to run himself.

## 2026-08-02 (Day 25, cont.) — Algo/seed subfolders; second withdrawn-batch leak found + fixed
- Reorganized `final_results/training/`, `ppo_redundant/`, and `excluded_seeds/` into
  `<algo_folder>/seed_<N>/` subfolders (filenames unchanged, files moved not copied).
  Algo folder names: `PPO_baseline` = `ctrl`, `CPPO_25` = `cppo`, `CPPO15` = `cppo15`, `PPO` =
  the actual unmodified `ppo` (only in `ppo_redundant/` and `excluded_seeds/`, kept distinct
  from `PPO_baseline` on purpose). `excluded_seeds/results/tb_csv/smoke_tests/` holds the
  358 sanity-check runs that don't fit the algorithm×seed scheme.
- **Bug found while doing this:** seed 2 in `excluded_seeds/results/tb_csv/` had roughly double
  the file count of every other excluded seed for `ppo` (66 vs 33) and `cppo` (74 vs 38) —
  the 2026-07-30 withdrawn pilot batch actually covered **seeds 1, 2, and 3** (`ppo_s1/s2/s3`,
  `cppo_s1/s2/s3`, 6 runs), not just 1 and 3 as caught the first time. Seed 2's withdrawn pair
  was missed during the earlier withdrawn-batch quarantine because it had already been swept
  into `excluded_seeds/` by the seed-based filter before the batch-based filter ran against
  `results/tb_csv/` — two filters applied in sequence, each only checking its own folder.
  Moved the missing 69 files (33 `ppo_s2` + 36 `cppo_s2`) into `withdrawn_runs/`, which now
  holds 207 files (6 runs) instead of 138 (4 runs). `final_results/` and `results/tb_csv/` were
  never affected (seed 2 isn't a selected seed), so nothing that reaches the thesis was wrong —
  but this is now the second time a filter-by-one-axis approach let withdrawn data through, so
  the general rule (`withdrawn_runs/README.md`) is: filter out the withdrawn batch by run
  timestamp FIRST, before any other split, everywhere, not just in the one folder being worked
  on at the time.
- All counts verified after every move (per-seed file counts now even within each algo folder).
  READMEs updated in all three folders + this correction logged here.
- Extended the same `<algo_folder>/seed_<N>/` reorganization to the evaluation side:
  `final_results/evaluation/` (45 files) and, on request, the source
  `ur5_grasp/tools/eval_episodes/` (45 files, selected seeds only) — both now match `training/`'s
  structure. Left the training source (`results/tb_csv/`) flat, unchanged from before, so there's
  now a deliberate asymmetry (eval source organized, training source flat) — noted in
  `final_results/README.md` in case it needs revisiting later. All counts verified (3 files per
  algo/seed folder, 15 folders, 45 total, both places).

## 2026-08-02 (Day 25, night) — Chapter 1 (Introduction) drafted (Cowork)
- Read `logbook/HANDOFF.md`, `00_INDEX.md`, `CLAUDE.md`, `06_writing.md`, `11_writing_style.md`
  in full before touching anything, per the project's own onboarding convention. Verified the
  Day-25 scope lock (5 seeds, 3 arms, `ctrl` = "PPO (baseline)") against
  `Comparison_test/final_results/README.md` directly — matches HANDOFF.
- Cross-checked chapter status against the actual files rather than trusting the logbook
  summaries: em-dash counts in `11_writing_style.md` were off by one on Ch3 (8, not 9) and Ch4
  (44, not 45) — minor drift, not fixed here. `04_results.tex` confirmed to carry "ten seeds" /
  "n = 10 seeds" language at 10+ locations, matching the HANDOFF warning that it needs
  substantive re-derivation, not a wording pass.
- Asked Touhid which chapter to start on rather than assuming Chapter 4. He picked Chapter 1.
- **Wrote Chapter 1 in full** (`Thesis_LaTeX/chapters/01_introduction.tex`, 124 lines): 1.1
  Background, 1.2 Problem Description, 1.3 Objectives, 1.4 Scope. Citations against the Chapter 1
  claim map in `logbook/10_references.md`: `xia2024proactive`, `achiam2017cpo`,
  `henderson2018matters`, `khan2026rl_precision_grasping`, `khan2025csrt_ibvs`. Deliberately did
  not pull `shen2022reactive` or `altman1999cmdp` forward into Chapter 1 even though the claim
  map licenses them there, since both are already argued in full in Chapter 2 (§2.3, §2.6) and
  duplicating them looked worse than leaving a pointer. Flagged as an open call for Touhid in the
  chapter's own draftnote.
- **Finding, not fixed:** Chapter 2 §2.1 turned out to be near-verbatim the same "reserved prose"
  Chapter 1 was supposed to be drafted from, not a forward-pointer to it as
  `01_introduction.tex`'s old draftnote claimed. The two chapters now overlap in their opening
  framing paragraphs. Left as-is (surgical scope: only Chapter 1 was in scope for this session);
  flagged in Chapter 1's draftnote and here for Touhid to decide whether §2.1 gets trimmed.
- Ran the mandatory humanizer draft to audit to final loop on all new prose before saving (no
  PERSONALITY AND SOUL section per the thesis calibration; checked for AI vocabulary, boldface
  overuse, negative parallelism, vague attribution — none found). Verified
  `grep -c '\-\-\-' chapters/01_introduction.tex` = 0.
- Verified with a full `latexmk -pdf` build: 3 passes, bibtex ran twice, 0 warnings survive into
  the final pass, 48 pages (up from 47), all five new citations and all cross-references resolve
  clean.
- Updated `logbook/06_writing.md` and `logbook/11_writing_style.md` to mark Chapter 1 done.

## 2026-08-03 (Day 26) — Data migration check, font/examiner settled, Chapter 2 audit (Cowork, new account)
- First session in the new Cowork account/project. Touhid uploaded a Claude.ai data export
  (`claude_data.zip`) from the old account expecting to need to merge thesis files across
  accounts. Checked it: the zip is only `conversations.json` + `projects/*.json` (a chat/project
  export), not thesis files. Its one relevant project ("THESIS UR5e comparison") held two docs,
  `Results_Chapter_Layer1.md` and `SUMMARY_BANGLA.md` — both already present in this connected
  folder, and the local copies are *more current* than the zip's (10-seed draft vs. the local
  5-seed-aware version). Nothing imported; this folder was already ahead. Confirmed the
  connected folder (`ur5-safe-rl-thesis`) is the live, current workspace.
- Font size: confirmed 12pt by Touhid. Checked `Thesis_LaTeX/main.tex` — already
  `\documentclass[12pt,a4paper,oneside]{book}`, not the "commented, undecided" state HANDOFF
  described. No change needed; `book` class is correct for 12pt (only `extbook` would have been
  needed for 14pt).
- Board of Examiners: Touhid confirmed 2 members total (Chairman/Supervisor + one Member), not
  3. Removed the `\examiner{3}{...}` line from `frontmatter/approval.tex` and updated its
  draftnote. Examiner 2's name/designation/department are still `\todo{}` — still needed from
  Touhid, still the only hard-error blocker for a `[final]` build.
- Audited Chapter 2 against HANDOFF's claim of "done, 0 em dashes." Found that claim was wrong:
  14 em dashes in real body prose (not draftnotes) at 12 distinct lines, and the stale "ten
  independent seeds" language (pre-scope-lock) at two locations (near line 271, line 312) that
  the Day-25 scope-lock audit caught in Chapter 4 but missed in Chapter 2. Flagged to Touhid
  rather than silently fixed. Chapters 1 and 3 spot-checked clean/as-logged (Ch1: 0 em dashes,
  no stale seed language; Ch3: 8 em dashes as HANDOFF logged, no stale seed language).
- Touhid's next requests, in order: (1) guide him through downloading the cited papers so
  Chapter 2 can use real figures/data instead of metadata-only claims, (2) fix Chapter 2 (em
  dashes + seed count) and expand it — add a page before the per-source review section
  summarizing the thesis and how the reviewed papers relate to it, add more technical detail/
  data to each paper review, use figures from the papers where useful. Paper download guide
  delivered this session; Chapter 2 rewrite not yet started.
- Touhid downloaded 12 of the 20 needed papers into `Thesis_LaTeX/source_papers/` (all 3 Tier-1
  "read in full" papers plus 9 of 11 Tier-2 foundational ones). Verified each: title/authors
  match the citation, page counts sane, real figures inside (checked via `pdfinfo` +
  `pdftotext` + `pdfimages -list`), none are landing pages or corrupted downloads.
- Priorities changed: Touhid asked to fix Chapter 1 before Chapter 2. Chapter 1 requests: expand
  to at least 5 pages; add a new ~2-page section on robotic manipulators and the UR5e
  specifically (specs + a real photo, placeholder until Touhid supplies his own, logged
  somewhere trackable); expand Background into a more narrative, storytelling style while
  staying technical; leave Problem Description and Objectives untouched; enlarge Scope with
  concrete, briefly-explained sub-scopes; suggest figures from source papers but ask before
  inserting any.
- Found a strong candidate for the interim UR5e photo while scanning source papers for figures:
  `xia2024proactive` Fig. 1 is a genuine photograph (not a diagram) of a UR5e working next to a
  person in a real lab, open access under CC BY-NC-ND 4.0. Asked Touhid before using it; he
  approved using it as an interim placeholder. Extracted the embedded image directly via
  `pdfimages` (975x650, 300 dpi, not a page rasterisation) and saved it as
  `Thesis_LaTeX/figures/ur5e_platform_interim.png`.
- Verified the UR5e hardware specs before writing anything, rather than pulling them from
  memory: web search against the official Universal Robots UR5e datasheet. Payload 5 kg, reach
  850 mm, 6 revolute joints, repeatability +/- 0.03 mm, arm weight 20.6 kg, max joint speed
  180 deg/s on every joint (a second search specifically confirmed all six joints share the same
  180 deg/s ceiling, not just some). That number, 180 deg/s = pi rad/s, exactly matches this
  project's own `velocity_limit_sim = 3.14 rad/s` training ceiling (see `03c` and `09` — that
  ceiling was chosen without this cross-check at the time). Added a new bib entry
  `universalrobots2023ur5e` (Group H, new) and a claim-map row in `logbook/10_references.md` for
  both the spec claims and the interim photo, rather than citing anything outside the claim map.
- **Rewrote `chapters/01_introduction.tex`.** New §1.1 "The UR5e Manipulator and This Thesis"
  (manipulators in general, narrowing to the UR5e's specs and why this platform was chosen, the
  interim photo as a `kuetfigure`). §1.2 Background (renamed from the old §1.1) expanded with a
  concrete worked example, the UR5e's own joint-speed limit used as the illustration of the
  reward-weight-vs-constraint-budget problem, rather than staying fully abstract. Problem
  Description and Objectives copied through unchanged. Scope gained two new bullets, Algorithms
  (established methods only, no new optimiser proposed) and Hardware validation (simulation
  only, explicitly no physical-UR5e run in this deliverable). Ran the mandatory humanizer draft
  → audit → final loop before saving (audit found two minor smoothing edits, no AI-vocabulary or
  rule-of-three issues; PERSONALITY AND SOUL section correctly not applied per the thesis
  calibration). Verified `grep -c -- '---' 01_introduction.tex` = 0 and no `—`/`–` characters.
- Full `latexmk -pdf` rebuild: exit 0, 50 pages total (was 48), 0 undefined citations/refs, new
  figure renders correctly, captioned and centred per the `kuetfigure` convention. Chapter 1 now
  spans 6 pages (was 3; Chapter 2 now starts on page 7, was page 4). Visually inspected the
  rendered pages (title page, chapter opening, the photo page) to confirm layout, not just a
  clean exit code.
- Logged the photo-pending status in two places per Touhid's request: a draftnote at the top of
  `01_introduction.tex`, and a new `Thesis_LaTeX/figures/README.md` with swap-in instructions
  for when he supplies his own UR5e photograph.
- Updated `logbook/06_writing.md`'s Chapter 1 line and `logbook/10_references.md`'s claim map
  (two new rows) to match.
- Not yet started: Chapter 2 (em dashes, stale seed count, the new pre-review summary page,
  expanded per-paper reviews with figures from `source_papers/`).

## 2026-08-03 (Day 26, cont.) — Chapter 1 second pass: heading removed, wider Scope, bulleted problems
- Touhid asked for four changes before Chapter 2: drop the "§1.1" heading from the new platform
  section (unheaded opening paragraphs instead), add a paragraph on where UR5e-class arms are
  actually used, make Problem Description's two core issues more scannable, and make Scope
  "wider" using the original three-layer proposal, with a nod to IBVS and to cPPO-safety as a
  broader robotics practice, not just this thesis's own boundary statement.
- Asked before writing per his request. Two questions: (1) convert Problem Description to a
  bullet list or keep prose and add a bullet summary on top — he chose convert; (2) how far
  Scope should reach into IBVS/cPPO-in-robotics territory, given it risks duplicating Chapter 2
  (Lit Review) and Chapter 6 (Future Works, which already owns "IBVS and sim-to-real are future
  work") — he chose scope-appropriate depth, no new citations, reusing sources already in
  `references.bib` (`khan2025csrt_ibvs`, `xia2024proactive`, `khan2026rl_precision_grasping`)
  rather than sourcing Shi 2020 / Zhang 2023 from the original proposal.
- Removed the `\section{...}` line for the platform material; it now reads as unheaded opening
  paragraphs directly under `\chapter{Introduction}`. Sections renumber automatically in LaTeX
  (Background 1.1, Problem Description 1.2, Objectives 1.3, Scope 1.4), no manual renumbering
  needed, and nothing else in the document referenced the old numbers directly (checked before
  editing).
- Added a paragraph on real-world UR-class deployment (pick-and-place, machine tending,
  small-parts assembly/packaging, inspection) and why the same collaborative certification makes
  it a common research platform too, grounded in the two already-cited papers that use UR5-class
  hardware (`ferreira2025grasping`, `xia2024proactive`) rather than inventing statistics.
- Converted Problem Description's "First.../Second..." prose into a two-item bulleted list, "The
  cost-critic confound" and "Seed variance," keeping the surrounding framing and closing
  paragraphs as prose per Touhid's chosen option.
- Rewrote Scope's opening: states the full originally registered title for the first time in the
  book, describes concretely what Layer 2 (RL-tuned image Jacobian visual servoing, replacing
  privileged pose with eye-in-hand RGB-D) and Layer 3 (ROS 2 transfer, RH-P12-RN gripper gap)
  would have covered, and adds one positioning sentence on constrained RL as existing robotics
  practice, not just this thesis's approach, citing only sources already in the bibliography.
- Self-audited the draft against the humanizer checklist before the formal pass: found the new
  material had piled up five "is not X" / "not X but Y" contrastive constructions in close
  proximity (a negative-parallelism tell), concentrated in the new UR5e-usability paragraph.
  Rewrote two of them to plain positive statements before finalizing; left two earlier,
  already-approved instances alone since they weren't part of the new cluster and read fine in
  isolation.
- Ran the humanizer draft → audit → final loop, verified `grep -c -- '---' 01_introduction.tex`
  = 0 and no `—`/`–` characters, before saving.
- Rebuilt (`latexmk -pdf`): exit 0, 50 pages total (unchanged net, heading removal offset the
  added prose), 0 undefined citations/refs. Chapter 1 still spans 6 pages (1–6, Chapter 2 starts
  page 7, same as the previous pass). Visually inspected the opening page (heading gone, flows
  straight into paragraphs), the Problem Description bullets, and the renumbered Objectives/Scope
  headings (1.3, 1.4) to confirm the auto-renumbering landed correctly, not just a clean exit
  code.
- Chapter 2 still not started.

## 2026-08-03 (Day 26, cont.) — Chapter 1 figure placement fixed (Cowork)
- Touhid asked for the UR5e photo to sit at the bottom-middle of the page instead of inline
  right after the paragraph it follows.
- Parameterised `thesis-format.sty`'s `kuetfigure` environment with an optional placement
  argument, default `htbp` (backward compatible, every other `kuetfigure` call in the book is
  unaffected). First attempt used `[b]` alone; rebuilt and the figure drifted to the very last
  page of the chapter (physical page 19, chapter-page 7) instead of near where it's written,
  because the image plus caption is taller than LaTeX's default `\bottomfraction` (30% of text
  height), so a plain `[b]` float can never satisfy the fit check on the page it's meant for and
  gets deferred until the `\clearpage` at the next chapter forces it out. Fixed by using `[!b]`
  instead, the `!` overrides the fraction restriction for this one float. Rebuilt: the figure now
  lands at the bottom of chapter-page 3 (physical page 15), directly under the paragraph that
  precedes it, caption below, centred, not drifted.
- Note for later, not acted on: `Thesis_LaTeX/chapters/02_literature_review.tex` and
  `Thesis_LaTeX/figures/README.md` grew substantially during this window (Chapter 2 now 991
  lines with real figures pulled from `source_papers/` and several `kuettable`s), which is not
  work done in this session. Total book page count is now in the 60s. Not investigated further
  since it isn't part of the current task; flagging only so the next session doesn't mistake it
  for drift.

## 2026-08-03 (Day 26, cont.) — Figure drift into §1.1 fixed
- The `[!b]` fix from the previous entry let the figure land bottom-of-page, but LaTeX's normal
  float queue let it drift past the paragraph it was written after: it ended up on the same page
  as, and visually below, the "1.1 Background" heading, reading as if the photo belonged to
  §1.1. Touhid caught this and also wanted it moved earlier, roughly 2 paragraphs up from where
  it was (it was sitting after the third of four opening paragraphs).
- Fixed by switching to `[H]` (the `float` package's exact-position specifier, already loaded in
  `thesis-format.sty`) instead of `[!b]`, and moving the `kuetfigure` block to right after the
  first opening paragraph instead of the third. `[H]` cannot drift, the float package inserts it
  exactly at that point in the source, so it is now provably inside the unheaded starting
  section and nowhere near §1.1 regardless of how the rest of the chapter reflows.
- Trade-off, not yet re-confirmed with Touhid: `[H]` renders at the top of chapter-page 2 rather
  than the bottom of a page, because there was not quite enough remaining room on page 1 after
  the first paragraph for LaTeX's page-breaker to fit the figure there too, so it starts the next
  page instead. This satisfies "inside the starting section, moved up," the more urgent fix, but
  does not exactly reproduce the earlier "bottom of the page" framing. Flagged to Touhid rather
  than iterating further blind.
- Rebuilt: exit 0, 0 em dashes, Chapter 1 back to 6 pages (1-6, Chapter 2 starts page 7).
  Verified by rendering the actual pages, not just checking the exit code: page 1 ends mid-page
  after the first paragraph with nothing below it, page 2 opens with the figure at the top,
  captioned, centred, followed immediately by the specs paragraph.

## 2026-08-03 (Day 26, cont.) — Chapter 1 audit and correction pass
- Touhid asked for a full read of Chapter 1 with opinions before any further edits. Read the whole
  chapter, checked every factual claim against `CLAUDE.md`'s locked results scope, and
  cross-checked against Chapters 2 and 4. Reported findings ranked by severity; he approved
  fixing items 1, 2 and 4.
- **Item 1, the significant one: Chapter 1 contradicted itself about its own experiment.** §1.2
  Problem Description described the three arms as {unconstrained baseline, control arm with
  multiplier at zero, fully constrained agent}. §1.4 Scope described them as {unconstrained PPO
  baseline, two PPO-Lagrangian variants at different budgets}. Two different sets of three, four
  pages apart. §1.4 matched the scope lock (`ctrl` / `cppo` d=25 / `cppo15` d=15, 5 seeds); §1.2
  was carrying the older pre-lock design. Neither §1.2 nor the Objectives mentioned the second
  cost budget at all, which is a third of the delivered experiment.
- Rewrote §1.2's closing so it explains *why* the control arm exists without committing to an arm
  count, names both budgets (25 and 15), states five seeds, and then records that the control arm
  reproduced the unconstrained baseline exactly at the level of stored weights, so the two collapse
  into one reported arm. That last point matters editorially: the collapse is a *result*, not a
  design choice, and the previous text hid it. Added forward pointers to
  `Chapter~\ref{ch:results}` and `Section~\ref{sec:r-validity}`.
- **Item 2: Objectives did not match the delivered scope.** Replaced "multiple independent random
  seeds" with five, added an objective covering the two cost budgets, and added a final
  outcome-framed objective ("whether the constraint changes the average safety outcome, the spread
  across runs, or both") since all four originals were activity-framed ("To implement, To isolate,
  To train, To evaluate") and none said what would count as an answer.
- **Item 4, cleanup:** `pi` written as a word is now `\(\pi\)` rad/s (renders correctly, and
  matches the `180 deg/s (π rad/s)` row that Chapter 3's UR5e spec table independently uses);
  added a clause in §1.4 explaining that the book's title is narrower than the registered title
  because the delivered work is narrower; rewrote four low-value "not X" constructions positively
  (negative-construction count 24 to 21, leaving the load-bearing contrasts alone).
- **Consistency verified against Chapter 3**, which was written in a separate session while this
  audit was running. Its Table 3.11 and footnote give the same three arms, same budgets, same five
  seeds, same "plain PPO trained but byte-identical to `ctrl`, so not reported separately" story,
  and point at the same `sec:r-validity`. Chapter 1 and Chapter 3 now agree.
- Humanizer draft → audit → final loop run on all new prose. The audit caught two ornate spots in
  my own draft ("how hard a budget binds is itself a variable worth separating from whether a
  budget exists at all", an aphorism-shaped restatement, and "returns a measured value of zero",
  contorted) and both were simplified before saving.
- Builds verified in **both** modes, not just draft: `[draft]` exit 0, 78 pages; `[final]` exit 0,
  Chapter 1 = 6 pages (physical 14-19), figure on chapter page 1. 0 undefined citations or
  references in either. Rendered pages inspected to confirm the new §1.2 prose, the renumbered
  Objectives and the π glyph all typeset correctly.
- **Reported but NOT fixed, per surgical-scope rule:** (1) Chapter 2 §2.2 still duplicates
  Chapter 1 §1.1's opening argument almost beat for beat (classical controller inspectable, RL
  policy not, rare configurations are the condition deployment depends on). Needs a decision about
  which chapter keeps it. (2) Chapter 4 still says ten seeds and names a `ppo` arm, so it now
  disagrees with both Chapter 1 and Chapter 3; fixing Ch1 alone just moved the contradiction
  downstream. (3) Flagged `approval.tex`'s examiner 2 as blank-and-silently-passing the `[final]`
  build; `logbook/06_writing.md` shows this is a deliberate hand-completion decision, so no action
  needed.

## Day 26 (2026-08-03) — Chapter 2 rewritten from the source PDFs
- Read all 12 PDFs in `Thesis_LaTeX/source_papers/` properly (pdftotext + page renders), rather
  than working from metadata. That is what unlocked real numbers and real figures for Chapter 2,
  and the reading-status table in `logbook/10_references.md` was updated to match: 12 entries move
  from "metadata only" to "PDF held and read".
- **Rewrote `chapters/02_literature_review.tex`.** Ten sections became twelve. New §2.1 "How to
  read this chapter" (argument in one paragraph, four-movement structure, three reading routes,
  §-to-source map table, and a boxed seven-point key-findings preview). New §2.8 "Experimental
  methods of the reviewed studies" with a side-by-side apparatus table for all eight experimental
  papers plus this thesis. §2.9 (manipulability) rebuilt around Yoshikawa's actual development:
  the Jacobian velocity relation, rank deficiency as the definition of singularity, w = √det(JJᵀ),
  the SVD form w = σ₁…σ_m, the manipulability ellipsoid, the m = n reduction to |det J|, and the
  two-link worked example w = ℓ₁ℓ₂|sin θ₂| with best posture θ₂ = ±90°, then the joint-speed
  normalisation and why a small w becomes a large joint rate on a real UR5e. §2.10 (seed variance)
  rebuilt around Henderson's own 2×5-seed split (t = −9.0916, p = 0.0016) and his bootstrap CI
  table, set against the seed counts actually reported by the reviewed papers. §2.11 gaps recast
  as two coloured boxes with the decomposition identity written out. §2.12 summary rewritten as a
  continuous narrative retracing the argument, then stating the scope boundaries explicitly.
- **Four figures reproduced from the source PDFs** into `Thesis_LaTeX/figures/`, extracted at
  400 dpi (or via `pdfimages` where the source was an embedded raster), each credited in its
  caption: Stooke Fig. 1 (Lagrangian vs PID oscillation), Ferreira Fig. 1 (UR5 + 2F-85 PyBullet
  scene, CC BY), Shen Fig. 12 (manipulability landscape with GPM vs RL paths, CC BY), Henderson
  Fig. 5 (the two-groups-of-five-seeds plot). Licence audit and the two figures rejected on
  licence grounds are recorded in `Thesis_LaTeX/figures/README.md`.
- Eight tables and ten display equations added. The equations are PPO's clipped surrogate, the
  CMDP problem, the Lagrangian relaxation, CPO's constrained trust-region step, Stooke's PID
  multiplier rule, Yoshikawa's w in four forms, Shen's null-space and reward equations, and
  Ferreira's shaped reward. Tables carry Ray's Safety Gym normalised metrics, Shen's GPM
  comparison, Henderson's bootstrap intervals, Khan's PPO-vs-cPPO results, the cross-study
  apparatus comparison, and a positioning matrix.
- **Fixed the stale "ten independent seeds" language** at both places flagged on 2026-08-02.
  Chapter 2 now says five seeds (1, 3, 4, 52, 54) per the locked scope. **Chapter 4 still says ten
  and still has not been re-derived** — that gap is now visible between two chapters of the same
  book, so it needs clearing before submission.
- Mandatory humanizer loop run before saving. Audit found and fixed: 4 em dashes (all in comments
  and the draftnote), 2 negative parallelisms ("not only its average"), one AI-coded abstract noun
  ("the benchmarking landscape has since consolidated"), one broken sentence ("What none of those
  results is a bound"), one staccato pair, and 11 of 28 uses of "rather than" thinned out.
  Verified: `grep -c -- '---'` = 0, no unicode em/en dashes, no "not only/just/merely".
- Build: `latexmk -pdf` exit 0, 65 pages total, 0 errors, 0 undefined citations or references,
  19 bibitems. Chapter 2 spans pp. 20–41. Table overfulls fixed with `raggedright` p-columns and
  tighter `tabcolsep`; the large remaining overfull boxes in the log all belong to other chapters'
  draftnotes (long file paths) and vanish in `[final]`. Rendered and visually checked the
  key-findings box, the gap boxes, the comparative table and all four figure pages.
- **Open, for Touhid to decide:** Chapter 2 is 22 pages against the 14–16 he chose. Nothing is
  padding, but §2.8 and the Henderson bootstrap table are the cheapest ~3 pages to cut if the
  book total needs to come down.
- **Later the same day, on Touhid's instruction: all colour and all framing removed from
  Chapter 2.** The `keybox` mdframed environment (blue rule + 4 % tint) is now an empty
  environment that only adds vertical space, `\gapmark` is plain bold instead of amber, and the
  two `\definecolor` declarations are deleted. The key-findings block and the two gap statements
  now read as plain black text with bold run-in headings. Verified with
  `grep -n "color\|mdframed\|linecolor\|backgroundcolor\|fbox\|rule{"` on the chapter: zero hits.
  Table `\hline` rules are kept, since they are the KUET table convention and not decoration.
  Rebuild: exit 0, 65 pages, 0 errors, 0 undefined. Chapter 2 now spans pp. 19–41 of the PDF
  (body pp. 7–29, 23 pp.) — one page more than the boxed version, because the frames had been
  packing the text slightly tighter.
- Still coloured and framed, but **only in the `[draft]` build**: the red `draftnote` boxes
  defined in `thesis-format.sty`. They are excluded by `\excludecomment` under `[final]`, so they
  never reach the printed book. Left alone rather than changed, since editing the `.sty` touches
  every chapter.

## Day 26 (2026-08-03, Cowork) — Chapter 3 written: §3.3 software framework, gradient-clip audit, frozen values, 8 citations

- **New §3.3 "Software framework"** (the draftnote's "3.2", inserted after the environment section
  so it numbers as 3.3; the chapter was NOT regrouped under three headings, that would have been a
  restructure nobody asked for). Contents: the `ur5_grasp` package rationale (installed beside
  Isaac Lab, so a run is reproducible against one tagged commit), Table 3.1 mapping all 13 modules
  to their roles, the cost computer (cached index resolution, batched, no host sync at 4096 envs),
  the four `safe_rl/` modules that extend `rsl_rl`, and the two-script train/eval pipeline with the
  dumped-config comparison trick.
- **New §3.3.1 "The gradient-clip audit"** — the Day-23 withdrawal now has its own room in the
  Methods chapter instead of being squeezed into §4.2. Narrates: `Loss/cost_lambda` at 0.0 →
  the update was algebraically stock PPO → one global `clip_grad_norm_` spanning the cost critic
  shrank the actor's step on every update → cPPO was PPO with a quieter optimiser. Also the 100-slot
  Jc buffer against 4096 simultaneous terminations, and the never-binding budget. Then the fix
  (two-group clip, resized buffer, `test_grad_clip_fix.py`'s three checks) and why the `ctrl` arm
  had to exist. §4.2's "assumes Chapter 3 sets this up" is now satisfied.
- **Every stale Day-19 number replaced with the frozen `matrix-v2` values** (Touhid's call:
  frozen values only, no two-stage narrative). Goal box (0.4/0.6…) → (0.22,0.60)/(-0.30,0.30)/
  (0.10,0.50) with the 0.84 m reach-margin justification; reward weights 15/16 → 10/15 and the lift
  gate now goal-relative; `JOINT_LIMIT_MARGIN` 0.10 → 0.175 rad; `COLLISION_Z_FLOOR` 0 → 0.05 m;
  `MANIP_FLOOR` 0.045 → 0.06. §3.6 rewritten off `calib_probe_v2`: w distribution min .0171 /
  mean .0750 / max .1109, p10 .0517 / p25 .0682, floor at ~p18; joint-limit now an ACTIVE
  constraint at 33.7 % of steps and ~86 % of natural cost; collision inactive at 0.0896 m min
  height; natural episodic cost ~105, so d = 25 is a ~76 % cut, not the ~⅔ the Day-9 text claimed.
  §3.8 rewritten for `eval_policy.py`: frozen deterministic policy, corruption off, 1000 episodes ×
  eval seeds 101/102/103 × 128 envs, distance distribution reported instead of a lone 1 cm
  threshold (weld ceiling), per-episode safety counts.
- **New §3.7.1 "Experimental arms and seeds"** — 3 arms, 5 seeds (1, 3, 4, 52, 54), and the
  CLAUDE.md-mandated one-time footnote explaining that `ctrl` is reported as "PPO (baseline)",
  pointing at §4.2 and `Comparison_test/ppo_redundant/README.md`.
- **8 citations added per the claim map**: `altman1999cmdp` (§3.1 first sentence), `mittal2023orbit`
  + `makoviychuk2021isaacgym` (§3.2 platform and the 4096-env justification), `rudin2022walk`
  (§3.2, §3.3, and again at the audit), `elguea2023review` (reward design as conventional),
  `schulman2017ppo` + `ray2019benchmarking` + `achiam2017cpo` (§3.5, with Ray's CPO-vs-Lagrangian
  result as the stated reason for choosing PPO-Lagrangian), `henderson2018matters` (§3.7.1, at
  n = 5). `yoshikawa1985manipulability` left exactly as it was. Those three tooling entries were
  the last uncited entries in `references.bib`.
- Table M1 (bold body text + uncaptioned `longtable`) → real `kuettable` float, now Table 3.2 in
  the List of Tables alongside the new Table 3.1.
- Humanizer pass on all new prose (draft → audit → final). Own-draft audit caught three "-ing"
  tails, one copula avoidance, two filler phrases, one inherited "Crucially", and 11 em dashes.
  Verified `grep -c -- '---' chapters/03_methodology.tex` = **0** (was 8).
- Build: `latexmk -pdf` exit 0, **70 pages** (was 65), 0 errors, 0 undefined citations, 0 undefined
  references, 0 overfull boxes in Chapter 3. Rendered pp. 42–52 of the PDF to PNG and read them
  rather than trusting the exit code; caught and fixed two things that way (the §3.6 opener still
  said "both" thresholds after the section had grown to three, and the module table needed
  0.44/0.44 columns). Chapter 3 now spans body pp. 30–40.
- Claim map corrected: `logbook/10_references.md`'s Chapter 3 `henderson2018matters` row said
  "cite where n = 10 is set". Stale — the locked scope is 5 seeds. Row rewritten and dated.

**Flagged, NOT fixed (out of the scope Touhid set for this session):**
1. Chapter 2 §2.9.1 and Chapter 4 both refer to the manipulability floor being "recalibrated from
   0.045 to 0.06". Chapter 3 now states 0.06 as the operative value and mentions the 0.045
   predecessor in one clause of §3.6 so those two cross-references still land. If the two-stage
   calibration story is wanted in full, it belongs in §3.6 and is a paragraph, not a clause.
2. `04_results.tex` still says ten seeds, names the arms `ppo`/`ctrl`/`cppo`, and quotes 30,000
   episodes per arm. Chapter 3 now says five seeds, `ctrl`/`cppo`/`cppo15`, 15,000 episodes.
   The two chapters currently disagree. Chapter 4's re-derivation is the fix and is still open.
3. Chapter 4 Table 4.1 lists `MANIP_FLOOR` 0.06 as "recalibrated from 0.045" and describes the
   joint-limit margin as "reclassified active" — both now consistent with Chapter 3, so no change
   needed there beyond the seed count.

## Day 26 (2026-08-03, cont.) — supervisor corrected; Board of Examiners blocker CLOSED

- **Supervisor corrected** in `Thesis_LaTeX/frontmatter/_thesis_details.tex`, which is the single
  source all front-matter pages read from. Was `Dr.\ Md.\ Helal-An-Nahiyan`, Professor, Department
  of Mechanical Engineering. Now **Priyo Nath Roy, Assistant Professor, Department of Mechatronics
  Engineering.** Touhid's call on the honorific: plain name, no `Dr.`/`Mr.` prefix. Propagates
  automatically to the title page, the declaration and Examiner 1 on the approval page.
- **Board of Examiners: member 2 left deliberately blank.** Not announced yet, so
  `\examiner{2}{\todo{name}}{\todo{designation}}{\todo{department}}{Member}` became
  `\examiner{2}{}{}{}{Member}`. The block still prints its signature rule and the Name /
  Designation / Department / KUET labels, so the examiner can complete it by hand.
- **This closes the last hard-error blocker in the book.** `HANDOFF.md` and `06_writing.md` both
  said the six `\todo{}` markers in `approval.tex` were the only thing failing the `[final]`
  build. Verified by building a throwaway copy with `[final]` substituted for `[draft]`:
  **exit 0, 68 pages, 0 errors, 0 undefined citations, 0 undefined references.** The scratch
  `_finaltest.*` files were deleted afterwards; `main.tex` is untouched and still on `[draft]`.
- Rendered and read the approval page and the title page from the `[final]` PDF rather than
  trusting the exit code. Both correct.
- `[draft]` build re-verified after the cleanup: exit 0, 70 pages, 0 undefined.

**Flagged, not fixed:** the title page still shows an empty framed box labelled `monogram` where
the KUET logo belongs. Pre-existing, unrelated to this change, and it will print as an empty
rectangle if it reaches submission.

## Day 26 (2026-08-03, cont.) — KUET crest added to the title page

- Touhid supplied the KUET logo; saved as `Thesis_LaTeX/figures/kuet_monogram.png` (1762 × 2000 px,
  transparent). No LaTeX change was needed: `frontmatter/titlepage.tex` already tried
  `figures/kuet_monogram.pdf`, then `.png`, then fell back to an empty `monogram` framebox. The
  file simply had never been supplied.
- **Trap worth remembering:** the first rebuild after copying the file still printed the empty
  placeholder. `latexmk` saw no changed source and skipped the run entirely, because a file
  probed by `\IfFileExists` and NOT found leaves no trace in `.fls`/`.fdb_latexmk` for the
  dependency tracker to invalidate. `latexmk -pdf -g` (force) fixed it. Anytime a file is added
  that an `\IfFileExists` fallback was previously missing, force the rebuild or the PDF will
  silently keep the old branch. Verified by rendering the page, not by the exit code, which was
  0 in both cases.
- Rebuilt and visually checked: crest renders at 28 mm, colours correct, Bengali text legible.
  `[draft]` exit 0, 70 pages, 0 undefined. `[final]` re-tested on a throwaway copy: exit 0,
  68 pages, 0 undefined, scratch files deleted.
- Cover page deliberately left text-only, matching `KUET_FORMAT_SPEC.md` section 7 as measured
  off the accepted book. `figures/README.md` updated with the crest's provenance and the note
  that dropping in a vector `kuet_monogram.pdf` would take precedence with no code change.

## Day 26 (2026-08-03, cont.) — Chapter 3 expanded: preliminaries, six tables, key-point blocks

Chapter 3 goes from 11 pages to **20** (body pp. 30–49). Book is 80 pages `[draft]` / 78 `[final]`.

- **New §3.1 Preliminaries**, four sub-sections, ~3 pages. Scoped as tools-and-platform on Touhid's
  choice, NOT as a second literature review: §3.1.1 Isaac Sim and Isaac Lab (USD assets, PhysX,
  GPU-resident stepping, the manager-based design that makes the Franka→UR5e retarget a config
  swap); §3.1.2 reinforcement learning with the on-policy/off-policy distinction and **why this
  study is on-policy** (samples are cheap at 4096 envs, so the sample efficiency an off-policy
  method buys has nothing to pay for itself with); §3.1.3 PPO's three relevant mechanics and cPPO
  stated as "PPO plus three additions and no other change"; §3.1.4 the UR5e with Table 3.1 tying
  each spec to the modelling decision it drives. Each section points at Chapter 2 for the argument
  and the evidence rather than restating them.
- **§3.2 Problem formulation roughly tripled.** Full MDP tuple with every element named, then three
  properties of Eq. 3.1 stated explicitly so the results are not over-read: the constraint binds an
  **expectation not a maximum** (`brunke2022safe`, and Ch. 4 has the counter-result where the worst
  single episode is no better under the constraint), the cost is **undiscounted and episodic** so d
  is tied to the 5 s episode length, and the budget is **one scalar over three summed hazards** so
  the agent may trade between them and no per-hazard guarantee is available.
- **Six tables, all captioned floats, all in the List of Tables:** 3.1 UR5e specs, 3.2 simulation
  environment summary (16 rows), 3.3 `ur5_grasp` package, 3.4 shared hyperparameters, 3.5 training
  protocol, 3.6 evaluation protocol.
- **Nine "Key points" blocks**, one closing each section. Plain bold run-in heading + itemize, no
  frame and no colour, matching the de-coloured Chapter 2 style Touhid set on 2026-08-02.
  Environment is named `keypoints`, deliberately **not** `keybox` — Chapter 2 already defines that
  name locally and a second `\newenvironment` would have been a hard error, since both files are
  input into one document.
- **Sub-section headings are now bold italic** (`thesis-format.sty`, `\titleformat{\subsection}`
  and `\subsubsection`). This is a **deliberate deviation** from the measured KUET template, which
  has plain italic. Recorded as deviation **D1** in `KUET_FORMAT_SPEC.md` with the one-word revert
  instruction. Applies book-wide; Chapter 2's two sub-sections are affected too. **Worth confirming
  with Priyo Nath Roy before the submission build.**
- **`kuettable` now takes an optional placement argument**, same as `kuetfigure`:
  `\begin{kuettable}[H]{caption}{label}`, default `htbp`, existing two-brace calls unaffected.
  Added because the training-protocol table floated INTO its key-points list and split it, leaving
  an orphan bullet with no heading on the next page. Same float-drift class as the Chapter 1 figure
  bug. Tables 3.2, 3.4, 3.5 and 3.6 now use `[H]`; 3.1 and 3.3 float fine and were left alone.
- **Three claim-map rows added** to `logbook/10_references.md` before the sentences were written,
  per the standing rule: `universalrobots2023ur5e` extended to Ch. 3 (specs table, numbers must
  match Ch. 1 exactly), `shahid2022continuous_grasping` for the existence of both algorithm
  families (**not** for any SAC number), `brunke2022safe` for the expectation-not-worst-case
  caveat. All three were already licensed elsewhere in the book; these rows extend them.
- Humanizer pass on all new prose. Verified `grep -c -- '---'` = 0, 0 overfull boxes in Chapter 3.
- Builds: `[draft]` exit 0, 80 pp., 0 undefined. `[final]` exit 0, 78 pp., 0 undefined. Rendered
  pp. 43–63 and read them; the split key-points list was caught that way, not by the exit code.

## Day 26 (2026-08-03, cont.) — Chapter 3 restructured: platform section, RL taxonomy figure, PPO maths

Chapter 3 is now **pp. 30–55 (26 pp.)**. Book 87 pp. `[draft]` / 85 `[final]`, both exit 0,
0 undefined, 0 overfull boxes in Ch. 3, 0 em dashes.

- **"3.1 Preliminaries" heading deleted** on Touhid's instruction. Its framing paragraph is now
  unheaded plain text under the chapter title, and its four sub-sections were promoted to full
  sections. New order: 3.1 Simulation environment: Isaac Sim and Isaac Lab · 3.2 Reinforcement
  learning, on-policy and off-policy · 3.3 Proximal policy optimisation · 3.4 The UR5e manipulator ·
  3.5 Problem formulation · 3.6 The grasping task · 3.7 Software framework · 3.8 Cost function ·
  3.9 cPPO · 3.10 Calibration · 3.11 Training protocol · 3.12 Evaluation protocol.
- **Renaming forced by the promotion, flagged rather than silent:** the old §"Simulation environment
  and task" would have collided with the new §3.1. It is now **§3.6 "The grasping task"**, and its
  opening paragraph was rewritten because it duplicated the platform description that has moved to
  §3.1. Label `sec:m-env` unchanged, so no cross-reference broke.
- **§3.1 now carries the exact stack and the clone commands.** New Table 3.1: Isaac Sim 5.0.0,
  Isaac Lab 2.3.0 pinned to the **`v2.3.0` tag**, `rsl_rl` 3.0.1, `skrl` 2.1.0, Python 3.11,
  PyTorch 2.7.0+cu128, CUDA 12.8, RTX 5090 (sm_120), driver 580, i9/64 GB. Prose explains that
  PyTorch 2.7 and the 570+ driver are Blackwell *requirements*, and reproduces the Day-8 tag-vs-
  branch bug (the `release/2.3.0` branch moved to 2.3.1, which exact-pins URDF importer 2.4.31
  against the shipped 2.4.19, crashing start-up). Both clone commands given verbatim, plus the
  `567e4c0` / `matrix-v2` provenance line.
- **New Figure 3.1: RL taxonomy**, model-free vs model-based, policy optimisation vs Q-learning,
  with the DDPG/TD3/SAC interpolation group and PPO set in bold. **Drawn in TikZ, not downloaded** —
  image fetching is not available to this session, and redrawing a factual taxonomy avoids
  reproducing OpenAI's artwork. The caption says explicitly that it is an original rendering.
  `tikz` + `positioning` + `arrows.meta` added to `thesis-format.sty`. First attempt had the three
  right-hand leaf boxes overlapping (DDPG box struck through TRPO and DQN); fixed by respacing the
  y-coordinates, caught by rendering the page.
- **New Table 3.2: on-policy vs off-policy**, eight rows, with algorithm examples both sides and a
  final row stating which family this thesis uses.
- **§3.3 PPO expanded from one paragraph to four sub-sections with the mathematics:** Eq. 3.1 the
  policy-gradient estimator and why ascending it directly fails; Eq. 3.2 the probability ratio;
  Eq. 3.3 the clipped surrogate with the asymmetric-behaviour explanation and why the min makes it a
  pessimistic bound; Eqs. 3.4–3.5 the TD residual and GAE; Eq. 3.6 the full three-term objective with
  this project's actual coefficients (eps 0.2, c1 1.0, c2 0.006, 5 epochs x 4 minibatches, adaptive
  LR at target KL 0.01). Closes with §3.3.4 stating that cPPO changes exactly one quantity, the
  advantage.
- **Notation clash found by reading the rendered page and fixed:** the GAE parameter and the
  Lagrange multiplier are both conventionally lambda, and Ch. 3 now uses both. GAE's is written
  `\lambda_GAE` throughout §3.3 with an explicit sentence that an unsubscripted lambda always means
  the multiplier from §3.9 onward.
- **New source, entry 23: `achiam2018spinningup`** (OpenAI Spinning Up). Verified from the
  publisher page: (c) 2018 OpenAI, author Joshua Achiam, the same author as `achiam2017cpo`. Claim-map
  row added **before** the sentences were written, restricting it to the taxonomy and the
  on-policy/off-policy framing, never a numerical claim and never as any algorithm's origin. PPO's
  origin stays `schulman2017ppo`.

## Day 26 (2026-08-03, cont.) — Chapter 3 shortened: 26 pp -> 24 pp

Touhid asked for the chapter to be cut. Proposed the options with measurements rather than guesses;
he approved cut D (gripper diagnosis + PPO preamble), "make tables rather than just descriptions",
then in a second round single-spaced tables, removal of prose that repeats a table, and condensing
the audit. **He declined to remove the 12 Key points blocks**, twice. They stay.

**Round 1, prose -> tables. Honest result: page-neutral.** Converted \S3.6.1 state/action/reward
into two tables (observation/action/episode, and reward terms), \S3.8's three cost terms into one
table with a Status column naming which are active, \S3.10's calibration measurements into a
measured/outcome table, and \S3.11.1's arms into a table with the "PPO (baseline)" footnote attached
via `\footnotetext`. Measured before and after: 9,456 -> 9,576 words, 26 pp -> 26 pp. Prose outside
tables fell from ~8,000 to 6,763 words but table markup and 1.5-spaced table rows gave it all back.
Reported this to Touhid rather than claiming a saving.

**Round 2, what actually worked:**
- **Tables are now single-spaced at 11 pt**, not the body's 1.5 spacing (`\tablesize` in
  `thesis-format.sty`). Standard thesis practice, zero content lost, applies book-wide, and it helps
  Chapter 4 more than Chapter 3 because Ch. 4 is table-heavy.
- **Prose that repeated a table was cut** in \S3.4 (UR5e), \S3.7 (the four `safe_rl` modules walk-
  through, keeping only the two attachment details that matter later), \S3.11 (training settings) and
  \S3.12 (the episode/seed enumeration). What survived in each case is the argument a table cannot
  carry, e.g. why evaluation seeds are disjoint and why goal-reach needs a distribution.
- **\S3.7.1 audit condensed** 696 -> ~290 words, pointing at \S4.2 for the full narrative.
- **Cut D applied:** gripper-fault diagnosis reduced to one paragraph (the 84.4 mm and nine-body
  detail is appendix material), \S3.3.1 "The problem PPO solves" folded into two sentences.

**Net: Chapter 3 pp. 29–52 (24 pp, was 26). Book 84 pp `[draft]` / 82 `[final]`, was 87/85.
9,025 words, was 9,576. 0 undefined, 0 em dashes, 0 overfull boxes in Ch. 3.**

**Two layout traps hit and fixed, both caught by rendering not by the exit code:**
1. `[H]` on nearly every table forced half-page whitespace gaps. Relaxed `tab:m-stack`, `tab:m-mdp`,
   `tab:m-reward`, `tab:m-cost` and `tab:m-calib` back to floating; `[H]` kept only where a table
   sits immediately before a Key points list, which is the case it was introduced for.
2. Two overfull boxes (85 pt and 48 pt) from unbreakable `\texttt{}` script paths in the rewritten
   paragraphs. Fixed by dropping the filenames, which the \S3.7 package table already lists.

**Still available if more length has to come out, in order of value:**
- The 12 Key points blocks: 1,284 words, ~3.5 pp, pure restatement of prose on the same page. Could
  also become a single chapter-end summary instead of twelve per-section blocks.
- Chapter 2 is 22 pp against the 14–16 Touhid chose; \S2.8 and the Henderson bootstrap table are the
  cheapest 3 pp in the book.
- **Third pass on Chapter 2, same day: cut from 23 pages to 18, and the research gap turned
  visual.** All twelve sections kept. Prose tightened throughout (§2.5 and §2.7 hardest hit),
  the Henderson bootstrap table dropped and replaced by one sentence carrying the HalfCheetah
  interval, and the summary cut from eight paragraphs to five.
- **New Figure 2.5, `figures/lit_arms.pdf`** — the first original figure in this chapter, black
  line art only, no colour or fill. Three boxes (PPO baseline / ctrl / cPPO) with what changes
  between each pair, a brace above spanning the difference prior work reports, and two braces
  below splitting it into the implementation term and the constraint term. Generated by
  `Thesis_LaTeX/tools/make_ch2_design_fig.py`, so it regenerates rather than being hand-drawn.
- **New Table 2.5** replaces the two prose gap statements: Gap / what the literature does / why
  it is a problem / what this thesis does, with the answering section referenced in each row.
  The decomposition identity is now a numbered equation (2.14) instead of an inline display.
- **All five figure captions shortened** to one or two lines. They previously ran to five or six
  lines each and were doing the job of body text.
- Humanizer re-run on the rewritten prose: 0 em dashes, 0 unicode dashes, 0 negative
  parallelisms, 0 AI-vocabulary hits. One "not merely" caught and rewritten.
- Build: exit 0, 0 errors, 0 undefined. **Chapter 2 now spans pp. 20–37 of the PDF, 18 pages.**
- **Unrelated, noticed during this build:** Chapter 3 has been substantially expanded by another
  session (§3.7 software framework, §3.9--3.11, "Key points" blocks, tables up to 3.13). It now
  runs pp. 38--61, 24 pages, and the book total is 79 pages. Nothing here touched it; flagging
  because the earlier 65-page figure in this log is superseded.

## Day 26 (2026-08-03, cont.) — Chapter 3 cut again: 24 pp -> 22 pp, all git references removed

**Book is now 77 pp `[draft]` / 75 `[final]`** (was 84/82), both exit 0, 0 undefined, 0 em dashes,
0 overfull boxes in Ch. 3. Chapter 3 body pp. 25–46 (22 pp). 8,126 words, was 9,025.

Done on Touhid's instruction:
- **All repository, commit and tag references removed from Chapter 3.** Gone: both `git clone`
  blocks, the `567e4c0` / `matrix-v2` provenance line, the `Frozen at` row of the training-protocol
  table, the `v2.3.0` tag row in the stack table, and every "tagged commit" phrase in prose and key
  points. The Isaac Lab 2.3.0-vs-2.3.1 problem is kept but restated as a version issue, not a git
  one. **Chapter 4 still carries its own commit/tag row in Table 4.1** — deliberately not touched,
  since Ch. 4 is out of scope, but it is now inconsistent with Ch. 3 and should be decided one way
  or the other before submission.
- **\S3.1 shortened**, mostly by deleting the tag-vs-branch narrative and the two clone blocks.
- **\S3.2 descriptions cut** to a short lead-in each side of Fig. 3.1 and Table 3.2, since the
  figure and table carry the content.
- **\S3.4:** key points removed; new **Table 3.4** with the six joint names, working range and the
  home configuration; new **Figure 3.2 placeholder** for an image Touhid will supply.
- **\S3.6 prose tightened**, summary table already present (Table 3.6).
- **Key points removed** from \S3.6.1, \S3.9, \S3.10, \S3.11.1 and \S3.12. Six blocks remain, in
  \S3.1, \S3.2, \S3.3, \S3.5, \S3.7 and \S3.8, none of which Touhid asked to cut.
- **\S3.7.1 "The gradient-clip audit" deleted as a subsection.** Touhid's instruction was
  conditional ("if it is not important"), and my judgement was that it is load-bearing but not at
  subsection length: \S4.2 tells the whole story, and Ch. 3 only needs enough to explain why the
  control arm exists. It is now three sentences at the end of \S3.7, pointing at \S4.2. **Check that
  \S4.2 still reads as self-contained**, since it was written assuming Ch. 3 set the scene.

Two things flagged in the chapter's own draftnote so they cannot be lost:
1. **The \(\pm\)360\textdegree{} joint working range in Table 3.4 is NOT verified.** The Universal
   Robots product URL redirects to a general index, so it could not be checked against the publisher
   record in this session. It is the widely quoted UR5e figure, but Touhid must confirm it against
   the datasheet. The home-position columns ARE exact, read from `ur5e_robotiq.py`.
2. **Figure 3.2 is a placeholder** that prints an empty labelled box until
   `figures/ur5e_sim.png` (or `.pdf`) exists. Uses the same `\IfFileExists` idiom as the KUET
   monogram, so no edit is needed when the image lands — **but the rebuild must be forced**
   (`latexmk -pdf -g`), or the placeholder branch silently persists. That trap already cost time
   once with the monogram.

**Correction to an earlier entry today:** the "Chapter 2 is 22 pp" figure was stale. Single-spacing
the tables shrank Chapter 2 to **18 pp** (body pp. 7–24), which is inside the 14–16 target Touhid
picked, near enough. Verified against the PDF, not the TOC alone: body p. 1 is physical p. 14, and
Chapter 3 opens on physical p. 38 = body p. 25.

## Day 26 (2026-08-03, cont.) — Chapter 3 restructured: PPO and cPPO merged, duplication cut

Touhid asked for a review of Chapter 3 and then approved the two items I ranked first.

**The merge.** PPO (\S3.3) and cPPO (\S3.9) were ten pages apart. \S3.3's last subsection was
literally "From PPO to cPPO" and then handed off six sections later, and \S3.9 opened by
re-introducing PPO from scratch, re-citing `schulman2017ppo`, `ray2019benchmarking` and
`achiam2017cpo` that \S3.3 had already cited. The equation run was also broken: 3.1–3.5 PPO,
3.6 CMDP, 3.7–3.9 cPPO.

Merged into one section, **\S3.8 "Policy optimisation: PPO and cPPO"**, placed where the cPPO
section used to sit rather than where PPO did. That direction matters: the algorithm now comes
*after* the CMDP (\S3.4) and the cost function (\S3.7), so it can use d and c meaningfully instead
of forward-referencing them. Equations now read **3.1 = the CMDP, 3.2–3.9 = the algorithm in one
continuous sequence.** The duplicated PPO re-introduction is gone; the two key-points blocks became
one.

**Also reordered:** \S3.4 (UR5e) was sitting between PPO and the CMDP, hardware wedged between two
theory sections. Moved up to \S3.2, next to the platform. New order: 3.1 simulator · 3.2 UR5e ·
3.3 RL and on/off-policy · 3.4 problem formulation · 3.5 grasping task · 3.6 software · 3.7 cost
function · 3.8 PPO and cPPO · 3.9 calibration · 3.10 training · 3.11 evaluation.

**Duplication cut:**
- Table "Summary of the simulation environment" had 14 rows, 7 of which repeated the two tables on
  the facing pages (action, observation, episode, goal box, reward terms, lift gate, safety-in-
  reward). Now 9 rows and retitled "Scene and simulation settings", carrying only what nothing else
  states.
- \S3.5's opening paragraph repeated \S3.1 almost verbatim on GPU-resident physics. Cut.
- \S3.5's third paragraph re-listed the six joints and the action scale that Tables 3.3 and 3.5
  already give. Cut to one sentence on the cube.
- The chapter's opening paragraph was rewritten, since "the first four sections describe the tools"
  and "from Section 3.5 onward the chapter turns to what was built" were both false after the
  reorder. It now states the reading order explicitly.
- \S3.3 gained a forward pointer to \S3.8 so the algorithm hand-off is not left dangling.

**Two consistency fixes found in the same review:**
- Table 3.10 (hyperparameters) had two rows reading "GAE \(\lambda\)", contradicting \S3.8.2's own
  stated convention that an unsubscripted lambda always means the Lagrange multiplier. Both now
  `\lambda_GAE`.
- The lambda-convention sentence pointed at the section it was already inside. Repointed at
  \S3.8.3, where the multiplier actually appears.

**Result: Chapter 3 pp. 25–45 (21 pp, was 22). Book 76 pp `[draft]` / 75 `[final]`. 7,938 words,
was 8,126.** Both builds exit 0, 0 undefined, 0 em dashes, 0 overfull boxes in Ch. 3. Rendered the
merged section and confirmed the equation sequence reads continuously.

**Still open, raised in the review and NOT actioned (Touhid chose the merge and the cuts only):**
1. Two repository paths survived the earlier sweep and should go: the \S3.10.1 footnote ends with
   `Comparison_test/ppo_redundant/README.md`, and Table 3.12's last row is
   `Source of all figures | Comparison_test/final_results/`.
2. Table ordering in \S3.10: the section text points at the training-protocol table, but the arms
   table appears first because it sits in the subsection.
3. "Layer 1/2/3" is used three times in \S3.5 with no gloss. Defined in Ch. 1 \S1.5, so not wrong,
   but 25 pages earlier.
4. Three figures worth adding, all TikZ, no external files: a cPPO block diagram (highest value,
   would let a paragraph of wiring prose be deleted), the cost-term penalty shape against w, and the
   goal box against the reach envelope.

## Day 26 (2026-08-03), later — Chapter 2 reconciled against the rewritten Chapter 3
Re-read Chapter 2 end to end and cross-checked it against Chapters 1, 3 and 4. Chapter 3 had been
substantially expanded by a separate session in the meantime, which invalidated several things in
Chapter 2. Six fixes, all confined to Chapter 2.

1. **Figure 2.6 (was 2.5) was factually wrong and is redrawn.** It showed the arms as
   PPO / ctrl / cPPO. Chapter 3 Table 3.11 says the three trained arms are `ctrl` (reported as
   "PPO (baseline)"), `cppo` at d=25 and `cppo15` at d=15, with a plain `ppo` arm trained but not
   reported separately because its weights are byte-identical to `ctrl`. Two of the three boxes
   were therefore the same arm and `cppo15` was missing entirely. The new figure shows `ppo` as a
   dashed box tied to `ctrl` by a double line (the identity that makes the implementation term
   zero by verification), then ctrl -> cppo -> cppo15 with braces for the constraint term and for
   budget sensitivity. Script header now carries a "must match Table 3.11" note.
2. **The second budget is no longer missing.** `cppo15` is 5 of the 15 trained policies and was
   absent from the whole chapter. Added as Gap 3 in Table 2.5 ("one budget only": Ray fixes d=25,
   Khan inherits it, neither varies it), as a new row in the positioning table, in key finding 7,
   and in the summary's contribution statement, which now promises three contributions.
3. **§2.9's opening claim hedged.** It called manipulability "the operative safety constraint".
   Chapter 3's own calibration table measures joint-limit proximity at ~86 % of realised cost
   against manipulability at ~14 % and collision at 0 %. It now reads as the *framing* constraint,
   with the split stated up front. **Chapter 3 §3.8 still says "the operative constraint of this
   thesis" of the singularity term and contradicts its own Table 3.9 — not fixed, out of scope,
   flagged in the Chapter 2 draftnote.**
4. **Duplication with Chapter 3 removed.** Both chapters stated the CMDP tuple and the PPO clipped
   surrogate with equations, in near-identical prose about eight pages apart. Chapter 2 now cites
   Equation (3.1) and Equation (3.3) instead, and states the division of labour explicitly: this
   chapter carries the equations of the reviewed literature, Chapter 3 those of the method. The
   Lagrangian relaxation is deliberately kept in both, because §2.4's argument turns on seeing it.
5. **New Figure 2.3, `figures/lit_twolink_w.pdf`** — original, black line, generated by
   `tools/make_ch2_manip_fig.py`. Plots w = l1*l2*|sin(theta2)| against the elbow angle, marking
   the folded and extended zeros and the right-angle peak. §2.9 was the most abstract stretch in
   the chapter and was carrying its central idea in prose alone.
6. **Two small factual slips:** Table 2.4's "This thesis" row said "PPO, control arm, cPPO" and
   now names the three arms properly; §2.5 claimed both UR5 studies use PPO, but Xia uses SAC
   alone and is not a grasping study.

Verified: `grep -c -- '---'` = 0, no unicode dashes, no colour or framing, no AI-vocabulary hits,
one "not just" rewritten. Build exit 0, 78 pages, 0 errors, 0 undefined citations or references;
cross-chapter references resolve correctly to Equation (3.1) and Equation (3.3). Chapter 2 spans
pp. 21--39 (19 pp. in `[draft]`, about 18 in `[final]` once the draftnote drops).

**Next, agreed with Touhid: Chapter 4 tonight.** It is still on ten seeds, still sourced from the
superseded `MATRIX_V2_PARTIAL_3ARM.md`, and its principal §4.6 finding names seeds 2, 5, 50 and 51,
all of which are excluded under the locked scope. Chapters 2 and 3 now both say five. That needs
re-derivation from `Comparison_test/final_results/`, not a wording pass.

## Day 26 (2026-08-03), night — Chapter 4 re-derived from scratch
Touhid asked for this to be done now rather than in a later session. The chapter was not edited;
it was rebuilt from the CSVs.

**Method.** Two new scripts under `Comparison_test/results/scripts/`, both reading
`final_results/` and nothing else:
- `summarize_final.py` — emits every table in the chapter (training tail means, lambda
  statistics, pooled and per-seed evaluation, and the ppo-vs-ctrl identity check). No number in
  Chapter 4 is typed by hand; re-run this to reproduce any of them.
- `make_ch4_figs.py` — regenerates `per_seed_cost.pdf` for three arms and five seeds, and
  produces the new `lambda_traj.pdf`. Black line art, arms separated by marker and line style.

**What the recomputation changed.**
- Seeds 10 -> 5 (1, 3, 4, 52, 54); policies 30 -> 15; evaluation episodes 30,000 -> 15,000 per
  arm, 45,000 total.
- **`cppo15` is now reported for the first time.** It was a whole arm missing from the results
  chapter. New Section 4.8 treats the d=25 vs d=15 comparison directly, which is what answers
  the budget-sensitivity gap Chapter 2 Section 2.11 promises as Gap 3.
- **The principal finding survives but the qualification shrinks.** The old text said "on six of
  the ten seeds the constrained agent's cost is HIGHER". On the retained five it is one seed,
  54, whose unconstrained policy was already under budget at 7.95. The other four fall sharply.
  Spread: baseline 20.4x (7.95 to 162.30), cPPO d=25 2.1x, d=15 3.8x. Evaluation cost sd across
  seeds 62.75 -> 5.38 -> 5.01, an 11.7x and 12.5x tightening.
- **New finding, not anticipated: the variance collapse shows up in TASK performance too.** The
  seed-to-seed sd of sub-centimetre goal-reach falls from 7.52 points to 1.04 and 0.95. One
  baseline seed lands at 80.0 % where the others are 94 to 99 %. No constrained seed is below
  96.97 %.
- Safety: true singularity crossings 2.66 % (399/15,000) -> 0.38 % (57) -> 0.07 % (10), factors
  of 7.0 and 39.9. Joint-limit contact 10.70 % -> 0.00 % -> 0.00 %. The baseline's 10.70 % is
  itself a lottery: per-seed 47.83, 0, 0, 0, 5.67 %.
- Task: reward 133.06 / 132.18 / 134.09. The tighter constrained arm has the HIGHEST reward and
  the smallest spread, so the "no task cost" claim is now stated as an upper bound in both
  directions.
- Counter-result retained and re-verified: worst single-episode manipulability is 0.000001 on
  all three arms. Tightening the budget does not change it.

**Limitation 2 is discharged.** `cost_lambda.csv` exists for every constrained seed, so the
"lambda engaged then relaxed" reading is now measured, not deduced. New Section 4.7 and
Figure 4.2. Every run shows one sharp peak between iterations 47 and 58 (peaks 15.84 to 48.05 at
d=25, 17.62 to 40.83 at d=15) decaying to zero, with lambda above 0.01 for 36 to 120 iterations
of 1500. Nine of ten runs end at exactly zero, which is why the old table of final values was
close to uninformative. This is the integral-control overshoot Stooke et al. describe, and
Chapter 2 Section 2.5 sets it up.

**Identity check strengthened.** ppo vs ctrl now verified three ways: training scalars identical
to every logged decimal on all five seeds; the historical checkpoint tensor comparison (68 of
100 tensors byte-identical); and NEW, all 15,000 evaluation episodes compared episode by episode
on goal distance, minimum manipulability and episodic cost, all identical.

**Also cleaned up.** The 33.7 % joint-limit figure is now sourced to Chapter 3's calibration
section rather than a logbook entry, so the "Draft notes for revision" draftonly block and the
"Citation status" block were both deleted. Limitation 1 rewritten: the binding-budget arm is no
longer missing, only the off-policy SAC arm is.

Humanizer pass done: 44 em dashes -> 0, no unicode dashes, no AI vocabulary, two negative
parallelisms rewritten. Build: latexmk exit 0, 78 pages, 0 errors, 0 undefined citations or
references. Chapter 4 spans pp. 61-73 (13 pp.). All Chapter 2 and Chapter 3 forward references
into Chapter 4 resolve.

**Still open after tonight:** the SAC arm (never trained, correctly a limitation); Chapter 3
Section 3.8 still calls the singularity term "the operative constraint" against its own
Table 3.9; Chapter 2 Section 2.2 still overlaps Chapter 1 Section 1.2; Chapters 5 and 6 are
stubs; the six examiner-name TODOs in frontmatter/approval.tex still block the [final] build.

## Day 27 (2026-08-04) — Chapter 4 figures: eleven, in colour, in true Times New Roman
Chapter 4's prose was NOT touched. It was re-derived the previous night and is correct. This
session was figures only, plus the documentation needed to stop a later session undoing them.

**Two sessions collided and it was caught before damage.** This session had been asked to write
Chapter 4 and had independently recomputed every number from `final_results/` before discovering
the chapter had already been rebuilt at 01:03. The two computations agree (reward 133.06 /
132.18 / 134.09; true singularity 2.66 / 0.38 / 0.067 %; joint limit 10.70 / 0 / 0), which is a
free cross-check on both. The rewrite was abandoned rather than duplicated.

**Colour convention changed, deliberately.** The 2026-08-03 rule was "black line art, no colour,
arms separated by marker and line style". Touhid asked for red/blue/green. Rather than split the
book, Chapter 2's two original figures were recoloured to the same palette, so an arm is one
colour everywhere: `ctrl` red `#D11A1A`, `cppo` blue `#1257A8`, `cppo15` green `#17803D`.
Recorded in `Thesis_LaTeX/figures/README.md` and in the banner of `logbook/NEXT_SESSION_ch4.md`.
`make_ch4_figs.py` now refuses to run without an explicit override, because re-running it would
silently revert two figures.

**Fonts.** Figures now render in genuine Times New Roman, installed on the Ubuntu 22.04 machine
via `ttf-mscorefonts-installer` and copied into `Thesis_LaTeX/fonts/`. That folder is gitignored
(Monotype licence permits use, not redistribution, and the repo has a public remote); its README
is tracked and carries the install steps. The figure script detects the font by family name read
from inside the file, so Windows `times.ttf` and Ubuntu `Times_New_Roman.ttf` both work, and it
prints which font it actually used. Without the files it falls back to Liberation Serif and says
so loudly.

**Figures: 2 -> 11** (4.1 to 4.11), all from one script,
`Comparison_test/results/scripts/make_final_results_figs.py`, fed by `build_final_results_data.py`.
Design decisions worth not re-litigating:
- **No shaded +/- std bands.** Three translucent bands over each other were unreadable. The seed
  spread moved into two dedicated figures instead, `fig_seed_variance` (per-seed training cost,
  one panel per arm) and the existing `per_seed_cost`. The variance-collapse claim of Section 4.6
  now rests on those.
- **Curves are EMA-smoothed (weight 0.88) and every caption says so.** No number in the chapter
  comes from a smoothed curve; all values trace to the unsmoothed JSON.
- `fig_mean_episode_cost` clips its log axis below 1. The full range spans six decades and
  compresses the converged region to a sliver. Caption states the clipping.
- `fig_eval_task_performance` shows success rates twice: zoomed to 90--100 % with the suppressed
  region hatched, and as failure rate on a log axis where 0.09 vs 6.97 % separates by 70x.
- `fig_eval_safety_violations` is a 2x2 grid, each panel independently scaled, because the four
  metrics span three orders of magnitude.
- **`per_seed_cost` keeps seeds on the x-axis** and `lambda_traj` stays per-seed rather than
  averaged. Both are dictated by prose that already quotes them ("one vertical segment joining
  its three arm values"; "peaks 15.84 to 48.05"). Transposing or averaging either would
  contradict the text. Verified the lambda peaks reproduce exactly.

**Verified:** latexmk exit 0 on a forced full rebuild, 86 pages, 0 errors, 0 undefined references
or citations, all 11 figures resolve into the List of Figures as 4.1--4.11, em-dash count in
Chapter 4 still 0. The 9 remaining overfull boxes were traced and none are new: they sit in
draftnote blocks and in the Chapter 5/6 stub boxes, all of which drop in `[final]`.

**One factual fix inside the chapter:** the draftnote's sourcing rule said "both figures are
produced by make_ch4_figs.py". Updated to name the current script and to disclose the smoothing.
No other prose was altered.
