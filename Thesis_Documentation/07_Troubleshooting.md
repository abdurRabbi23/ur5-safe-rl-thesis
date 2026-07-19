# 07 — Troubleshooting (every bug hit + the fix)

**Status:** ▶ Growing — add a row whenever a new problem is solved.

This is the single most valuable page for anyone replicating the thesis. Most reproduction failures
come from *undocumented errors*. Every wall hit during this project is recorded here with the cause
and the fix, so you don't lose the days we lost.

---

## Environment / stack

**PyTorch doesn't see the GPU / `sm_120 is not compatible` warning.**
Cause: a non-`cu128` PyTorch build; Blackwell needs CUDA 12.8. Fix: reinstall with
`pip install torch==2.7.0 … --index-url https://download.pytorch.org/whl/cu128`. Verify with the
one-liner in section 01.

**Commands fail with "module not found" in a fresh terminal.**
Cause: new NoMachine terminals open in `(base)`, not the project env. Fix: `conda activate isaaclab`
— confirm the prompt shows `(isaaclab)`.

**Isaac Sim `TiledCamera` hangs / freezes on the RTX 5090.**
Cause: `TiledCamera` is broken on Blackwell under this Isaac Sim. Fix: use the plain **`Camera`**
sensor instead (identical output at `num_envs=1`). Relevant in Layer 2.

**Training crashes at startup: URDF importer wants `2.4.31` but Isaac Sim ships `2.4.19`.**
Cause: the Isaac Lab clone was on the `release/2.3.0` **branch tip**, which advanced to 2.3.1 and
exact-pinned a newer importer. Fix: check out the **tag**: `git checkout -b frozen/2.3.0 v2.3.0`.
**Lesson: pin Isaac Lab to the v2.3.0 tag, never the branch.**

---

## Grasp environment (grippered arm)

**Hang at "Starting the simulation" with 4096 envs.**
Cause: `enabled_self_collisions=True` on the multi-body gripper overflowed GPU contact-pair
buffers. Fix: `enabled_self_collisions=False` (Isaac Lab's convention for grippered arms).

**NaN crash ~iter 35: `normal expects std >= 0.0`.**
Cause: all six gripper joints actively driven, fighting the closed 4-bar linkage → physics blow-up.
Fix: drive only `finger_joint`; make the coupled joints passive (stiffness/damping 0).

**Still NaN ~iter 92 after making joints passive.**
Cause: undamped passive linkage builds up energy in the loop constraint. Fix: add `armature=0.01` +
`friction=0.1` on gripper joints, `damping=0.5` on passive joints, `armature=0.01` on arm joints,
and an observation clamp `(-100, 100)` as a NaN firewall.

**Policy trains to high reward but throws the cube instead of holding it.**
Cause: reward hack — height reward pays out without requiring the cube be *held*; the 2f-85's
passive pads transmit no normal force, so the gripper can't truly grip. Fix: the **proximity weld**
(section 02) — latch the cube when the gripper commands CLOSE within `GRASP_TOL=0.06 m`; this also
makes throwing impossible. Then **retrain** (the old checkpoint is reward-hacked and dead).

**`play.py` grasp-hold test: cube falls straight through a closed gripper.**
Cause: same passive-pad no-force problem; raising finger stiffness (20→400) / effort (50→200) did
not help. Fix: the weld, as above.

**Reach-frame probe reports "offset = 0" / "true grasp point == wrist_3".**
Cause: an artifact — the inner-finger body origins sit at the flange. This is *not* a real zero
offset. Fix: **keep `offset = 0.16` m**, do NOT zero it. (Confirmed twice, Day 8 and Day 9.)

---

## cPPO / safety benchmark

**`KeyError: 'cost'` in `process_env_step`.**
Cause: the env isn't emitting cost (COST_ENABLED off, or `extras` overwritten). Check the env emits
`extras["cost"]` for both agents.

**Traceback in `_manipulability` / index error, or `manipulability_mean` ~0 or absurdly huge.**
Cause: the Jacobian body-axis index is wrong for this asset (the code auto-detects fixed-base vs
floating-base; a mismatch breaks it). Sanity: `w` should spread ≈0.01–0.1. Confirmed correct when
the smoke test showed `manipulability_mean = 0.11`.

**Constraints read 0 / never violated (benchmark is meaningless).**
Cause: thresholds set where unconstrained PPO never breaks them. Fix: **calibrate from the trained
baseline** so the active constraint bites ~20% of the time (section 03, step 4).

**`cost_lambda` railed at `lambda_max = 100`, or reward collapses to ~0.**
Cause: over-constrained — `cost_limit` too tight or `lambda_lr` too high. Fix: loosen `cost_limit`
or lower `lambda_lr`.

**PPO baseline and cPPO cost curves aren't comparable.**
Cause: baseline trained at an old `MANIP_FLOOR` (e.g. 0.02) where its cost is ~0. Fix: re-run the
unconstrained PPO baseline at the **same floor (0.045)** used by cPPO.

---

## Workflow / infrastructure

**A training run dies when the NoMachine connection drops.**
Cause: the run was a child of the SSH/desktop shell. Fix: always launch training **inside tmux**
(`tmux new -s thesis_abrabbi`; detach Ctrl-b then d; reattach `tmux attach -t thesis_abrabbi`).

**TensorBoard: browser says "connection refused".**
Cause: the TensorBoard *process is down*. Fix: restart it.

**TensorBoard: page just hangs (never loads).**
Cause: *network/firewall* — process is fine, traffic isn't reaching it. Fix: check the address /
VPN (Tailscale) / `--bind_all`.
