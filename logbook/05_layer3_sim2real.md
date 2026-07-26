# Module 05 — Sim-to-Real Transfer (Layer 3, optional)

Status: ▶ ACTIVE — RH-P12-RN imported into sim and grasping with REAL CONTACT (no weld).
ROS 2 hardware transfer still ⏳ later.
Chat type: hardware / ROS 2 / gripper
Last updated: 2026-07-26 (Day 16)

## Goal
Zero-shot transfer of the trained policy to the physical UR5e via ROS 2 Humble +
Universal_Robots_ROS2_Driver.

## ✅ Gripper gap CLOSED in sim (2026-07-26)
The largest sim-to-real gap — sim used a Robotiq 2f-85, the real robot has a ROBOTIS
RH-P12-RN — is now closed on the simulation side. The RH-P12-RN is imported, mounted,
and **holds a cube with contact forces alone**. Layer 1 files were not touched; this is
a parallel env.

### Why this was possible at all
The Robotiq 2f-85 is a closed-loop 4-bar. PhysX articulations are trees, so the loop is
never closed, the pad joints stay passive, and NO force reaches the contact surfaces —
that is why Layer 1 needs a proximity weld and why `grasp_hold_test.py` said GRIP TOO
WEAK at any clamp force.

The RH-P12-RN URDF is a pure TREE: 5 links, 4 revolute joints, no loop.

    rh_p12_rn_base
      |-- rh_p12_rn (+x, 0..1.1) --> r1 --|-- rh_r2 (-x, 0..1.0) --> r2
      |-- rh_l1     (-x, 0..1.1) --> l1 --|-- rh_l2 (+x, 0..1.0) --> l2

Every joint is directly drivable, so there is a real force path to the pads. No PhysX
mimic joints and no loop-closure joint needed. The opposed axis signs mean all four
joints take the SAME scalar target q and the pads stay parallel: q=0 open, q=1.0 closed.

### Verified numbers
- Merged asset loads as ONE articulation: **10 joints / 12 bodies**.
- Joint order is INTERLEAVED — `[...arm x6, 'rh_l1', 'rh_p12_rn', 'rh_l2', 'rh_r2']`.
  Always resolve gripper joints by NAME (`find_joints`), never by index.
- Stroke sweep monotonic: pad gap 0.1145 (q=0) -> 0.0216 (q=1.0). Subtract ~0.0078 for
  the pad faces -> ~107 mm clear opening, matching the 106 mm spec.
- Default flange mount was correct (pos 0,0,0 + identity rot on `wrist_3_link`).
- **The TCP is not a fixed point.** The fingers curl forward as they close, so the pad
  midpoint travels 0.0767 m (open) -> 0.1049 m (closed) from `wrist_3_link`.

### Grasp result (contact only, weld disabled)
`results/rhp12_grasp_sweep.txt`, seat 45 / hold 120 steps:

| offset (m) | q_final | pad_gap (m) | cube->grasp (m) | verdict |
|---|---|---|---|---|
| 0.060 | 0.642 | 0.0943 | 0.0789 | dropped |
| 0.070 | 0.713 | 0.0824 | 0.2548 | dropped |
| 0.075 | 0.730 | 0.0787 | 0.0638 | dropped |
| 0.080 | 0.719 | 0.0812 | 0.0548 | dropped |
| 0.085 | 0.693 | 0.0859 | 0.0550 | dropped |
| 0.090 | 0.757 | 0.0739 | 0.0255 | **HELD** |
| 0.095 | 0.783 | 0.0688 | 0.0179 | **HELD** |
| 0.100 | 0.774 | 0.0706 | 0.0295 | **HELD** |
| 0.110 | 0.757 | 0.0739 | 0.0191 | **HELD** |

Reading it: `q_final` stalled short of 1.0 in EVERY row, so the fingers made contact
everywhere — no row is a geometry miss. The failures at 0.060–0.085 stall EARLIER
(q 0.64–0.73) with a WIDER pad gap: the cube sits too deep and is caught on the curved
proximal (r1/l1) links instead of the flat pads, which cannot hold it. From 0.090 the
cube sits in the pad region, the fingers close further (q 0.757–0.783), and it holds.
Note the holding band brackets the closed-pose TCP of 0.1049 — as expected, the cube
ends up where the closed pads are.

### Extended sweep -> TCP_OFFSET LOCKED at 0.130
The first sweep stopped at 0.110; extending to 0.100-0.140 held at ALL five offsets, so
"held" alone could not pick a value. Converting `pad_gap` (body origins) to the clear
opening between the pad FACES (`face_gap = pad_gap - 0.0078`) and comparing against the
0.0412 m DexCube settled it:

