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
