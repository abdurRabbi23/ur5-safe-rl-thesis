# Run Log — `Comparison test/` (scoped)

Daily timeline for work done **inside `Comparison test/`** specifically — the 4-algorithm
benchmark redo (PPO/SAC/TD3/cPPO), retrained fresh and self-contained, separate from the main
`ur5_grasp/` + `IsaacLab/logs/` history. Same convention as the project-wide `run_log.md` (a
dated line/entry whenever something happens here), just filtered to this folder so a new session
working only on the comparison test doesn't have to read the whole project history to get
context.

**Dual-tracked:** every entry here also appears in the project-wide `../run_log.md` (that one
stays the single front-door timeline for the whole thesis). This file exists so `Comparison
test/` is self-contained on its own — read this first if you're only picking up work in this
folder; read `../run_log.md` for the full project picture.

For deep context (goals, decisions, file layout, next steps) see `../logbook/09_comparison_test.md`
(current work) and `../logbook/03c_multialgo_benchmark.md` (decision record — hypothesis,
fairness protocol, cut order, schedule).

---

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
reached. Reassessed: pausing here, picking up next session.

**NEXT (not yet done):**
1. ~~`play.py` visual gate~~ — superseded, see Day 20 cont. entry below.
2. Short smoke-train (~50 iters) on the new task to confirm the full RL reward/obs loop behaves
   with the new gripper before committing to a full run.
3. Once both pass: re-freeze/tag this as the new Layer-1 env, update `09_comparison_test.md` /
   `03c_multialgo_benchmark.md` to point the run matrix at `-SimpleGripper-v0` instead of `-v0`,

## 2026-07-29 (Day 20, cont.) — Live GUI grasp+lift demo: black gripper, TCP axis markers

Built `ur5_grasp/scripts/simple_gripper_live_grasp_demo.py` — standalone `InteractiveScene` script
(bypasses the gym task's 5 s episode timeout so it can run indefinitely). Real IK-driven
approach-descend-close-lift-hold-lower-release cycle on the ACTUAL cube (read live from
`object.data.root_pos_w`, no pinning/teleporting), looping until the viewport is closed. Gripper
(`base_link`/`left_finger`/`right_finger`) painted black via a visual-purpose `UsdPreviewSurface`
material, separate from the existing physics friction material. TCP (same 0.075 m pad-midpoint
offset as the training env cfg) tracked live with an RGB axis-arrow `VisualizationMarkers`
instance, same marker type IsaacLab's own diff-IK tutorial uses.

Full detail + exact run command + what's verified vs. not in `../run_log.md` (2026-07-29, Day 20
cont.). Short version: syntax-checked and every non-trivial API call cross-checked against this
repo's actual `IsaacLab/source/isaaclab`; not run — no GPU here. Waiting on a lab-PC run and
report-back before this counts as done.
   THEN launch PPO ×3 / cPPO ×3.

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

## 2026-07-30 (Day 22, cont.) — Grasp test PASSED (result was sitting unread on disk). Matrix repointed to the WELD env `-v0`.

### Result — SimpleGripper contact grasp: PASS
`ur5_grasp/tools/simple_gripper_grasp_report.txt`, timestamped 01:19 — written by the re-run
after the instrument fix, and never read. The fixed script worked exactly as intended:

```
[local offset] measured wrist_3->TCP = [+0.0000, +0.0000, +0.0750] m
[segment] wrist_3->mount (base_link_0) = [+0.0000, +0.0000, +0.0150] m
[segment] mount->TCP, in the GRIPPER's own frame = [+0.0000, -0.0000, +0.0600] m

 left_finger_joint=+0.0163  right_finger_joint=-0.0165
 cube held at z=+0.268 (pad +0.269) after release -> GRIP HOLDS
```

Both halves of the Day-20 pass bar are met. The fingers stalled at a **62.8 mm pad gap**
against a 30 mm closed target — obstructed by the cube, not passing through — and the cube's
z held for 140 steps after the pin released. Every authored segment resolved to its designed
value to 4 decimal places. **The SimpleGripper is a working contact grasp.**

Note the cube is therefore ~63 mm across (0.8-scaled DexCube), which matters below: the
2f-85's 85 mm stroke would clear it with 22 mm to spare.

### Decision (Touhid, Day 22): the 15-run matrix runs on `-v0`, the FROZEN WELD env.
This reverses the Day-20/21 repoint to `-SimpleGripper-v0`. Reasons:

- `-v0` is frozen, git-tagged (`layer1-env-freeze`), and already produced the Day-10 headline
  result. Zero new code, launchable immediately.
- The 2f-85 *is* present and driven in `-v0` — real asset, real linkage, actuated
  `finger_joint`. What is abstracted is the grasp (proximity weld), and Methods §2 already
  declares that abstraction with its two consequences stated.
