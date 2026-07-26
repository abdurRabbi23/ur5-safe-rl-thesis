# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""RH-P12-RN grasp test + TCP calibration in one run (physics only, no policy).

Answers the two open questions together:

  Q1  Does the RH-P12-RN actually hold a cube with CONTACT FORCES (no weld)?
  Q2  Where exactly along wrist +z is the grasp point?

Why they have to be answered together: the build report showed the pad midpoint is NOT
a fixed point — the fingers curl forward as they close, so it travels 0.0767 m (open)
to 0.1049 m (closed) from wrist_3_link. A single guessed `TCP_OFFSET` can therefore fail
for a geometric reason that looks exactly like "the grip is too weak". So sweep the
offset and let the physics pick.

PROCEDURE (per candidate offset)
  1. reset, settle at the ready pose with the gripper OPEN,
  2. teleport the cube to wrist_pos + R_wrist @ [0, 0, offset], zero its velocity,
  3. command CLOSE and hold ~2 s of physics,
  4. measure how far the cube ended up from the gripper, and how far it fell.

VERDICT per row: HELD if the cube is still within HOLD_TOL of the grasp point at the end.

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/rhp12_grasp_sweep.py \
        --task Isaac-Lift-Cube-UR5e-RHP12-Play-v0 --num_envs 1 --headless

