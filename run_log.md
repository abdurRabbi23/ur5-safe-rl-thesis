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
