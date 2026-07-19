# 02 — The UR5e Grasp Environment & PPO Baseline

**Status:** ✅ Done · **Layer:** 1 (must-pass) · **Roadmap:** Weeks 5–8

**Goal of this section:** build a simulated task where a **UR5e** arm learns to **reach, grasp, and
lift** a cube, and train a **plain PPO** policy on it as the *baseline* we will later compare
against safe RL (cPPO). When you finish, the arm reliably picks up and lifts the cube in
simulation, and you have a saved checkpoint.

> This section documents real dead-ends and the fixes, because a beginner *will* hit the same
> walls. Skipping them would make the docs un-replicable.

---

## 1. The plan — don't build a task from scratch

**Why:** writing an RL grasping task from zero is huge. Isaac Lab already ships a **Franka lift**
environment — the canonical "reach, grasp, lift a cube to a goal" task with the reward shaping and
privileged object-pose observations we want. We **retarget** it to the UR5e instead of reinventing
it.

"Privileged pose info" means: during simulation training we *let the policy read the exact cube
position* (something a real camera would have to estimate). This is standard for Layer 1 — it
isolates the *safe-grasping* question from the *perception* question, which is Layer 2's job.

Our code lives in a **separate, git-tracked package** `ur5_grasp/`, kept apart from the (huge,
un-committed) `IsaacLab/` clone.

---

## 2. The robot and the gripper decision

**The arm:** UR5e, from Isaac's built-in asset library (Nucleus):

```
{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd
```

It has 6 arm joints (`shoulder_pan`, `shoulder_lift`, `elbow`, `wrist_1/2/3`) and ships with a
built-in **Robotiq 2f-85** gripper variant.

**Key decision — which gripper (2026-07-12):**

- **Simulation (Layer 1): use the built-in Robotiq 2f-85.** The cPPO-vs-PPO safe-RL result is
  *gripper-agnostic* (the policy only outputs one normalised open/close number), so we use the free
  built-in gripper to protect the Layer 1 timeline.
- **Real robot: ROBOTIS RH-P12-RN.** This different gripper is imported into sim only during the
  **Layer 3** sim-to-real window (details parked in `05_Layer3_SimToReal.md`). This mismatch is
  logged as a known sim-to-real gap.

> **Beginner note — what a USD is.** Isaac describes robots and scenes in `.usd` files (Universal
> Scene Description — think "the 3D file format for the simulator"). We combine the arm USD and the
> gripper USD into one file the simulator can treat as a single robot.

---

## 3. Merge arm + gripper into one articulation

**Why:** the physics engine treats a robot as one **articulation** (one connected chain of joints).
The arm and the gripper start as two separate articulations; we must merge them into one or the
trainer gets confused.

The tool that does this:

```bash
# builds ur5_grasp/assets/ur5e_robotiq_2f85.usd
python ur5_grasp/tools/make_ur5e_robotiq_usd.py
```

**What it does / why:** it stitches the Robotiq gripper onto the UR5e flange and **disables the
gripper's nested articulation root**, so the whole thing loads as *one* articulation.

**Expected result:** the merged USD loads cleanly as **one articulation: 12 joints / 16 bodies**.
The gripper's driven joint is `finger_joint` (0 = open, ~0.8 = closed); the other five finger
joints are mechanically coupled.

---

## 4. Scaffold the environment and register the task

**Why:** Isaac Lab finds tasks by a **gym id** (a string name). We register our retargeted env so
we can launch it by name, exactly like the built-in tasks.

The `ur5_grasp/` package registers:

- `Isaac-Lift-Cube-UR5e-v0` — the training task.
- `Isaac-Lift-Cube-UR5e-Play-v0` — the same task set up for *watching* a trained policy (fewer
  envs, GUI-friendly).

with its own launcher at `ur5_grasp/scripts/train.py`. The env swaps in the UR5e robot config, a
6-joint arm action, a binary gripper action, and an end-effector frame (root `base_link`, target
`wrist_3_link`, with a ~0.16 m offset down to the fingertips).

**First smoke test (tiny, cheap):**

```bash
cd ~/Abdur_Rabbi_THESIS/IsaacLab
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 64 --max_iterations 10
```

**Expected (Day 7 result):** env loads as one articulation, all reward terms compute, the reach
reward rises, episode length grows (20 → ~127), no crash. This proves the Layer 1 infrastructure
works before spending hours on a full run.

---

## 5. The three bugs on the way to a full run (and their fixes)

A full-size run (4096 envs) exposed three failures. This is the most important part of the section
to read, because each fix encodes a real lesson about simulating a grippered arm.

**Bug #1 — hang at "Starting the simulation" (4096 envs).**
*Cause:* `enabled_self_collisions=True` on the multi-body gripper overflowed the GPU's
contact-pair buffers.
*Fix:* set `enabled_self_collisions=False` (this matches Isaac Lab's own convention for grippered
arms).

**Bug #2 — NaN crash around iteration 35 (`normal expects std >= 0.0`).**
*Cause:* all six 2f-85 joints were actively driven, so the motors fought the closed-loop 4-bar
linkage of the gripper until the physics blew up.
*Fix:* drive **only** `finger_joint`; leave the coupled joints **passive** (stiffness/damping 0),
mirroring Isaac Lab's UR10e-Robotiq split. Bonus: the mechanical linkage then closes the fingers
for free.