Drop --headless to watch it. Writes results/rhp12_grasp_sweep.txt.
"""

"""Launch Isaac Sim Simulator first."""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

# --- make the external ur5_grasp package importable ------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
# --------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="RH-P12-RN grasp hold test + TCP sweep.")
parser.add_argument("--disable_fabric", action="store_true", default=False)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--task", type=str, default="Isaac-Lift-Cube-UR5e-RHP12-Play-v0")
parser.add_argument("--offsets", type=str, default="0.060 0.070 0.075 0.080 0.085 0.090 0.095 0.100 0.110")
parser.add_argument(
    "--seat_steps",
    type=int,
    default=45,
    help="control steps during which the cube is held still while the fingers close around it",
)
parser.add_argument("--hold_steps", type=int, default=120, help="control steps of free physics after seating")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import torch

from isaaclab.utils.math import quat_apply

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import ur5_grasp.tasks  # noqa: F401  # registers the task
from ur5_grasp.robots.ur5e_rhp12 import GRIPPER_JOINT_NAMES

SETTLE_STEPS = 30       # let the arm reach the ready pose with the gripper open
HOLD_TOL = 0.05         # m — cube still "in the hand" if within this of the grasp point

# `pad_gap` is measured between the r2/l2 BODY ORIGINS. The gripping faces sit closer
# together than that by the inset of each pad mesh (r2 spans y = -0.0039 .. +0.018 in
# its own frame), so the clear opening is pad_gap - 2*0.0039.
PAD_FACE_INSET = 0.0078
# DexCube edge 0.0515 m at the env's 0.8 scale.
CUBE_WIDTH = 0.0412
REPORT = os.path.normpath(os.path.join(_HERE, "..", "..", "results", "rhp12_grasp_sweep.txt"))


def main():
    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env = gym.make(args_cli.task, cfg=env_cfg)

    inner = env.unwrapped
    obj = inner.scene["object"]
    robot = inner.scene["robot"]
    device = inner.device

    offsets = [float(v) for v in args_cli.offsets.split()]
    rows = []

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    fh = open(REPORT, "w")

    def log(msg=""):
        print(msg, flush=True)
        fh.write(msg + "\n")
        fh.flush()

    log("=" * 78)
    log("RH-P12-RN GRASP SWEEP — contact-only hold test (no weld)")
    log("=" * 78)
    log(f"task      : {args_cli.task}")
    log(f"hold      : {args_cli.hold_steps} control steps after CLOSE")
    log(f"hold_tol  : {HOLD_TOL} m")
    log("")
    log(f"seat      : {args_cli.seat_steps} control steps with the cube held still")
    log("")
    log(f"cube width: {CUBE_WIDTH:.4f} m  <- face_gap should land ON this for a true pad grip")
    log("")
    log("  offset(m)   q_final   face_gap(m)   cube->grasp(m)   z_drop(m)   verdict")

    # NOTE: the WHOLE sweep — including every env.reset() — must sit inside a single
    # inference_mode block. The env publishes safety-cost tensors into `self.extras`
    # during step(); those become inference tensors, and a later reset() called outside
    # inference mode tries to update them in place, which PyTorch forbids
    # ("Inplace update to inference tensor outside InferenceMode"). Resetting once, as
    # grasp_hold_test.py does, hides the problem; sweeping in a loop exposes it.
    with torch.inference_mode():
        env.reset()
        wid = robot.find_bodies("wrist_3_link")[0][0]
        r2 = robot.find_bodies("rh_p12_rn_r2")[0][0]
        l2 = robot.find_bodies("rh_p12_rn_l2")[0][0]
        gid, _ = robot.find_joints(GRIPPER_JOINT_NAMES)
        act = torch.zeros(env.action_space.shape, device=device)
        local = torch.zeros((inner.num_envs, 3), device=device)
        zero6 = torch.zeros((inner.num_envs, 6), device=device)

        def grasp_point():
            return robot.data.body_pos_w[:, wid] + quat_apply(robot.data.body_quat_w[:, wid], local)

        for off in offsets:
            env.reset()

            # 1. settle with the gripper OPEN
            for _ in range(SETTLE_STEPS):
                act[:] = 0.0
                env.step(act)

            # 2. place the cube at wrist + R_wrist @ [0,0,off]
            local[:] = 0.0
            local[:, 2] = off
            grasp_pt = grasp_point()
            start_z = grasp_pt[0, 2].item()

            pose = torch.zeros((inner.num_envs, 7), device=device)
            pose[:, 0:3] = grasp_pt
            pose[:, 3] = 1.0                                # identity quat (w,x,y,z)
            obj.write_root_pose_to_sim(pose)
            obj.write_root_velocity_to_sim(zero6)

            # 3. SEAT PHASE — close the fingers around a cube that is held still.
            #    Without this the cube free-falls out of the open jaw during the ~0.2 s
            #    the gripper takes to close, and every offset "fails" for a reason that
            #    has nothing to do with grip strength. This is the hand-of-God step; it
            #    is a test fixture only, NOT the weld (it is switched off below).
            for _ in range(args_cli.seat_steps):
                act[:] = 0.0
                act[:, -1] = -1.0                           # negative = CLOSE
                env.step(act)
                pose[:, 0:3] = grasp_point()
                obj.write_root_pose_to_sim(pose)
                obj.write_root_velocity_to_sim(zero6)

            # Diagnostics at the end of seating, BEFORE gravity is allowed to act.
            q_final = robot.data.joint_pos[0, gid].mean().item()
            pad_gap = torch.norm(
                robot.data.body_pos_w[0, r2] - robot.data.body_pos_w[0, l2]
            ).item()

            # 4. HOLD PHASE — stop helping. Contact forces alone from here.
            for _ in range(args_cli.hold_steps):
                act[:] = 0.0
                act[:, -1] = -1.0
                env.step(act)

            # 5. measure against the CURRENT grasp point (the hand may have drifted)
            cube = obj.data.root_pos_w
            dist = torch.norm(cube - grasp_point(), dim=-1)[0].item()
            drop = start_z - cube[0, 2].item()

            face_gap = pad_gap - PAD_FACE_INSET
            held = dist < HOLD_TOL
            rows.append((off, dist, drop, held, q_final, face_gap))
            log(
                f"   {off:6.3f}    {q_final:6.3f}    {face_gap:7.4f}       {dist:8.4f}"
                f"       {drop:+7.4f}    {'HELD' if held else 'dropped'}"
            )

    log("")
    good = [r for r in rows if r[3]]
    log("=" * 78)
    log(" READ q_final FIRST — it says WHICH failure you have:")
    log("   q_final ~ 1.00  the fingers closed all the way with nothing in the way, so")
    log("                   they never touched the cube. That is a GEOMETRY or COLLIDER")
    log("                   problem (wrong offset band, or the convex decomposition")
    log("                   produced no usable pad geometry). Friction is irrelevant.")
    log("   q_final ~ 0.78  the fingers stalled on the cube. Contact is real and the")
    log("                   residual position error is being converted into clamp force.")
    log("                   If it still dropped, NOW it is a friction / effort problem.")
    log("")
    if not good:
        log(" NO OFFSET HELD.")
        log(" If q_final stalled (< ~0.95) but the cube still fell, tune in THIS order,")
        log(" one at a time, re-running between each:")
        log("   1. pad friction — add a high-friction physics material to rh_p12_rn_r2/l2;")
        log("      default material friction is ~0.5 and a smooth DexCube will squirt out.")
        log("   2. effort_limit_sim on the 'gripper' actuator in robots/ur5e_rhp12.py")
        log("      (5.0 Nm now). Raise toward 10.0 if the cube is squeezed but slides.")
        log("   3. solver_position_iteration_count (16 now) if the cube jitters or")
        log("      sinks into the pads rather than resting on them.")
        log(" Do NOT raise stiffness first — that fights the solver and was the failure")
        log(" mode on the Robotiq.")
    else:
        log(f" GRIP HOLDS at {len(good)}/{len(rows)} offsets: {[f'{r[0]:.3f}' for r in good]}")
        # HELD is a coarse binary and the swept range may be truncated, so an arithmetic
        # "centre of the holding band" is a misleading statistic. Choose on the physics:
        # a true parallel-pad grip is the offset whose face_gap lands ON the cube width.
        # Too wide => the cube is wedged on the curved proximal links, not the pads.
        # Too narrow => the pads are compressing the cube and relying on penetration.
        seat = min(good, key=lambda r: abs(r[5] - CUBE_WIDTH))
        log("")
        log(f"   offset {seat[0]:.3f} m has face_gap {seat[5]:.4f} vs cube {CUBE_WIDTH:.4f}"
            f"  (delta {seat[5] - CUBE_WIDTH:+.4f})")
        log("   -> that is the TRUE PAD GRIP. Prefer it for TCP_OFFSET.")
        log("")
        log(" Sanity checks before you lock it in:")
        log("   * face_gap MUCH WIDER than the cube but still 'HELD' means the cube is")
        log("     wedged on the curved r1/l1 links, not held by the flat pads. It will")
        log("     hold in a static test and fail under the accelerations of a real lift.")
        log("   * face_gap NARROWER than the cube means the pads are interpenetrating it;")
        log("     the hold is partly solver depenetration, not friction.")
        log("   * if EVERY swept offset held, the band is truncated — extend the sweep")
        log("     until you find the edge, then re-read this line.")
    log("=" * 78)
    log(f"[saved to {REPORT}]")

    fh.close()
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