| offset | q_final | face_gap | delta vs cube |
|---|---|---|---|
| 0.100 | 0.774 | 0.0628 | +0.0216 |
| 0.110 | 0.796 | 0.0583 | +0.0171 |
| 0.120 | 0.810 | 0.0555 | +0.0143 |
| **0.130** | 0.875 | **0.0415** | **+0.0003** |
| 0.140 | 0.884 | 0.0396 | -0.0016 |

**0.100-0.120 are false positives.** They pass the static hold test with the pads stopped
14-22 mm WIDER than the cube, i.e. the cube is wedged on the curved proximal r1/l1 links
rather than held by the flat pads — a grip that survives a static test and fails under
the accelerations of a real lift. 0.140 interpenetrates by 1.6 mm and leans on solver
depenetration. 0.130 is the true flat-pad parallel grip (delta +0.3 mm, z_drop 2.9 mm).

LESSON FOR THE WRITE-UP: a binary HELD/dropped criterion is not sufficient to calibrate a
grasp. The physical check — do the pad faces close to the object's width? — is what
separates a real grip from a wedge. `rhp12_grasp_sweep.py` now reports `face_gap` and
selects on it instead of on an arithmetic centre-of-band.

### Confirmation run at the locked value (2026-07-26)
`--offsets "0.125 0.130 0.135"`, env `ee_frame` now actually using 0.130:

| offset | q_final | face_gap | delta vs cube | cube->grasp | z_drop | verdict |
|---|---|---|---|---|---|---|
| 0.125 | 0.831 | 0.0511 | +0.0099 | 0.0056 | +0.0010 | HELD |
| **0.130** | 0.876 | **0.0413** | **+0.0001** | 0.0045 | +0.0030 | HELD |
| 0.135 | 0.883 | 0.0399 | -0.0013 | 0.0110 | -0.0002 | HELD |

CALIBRATION CLOSED. 0.130 reproduces to within 0.2 mm across runs (face_gap 0.0415 then
0.0413) and lands 0.1 mm off the cube width. `q_final` 0.876 = the fingers stall on the
cube and convert the residual 0.124 rad of commanded travel into clamp force.

## Files (all additive — Layer 1 untouched)
- `ur5_grasp/assets/rh_p12_rn/` — vendored flat URDF + 5 STLs + ROBOTIS licence.
  Three edits vs upstream xacro: xacro removed / relative mesh paths; `world` link and
  `world_fixed` joint dropped; and **inertias fixed** (upstream ships placeholder
  ixx=iyy=izz=1.0 with the real values commented out — a 22 g fingertip with 1.0 kg·m²
  behaves like a flywheel). `rh_*_2` ixx/izz round to 0.0 upstream -> 1e-5 floor.
- `ur5_grasp/assets/ur5e_rhp12.usd` — merged single-articulation asset.
- `ur5_grasp/tools/make_ur5e_rhp12_usd.py` — URDF->USD, merge, validate + stroke sweep.
  Report: `tools/make_rhp12_report.txt`.
- `ur5_grasp/robots/ur5e_rhp12.py` — ArticulationCfg. Drives ALL FOUR finger joints
  (legal here: tree, no loop to fight). Grip force set by `effort_limit_sim=5.0` Nm
  (~100 N at the pad), NOT by stiffness.
- `ur5_grasp/tasks/lift/ur5e_rhp12_env.py` — `UR5eCubeLiftEnv` subclass with
  `_apply_weld()` as a no-op. Safety-cost channel retained.
- `ur5_grasp/tasks/lift/ur5e_rhp12_env_cfg.py` — env cfg; one binary command over all 4
  joints, so the ACTION SPACE is unchanged from Layer 1 and policies stay comparable.
- `ur5_grasp/scripts/rhp12_grasp_sweep.py` — contact-only hold test + TCP calibration.
- Task ids: `Isaac-Lift-Cube-UR5e-RHP12-v0`, `Isaac-Lift-Cube-UR5e-RHP12-Play-v0`.

## Remaining sim-to-real gaps
- Domain randomization coverage; camera calibration; controller/rate matching.
- Real hardware bring-up: ROS 2 Humble + Universal_Robots_ROS2_Driver, DYNAMIXEL 2.0
  for the hand (the real hand is 1-DOF: drive `rh_p12_rn`, the rest follow mechanically).