- Schedule. `03c`'s locked plan had PPO ×3 + cPPO ×3 finishing **today**; the count is
  currently zero of fifteen. SAC/TD3 are the entire schedule risk, TD3 hard-cuts Aug 6,
  writing is due Aug 11.

The SimpleGripper is **not** dropped. It is reduced to a ~50-iter smoke train (Touhid's call:
prove `-SimpleGripper-v0` trains, hold the full matrix), and stands in the thesis as a
separately demonstrated real-contact grasp — which is a stronger position than before, because
it is now backed by a measurement rather than a plan.

### Correction to `logbook/09`
That file states `Comparison test/ur5_grasp/` is "**not** git-tracked as part of the main repo
(it's a plain filesystem copy)". **False as of today.** `git ls-files "Comparison test"` returns
tracked files (`ur5_grasp/CONTEXT.md`, `assets/ur5e_robotiq_2f85.usd`, `results/scripts/…`, …),
and `git status` shows five *modified* tracked files under it. The folder is in the repo. Fixed
in `09`.

### Fragility found while checking the launch path — one command fixes it
`tasks/lift/__init__.py` registers the SimpleGripper cfg alongside `-v0`, so importing the task
package imports `robots/gripper_geometry.py`, which **raises `FileNotFoundError` at import time**
if `assets/wrist_frame.json` is absent. That file is currently **untracked** (`??` in
`git status`). Its own docstring warns about exactly this blast radius:

> HEADS UP on the blast radius: this failure blocks EVERY task import in the package,
> including the frozen weld env `Isaac-Lift-Cube-UR5e-v0` […]

So the frozen weld env's importability presently depends on an uncommitted JSON file produced
by a Day-21 measurement tool. For a six-run overnight batch, and for reproducibility of the
thesis numbers, that is not acceptable. **Fix: commit it** as part of the freeze. (The
alternative — making the SimpleGripper registration lazy so `-v0` cannot depend on it — is
cleaner but touches the frozen `__init__.py`, so it is flagged, not done.)

### Instruments built this session (both verified as far as a GPU-free sandbox allows)
- **`run_ppo_cppo_seeds.sh` rewritten.** The Day-19 version wrapped all six runs in
  `set -euo pipefail`, so one failed run silently cancelled the five after it — you would come
  back to a third of a matrix with no record of what died. Now: exit codes captured per run,
  batch always continues, per-run wall-clock recorded (`03c` wants wall-clock reported
  separately), and each run is verified by the artefacts rsl_rl writes to disk — run directory
  present, checkpoint count non-zero — rather than by stdout, which this project has now lost
  four separate times. Writes a flushed `logs/batch_report.txt`. Script exit code = number of
  failed runs.
  *Verified* against a stubbed `isaaclab.sh` covering both failure modes: a hard crash
  (exit 1) and the nastier silent one (exit 0 but no checkpoint written). Both were caught and
  distinguished, the remaining runs still executed, exit code was 2.
- **`ur5_grasp/tools/summarize_runs.py` (new).** Parses TensorBoard event files into a flushed
  text report plus per-tag CSVs. This closes a real reproducibility gap:
  `results/scripts/make_layer1_figs.py` reads CSVs from
  `/sessions/compassionate-relaxed-sagan/mnt/.../results/tb_csv` — a hardcoded path from a
  throwaway sandbox that exists on no machine — so the export that fed the Layer-1 figures was
  manual and unreproducible. No GPU, no Isaac; safe to run mid-batch.
  *Verified*: py_compile; run end-to-end against a stubbed EventAccumulator over three fake
  runs (headline-metric selection, cross-run table, CSV export, alignment); the missing-logs
  path returns exit 1 and names the cwd-relative-log-path trap as the likely cause; the
  missing-tensorboard path reports and exits 2. **Not verified: the real TensorBoard API
  contract** — the sandbox has no network and tensorboard could not be installed. The
  `EventAccumulator` / `Tags()` / `Scalars()` calls are standard and stable, but the first real
  run is what proves them.

### NEXT (lab PC, in order) — see logbook/09 for the full command list
0. Commit `wrist_frame.json` + this session's changes; re-tag the env.
1. Smoke train `-v0` PPO, 50 iters. **Do not skip** — `-v0` has never been trained inside this
   folder, and `train.py` + `tasks/lift/__init__.py` have both changed since the freeze.
2. Smoke train `-v0` cPPO, 50 iters (proves `LagrangianRunner` + the `extras["cost"]` channel).
3. Smoke train `-SimpleGripper-v0`, 50 iters.
4. `./run_ppo_cppo_seeds.sh` — the full PPO ×3 + cPPO ×3.
5. `summarize_runs.py`; reports get read from here.

## 2026-07-30 (Day 22, close) — All three smoke trains PASS. The Layer-1 mechanism is already visible at 50 iterations.

Freeze done first: commit `2b19e90`, tag `comparison-matrix-v0`. Folder renamed
`Comparison test` → `Comparison_test` (space removed).

Four runs read from `ur5_grasp/tools/summarize_runs_report.txt`. Which env each run actually
used was confirmed, not assumed, by grepping `<run_dir>/params/env.yaml` for the robot USD:
`smoke_ppo` and `smoke_cppo` → `ur5e_robotiq_2f85.usd`; `smoke_sg` and the earlier 23:48
`simplegripper_smoke` → `ur5e_simple_gripper.usd`. All four reached 49 iters, 2 checkpoints each.

### Gate results — all PASS
1. **`-v0` PPO trains.** reward 65.47, episodes 246.9/250, no crash.
2. **`-v0` cPPO wiring is live.** Three cPPO-only tags present and non-degenerate —
   `Loss/cost_lambda` 19.40, `Loss/cost_value_function` 0.21, `Loss/mean_episode_cost` 35.12.
   So `LagrangianRunner`, `ActorCriticCost` and the `extras["cost"]` channel are all connected.
3. **`-SimpleGripper-v0` trains.** reward 2.61, no crash.

### The headline separation is ALREADY present at 50 iterations
| metric (tail-mean, last 10%) | PPO `-v0` | cPPO `-v0` |
|---|---|---|
| `Train/mean_reward` | 65.47 | **73.61** |
| `safety/manipulability_mean` | 0.0330 | **0.0972** |
| `safety/manipulability_min` | 5.73e-06 | **0.0472** |
| `safety/viol_singularity` | **0.7186** | 0.0035 |
| `safety/cost_total` | 0.5455 | 0.000639 |

cPPO is holding mean manipulability ~3× higher, min manipulability above `MANIP_FLOOR = 0.045`,
and ~200× fewer singularity violations. Collision and joint-limit costs are ~0 in both, which
confirms the Day-9 finding that **singularity is the single binding constraint**.

### Three things to watch at 1500 iters — recorded now as predictions, not conclusions
- **The separation is much larger than Day 10's.** Day 10 (1500 iters) was viol 6.65% vs 16.86%.
  Here it is 0.35% vs 71.9% — PPO 4× worse than its own final figure, cPPO 20× better than its.
  Expected cause: `lambda = 19.4` is still climbing, so cPPO is currently **over-constraining**,
  which is cheap while reward is still small. **Prediction: by 1500 iters lambda settles and
  cPPO's viol rises toward ~6-7%.** If lambda is still ~19 and viol still ~0.3% at 1500, the
  constraint is over-binding and task performance is being paid for it — check reward parity.
- **cPPO reward (73.61) currently EXCEEDS PPO (65.47).** A constrained agent should not beat its
  unconstrained baseline. At 50 iters, one seed, this is almost certainly noise — Day 10 had them
  effectively tied (166.3 vs 167.2). **If it persists across 3 seeds at 1500, suspect the cost
  term is leaking into the reward path.**
- **PPO's `manipulability_min` = 5.7e-06** is a genuine rank-deficient Jacobian, four orders below
  the Day-9 calibrated baseline min of 0.021. Explainable at 50 iters (near-random policy flails
  into singular configs). If it stays at ~1e-06 at 1500, the *min* statistic is being set by a
  handful of pathological envs out of 4096 and **the mean is the more honest number to report**.

### Bug found and mitigated: `experiment_name` comes from the AGENT cfg, not the task
`smoke_sg` (SimpleGripper) landed in `logs/rsl_rl/ur5e_lift/` — the same directory as the
weld-env PPO runs — because both use `UR5eLiftPPORunnerCfg` (`experiment_name = "ur5e_lift"`).
The task ID never appears in the log path. Two physically different robots therefore become
indistinguishable by directory, and any glob over `ur5e_lift/*` silently averages them.
Same failure class as everything else in this project: an instrument that looks right and
quietly reports the wrong thing.

Mitigated by moving both SimpleGripper runs to `logs/rsl_rl/ur5e_lift_simplegripper/`. Real fix,
if the SimpleGripper is ever trained past a smoke test: give it its own agent cfg with its own
`experiment_name`. Not done now — it touches registration, and the matrix is on `-v0` anyway.

### NEXT
`./run_ppo_cppo_seeds.sh`, then `summarize_runs.py`. Nothing else is open.

## 2026-07-30 (Day 22, close) — MATRIX RUN: PPO x3 + cPPO x3 complete. Day-10's headline does NOT reproduce.

All 6 runs OK, 10-11 min each, 66 min total (my 4-6 h estimate was wrong; `03c`'s 12-15 min was
right). `logs/batch_report.txt`, git `d57063a`, 0 dirty paths, 31 checkpoints per run.

### Results, 1500 iters, tail-mean over last 10%, mean of 3 seeds
| | PPO | cPPO |
|---|---|---|
| `Train/mean_reward` | 132.0  (141.9 / 90.8 / 163.3) | **162.8**  (163.9 / 166.2 / 158.3) |
| `viol_singularity` | **83.7%**  (73.9 / 85.4 / 91.9) | 42.3%  (54.8 / 13.8 / 58.2) |
| `viol_joint_limit` | **30.3%**  (35.4 / 55.4 / 0.0) | 0.85%  (0.9 / 0.0 / 1.6) |
| `cost_total` | 1.005 | 0.073 |
| `Loss/cost_lambda` | — | 0.155 / 0.0 / 0.059 |
| `mean_episode_cost` | — | 24.26 / 9.78 / 20.89  (limit 25) |

cPPO beats PPO on **both** axes, consistently across all three seeds.

### ❌ Day-10's headline does NOT reproduce — and the cause is NOT a code change
Day 10: cPPO viol 6.65% vs PPO 16.86%, reward 166.3 vs 167.2. Now: 42.3% vs 83.7% — ~5x higher
in **both** arms.

Checked before speculating: `ur5e_lift_env.py`, `ur5e_lift_env_cfg.py`, `costs.py`,
`ur5e_robotiq.py` and `ppo_lagrangian.py` in this folder are **byte-identical to
`layer1-env-freeze`** (`git show layer1-env-freeze:… | diff`). The runs' own dumped
`params/env.yaml` confirms `velocity_limit_sim: 3.14`, `episode_length_s: 5.0`, and
`params/agent.yaml` confirms `cost_limit: 25.0`, `lambda_lr: 0.035`, `lambda_init: 0.0`.
**Nothing changed.**

Most likely reading: **Day-10's numbers came from a single seed that happened to land well.**
Three seeds now show PPO's singularity violation at 74-92% and reward from 90.8 to 163.3 — a
72-point spread. That is not a stable baseline, and one draw from it is not a result. This is
precisely why `03c` mandated 3 seeds. Decision (Touhid): **retire the Day-10 headline**; the
3-seed figures are the thesis numbers, with a Methods paragraph on why the picture changed.

### Why lambda collapsed to ~0 — the ALGORITHM is right, the CONSTRAINT is too loose
`mean_episode_cost` = 24.26 / 9.78 / 20.89, all under `cost_limit = 25`. So the Lagrangian did
exactly what it was told: it met the budget, so lambda decayed toward 0. Correct behaviour.

But `costs.py` line 123 computes `c_manip = clamp(1 - w/manip_floor, 0, 1)` — a *margin*, not a
count — while `viol_singularity` is the binary fraction `(w < floor)`. A budget of 25 spread over
250 steps permits ~0.1 cost/step, i.e. `w ≈ 0.0405` against a floor of 0.045: **the arm can sit
just 10% under the floor essentially permanently and still satisfy the constraint.** Hence 42%
violation with the budget met. The Day-9 calibration of `cost_limit = 25` no longer describes
this system.

### ⚠ cPPO now BEATS PPO on reward (162.8 vs 132.0) — flagged at 50 iters, now confirmed
Predicted last session as a thing to watch; it survived 3 seeds, so it is not noise.
Plausible mechanism, NOT yet tested: unconstrained PPO drives into joint limits (30% of steps,
55% on seed 2) and singularities (84%), and those states wreck its own learning; the cost term
keeps cPPO in a well-conditioned region, acting as a regulariser. That upgrades the claim from
"safety at no task cost" to "safety improves task performance" — stronger, but an examiner will
probe it, and it needs the success-rate numbers before it can be asserted at all.

### Still missing: SUCCESS RATE
No success scalar is logged during training. The "100% lift" claim comes only from
`eval_success.py`. Until that runs, the headline is unsupported.

**`eval_success.py` wrote no file** — 9 `print()` calls, zero `_FH`. Fifth instance of the same
trap; caught BEFORE running this time, by grepping for `_FH`/`log()` per the standing rule.
Fixed: flushed report that **appends** (so a 6-checkpoint sweep accumulates in one file),
PROGRESS lines, machine-readable CSV row per run, traceback logged into the report.
Added `run_eval_success.sh`: all 6 checkpoints, 512 episodes (`03c` protocol), **fixed eval seed
42 for all six** so every policy is scored on identical cube spawns rather than its own training
seed. `py_compile` + `bash -n` pass; all 6 checkpoints resolve.

### NEXT
`./run_eval_success.sh`, then read `ur5_grasp/tools/eval_success_report.txt`. The cost_limit
decision waits on those numbers.
