# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Physics-only grasp HOLDING test (no policy, no reward, no IK).

Isolates the one question the reward-hacking hides: can the 2f-85 actually clamp
a cube and hold it against gravity? Procedure:
  1. reset, let the arm settle at its ready pose (gripper open),
  2. teleport the cube to the reach-frame point (between the finger pads), zero its
     velocity,
  3. command the gripper CLOSE and hold,
  4. print the cube's height over time. If it stays near pad level -> HOLDS.
     If it falls to the table (~0.02 m) -> the grip is too weak.

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/grasp_hold_test.py \
        --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1
"""

"""Launch Isaac Sim Simulator first."""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

# --- TOUHID: make external ur5_grasp package importable --------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
# --------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Physics-only grasp holding test.")
parser.add_argument("--disable_fabric", action="store_true", default=False)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--task", type=str, default=None)
parser.add_argument("--no_weld", action="store_true", default=False,
                    help="disable the proximity weld to test TRUE contact physics")
parser.add_argument("--freeze_cube", action="store_true", default=False,
                    help="hold the cube fixed at the grasp point so gravity can't remove it "
                         "before the fingers close (isolates contact from free-fall)")
parser.add_argument("--grip_fix", action="store_true", default=False,
                    help="test the CORRECTED grasp: open the hand first, place the cube at the "
                         "true pad midpoint, then physically close (finger_joint->0). Confirms a "
                         "real hold is possible once the open/close inversion + frame offset are fixed.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import ur5_grasp.tasks  # noqa: F401  # TOUHID: registers the task


def main():
    env_cfg = parse_env_cfg(
        args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs, use_fabric=not args_cli.disable_fabric
    )
    env = gym.make(args_cli.task, cfg=env_cfg)
    env.reset()

    scene = env.unwrapped
    if args_cli.no_weld:
        scene._apply_weld = lambda: None   # true contact physics only
        print("\n[--no_weld] proximity weld DISABLED — testing real finger contact\n")
    obj = scene.scene["object"]
    ee = scene.scene["ee_frame"]
    device = scene.device

    # --- diagnostic: watch the gripper joints so we can tell force vs geometry ---
    try:
        robot = scene.scene["robot"]
    except KeyError:
        robot = scene.scene["Robot"]
    jnames = list(robot.joint_names)
    grip_ids = [i for i, n in enumerate(jnames) if ("finger" in n or "knuckle" in n)]
    grip_names = [jnames[i] for i in grip_ids]
    print("[gripper joints tracked]", grip_names)

    # pad bodies (the inner fingers that actually touch the cube) for gap measurement
    bnames = list(robot.body_names)
    pad_ids = [i for i, n in enumerate(bnames) if "inner_finger" in n and "knuckle" not in n]
    wrist_ids = [i for i, n in enumerate(bnames) if n == "wrist_3_link"]
    print("[pad bodies tracked]", [bnames[i] for i in pad_ids])

    # zero action template; last slot is the gripper (negative = close)
    act = torch.zeros(env.action_space.shape, device=device)

    WARMUP = 30       # let the arm settle at ready pose (gripper open)
    PLACE_AT = 30     # teleport the cube between the pads here
    HOLD_UNTIL = 220  # keep closing until this step
    placed = False
    grasp_point = None
    frozen_pose = None   # set at placement; re-applied each step when --freeze_cube

    step = 0
    while simulation_app.is_running() and step <= HOLD_UNTIL:
        with torch.inference_mode():
            if args_cli.grip_fix:
                # measured convention: act<0 -> finger_joint 0.8 = physically OPEN,
                #                      act>0 -> finger_joint 0.0 = physically CLOSED
                act[:] = 0.0
                act[:, -1] = -1.0 if step < PLACE_AT else +1.0   # open first, then real close
            elif step < PLACE_AT:
                act[:] = 0.0                     # legacy path (mislabeled convention)
            else:
                act[:] = 0.0
                act[:, -1] = -1.0

            env.step(act)
            step += 1

            # place the cube between the pads once, after warmup
            if not placed and step == PLACE_AT:
                grasp_point = ee.data.target_pos_w[0, 0].clone()   # reach frame (wrist+0.16)
                # where to drop the cube: reach frame (legacy) vs TRUE pad midpoint (grip_fix)
                if args_cli.grip_fix and len(pad_ids) >= 2:
                    place_pt = robot.data.body_pos_w[0, pad_ids].mean(dim=0).clone()
                else:
                    place_pt = grasp_point
                root_pose = torch.zeros((scene.num_envs, 7), device=device)
                root_pose[:, 0:3] = place_pt
                root_pose[:, 3] = 1.0            # identity quaternion (w,x,y,z)
                obj.write_root_pose_to_sim(root_pose)
                obj.write_root_velocity_to_sim(torch.zeros((scene.num_envs, 6), device=device))
                frozen_pose = root_pose.clone()
                placed = True   # (bugfix) enables --freeze_cube; was never set before
                grasp_point = place_pt.clone()  # report distances relative to where we actually placed it
                # --- measure the correct EE-frame offset so Bug 2 can be fixed exactly ---
                if len(pad_ids) >= 2 and wrist_ids:
                    pad_mid = robot.data.body_pos_w[0, pad_ids].mean(dim=0)
                    w_pos = robot.data.body_pos_w[0, wrist_ids[0]]
                    delta_w = (pad_mid - w_pos)
                    print(f"[offset check] pad-midpoint - wrist_3 (world) = "
                          f"[{delta_w[0]:+.3f}, {delta_w[1]:+.3f}, {delta_w[2]:+.3f}] m, "
                          f"|delta| = {torch.norm(delta_w).item():.3f} m "
                          f"(current cfg uses [0,0,0.16])")
                print(f"\n[placed cube at z={place_pt[2]:.3f}] "
                      f"{'REAL close' if args_cli.grip_fix else 'closing'} gripper...\n")

            # keep the cube pinned at the grasp point so free-fall can't hide contact
            if placed and args_cli.freeze_cube and frozen_pose is not None:
                obj.write_root_pose_to_sim(frozen_pose)
                obj.write_root_velocity_to_sim(torch.zeros((scene.num_envs, 6), device=device))

            # report cube height a few times while holding
            if grasp_point is not None and step % 10 == 0:
                cz = obj.data.root_pos_w[0, 2].item()
                gz = grasp_point[2].item()
                held = "HELD" if (cz > gz - 0.05) else "DROPPED"
                gp = robot.data.joint_pos[0, grip_ids].tolist()
                gp_str = "  ".join(f"{n}={v:+.3f}" for n, v in zip(grip_names, gp))
                dxy = torch.norm(obj.data.root_pos_w[0, :2] - grasp_point[:2]).item()
                print(f"  step {step:4d} | cube z = {cz:+.3f}  (pad z {gz:+.3f})  -> {held}"
                      f" | cube-XY off pads = {dxy*1000:5.1f} mm")
                print(f"           gripper: {gp_str}")
                if len(pad_ids) >= 2:
                    pads = robot.data.body_pos_w[0, pad_ids]        # (>=2, 3)
                    sep = torch.norm(pads[0] - pads[1]).item()
                    mid = pads.mean(dim=0)
                    cube_to_mid = torch.norm(obj.data.root_pos_w[0] - mid).item()
                    print(f"           pad gap = {sep*1000:5.1f} mm | cube-to-pad-centre = {cube_to_mid*1000:5.1f} mm")

    # final verdict
    if grasp_point is not None:
        cz = obj.data.root_pos_w[0, 2].item()
        gz = grasp_point[2].item()
        print("\n================= GRASP HOLD RESULT =================")
        if cz > gz - 0.05:
            print(f" cube stayed at z={cz:+.3f} (pad {gz:+.3f})  ->  GRIP HOLDS ✅")
        else:
            print(f" cube fell to z={cz:+.3f} (pad {gz:+.3f})  ->  GRIP TOO WEAK ❌")
        print("====================================================\n")

    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