**Bug #2b — still NaN around iteration 92.**
*Cause:* the passive-but-undamped linkage accumulated energy in the loop constraint.
*Fix:* add `armature=0.01` + `friction=0.1` to the gripper joints, `damping=0.5` on the passive
joints, `armature=0.01` on the arm joints, plus an **observation clamp `(-100, 100)`** as a NaN
firewall.

> **Beginner takeaway.** A NaN crash in RL almost always means the *physics* went unstable, not the
> learning algorithm. The fixes here — don't over-drive coupled joints, add a little
> armature/damping, clamp observations — are the standard toolkit for taming an unstable simulated
> mechanism.

---

## 6. First full PPO run — and why it was thrown away

**The run itself succeeded:**

```bash
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096
```

**Expected training signals (Day 7):** clean 1500-iter run, no NaN; `mean_reward` 0.72 → ~8.5
(peak 10.6); the `lifting_object` reward term rose 0.12 → 2.16 — numerically, the arm was grasping
and lifting.

**But visual verification FAILED (Day 8).** Watching the policy, the arm **flings the cube** instead
of holding it.

*Diagnosis:* the base lift reward pays out for the cube being above 4 cm **without requiring it to
be held**. So the policy found a shortcut — *throw the cube upward* to collect height reward. This
is a classic **reward hack**. The same reward works for Franka because Franka's gripper actually
holds; ours did not.

*Root cause of the no-hold:* the Robotiq 2f-85's passive finger pads (stiffness 0) transmit **no
normal force**, so a closed gripper can't actually grip. Bumping finger stiffness 20→400 and effort
50→200 did not help (no force, though also no NaN). This is a known limitation of that gripper's
closed-loop model in sim.

---

## 7. The fix — a proximity "weld" grasp

**Why:** rather than fight the gripper's force model (a rabbit hole that risks the Layer 1
deadline), we make grasping *reliable in the RL sense* with a **proximity weld** — a pre-agreed
escape hatch.

**How it works** (env class `tasks/lift/ur5e_lift_env.py:UR5eCubeLiftEnv`): when the gripper
**commands CLOSE** *and* the cube is within `GRASP_TOL = 0.06 m` of the reach frame, the cube
**latches** to the gripper — its pose tracks the reach frame and its velocity is zeroed. Opening the
gripper releases it.

**Two wins:**
1. The grasp now holds, so the arm can actually lift.
2. Throwing becomes impossible, so the height reward is **no longer hackable**.

**Verification (hold test):** with the weld, a closed grip holds the cube at pad level for 210+
steps, no NaN. Grasp is now reliable.

Registered for both `-v0` and `-Play-v0`.

> **Honesty note for the write-up.** The weld is a *sim abstraction* of a grasp, not a physical
> force model. That's fine and common for safe-RL research (the contribution is the *safe control*,
> not gripper contact physics), but it must be stated plainly in the thesis and revisited in Layer
> 3 with the real gripper.

---

## 8. Retrain the PPO baseline on the weld env

**Why:** the first checkpoint learned the throwing hack and is dead. cPPO will reuse this exact
env, so the baseline **must** be retrained on the weld before any comparison is meaningful.

```bash
cd ~/Abdur_Rabbi_THESIS/IsaacLab
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096
```

**What to watch (pass vs fail):**

| Signal | Pass | Fail |
|--------|------|------|
| `Train/mean_reward` | climbs 0.7 → ~8+ and holds | flat, or NaN |
| `Episode/...lifting_object` | rises over training | stays ~0 |
| Any NaN / `std >= 0.0` crash | none (the obs clamp should prevent it) | crash |

Stop at ~**1500 iterations** — don't chase convergence. The retrained checkpoint lands in
`IsaacLab/logs/rsl_rl/ur5e_lift/`.

---

## 9. Watch the trained policy (visual verification gate)

**Why:** numbers can lie (see the throwing hack). *Always* watch the policy before trusting it.

```bash
./isaaclab.sh -p ../ur5_grasp/scripts/play.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 9 --real-time
```

**Pass condition:** real **reach → close-near-the-cube → lift-to-goal**, with **no flinging**. If it
flings, stop and revisit the reward/weld before moving to safety work — cPPO inherits this exact
env, so a broken grasp here poisons the whole benchmark.

`play.py` also exports the policy to **JIT/ONNX** formats, which Layer 3 will need to deploy the
policy onto the real robot over ROS 2.

---

## What "done" looks like for this section

- Merged UR5e + 2f-85 USD loads as one articulation (12 joints / 16 bodies).
- `Isaac-Lift-Cube-UR5e-v0` is registered and passes the 64-env smoke test.
- The weld env holds the cube (hold test 210+ steps, no NaN).
- A PPO baseline is trained on the weld env (~1500 iters, `mean_reward` ~8+).
- `play.py` shows a real reach-grasp-lift with no throwing.

With a trustworthy baseline in hand, continue to `03_Safety_and_cPPO_Benchmark.md` — the core
Layer 1 deliverable.