- Policy exported to JIT + ONNX by `play.py` (in the checkpoint's `exported/` dir).

## Ready-pose geometry check — PASSED (2026-07-26)
`results/rhp12_geometry_check.txt`. Ran before training because `TCP_OFFSET` had moved
0.085 -> 0.130 and the grasp sweep only ever proved the gripper holds a cube TELEPORTED
between its pads — it never proved the reach target the reward chases is reachable.

| measurement (closed pads) | value | gate | |
|---|---|---|---|
| ee_frame vs pad-origin midpoint | 0.0251 m | < 0.03 | PASS |
| ee_frame height above table | +0.2123 m | > 0.02 | PASS |
| ee_frame -> cube distance | 0.2731 m | 0.05–0.60 | PASS |

The feared failure did not happen: the handoff guessed the grasp point sat only
~0.065–0.078 m above the table, but it is actually at +0.212 m. Nothing is inside the
table and the reach reward is learnable.

The script was FIXED before this run. Its original single-shot check compared ee_frame
against the pad origins with the fingers OPEN (`BinaryJointPositionAction` masks on
`action < 0`, so a zero action leaves the gripper open) and gated at < 0.02 m. That is
apples-to-oranges: the RH-P12-RN fingers CURL FORWARD as they close, so the grasp centre
travels 0.0765 -> 0.1049 m along wrist +z (measured, +0.0284 m). Against the open pose
the error reads 0.0535 m and the script would have "failed" a correct configuration and
recommended replacing 0.130 with ~0.077 — a value outside the 0.125–0.135 band that the
contact sweep proved HELD. It now probes open AND closed, gates only on the closed pose,
separates BLOCKING checks (table height, cube distance) from the advisory frame error,
and states explicitly that the contact sweep is the authority.

Residual 0.0251 m is expected, not error: pad_mid is the r2/l2 BODY ORIGIN midpoint,
which sits behind the flat contact faces, so ee_frame should lead it by about the pad
half-depth.

## Reward shaping decision — dense lift progress (2026-07-26)
DECIDED: shape the reward BEFORE the first full run rather than after a stall. Code:
`ur5_grasp/tasks/lift/rhp12_rewards.py`, wired in `ur5e_rhp12_env_cfg.py`. RH-P12-RN task
only; Layer 1 files untouched.

THE PROBLEM. `lifting_object` is `object_is_lifted`, a step at 0.04 m. Under the weld
that step is free — the latch fires and the cube is up. Without the weld a random policy
must find a pad alignment good enough to hold the cube before it sees ANY lift reward,
and below 0.04 m the only live gradient is `object_ee_distance`, which saturates near the
cube and then goes flat. Hard exploration; the run would measure that, not grasp mechanics.

THE FIX. `object_lift_progress` is a strict superset of the stock term:
`z >= 0.04` -> 1.0 (identical), `z < 0.04` -> gated linear ramp from `rest_height`.
The landscape at and above the threshold is untouched, so `object_goal_distance` still
switches on at the same point and weight 15.0 keeps its meaning. `rest_height = 0.021` is
measured (resting cube centre, `results/rhp12_geometry_check.txt`), not assumed.
Ramp values: z=0.026 -> 3.95, z=0.031 -> 7.89, z=0.036 -> 11.84, z>=0.040 -> 15.00.

WHY NOT A GRASP BONUS. The obvious shaping — "bonus when the gripper is closed and the
cube is near the TCP" — is literally `_apply_weld`'s latch predicate
(`closing & (dist < GRASP_TOL)`). Rewarding it reinstates the weld in reward-space and is
open to the exact criticism this run exists to answer. The dense lift term rewards only
the OUTCOME and says nothing about how to grasp; a UR5e cannot raise a cube without
holding it. `near_tol = 0.05` blocks the one gaming route (batting the cube upward for
transient height) because a flick sends it away from the TCP.

WHAT THIS COSTS. Raw episode reward is now NON-comparable with Layer 1 (cPPO 166.3 /
PPO 167.2). The comparison moves to metrics that do not depend on the reward function:
lift-success % from `scripts/eval_success.py` and safety-violation % from `_apply_cost`.
Both are already implemented and were used for the Layer 1 numbers. State the shaping as
an explicit caveat in the write-up.

## Smoke test PASSED + run plan revised to TWO runs (2026-07-26)
20 iters, 256 envs, shaped env. `lifting_object` 0.1584 (nonzero = the ramp pays, as
required) and `object_goal_tracking` 0.0227 — that term is gated on z > 0.04 m, so the
cube already clears the lift threshold by chance. The success event is REACHABLE, which
is what makes exploration tractable. Safety channel live (manip mean 0.0970 / min 0.0637,
costs 0.0 because MANIP_FLOOR 0.045 is not breached yet; Layer 1 read 0.1010 / 0.0696 at
the same stage).

DO NOT compare this against Layer 1's iteration 19 — 256 envs vs 4096 means 122,880
timesteps here vs 1.97M there. At MATCHED timesteps (L1 iters 0-1, ~98-197k):

| ~100-200k timesteps | L1 weld | RHP12 contact (shaped) |
|---|---|---|
| Mean reward | 0.73-0.84 | 1.22 |
| reaching_object | 0.0019-0.0069 | 0.0723 |
| lifting_object | 0.1182-0.1286 | 0.1584 |
| object_goal_tracking | 0.0197-0.0219 | 0.0227 |
| object_dropping | 0.0000-0.0005 | 0.0423 |

Ahead on every reward term, but THREE things differ at once (shaped reward, 16x smaller
batches, 20 optimizer steps vs 1-2), and more updates on smaller batches makes more
progress per timestep regardless of env. Read it as "nothing is broken", not as evidence
about the weld.

WATCH: `object_dropping` 4.23% vs Layer 1's ~0%. Expected — without the weld the cube is
free to be knocked away. If it CLIMBS during the full run, the policy is learning to sweep
the cube off the table instead of grasping it.

### Run plan revised: TWO runs, not one
Checked the Layer 1 log: 1500 iters / 147,456,000 timesteps / **11 min 19 s** at 220k
steps/s. The handoff's "this is hours" was wrong. At ~11 min a run there is no reason to
choose between shaped and unshaped — run both:

| task id | lift reward | answers |
|---|---|---|
| `Isaac-Lift-Cube-UR5e-RHP12-Stock-v0` | stock 0.04 m step | is the task learnable without the weld AND without help? reward directly comparable with Layer 1 |
| `Isaac-Lift-Cube-UR5e-RHP12-v0` | dense `object_lift_progress` | and how much help does it need? |

The GAP between them is the exploration cost of removing the weld — a measured number,
which is strictly better than the shaped run alone plus a caveat. Added
`UR5eRHP12LiftEnvCfg_STOCK` (+ `_PLAY`) and registered `-Stock-v0` / `-Stock-Play-v0`
rather than reverting the shaping by hand, so both conditions stay reproducible from a
task id forever and the logs self-document which one ran. Same `--seed 42` for both so the
difference is not seed noise.

## RESULTS — both contact runs done (2026-07-26, Day 16)
1500 iters, 4096 envs, seed 42, 15 min each. Logs: `logbook/05_rhp12_ppo_stock.log`,
`logbook/05_rhp12_ppo_shaped.log`. Checkpoints: `IsaacLab/logs/rsl_rl/ur5e_lift/`
`2026-07-26_21-36-58` (stock) and `2026-07-26_22-30-27` (shaped).

| final (iter 1499) | L1 weld PPO | contact STOCK | contact SHAPED |
|---|---|---|---|
| mean reward | 167.18 | 104.28 | 136.59 |
| reaching_object | 0.9293 | 0.7586 | 0.7714 |
| lifting_object | 14.7966 | 13.8378 | 14.4163 |
| object_goal_tracking | 14.8479 | 9.5965 | 12.6716 |
| goal_tracking_fine | 4.1099 | 0.4076 | 1.6488 |
| object_dropping | 0.0000 | 0.0184 | 0.0035 |
| episode length | 250 | 250 | 250 |
| **viol_singularity** | **0.1686** | **0.1398** | **0.9157** |
| cost_total | 0.0201 | 0.0262 | 0.4334 |
| manipulability_mean | 0.0567 | 0.0637 | 0.0287 |
| manipulability_min | 0.0139 | 0.0058 | 0.0002 |

viol_collision and viol_joint_limit are 0.0000 in ALL THREE runs — singularity remains the
only active constraint, as in Layer 1.

### FINDING 1 — the weld did not fabricate the task
STOCK learned to grasp and lift with real finger contact, no weld, and NO reward help:
`lifting_object` 13.84 of a 15.0 maximum (94% of the weld run's 14.80). This is Layer 3's
minimum defensible result and it is now secured.

### FINDING 2 — the cost of the weld, measured
STOCK and Layer 1 use IDENTICAL reward functions, so their rewards are directly
comparable. 167.18 -> 104.28 = **-37.6% episode reward** at an equal training budget.
The loss concentrates in the precision terms, not in grasping: `lifting_object` only
falls 6%, but `object_goal_tracking` falls 35% (14.85 -> 9.60) and the fine-grained
term collapses 90% (4.11 -> 0.41). Reading: contact grasping succeeds about as often,
but the held cube is placed far less precisely — a real contact grip lets the cube shift
in the fingers, whereas the weld pinned it rigidly to the TCP. That is the honest
statement of what the abstraction bought.

### FINDING 3 — the Layer 1 SAFETY claim survives contact grasping
Baseline singularity violation: weld PPO 16.86% vs contact STOCK 13.98%. Same ballpark,
and slightly LOWER without the weld. So the Layer 1 cPPO-vs-PPO result is not an artifact
of the weld — the constraint behaves the same way when the grasp is real. `MANIP_FLOOR`
= 0.045 transfers exactly, because manipulability is computed from the ARM Jacobian at
`wrist_3_link` and the gripper swap does not change arm kinematics.

### FINDING 4 — the reward shaping BACKFIRED, and this is the most interesting result
SHAPED bought +31% reward over STOCK (136.59 vs 104.28) and paid for it with a **6.5x
increase in singularity violations: 91.57% vs 13.98%**, cost_total 16x higher (0.4334 vs
0.0262), and manipulability_min driven to 0.0002 — effectively parked ON a singularity.
It is not a transient exploration phase: violation climbed from ~60% around iteration 480
to 91% by 1100 and stayed flat there for 400 iterations. STOCK, on the same env with the
same seed, learned AWAY from singularities (peak 42% at iter 300 -> 14% at the end).

Interpretation: the dense lift ramp pays for the time-integral of "cube raised AND within
`near_tol` of the TCP", and the cheapest way to hold that pose turns out to be a
near-degenerate wrist configuration. Plain PPO has no reason to resist — nothing in its
objective mentions the cost channel. An apparently innocuous, well-motivated shaping term
silently traded safety for task reward, and ONLY the cost channel revealed it.

That is a textbook argument for constrained RL, produced accidentally, on this thesis's
own hardware. It is a stronger motivation for cPPO than the Layer 1 numbers are.

### CAVEATS
- One seed per condition. The 91.57% vs 13.98% gap is far too large to be seed noise, but
  the -37.6% reward gap deserves a second seed before it goes in the thesis as a number.
- SHAPED's reward is NOT comparable with Layer 1 (different reward function). Its per-term
  values for the UNCHANGED terms (reach, goal, goalfine, dropping) still are.
- Both weld and STOCK drift upward in violation over the last ~200 iterations (STOCK peaks
  28.87% at iter 1420 before settling to 13.98%). Neither is fully converged on safety.

## Next steps
1. DONE — `TCP_OFFSET = 0.130` locked in `robots/ur5e_rhp12.py`.
2. DONE — confirmed at 0.125/0.130/0.135, all HELD, 0.130 within 0.1 mm of cube width.
3. DONE — ready-pose geometry check PASSED (see section above). Cleared for training.
4. DONE — dense lift reward added (see section above).
5. SMOKE TEST the training loop before committing GPU hours:
   `--task Isaac-Lift-Cube-UR5e-RHP12-v0 --headless --num_envs 256 --max_iterations 20`
   Watching for: NaNs, contact-buffer overflow at scale, and whether `lifting_object`
   moves off zero at all.
6. Train PPO full (`--num_envs 4096`, 1500 iters) and compare with the Layer 1 weld
   baseline. This is the thesis payoff: it turns the weld from an unexamined shortcut
   into a measured, justified abstraction.
   WATCH FOR: the reward shaping was tuned for the weld, where grasping is free. With
   real contact the grasp must be discovered, so exploration is materially harder and
   PPO may need more iterations or a shaped grasp bonus. A slower learning curve here is
   a FINDING about the weld's cost, not a failure — record it either way.
7. Only then consider a cPPO run on this env.

### What the comparison must show for the weld to stay defensible
The thesis claim is about SAFETY (cPPO vs PPO violation rates), not about grasp
mechanics. So the weld is a valid abstraction if swapping in real contact leaves that
claim intact: PPO still learns the task, and the cPPO-vs-PPO singularity-violation gap
reproduces in DIRECTION and roughly in MAGNITUDE. If instead contact grasping pushes the
policy into near-singular wrist poses to close the fingers, then the weld was hiding an
interaction between grasping and the safety constraint, and that must be stated openly.
Minimum defensible version if time runs short: PPO alone on the contact env, showing the
task is learnable without the weld. That proves the weld did not fabricate the task.

## run_log.md refs
Day 16 (2026-07-26).
